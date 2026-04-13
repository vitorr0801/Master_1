import socket
import threading
import json
import queue

HOST = "0.0.0.0"
PORT = 5000

# Fila thread-safe
task_queue = queue.Queue()

# Inicializa tarefas
task_queue.put({"user": "Michel"})
task_queue.put({"user": "Julia"})
task_queue.put({"user": "Carlos"})


def handle_client(conn, addr):
    print(f"[+] Conexão ativa: {addr}")
    buffer = ""

    try:
        while True:
            data = conn.recv(1024).decode()

            if not data:
                break

            buffer += data

            while "\n" in buffer:
                message, buffer = buffer.split("\n", 1)

                try:
                    payload = json.loads(message)
                    print(f"[MASTER] Recebido: {payload}")

                    # Worker pedindo tarefa
                    if payload.get("WORKER") == "ALIVE":

                        if not task_queue.empty():
                            task = task_queue.get()

                            response = {
                                "TASK": "QUERY",
                                "USER": task["user"]
                            }

                            print(f"[MASTER] Enviando tarefa: {task}")
                        else:
                            response = {"TASK": "NO_TASK"}
                            print("[MASTER] Nenhuma tarefa disponível")

                        conn.sendall((json.dumps(response) + "\n").encode())

                    # Worker retornando resultado
                    elif payload.get("STATUS") in ["OK", "NOK"]:
                        print(f"[LOG] Resultado recebido: {payload}")

                        response = {"STATUS": "ACK"}
                        conn.sendall((json.dumps(response) + "\n").encode())

                except json.JSONDecodeError:
                    print("[ERRO] JSON inválido")

    except Exception as e:
        print(f"[ERRO] {e}")

    finally:
        conn.close()
        print(f"[-] Conexão encerrada: {addr}")


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