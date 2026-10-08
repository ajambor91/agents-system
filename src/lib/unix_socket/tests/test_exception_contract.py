"""Regression check for error handling, independent of package import blockers."""

import importlib.util
import unittest
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / 'exceptions/base.py'
spec = importlib.util.spec_from_file_location('socket_exception_contract', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExceptionContractTests(unittest.TestCase):
    def test_socket_errors_can_be_raised_and_caught_as_exceptions(self):
        self.assertTrue(
            issubclass(module.UnixSocketException, Exception),
            'UnixSocketException must inherit Exception for transport raise/except to work',
        )
