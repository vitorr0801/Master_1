import importlib
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))


class TestSprint4Modules(unittest.TestCase):
    def test_master_sprint4_exports_report_builder(self):
        master = importlib.import_module("master_sprint4")
        self.assertTrue(hasattr(master, "build_monitor_report"))
        payload = master.build_monitor_report(server_uuid="master_demo", role="master")
        self.assertEqual(payload["server_uuid"], "master_demo")
        self.assertEqual(payload["role"], "master")
        self.assertIn("performance", payload)

    def test_worker_sprint4_exports_client_and_payload(self):
        worker = importlib.import_module("worker_sprint4")
        self.assertTrue(hasattr(worker, "build_presence_payload"))
        payload = worker.build_presence_payload("W-DEMO")
        self.assertEqual(payload["WORKER"], "ALIVE")
        self.assertEqual(payload["WORKER_UUID"], "W-DEMO")


if __name__ == "__main__":
    unittest.main(verbosity=2)
