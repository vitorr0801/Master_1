import json
import socket
import time


def send_message(sock: socket.socket, payload: dict) -> bool:
    try:
        if isinstance(payload, bytes):
            sock.sendall(payload)
        else:
            sock.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
        return True
    except Exception:
        return False


def receive_message(sock: socket.socket, buffer_size: int = 4096) -> bytes | None:
    try:
        data = sock.recv(buffer_size)
        return data or None
    except socket.timeout:
        return None
    except Exception:
        return None


def receive_message_timeout(sock: socket.socket, timeout: int) -> bytes | None:
    previous_timeout = sock.gettimeout()
    try:
        sock.settimeout(timeout)
        return receive_message(sock)
    finally:
        sock.settimeout(previous_timeout)


def decode_message(raw: bytes | str) -> dict:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="ignore")
    text = raw.strip()
    if not text:
        return {}
    return json.loads(text)
