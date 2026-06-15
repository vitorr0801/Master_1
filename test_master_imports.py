import importlib
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))


class TestMasterSprint4Import(unittest.TestCase):
    def test_master_sprint4_imports_without_missing_protocol_modules(self):
        module = importlib.import_module("master_sprint4")
        self.assertTrue(hasattr(module, "start_master_services"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
