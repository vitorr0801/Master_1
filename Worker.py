import socket
import json
import time
import uuid
import threading
import logging
import random

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuração
WORKER_ID = f"W-{uuid.uuid4().hex[:8]}"
HOST = "127.0.0.1"
PORT = 5000
INTERVAL = 10  # segundos
ORIGINAL_MASTER_ADDRESS = f"{HOST}:{PORT}"
REQUEST_TIMEOUT = 5

class Worker:
    def __init__(self, worker_id=None, master_host=None, master_port=None, original_master=None):
        self.worker_id = worker_id or WORKER_ID
        self.master_host = master_host or HOST
        self.master_port = master_port or PORT
        self.original_master_address = original_master or ORIGINAL_MASTER_ADDRESS
        self.socket = None
        self.buffer = ""
        self.is_borrowed = original_master is not None
        self.is_processing_task = False
    
    def connect_to_master(self):
        """Conecta ao Master atual"""
        try:
            logger.info(f"[WORKER_{self.worker_id}] Conectando a {self.master_host}:{self.master_port}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(REQUEST_TIMEOUT)
            self.socket.connect((self.master_host, self.master_port))
            logger.info(f"[WORKER_{self.worker_id}] Conectado!")
            return True
        
        except Exception as e:
            logger.error(f"[WORKER_{self.worker_id}] Erro ao conectar: {e}")
            return False
    
    def send_message(self, payload):
        """Envia mensagem para o Master"""
        try:
            msg = json.dumps(payload) + "\n"
            self.socket.sendall(msg.encode())
            logger.debug(f"[WORKER_{self.worker_id}] Enviado: {payload}")
            return True
        
        except Exception as e:
            logger.error(f"[WORKER_{self.worker_id}] Erro ao enviar: {e}")
            return False
    
    def receive_message(self):
        """Recebe mensagem do Master"""
        try:
            while True:
                data = self.socket.recv(1024).decode()
                
                if not data:
                    logger.warning(f"[WORKER_{self.worker_id}] Conexão fechada pelo Master")
                    return None
                
                self.buffer += data
                
                while "\n" in self.buffer:
                    message, self.buffer = self.buffer.split("\n", 1)
                    
                    try:
                        payload = json.loads(message)
                        return payload
                    
                    except json.JSONDecodeError:
                        logger.error(f"[WORKER_{self.worker_id}] JSON inválido: {message}")
        
        except socket.timeout:
            logger.warning(f"[WORKER_{self.worker_id}] Timeout aguardando resposta")
            return None
        
        except Exception as e:
            logger.error(f"[WORKER_{self.worker_id}] Erro ao receber: {e}")
            return None
    
    def handle_heartbeat(self):
        """Processa resposta de heartbeat"""
        response = self.receive_message()
        
        if response and response.get("TASK") == "HEARTBEAT" and response.get("RESPONSE") == "ALIVE":
            logger.info(f"[WORKER_{self.worker_id}] Heartbeat OK - Master está ativo")
            return True
        
        logger.warning(f"[WORKER_{self.worker_id}] Heartbeat falhou")
        return False
    
    def request_work(self):
        """Solicita trabalho ao Master"""
        payload = {
            "WORKER": "ALIVE",
            "WORKER_UUID": self.worker_id
        }
        
        # Adiciona SERVER_UUID se for worker emprestado
        if self.is_borrowed:
            payload["SERVER_UUID"] = self.original_master_address
        
        logger.info(f"[WORKER_{self.worker_id}] Solicitando trabalho...")
        
        if not self.send_message(payload):
            return None
        
        return self.receive_message()
    
    def process_task(self, task):
        """Processa uma tarefa"""
        if task.get("TASK") == "NO_TASK":
            logger.info(f"[WORKER_{self.worker_id}] Nenhuma tarefa disponível")
            return True
        
        if task.get("TASK") == "QUERY":
            user = task.get("USER", "Unknown")
            logger.info(f"[WORKER_{self.worker_id}] Recebeu tarefa para {user}")
            
            self.is_processing_task = True
            
            # Simula processamento
            processing_time = random.uniform(1, 3)
            logger.info(f"[WORKER_{self.worker_id}] Processando por {processing_time:.2f}s...")
            time.sleep(processing_time)
            
            # Decide sucesso ou falha (90% sucesso)
            status = "OK" if random.random() < 0.9 else "NOK"
            
            # Reporta resultado
            result = {
                "STATUS": status,
                "TASK": "QUERY",
                "WORKER_UUID": self.worker_id
            }
            
            logger.info(f"[WORKER_{self.worker_id}] Enviando resultado: {status}")
            
            if not self.send_message(result):
                self.is_processing_task = False
                return False
            
            # Aguarda ACK
            ack = self.receive_message()
            
            if ack and ack.get("STATUS") == "ACK":
                logger.info(f"[WORKER_{self.worker_id}] Tarefa completada com ACK")
                self.is_processing_task = False
                return True
            
            self.is_processing_task = False
            return False
        
        logger.warning(f"[WORKER_{self.worker_id}] Tipo de tarefa desconhecido")
        return False
    
    def handle_command_redirect(self, command):
        """Processa comando de redirecionamento para outro Master"""
        new_master_address = command.get("payload", {}).get("new_master_address")
        
        if not new_master_address:
            logger.error(f"[WORKER_{self.worker_id}] Comando de redirecionamento sem endereço")
            return False
        
        logger.info(f"[WORKER_{self.worker_id}] Redirecionamento para {new_master_address}")
        
        # Encerra conexão atual
        try:
            self.socket.close()
        except:
            pass
        
        # Extrai novo host e porta
        try:
            new_host, new_port = new_master_address.split(":")
            new_port = int(new_port)
        
        except:
            logger.error(f"[WORKER_{self.worker_id}] Endereço inválido: {new_master_address}")
            return False
        
        # Conecta ao novo Master
        self.master_host = new_host
        self.master_port = new_port
        self.is_borrowed = True
        
        # Aguarda um pouco antes de reconectar
        time.sleep(1)
        
        if not self.connect_to_master():
            return False
        
        # Registra como worker emprestado
        register_msg = {
            "type": "register_temporary_worker",
            "request_id": str(uuid.uuid4()),
            "payload": {
                "worker_id": self.worker_id,
                "original_master_address": self.original_master_address
            }
        }
        
        if not self.send_message(register_msg):
            return False
        
        ack = self.receive_message()
        logger.info(f"[WORKER_{self.worker_id}] Registrado como worker emprestado")
        
        return True
    
    def handle_command_release(self, command):
        """Processa comando de liberação para voltar ao Master original"""
        original_master = command.get("payload", {}).get("original_master_address")
        
        logger.info(f"[WORKER_{self.worker_id}] Liberado, retornando para {original_master}")
        
        # Encerra conexão atual
        try:
            self.socket.close()
        except:
            pass
        
        # Extrai host e porta original
        try:
            original_host, original_port = original_master.split(":")
            original_port = int(original_port)
        
        except:
            logger.error(f"[WORKER_{self.worker_id}] Endereço original inválido")
            return False
        
        # Restaura Master original
        self.master_host = original_host
        self.master_port = original_port
        self.is_borrowed = False
        
        time.sleep(1)
        
        return self.connect_to_master()
    
    def run(self):
        """Loop principal do Worker"""
        while True:
            try:
                if not self.socket:
                    if not self.connect_to_master():
                        logger.warning(f"[WORKER_{self.worker_id}] Reconectando em 5s...")
                        time.sleep(5)
                        continue
                
                # Solicita trabalho
                task = self.request_work()
                
                if not task:
                    logger.warning(f"[WORKER_{self.worker_id}] Reconectando em 5s...")
                    self.socket = None
                    time.sleep(5)
                    continue
                
                # Verifica se é comando especial
                msg_type = task.get("type")
                
                if msg_type == "command_redirect":
                    if not self.handle_command_redirect(task):
                        logger.error(f"[WORKER_{self.worker_id}] Falha ao processar redirect")
                        self.socket = None
                    continue
                
                elif msg_type == "command_release":
                    if not self.handle_command_release(task):
                        logger.error(f"[WORKER_{self.worker_id}] Falha ao processar release")
                        self.socket = None
                    continue
                
                # Processa tarefa normal
                if not self.process_task(task):
                    logger.warning(f"[WORKER_{self.worker_id}] Erro ao processar tarefa, reconectando...")
                    self.socket = None
                
                time.sleep(1)
            
            except Exception as e:
                logger.error(f"[WORKER_{self.worker_id}] Erro: {e}")
                self.socket = None
                time.sleep(5)

def main():
    """Inicia um Worker"""
    logger.info(f"[INICIANDO WORKER] {WORKER_ID}")
    
    worker = Worker()
    
    try:
        worker.run()
    
    except KeyboardInterrupt:
        logger.info(f"[WORKER_{WORKER_ID}] Interrompido pelo usuário")
    
    finally:
        try:
            if worker.socket:
                worker.socket.close()
        except:
            pass

if __name__ == "__main__":
    main()


if __name__ == "__main__":
    start_worker()