"""Exercise the restored ABC in isolation from broken package imports."""

import importlib.util
import unittest
from pathlib import Path


# Direct loading is intentional: package import failures are tested separately
# by test_public_contract, without substituting any production dependencies.
SOURCE = Path(__file__).resolve().parents[1] / 'abstract/models/configuration.py'
spec = importlib.util.spec_from_file_location('socket_configuration_contract', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
AbstractSocketConfiguration = module.AbstractSocketConfiguration


class ConfigurationContractTests(unittest.TestCase):
    def test_base_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            AbstractSocketConfiguration()

    def test_every_setting_is_required(self):
        implementations = {
            'socket_path': property(lambda self: Path('/tmp/app.sock')),
            'connect_timeout': property(lambda self: 0.25),
            'request_timeout': property(lambda self: 15.0),
            'maximum_response_bytes': property(lambda self: 1024),
        }
        for missing in implementations:
            with self.subTest(missing=missing):
                incomplete = type('IncompleteConfiguration', (AbstractSocketConfiguration,), {
                    key: value for key, value in implementations.items() if key != missing
                })
                with self.assertRaises(TypeError):
                    incomplete()

    def test_application_owns_data_without_validation_or_serialization_methods(self):
        class ApplicationConfiguration(AbstractSocketConfiguration):
            def __init__(self, path, connect_timeout, request_timeout, limit):
                self._path = Path(path)
                self._connect_timeout = connect_timeout
                self._request_timeout = request_timeout
                self._limit = limit

            @property
            def socket_path(self):
                return self._path

            @property
            def connect_timeout(self):
                return self._connect_timeout

            @property
            def request_timeout(self):
                return self._request_timeout

            @property
            def maximum_response_bytes(self):
                return self._limit

        first = ApplicationConfiguration('/tmp/first.sock', None, None, 1024)
        second = ApplicationConfiguration('/tmp/second.sock', 0.5, 5.0, 2048)
        self.assertEqual(first.socket_path, Path('/tmp/first.sock'))
        self.assertIsNone(first.connect_timeout)
        self.assertIsNone(first.request_timeout)
        self.assertEqual(first.maximum_response_bytes, 1024)
        self.assertEqual(second.socket_path, Path('/tmp/second.sock'))
        self.assertEqual(second.connect_timeout, 0.5)
        self.assertEqual(second.request_timeout, 5.0)
        self.assertEqual(second.maximum_response_bytes, 2048)
        for name in ('validate', 'to_mapping', 'from_mapping'):
            self.assertFalse(hasattr(first, name))
