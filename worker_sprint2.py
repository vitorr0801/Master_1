import socket
import json
import time
import random

HOST = "10.80.5.29" # IP do seu Master
PORT = 5000
WORKER_UUID = "W-PYTHON-01"
ORIGINAL_MASTER = "Master_A" # Caso seja emprestado, mudaria este campo

def process_task(task_name):
    """Simula o processamento da TAREFA 03"""
    print(f"[WORKER] Processando: {task_name}...")
    time.sleep(random.randint(2, 5)) # Simula tempo de cálculo/sleep
    return "OK" if random.random() > 0.1 else "NOK" # 90% de chance de sucesso

def start_worker():
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5) # Timeout de 5s conforme Nota de Implementação 3
            sock.connect((HOST, PORT))
            print("[WORKER] Conectado ao Master.")

            while True:
                # 1. Apresentação (Handshake)
                # O SERVER_UUID é enviado apenas se o worker for de outro nó (emprestado)
                presentation = {
                    "WORKER": "ALIVE",
                    "WORKER_UUID": WORKER_UUID
                    # "SERVER_UUID": ORIGINAL_MASTER # Ative se for simular CT02
                }
                sock.sendall((json.dumps(presentation) + "\n").encode())
                
                # 2. Receber Resposta do Master
                data = sock.recv(1024).decode()
                if not data: break
                
                # Tratamento de buffer simples para resposta única
                response = json.loads(data.split("\n")[0])
                
                if response.get("TASK") == "QUERY":
                    # 3. Simulação de Processamento e Reporte
                    status = process_task(response["TASK"])
                    
                    report = {
                        "STATUS": status,
                        "TASK": "QUERY",
                        "WORKER_UUID": WORKER_UUID
                    }
                    sock.sendall((json.dumps(report) + "\n").encode())
                    
                    # 4. Aguardar ACK Final
                    ack_data = sock.recv(1024).decode()
                    if ack_data:
                        print(f"[WORKER] Recebido do Master: {ack_data.strip()}")
                
                elif response.get("TASK") == "NO_TASK":
                    print("[WORKER] Sem tarefas. Aguardando 10s...")
                    time.sleep(10)
                
                time.sleep(2) # Pequena pausa entre ciclos

        except Exception as e:
            print(f"[ERRO] {e}. Reconectando em 5s...")
            time.sleep(5)

if __name__ == "__main__":
    start_worker()
