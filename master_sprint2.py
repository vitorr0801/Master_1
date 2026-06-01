import socket
import threading
import json
import queue

HOST = "10.62.217.31"
PORT = 5000

task_queue = queue.Queue()
running_tasks = {}
lock = threading.Lock()

task_queue.put({"user": "Michel"})
task_queue.put({"user": "Julia"})
task_queue.put({"user": "Carlos"})
task_queue.put({"user": "Lucas"})
task_queue.put({"user": "Ana paula"})
task_queue.put({"user": "Marivaldo"})
task_queue.put({"user": "Murilo"})
task_queue.put({"user": "Teu"})
task_queue.put({"user": "Pedro"})



def handle_client(conn, addr):

    print(f"[+] Worker conectado: {addr}")

    worker_uuid = None
    buffer = ""

    try:

        while True:

            data = conn.recv(1024)

            if not data:
                raise ConnectionError("Worker desconectado")

            buffer += data.decode()

            while "\n" in buffer:

                message, buffer = buffer.split("\n", 1)

                if not message.strip():
                    continue

                try:

                    payload = json.loads(message)

                    print(f"[MASTER] Recebido: {payload}")

                    # ==========================
                    # WORKER PEDINDO TAREFA
                    # ==========================
                    if payload.get("WORKER") == "ALIVE":

                        worker_uuid = payload.get("UUID")

                        with lock:

                            if not task_queue.empty():

                                task = task_queue.get()

                                running_tasks[worker_uuid] = task

                                print(
                                    f"[MASTER] Enviando {task} "
                                    f"para {worker_uuid}"
                                )

                                response = {
                                    "TASK": "QUERY",
                                    "USER": task["user"]
                                }

                            else:

                                response = {
                                    "TASK": "NO_TASK"
                                }

                        conn.sendall(
                            (json.dumps(response) + "\n").encode()
                        )

                    # ==========================
                    # TAREFA FINALIZADA
                    # ==========================
                    elif payload.get("STATUS") in ["OK", "NOK"]:

                        worker_uuid = payload.get("UUID")

                        with lock:

                            if worker_uuid in running_tasks:

                                task = running_tasks.pop(
                                    worker_uuid
                                )

                                print(
                                    f"[MASTER] "
                                    f"Tarefa concluída: {task}"
                                )

                        conn.sendall(
                            (
                                json.dumps(
                                    {"STATUS": "ACK"}
                                ) + "\n"
                            ).encode()
                        )

                except json.JSONDecodeError:

                    print(
                        f"[MASTER] JSON inválido: "
                        f"{message}"
                    )

    except Exception as e:

        print(
            f"[MASTER] Worker "
            f"{worker_uuid} desconectado: {e}"
        )

    finally:

        with lock:

            if (
                worker_uuid
                and worker_uuid in running_tasks
            ):

                task = running_tasks.pop(
                    worker_uuid
                )

                task_queue.put(task)

                print(
                    f"[MASTER] Tarefa "
                    f"recolocada na fila: {task}"
                )

                print(
                    f"[MASTER] Fila atual: "
                    f"{task_queue.qsize()} tarefas"
                )

        conn.close()

        print(
            f"[-] Conexão encerrada: {addr}"
        )


def start_server():

    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server.bind((HOST, PORT))
    server.listen()

    print(
        f"[MASTER] Escutando em "
        f"{HOST}:{PORT}"
    )

    while True:

        conn, addr = server.accept()

        thread = threading.Thread(
            target=handle_client,
            args=(conn, addr),
            daemon=True
        )

        thread.start()


if __name__ == "__main__":
    start_server()