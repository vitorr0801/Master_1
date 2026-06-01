import socket
import json
import time
import random

HOST = "10.62.217.31"
PORT = 5000

WORKER_UUID = "W-PYTHON-01"


def process_task(user):
    """
    Simula processamento da tarefa
    """

    print(f"[WORKER] Processando usuário: {user}")

    tempo = random.randint(3, 8)
    time.sleep(tempo)

    print(f"[WORKER] Usuário {user} concluído")


def start_worker():

    while True:

        try:

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((HOST, PORT))

            print("[WORKER] Conectado ao master")

            buffer = ""

            while True:

                request = {
                    "WORKER": "ALIVE",
                    "UUID": WORKER_UUID
                }

                sock.sendall(
                    (json.dumps(request) + "\n").encode()
                )

                data = sock.recv(1024).decode()

                if not data:
                    raise ConnectionError(
                        "Conexão encerrada pelo master"
                    )

                buffer += data

                while "\n" in buffer:

                    message, buffer = buffer.split("\n", 1)

                    payload = json.loads(message)

                    task = payload.get("TASK")

                    if task == "NO_TASK":

                        print("[WORKER] Sem tarefas")

                        time.sleep(5)
                        continue

                    if task == "QUERY":

                        user = payload.get("USER")

                        process_task(user)

                        result = {
                            "UUID": WORKER_UUID,
                            "STATUS": "OK",
                            "USER": user
                        }

                        sock.sendall(
                            (json.dumps(result) + "\n").encode()
                        )

                        print(
                            f"[WORKER] Resultado enviado para {user}"
                        )

                time.sleep(1)

        except Exception as e:

            print(
                f"[ERRO] {e}. Reconectando em 5 segundos..."
            )

            time.sleep(5)


if __name__ == "__main__":
    start_worker()