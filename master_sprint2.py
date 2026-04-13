import socket
import threading
import json

HOST = "0.0.0.0"  # Escuta em todas as interfaces
PORT = 5000

# Simulação de uma fila de tarefas pendentes (Backlog)
task_queue = [
    {"user": "Michel"},
    {"user": "Julia"},
    {"user": "Carlos"}
]

def handle_client(conn, addr):
    print(f"[+] Conexão ativa: {addr}")
    buffer = ""

    try:
        while True:
            data = conn.recv(1024).decode()
            if not data: break
            
            buffer += data
            while "\n" in buffer:
                message, buffer = buffer.split("\n", 1)
                try:
                    payload = json.loads(message)
                    print(f"[MASTER] Recebido de {addr}: {payload}")

                    
                    if payload.get("WORKER") == "ALIVE":
                        if task_queue:
                            task = task_queue.pop(0) 
                            response = {"TASK": "QUERY", "USER": task["user"]}
                            print(f"[MASTER] Enviando tarefa para {payload.get('WORKER_UUID')}")
                        else:
                            response = {"TASK": "NO_TASK"}
                        
                        conn.sendall((json.dumps(response) + "\n").encode())

                    
                    elif payload.get("STATUS") in ["OK", "NOK"]:
                        worker_id = payload.get("WORKER_UUID")
                        print(f"[LOG] Worker {worker_id} concluiu {payload.get('TASK')} com status {payload.get('STATUS')}")
                        
                        response = {"STATUS": "ACK", "WORKER_UUID": worker_id}
                        conn.sendall((json.dumps(response) + "\n").encode())

                except json.JSONDecodeError:
                    print("[ERRO] JSON inválido")
    except Exception as e:
        print(f"[ERRO] {e}")
    finally:
        conn.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[MASTER] Aguardando Workers em {PORT}...")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    start_server()
