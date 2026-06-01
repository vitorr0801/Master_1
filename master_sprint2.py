import socket
import threading
import json
import queue

HOST = "0.0.0.0"
PORT = 5000

# Fila principal
task_queue = queue.Queue()

# Tarefas em execução
running_tasks = {}

# Lock para acesso concorrente
lock = threading.Lock()

# Inicializa tarefas
task_queue.put({"user": "Michel"})
task_queue.put({"user": "Julia"})
task_queue.put({"user": "Carlos"})


def handle_client(conn, addr):
    print(f"[+] Conexão ativa: {addr}")

    buffer = ""
    worker_uuid = None

    try:
        while True:
            data = conn.recv(1024).decode()

            if not data:
                raise ConnectionError("Worker desconectado")

            buffer += data

            while "\n" in buffer:
                message, buffer = buffer.split("\n", 1)

                try:
                    payload = json.loads(message)
                    print(f"[MASTER] Recebido: {payload}")

                    # Worker solicita tarefa
                    if payload.get("WORKER") == "ALIVE":

                        worker_uuid = payload.get("UUID", str(addr))

                        with lock:

                            if not task_queue.empty():

                                task = task_queue.get()

                                running_tasks[worker_uuid] = task

                                response = {
                                    "TASK": "QUERY",
                                    "USER": task["user"]
                                }

                                print(
                                    f"[MASTER] Tarefa enviada para "
                                    f"{worker_uuid}: {task}"
                                )

                            else:
                                response = {"TASK": "NO_TASK"}

                        conn.sendall(
                            (json.dumps(response) + "\n").encode()
                        )

                    # Worker concluiu tarefa
                    elif payload.get("STATUS") in ["OK", "NOK"]:

                        worker_uuid = payload.get("UUID", worker_uuid)

                        with lock:
                            if worker_uuid in running_tasks:
                                tarefa = running_tasks.pop(worker_uuid)

                                print(
                                    f"[MASTER] Tarefa concluída por "
                                    f"{worker_uuid}: {tarefa}"
                                )

                        response = {"STATUS": "ACK"}

                        conn.sendall(
                            (json.dumps(response) + "\n").encode()
                        )

                except json.JSONDecodeError:
                    print("[ERRO] JSON inválido")

    except Exception as e:
        print(f"[ERRO] {e}")

    finally:

        # Se o worker caiu com tarefa pendente,
        # devolve ao final da fila
        with lock:

            if worker_uuid in running_tasks:

                tarefa = running_tasks.pop(worker_uuid)

                task_queue.put(tarefa)

                print(
                    f"[MASTER] Worker {worker_uuid} caiu. "
                    f"Tarefa devolvida à fila: {tarefa}"
                )

        conn.close()
        print(f"[-] Conexão encerrada: {addr}")


def start_server():

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server.bind((HOST, PORT))
    server.listen()

    print(f"[MASTER] Aguardando Workers em {PORT}...")

    while True:

        conn, addr = server.accept()

        threading.Thread(
            target=handle_client,
            args=(conn, addr),
            daemon=True
        ).start()


if __name__ == "__main__":
    start_server()