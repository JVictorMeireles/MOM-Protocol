import stomp
import json

BROKER = 'localhost'
PORTA = 61613
USUARIO = 'admin'
SENHA = 'admin'

class GerenciadorUsuarios(stomp.ConnectionListener):
  def __init__(self):
    self.usuarios_online = set()
    self.conn = stomp.Connection([(BROKER, PORTA)])
    self.conn.set_listener('', self)
    self.conn.connect(USUARIO, SENHA, wait=True)
    self.conn.subscribe(destination='/queue/gerenciador', id=1, ack='auto')
    print("Gerenciador iniciado. Aguardando mensagens...")

  def on_message(self, frame):
    try:
      msg = json.loads(frame.body)
      acao = msg.get('acao')
      usuario = msg.get('usuario')

      if acao == "registro":
        if usuario in self.usuarios_online:
          # Rejeita usuário duplicado
          self.conn.send(
              body=json.dumps({"status": "rejeitado", "usuario": usuario}),
              destination=f"/queue/retorno.{usuario}"
          )
          print(f"[REJEITADO] Usuário duplicado: {usuario}")
        else:
          self.usuarios_online.add(usuario)
          self.conn.send(
              body=json.dumps({"status": "aceito", "usuario": usuario}),
              destination=f"/queue/retorno.{usuario}"
          )
          print(f"[ACEITO] Novo usuário: {usuario}")

      elif acao == "logout":
        if usuario in self.usuarios_online:
          self.usuarios_online.remove(usuario)
          print(f"[LOGOUT] {usuario} desconectou.")
    except Exception as e:
      print(f"[ERRO] Falha ao processar mensagem: {e}")

if __name__ == "__main__":
  GerenciadorUsuarios()
  import time
  while True:
    time.sleep(1)
