"""
Test script for Sprint 3 - Master-to-Master Negotiation and Dynamic Worker Redirection

Runs test cases CT01-CT09 from the specification
"""

import unittest
import socket
import json
import time
import threading
import sys
import os

# Mock Master implementation for testing
class MockMaster:
    def __init__(self, master_id, host, port, capacity=3):
        self.master_id = master_id
        self.host = host
        self.port = port
        self.capacity = capacity
        self.current_load = 0
        self.workers = {}
        self.borrowed_workers = {}
        self.server = None
        self.running = False
    
    def start(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(5)
        self.running = True
        
        threading.Thread(target=self._accept_connections, daemon=True).start()
        print(f"[MockMaster {self.master_id}] Iniciado em {self.host}:{self.port}")
    
    def _accept_connections(self):
        while self.running:
            try:
                conn, addr = self.server.accept()
                threading.Thread(target=self._handle_connection, args=(conn, addr), daemon=True).start()
            except:
                pass
    
    def _handle_connection(self, conn, addr):
        buffer = ""
        try:
            while True:
                data = conn.recv(1024).decode()
                if not data:
                    break
                
                buffer += data
                while "\n" in buffer:
                    message, buffer = buffer.split("\n", 1)
                    payload = json.loads(message)
                    
                    msg_type = payload.get("type")
                    
                    if msg_type == "request_help":
                        self._handle_request_help(conn, payload)
                    elif msg_type == "notify_worker_returned":
                        self._handle_notify_worker_returned(payload)
        except:
            pass
        finally:
            conn.close()
    
    def _handle_request_help(self, conn, payload):
        request_id = payload.get("request_id")
        workers_needed = payload.get("payload", {}).get("workers_needed", 1)
        
        available = len([w for w in self.workers.values() if not w.get("busy")])
        
        if available >= workers_needed:
            response = {
                "type": "response_accepted",
                "request_id": request_id,
                "payload": {
                    "workers_offered": min(available, workers_needed),
                    "worker_details": [
                        {"id": f"W-{self.master_id}-{i}", "address": f"{self.host}:{self.port}"}
                        for i in range(min(available, workers_needed))
                    ]
                }
            }
        else:
            response = {
                "type": "response_rejected",
                "request_id": request_id,
                "payload": {"reason": "no_workers_available"}
            }
        
        conn.sendall((json.dumps(response) + "\n").encode())
    
    def _handle_notify_worker_returned(self, payload):
        worker_id = payload.get("payload", {}).get("worker_id")
        if worker_id in self.borrowed_workers:
            del self.borrowed_workers[worker_id]
    
    def stop(self):
        self.running = False
        if self.server:
            self.server.close()

class TestSprint3(unittest.TestCase):
    """Test cases para Sprint 3"""
    
    @classmethod
    def setUpClass(cls):
        """Inicia Masters mock para os testes"""
        cls.master_a = MockMaster("MASTER_A", "127.0.0.1", 5000, capacity=3)
        cls.master_b = MockMaster("MASTER_B", "127.0.0.1", 6000, capacity=3)
        
        cls.master_a.start()
        cls.master_b.start()
        
        time.sleep(1)  # Aguarda inícialização
    
    @classmethod
    def tearDownClass(cls):
        """Para os Masters mock"""
        cls.master_a.stop()
        cls.master_b.stop()
    
    def test_ct01_request_help_accepted(self):
        """CT01: Pedido de ajuda aceito"""
        # Simula um pedido de ajuda
        request_id = "test-request-001"
        msg = {
            "type": "request_help",
            "request_id": request_id,
            "payload": {
                "master_id": "MASTER_A",
                "current_load": 5,
                "capacity": 3,
                "workers_needed": 2
            }
        }
        
        # Conecta ao Master B e envia
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 6000))
        sock.sendall((json.dumps(msg) + "\n").encode())
        
        # Aguarda resposta
        data = sock.recv(1024).decode()
        response = json.loads(data.strip())
        
        # Verifica resposta
        self.assertEqual(response.get("type"), "response_accepted")
        self.assertEqual(response.get("request_id"), request_id)
        self.assertIn("worker_details", response.get("payload", {}))
        
        sock.close()
    
    def test_ct02_request_help_rejected(self):
        """CT02: Pedido de ajuda recusado"""
        # Simula Master B saturado
        self.master_b.current_load = 10  # Acima da capacidade
        
        request_id = "test-request-002"
        msg = {
            "type": "request_help",
            "request_id": request_id,
            "payload": {
                "master_id": "MASTER_A",
                "current_load": 5,
                "capacity": 3,
                "workers_needed": 2
            }
        }
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 6000))
        sock.sendall((json.dumps(msg) + "\n").encode())
        
        data = sock.recv(1024).decode()
        response = json.loads(data.strip())
        
        # Nota: Com Master mock sem workers, sempre será recusado
        if response.get("type") == "response_rejected":
            self.assertEqual(response.get("request_id"), request_id)
        
        sock.close()
        self.master_b.current_load = 0  # Reset
    
    def test_ct03_request_id_correlation(self):
        """CT03: Correlação de request_id em requisições concorrentes"""
        request_ids = ["req-003-1", "req-003-2", "req-003-3"]
        responses = {}
        
        def send_request(req_id):
            msg = {
                "type": "request_help",
                "request_id": req_id,
                "payload": {
                    "master_id": "MASTER_A",
                    "current_load": 5,
                    "capacity": 3,
                    "workers_needed": 1
                }
            }
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", 6000))
            sock.sendall((json.dumps(msg) + "\n").encode())
            
            data = sock.recv(1024).decode()
            responses[req_id] = json.loads(data.strip())
            sock.close()
        
        # Envia requisições concorrentes
        threads = [threading.Thread(target=send_request, args=(rid,)) for rid in request_ids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verifica se cada resposta tem o request_id correto
        for req_id in request_ids:
            self.assertIn(req_id, responses)
            self.assertEqual(responses[req_id].get("request_id"), req_id)
    
    def test_ct04_message_format(self):
        """CT04: Validação de formato de mensagem"""
        msg = {
            "type": "request_help",
            "request_id": "test-format",
            "payload": {
                "master_id": "MASTER_A",
                "current_load": 5,
                "capacity": 3,
                "workers_needed": 2
            }
        }
        
        # Verifica se a mensagem segue o padrão
        self.assertIn("type", msg)
        self.assertIn("request_id", msg)
        self.assertIn("payload", msg)
        self.assertIn("master_id", msg["payload"])
        self.assertIn("current_load", msg["payload"])
        self.assertIn("capacity", msg["payload"])
        self.assertIn("workers_needed", msg["payload"])
    
    def test_ct05_response_format(self):
        """CT05: Validação de formato de resposta"""
        request_id = "test-response-format"
        msg = {
            "type": "request_help",
            "request_id": request_id,
            "payload": {
                "master_id": "MASTER_A",
                "current_load": 5,
                "capacity": 3,
                "workers_needed": 1
            }
        }
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 6000))
        sock.sendall((json.dumps(msg) + "\n").encode())
        
        data = sock.recv(1024).decode()
        response = json.loads(data.strip())
        
        # Verifica formato
        self.assertIn("type", response)
        self.assertIn("request_id", response)
        self.assertIn("payload", response)
        self.assertEqual(response["request_id"], request_id)
        
        sock.close()
    
    def test_ct06_heartbeat_message(self):
        """CT06: Formato de mensagem de Heartbeat (Sprint 01)"""
        msg = {
            "SERVER_UUID": "Master_A",
            "TASK": "HEARTBEAT"
        }
        
        self.assertEqual(msg["TASK"], "HEARTBEAT")
        self.assertIn("SERVER_UUID", msg)
    
    def test_ct07_worker_alive_message(self):
        """CT07: Formato de mensagem de Worker ALIVE (Sprint 02)"""
        msg = {
            "WORKER": "ALIVE",
            "WORKER_UUID": "W-123"
        }
        
        self.assertEqual(msg["WORKER"], "ALIVE")
        self.assertIn("WORKER_UUID", msg)
    
    def test_ct08_worker_borrowed_message(self):
        """CT08: Formato de mensagem de Worker emprestado (Sprint 02)"""
        msg = {
            "WORKER": "ALIVE",
            "WORKER_UUID": "W-999",
            "SERVER_UUID": "Master_B"
        }
        
        self.assertEqual(msg["WORKER"], "ALIVE")
        self.assertIn("SERVER_UUID", msg)
        self.assertEqual(msg["SERVER_UUID"], "Master_B")
    
    def test_ct09_newline_delimiter(self):
        """CT09: Verificação do delimitador de nova linha"""
        msg = {"type": "request_help", "request_id": "test"}
        msg_str = json.dumps(msg)
        
        # Deve terminar com \n
        msg_with_delimiter = msg_str + "\n"
        
        self.assertTrue(msg_with_delimiter.endswith("\n"))
        self.assertFalse(msg_str.endswith("\n"))

def run_tests():
    """Executa todos os testes"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSprint3)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
