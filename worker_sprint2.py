import socket
import json
import time
import random

HOST = "10.62.217.31"
PORT = 5000

WORKER_UUID = "W-PYTHON-01"


def process_task(user):

    print(f"[WORKER] Processando usuário: {user}")

    tempo = random.randint(3, 8)
    time.sleep(tempo)

    print(f"[WORKER] Usuário {user} concluído")


def start_worker():

    while True:

        try:

            sock = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )

            sock.connect((HOST, PORT))

            print("[WORKER] Conectado ao master")

            buffer = ""

            while True:

                # Solicita trabalho
                request = {
                    "WORKER": "ALIVE",
                    "UUID": WORKER_UUID
                }

                sock.sendall(
                    (json.dumps(request) + "\n").encode()
                )

                data = sock.recv(1024)

                if not data:
                    raise ConnectionError(
                        "Master desconectado"
                    )

                buffer += data.decode()

                while "\n" in buffer:

                    message, buffer = buffer.split(
                        "\n",
                        1
                    )

                    if not message.strip():
                        continue

                    payload = json.loads(message)

                    # Ignora ACK
                    if payload.get("STATUS") == "ACK":
                        continue

                    task = payload.get("TASK")

                    # Sem tarefas disponíveis
                    if task == "NO_TASK":

                        print(
                            "[WORKER] Sem tarefas"
                        )

                        time.sleep(5)
                        continue

                    # Executa tarefa
                    if task == "QUERY":

                        user = payload.get(
                            "USER"
                        )

                        process_task(user)

                        result = {
                            "UUID": WORKER_UUID,
                            "STATUS": "OK",
                            "USER": user
                        }

                        sock.sendall(
                            (
                                json.dumps(result)
                                + "\n"
                            ).encode()
                        )

                        # Aguarda ACK
                        ack_data = sock.recv(
                            1024
                        ).decode()

                        if ack_data:

                            try:

                                ack = json.loads(
                                    ack_data.strip()
                                )

                                if (
                                    ack.get(
                                        "STATUS"
                                    )
                                    == "ACK"
                                ):

                                    print(
                                        "[WORKER] "
                                        "ACK recebido"
                                    )

                            except Exception:
                                pass

                time.sleep(1)

        except Exception as e:

            print(
                f"[ERRO] {e}. "
                f"Reconectando em 5s..."
            )

            time.sleep(5)


if __name__ == "__main__":
    start_worker()