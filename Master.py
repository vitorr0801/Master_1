import socket
import threading
import json

HOST = "10.62.217.28"
PORT = 5000


def handle_client(conn, addr):
    print(f"[+] Conexão recebida de {addr}")
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

                    if payload.get("TASK") == "HEARTBEAT":
                        response = {
                            "SERVER_UUID": payload.get("SERVER_UUID"),
                            "TASK": "HEARTBEAT",
                            "RESPONSE": "ALIVE"
                        }

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

    print(f"[MASTER] Escutando em {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()


if __name__ == "__main__":
    start_server()