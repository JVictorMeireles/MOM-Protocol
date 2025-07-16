import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk
import stomp
import threading
import json

# Configurações
BROKER = 'localhost'
PORTA = 61613
USUARIO = 'admin'
SENHA = 'admin'

class ChatListener(stomp.ConnectionListener):
  def __init__(self, nome, display_callback):
    self.nome = nome
    self.display_callback = display_callback

  def on_message(self, frame):
    try:
      dados = json.loads(frame.body)
      if "usuarios" in dados:
        self.display_callback({"tipo": "usuarios", "dados": dados["usuarios"]})
      else:
        self.display_callback(f"[RECEBIDO] {frame.body}")
    except:
      self.display_callback(f"[RECEBIDO] {frame.body}")

class ChatApp:
  def __init__(self, root, nome_usuario):
    self.topicos_disponiveis = []

    self.topico_ids = {}  # topico -> id
    self.root = root
    self.nome = nome_usuario
    self.root.title(f"Chat - {self.nome}")
    
    # Fila e tópico
    self.fila_privada = f"/queue/{self.nome}"
    self.topico_global = "/topic/chat.geral"
    
    # Interface
    self.frame_chat = tk.Frame(root)
    self.frame_opcoes = tk.Frame(root)
    self.frame_chat.pack(side=tk.LEFT)
    self.frame_opcoes.pack(padx=10)

    self.mensagens = scrolledtext.ScrolledText(self.frame_chat, wrap=tk.WORD, state='disabled', height=20)
    self.mensagens.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    self.topico_label = tk.Label(self.frame_opcoes, text="Selecionar tópico:")
    self.topico_label.pack()
    self.topico_var = tk.StringVar(value=self.topicos_disponiveis[0])
    self.topico_combo = ttk.Combobox(self.frame_opcoes, textvariable=self.topico_var, values=self.topicos_disponiveis, state='readonly')
    self.topico_combo.pack(fill=tk.X, padx=10)

    self.novo_topico_label = tk.Label(self.frame_opcoes, text="Novo tópico (nome simples):")
    self.novo_topico_label.pack()
    self.novo_topico_entry = tk.Entry(self.frame_opcoes)
    self.novo_topico_entry.pack(fill=tk.X, padx=10)

    self.frame_botoes = tk.Frame(self.frame_opcoes)
    self.frame_botoes.pack(pady=5)

    self.btn_add_topico = tk.Button(self.frame_botoes, text="Adicionar Tópico", command=self.adicionar_topico)
    self.btn_add_topico.pack(pady=5, side=tk.LEFT, padx=5)

    self.btn_remover_topico = tk.Button(self.frame_botoes, text="Remover Tópico", command=self.remover_topico)
    self.btn_remover_topico.pack(pady=5, side=tk.LEFT, padx=5)

    self.btn_verificar_filas = tk.Button(self.frame_botoes, text="Verificar Filas", command=self.listar_filas_com_mensagens)
    self.btn_verificar_filas.pack(pady=5, side=tk.LEFT, padx=5)

    self.btn_encerrar_privado = tk.Button(self.frame_botoes, text="Encerrar conversa privada", command=self.encerrar_conversa_privada)
    self.btn_encerrar_privado.pack(pady=5)

    self.frame_infos = tk.Frame(self.frame_opcoes)
    self.frame_usuarios = tk.Frame(self.frame_infos)
    self.frame_topicos = tk.Frame(self.frame_infos)
    self.frame_infos.pack(pady=5)
    self.frame_usuarios.pack(side=tk.LEFT)
    self.frame_topicos.pack(side=tk.RIGHT)

    self.lista_label = tk.Label(self.frame_topicos, text="Tópicos assinados:")
    self.lista_label.pack(side=tk.TOP)
    self.lista_topicos = tk.Listbox(self.frame_topicos, height=6)
    self.lista_topicos.pack(side=tk.BOTTOM)

    self.usuarios_label = tk.Label(self.frame_usuarios, text="Usuários online:")
    self.usuarios_label.pack(side=tk.TOP)
    self.lista_usuarios = tk.Listbox(self.frame_usuarios, height=6)
    self.lista_usuarios.pack(side=tk.BOTTOM)
    self.lista_usuarios.bind("<<ListboxSelect>>", self.selecionar_usuario)

    self.input_entry = tk.Entry(self.frame_chat)
    self.input_entry.pack(fill=tk.X, padx=10)
    self.input_entry.bind("<Return>", self.enviar_mensagem)

    self.enviar_btn = tk.Button(self.frame_chat, text="Enviar", command=self.enviar_mensagem)
    self.enviar_btn.pack(pady=5)

    # Conectar STOMP
    self.conn = stomp.Connection([(BROKER, PORTA)])
    self.conn.connect(USUARIO, SENHA, wait=True)
    self.conn.set_listener('', ChatListener(self.nome, self.exibir_mensagem))
    self.conn.subscribe(destination=self.fila_privada, id=1, ack='auto')
    self.conn.subscribe(destination="/topic/usuarios", id=9999, ack='auto')
    for i, topico in enumerate(self.topicos_disponiveis, start=100):
      self.conn.subscribe(destination=topico, id=i, ack='auto')
      self.topico_ids[topico] = i
    self.atualizar_lista_topicos()

    # Simulando usuários online (substitua com dados reais depois)
    self.atualizar_usuarios_online([self.nome])


    self.exibir_mensagem(f"Conectado como {self.nome}. Fila: {self.fila_privada}")

    self.destino_privado = None  # Armazena o nome de um usuário selecionado

  def exibir_mensagem(self, msg):
    if isinstance(msg, dict):
      if msg.get("tipo") == "usuarios":
        self.atualizar_usuarios_online(msg["dados"])
      return  # Não exibe no campo de mensagens
    self.mensagens.configure(state='normal')
    self.mensagens.insert(tk.END, msg + "\n")
    self.mensagens.configure(state='disabled')
    self.mensagens.see(tk.END)

  def enviar_mensagem(self, event=None):
    corpo = self.input_entry.get().strip()
    if not corpo:
      return

    if self.destino_privado:
      destino = f"/queue/{self.destino_privado}"
      self.conn.send(body=f"{self.nome} (privado): {corpo}", destination=destino)
      self.exibir_mensagem(f"[ENVIADO] para {self.destino_privado}: {corpo}")
    else:
      destino = self.topico_var.get()
      self.conn.send(body=f"{self.nome} (tópico): {corpo}", destination=destino)
      self.exibir_mensagem(f"[ENVIADO] para tópico {destino}: {corpo}")

    self.input_entry.delete(0, tk.END)

  def adicionar_topico(self):
    nome = self.novo_topico_entry.get().strip()

    if not nome:
      self.exibir_mensagem("[Erro] Nome do tópico vazio.")
      return

    topico_formatado = f"/topic/{nome}"

    if topico_formatado in self.topicos_disponiveis:
      self.exibir_mensagem("[Aviso] Tópico já existe.")
      return

    # Assinar o novo tópico
    novo_id = 100 + len(self.topicos_disponiveis)
    self.conn.subscribe(destination=topico_formatado, id=novo_id, ack='auto')
    self.topico_ids[topico_formatado] = novo_id

    # Adicionar ao menu
    self.topicos_disponiveis.append(topico_formatado)
    self.topico_combo['values'] = self.topicos_disponiveis
    self.topico_var.set(topico_formatado)  # Seleciona automaticamente
    self.exibir_mensagem(f"[Info] Novo tópico adicionado: {topico_formatado}")
    self.novo_topico_entry.delete(0, tk.END)

    self.atualizar_lista_topicos()

  def remover_topico(self):
    topico = self.topico_var.get()
    
    if topico not in self.topicos_disponiveis:
      self.exibir_mensagem("[Erro] Tópico não está na lista.")
      return

    if topico not in self.topico_ids:
      self.exibir_mensagem("[Erro] ID de assinatura do tópico não encontrado.")
      return

    if topico == "/topic/chat.geral":
      self.exibir_mensagem("[Aviso] O tópico geral não pode ser removido.")
      return


    # Cancelar a inscrição
    id_assinatura = self.topico_ids[topico]
    self.conn.unsubscribe(id=id_assinatura)

    # Remover da lista
    self.topicos_disponiveis.remove(topico)
    self.topico_combo['values'] = self.topicos_disponiveis
    self.topico_var.set(self.topicos_disponiveis[0] if self.topicos_disponiveis else "")
    del self.topico_ids[topico]

    self.exibir_mensagem(f"[Info] Desinscrito e removido: {topico}")

    self.atualizar_lista_topicos()

  def atualizar_lista_topicos(self):
    self.lista_topicos.delete(0, tk.END)
    for topico in self.topicos_disponiveis:
      self.lista_topicos.insert(tk.END, topico)

  def selecionar_usuario(self, event):
    selecao = self.lista_usuarios.curselection()
    if selecao:
      usuario = self.lista_usuarios.get(selecao[0])
      self.destino_privado = usuario
      self.exibir_mensagem(f"[Info] Conversa direcionada a: {usuario}")

  def listar_filas_com_mensagens(self):
    import requests
    from requests.auth import HTTPBasicAuth

    filas = [f"/queue/{usuario}" for usuario in self.lista_usuarios.get(0, tk.END)]

    self.exibir_mensagem("Quantidade de mensagens nas filas:")

    for fila in filas:
      nome_fila = fila.split("/")[-1]
      url = f"http://localhost:8161/api/jolokia/read/org.apache.activemq:type=Broker,brokerName=localhost,destinationType=Queue,destinationName={nome_fila}/QueueSize"

      try:
        response = requests.get(url, auth=HTTPBasicAuth('admin', 'admin'))
        if response.status_code == 200:
          dados = response.json()
          qtd = dados.get("value", 0)
          self.exibir_mensagem(f"{fila}: {qtd} mensagens")
        else:
          self.exibir_mensagem(f"{fila}: [Erro ao consultar]")
      except Exception as e:
        self.exibir_mensagem(f"{fila}: [Exceção: {e}]")

  def atualizar_usuarios_online(self, usuarios):
    self.lista_usuarios.delete(0, tk.END)
    for usuario in usuarios:
      if usuario != self.nome:  # Evitar mostrar o próprio nome
        self.lista_usuarios.insert(tk.END, usuario)

  def encerrar_conversa_privada(self):
    self.destino_privado = None
    self.exibir_mensagem("[Info] Conversa privada encerrada. Mensagens irão para o tópico selecionado.")

  def logout(self):
    try:
      # Enviar uma mensagem especial de logout (opcional)
      mensagem_logout = json.dumps({
        "acao": "logout",
        "usuario": self.nome
      })
      self.conn.send(body=mensagem_logout, destination="/queue/gerenciador")

      self.exibir_mensagem(f"[Sistema] Logout enviado para o gerenciador.")
    except Exception as e:
      print(f"Erro ao tentar enviar logout: {e}")

    try:
      self.conn.disconnect()
    except Exception as e:
      print(f"Erro ao desconectar: {e}")

    # Encerra a interface
    self.root.destroy()

def iniciar_interface():
  nome = input("Digite seu nome de usuário: ").strip()

  # Conectar temporariamente só para registrar o nome
  temp_conn = stomp.Connection([(BROKER, PORTA)])
  evento_resposta = threading.Event()
  resultado = {}

  class RegistroListener(stomp.ConnectionListener):
    def on_message(self, frame):
      try:
        dados = json.loads(frame.body)
        if "status" in dados and dados.get("usuario") == nome:
          resultado['status'] = dados.get("status")
          evento_resposta.set()
        elif "usuarios" in dados:
          resultado['usuarios'] = dados["usuarios"]
      except Exception as e:
        print(f"[Erro no listener de registro] {e}")

  temp_conn.set_listener('', RegistroListener())
  temp_conn.connect(USUARIO, SENHA, wait=True)
  temp_conn.subscribe(destination=f"/queue/registro.{nome}", id=999, ack='auto')

  # Envia mensagem de registro
  msg = {
    "acao": "registro",
    "usuario": nome
  }
  temp_conn.send(body=json.dumps(msg), destination="/queue/gerenciador")

  # Espera resposta por até 5 segundos
  if not evento_resposta.wait(5):
    print("[Aviso]  Nenhuma resposta do gerenciador. Encerrando.")
    temp_conn.disconnect()
    return

  if resultado.get("status") == "rejeitado":
    print(f"[Erro] Nome de usuário '{nome}' já está em uso. Escolha outro.")
    temp_conn.disconnect()
    return

  print(f"[Mensagem] Nome aceito: {nome}")
  temp_conn.disconnect()

  # Iniciar interface gráfica
  root = tk.Tk()
  usuarios = resultado.get("usuarios", [])
  app = ChatApp(root, nome)
  app.atualizar_usuarios_online(usuarios)
  root.protocol("WM_DELETE_WINDOW", app.logout)
  root.mainloop()


if __name__ == "__main__":
  threading.Thread(target=iniciar_interface).start()
