import socket
import json
import time
import random

HOST = "10.80.5.29"  # IP do Master
PORT = 5000
WORKER_UUID = "W-PYTHON-01"
ORIGINAL_MASTER = "Master_A"


def process_task(user):
    """Simula processamento da tarefa"""
    print(f"[WORKER] Processando usuário: {user}...")

    time.sleep(random.randint(2, 5))  # Simula processamento
    return "OK" if random.random() > 0.1 else "NOK"


def start_worker():
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((HOST, PORT))
            print("[WORKER] Conectado ao Master.")

            buffer = ""

            while True:
                # 1. Envia heartbeat (pedido de tarefa)
                presentation = {
                    "WORKER": "ALIVE",
                    "WORKER_UUID": WORKER_UUID
                }

                sock.sendall((json.dumps(presentation) + "\n").encode())

                # 2. Recebe resposta do master (com buffer)
                data = sock.recv(1024).decode()

                if not data:
                    print("[WORKER] Conexão fechada pelo servidor.")
                    break

                buffer += data

                while "\n" in buffer:
                    message, buffer = buffer.split("\n", 1)

                    try:
                        response = json.loads(message)

                        # 3. Recebe tarefa
                        if response.get("TASK") == "QUERY":
                            user = response.get("USER")

                            status = process_task(user)

                            report = {
                                "STATUS": status,
                                "TASK": "QUERY",
                                "WORKER_UUID": WORKER_UUID
                            }

                            sock.sendall((json.dumps(report) + "\n").encode())

                            # 4. Aguarda ACK
                            ack_data = sock.recv(1024).decode()
                            if ack_data:
                                print(f"[WORKER] ACK do Master: {ack_data.strip()}")

                        # Sem tarefas disponíveis
                        elif response.get("TASK") == "NO_TASK":
                            print("[WORKER] Sem tarefas. Aguardando 10s...")
                            time.sleep(10)

                    except json.JSONDecodeError:
                        print("[ERRO] JSON inválido recebido")

                time.sleep(2)  # pequena pausa entre ciclos

        except Exception as e:
            print(f"[ERRO] {e}. Reconectando em 5s...")
            time.sleep(5)


if __name__ == "__main__":
    start_worker()