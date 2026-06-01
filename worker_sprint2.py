import socket
import json
import time
import random

HOST = "10.62.217.31"
PORT = 5000

WORKER_UUID = "W-PYTHON-01"


# =========================
# EXECUÇÃO DE TAREFAS
# =========================
def execute_task(task, payload):
    print(f"[WORKER] Executando: {task}")

    time.sleep(random.uniform(1, 3))  # simula processamento

    # tarefas compatíveis com seu master
    if task == "PING":
        return {"TASK": "PING", "RESPONSE": "PONG", "WORKER": WORKER_UUID}

    elif task == "GET_TIME":
        return {"TASK": "GET_TIME", "TIME": time.ctime(), "WORKER": WORKER_UUID}

    elif task == "ECHO":
        return {
            "TASK": "ECHO",
            "MESSAGE": payload.get("MESSAGE", ""),
            "WORKER": WORKER_UUID
        }

    elif task == "GET_STATUS":
        return {
            "TASK": "GET_STATUS",
            "STATUS": "RUNNING",
            "WORKER": WORKER_UUID
        }

    elif task == "HEARTBEAT":
        return {
            "TASK": "HEARTBEAT",
            "RESPONSE": "ALIVE",
            "WORKER": WORKER_UUID
        }

    else:
        return {
            "TASK": task,
            "STATUS": "ERROR",
            "MESSAGE": "TASK não suportada pelo worker",
            "WORKER": WORKER_UUID
        }


# =========================
# WORKER LOOP
# =========================
def start_worker():
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((HOST, PORT))

            print("[WORKER] Conectado ao master")

            buffer = ""

            while True:

                # =========================
                # HEARTBEAT PADRÃO
                # =========================
                heartbeat = {
                    "TASK": "HEARTBEAT",
                    "WORKER_UUID": WORKER_UUID
                }

                sock.sendall((json.dumps(heartbeat) + "\n").encode())

                data = sock.recv(1024).decode()

                if not data:
                    print("[WORKER] Conexão encerrada pelo master")
                    break

                buffer += data

                while "\n" in buffer:
                    message, buffer = buffer.split("\n", 1)

                    try:
                        payload = json.loads(message)

                        task = payload.get("TASK")

                        # ignora respostas de controle
                        if task == "HEARTBEAT":
                            continue

                        # executa tarefa recebida
                        response = execute_task(task, payload)

                        # envia resposta ao master
                        sock.sendall((json.dumps(response) + "\n").encode())

                        print(f"[WORKER] Enviado resultado de {task}")

                    except json.JSONDecodeError:
                        print("[ERRO] JSON inválido recebido")

                time.sleep(2)

        except Exception as e:
            print(f"[ERRO] {e} - reconectando em 5s")
            time.sleep(5)


if __name__ == "__main__":
    start_worker()