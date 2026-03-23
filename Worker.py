import socket
import json
import time
import uuid

HOST = "127.0.0.1"
PORT = 5000
INTERVAL = 10  # segundos

SERVER_UUID = str("Master_1")


def start_worker():
    while True:
        try:
            print("[WORKER] Conectando ao master...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((HOST, PORT))

            print("[WORKER] Conectado!")

            buffer = ""

            while True:
                payload = {
                    "SERVER_UUID": SERVER_UUID,
                    "TASK": "HEARTBEAT"
                }

                sock.sendall((json.dumps(payload) + "\n").encode())
                print(f"[WORKER] Enviado: {payload}")

                data = sock.recv(1024).decode()
                if not data:
                    raise ConnectionError("Conexão perdida")

                buffer += data

                while "\n" in buffer:
                    message, buffer = buffer.split("\n", 1)
                    response = json.loads(message)

                    print(f"[WORKER] Recebido: {response}")

                time.sleep(INTERVAL)

        except Exception as e:
            print(f"[WORKER ERRO] {e}")
            print("[WORKER] Tentando reconectar em 5s...")
            time.sleep(5)


if __name__ == "__main__":
    start_worker()