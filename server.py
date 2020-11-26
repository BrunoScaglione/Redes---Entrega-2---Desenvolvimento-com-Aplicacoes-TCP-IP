import asyncio
import websockets
import time
import shlex
import socket
from uuid import getnode as get_mac


class Servidor:
  def __init__(self):
    self.conectados = []
  
  async def conecta(self, websocket, path):
    cliente = Cliente(self, websocket, path)
    if cliente not in self.conectados:
      self.conectados.append(cliente)
      print("Novo cliente conectado")            
    await cliente.gerencia()

  def desconecta(self, cliente):
    if cliente in self.conectados:
      self.conectados.remove(cliente)
    print("Cliente {0} desconectado".format(cliente.nome))            

  async def envia_a_todos(self, origem, mensagem, sistema=False):
    print("Enviando a todos")
    for cliente in self.conectados:
      if (origem != cliente and cliente.conectado):
        if sistema == True:
          print("Enviando de Sistema para <{0}>: {1}".format(cliente.nome, mensagem))
          await cliente.envia("Sistema >> {0}".format(mensagem))
        else:
          print("Enviando de <{0}> para <{1}>: {2}".format(origem.nome, cliente.nome, mensagem))
          await cliente.envia("{0} >> {1}".format(origem.nome, mensagem))

  async def envia_a_destinatario(self, origem, mensagem, destinatario):        
    for cliente in self.conectados:            
      if cliente.nome == destinatario and origem != cliente and cliente.conectado:
        print("Enviando de <{0}> para <{1}>: {2}".format(origem.nome, cliente.nome, mensagem))
        await cliente.envia("PRIVADO de {0} >> {1}".format(origem.nome, mensagem))
        return True
    return False

  def verifica_nome(self, nome):
    for cliente in self.conectados:
      if cliente.nome == nome:
        return False
    return True

#####################

class Cliente:    
  def __init__(self, servidor, websocket, path):
    self.cliente = websocket
    self.servidor = servidor
    self.nome = None        
  
  def conectado(self):
    return self.cliente.open

  async def gerencia(self):
    try:
      msg_inicial = """
        Bem vindo ao Chat, para comecar a interagir voce precisa se identificar.
        Comandos:\n
        Identificacao (seu nome no chat) => [/nome SeuNome] |
        Mensagem publica => [mensagem] |
        Mensagem privada => [/apenas destinatario mensagem] 
      """
      await self.envia(msg_inicial)
      while True:
        mensagem = await self.recebe()
        if mensagem:
          print("{0} < {1}".format(self.nome, mensagem))
          await self.processa_comandos(mensagem)                                            
        else:
          break
    except Exception:
      print("Erro")
      raise        
    finally:
      self.servidor.desconecta(self)

  async def envia(self, mensagem):
    await self.cliente.send(mensagem)

  async def recebe(self):
    mensagem = await self.cliente.recv()
    return mensagem

  async def processa_comandos(self, mensagem):        
    if mensagem.strip().startswith("/"):
      comandos = shlex.split(mensagem.strip()[1:])
      if len(comandos)==0:
        await self.envia("Comando vazio")
        return
      print(comandos)
      comando = comandos[0].lower()            
      if comando == "nome":
        await self.altera_nome(comandos)
      elif comando == "apenas":
        if self.nome:
          await self.apenas_para(comandos)
        else:
          await self.envia("Você precisa se identificar primeiro. Use o comando /nome SeuNome")
      else:
        await self.envia("Comando desconhecido")
    else:
      if self.nome:
        await self.servidor.envia_a_todos(self, mensagem)
      else:
        await self.envia("Você precisa se identificar primeiro. Use o comando /nome SeuNome")

  async def altera_nome(self, comandos):                
    if len(comandos)>1 and self.servidor.verifica_nome(comandos[1]):
      self.nome = comandos[1]
      await self.envia("Nome alterado com sucesso para {0}".format(self.nome))
      # envia mensagem a todos, avisando que esse cliente esta conectado
      await self.servidor.envia_a_todos(self, "Cliente {0} entrou no Chat".format(self.nome), sistema=True)
    else:
      await self.envia("Nome em uso ou inválido. Escolha um outro.")

  async def apenas_para(self, comandos):
    if len(comandos) <= 2:
      await self.envia("Comando incorreto. /apenas Destinatário mensagem")
      return
    destinatario = comandos[1]
    mensagem = " ".join(comandos[2:])
    enviado = await self.servidor.envia_a_destinatario(self, mensagem, destinatario)
    if not enviado:
      await self.envia("Destinatário {0} não encontrado. Mensagem não enviada.".format(destinatario))

##########################

print('hostname:', socket.gethostname())
print('host:', socket.gethostbyname(socket.gethostname()))
print('MAC adress:', get_mac())

servidor = Servidor()
loop = asyncio.get_event_loop()

start_server = websockets.serve(servidor.conecta, 'localhost', 8765)

loop.run_until_complete(start_server)
loop.run_forever()

