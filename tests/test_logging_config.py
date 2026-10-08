"""Logging protocol, startup configuration and CLI output regression tests."""
from __future__ import annotations

import contextlib
import io
import logging
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from lib.logging_config import RFC5424Formatter, configure_logging


class LoggingTests(unittest.TestCase):
    def setUp(self):
        self.root = logging.getLogger()
        self.handlers = self.root.handlers[:]
        self.level = self.root.level
        self.root.handlers = []

    def tearDown(self):
        for handler in self.root.handlers:
            handler.close()
        self.root.handlers = self.handlers
        self.root.setLevel(self.level)

    def test_rfc_header_severity_utf8_and_single_line_traceback(self):
        for level, pri in ((logging.DEBUG,31), (logging.INFO,30), (logging.WARNING,28), (logging.ERROR,27), (logging.CRITICAL,26)):
            record = logging.LogRecord('module.command', level, __file__, 1, 'Zażółć %s\nnext', ('value',), None)
            result = RFC5424Formatter('app name').format(record)
            self.assertRegex(result, rf'^<{pri}>1 \d{{4}}-\d{{2}}-\d{{2}}T\S+Z \S+ app_name \d+ command - \ufeffZażółć value\\nnext$')
        try:
            raise ValueError('test\nerror')
        except ValueError:
            record.exc_info = sys.exc_info()
        result = RFC5424Formatter('x'*100).format(record)
        self.assertIn('ValueError: test\\nerror', result)
        self.assertNotIn('\n', result)
        self.assertEqual(len(result.split(' ')[3]), 48)

    def test_info_default_stderr_and_no_duplicate_configuration(self):
        stream = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stderr(stream):
            configure_logging('test-app')
            configure_logging('nested-module')
            logger = logging.getLogger('test.command')
            logger.debug('hidden')
            logger.info('operation completed')
        self.assertEqual(len(self.root.handlers), 1)
        self.assertNotIn('hidden', stream.getvalue())
        self.assertIn(' test-app ', stream.getvalue())
        self.assertIn('operation completed', stream.getvalue())

    def test_systemd_environment_debug_and_invalid_level(self):
        for value, expected in (('DEBUG', logging.DEBUG), ('error', logging.ERROR), ('bogus', logging.INFO)):
            self.root.handlers = []
            stream = io.StringIO()
            with patch.dict(os.environ, {'AGENTS_MANAGER_LOG_LEVEL':value}), contextlib.redirect_stderr(stream):
                configure_logging('test-app')
            self.assertEqual(self.root.level, expected)
            if value == 'bogus':
                self.assertIn('Invalid AGENTS_MANAGER_LOG_LEVEL', stream.getvalue())

    def test_backend_cli_keeps_json_stdout(self):
        result = subprocess.run([sys.executable, '-m', 'agents_data_backend'], env={**os.environ, 'PYTHONPATH':str(ROOT/'src'), 'AGENTS_MANAGER_LOG_LEVEL':'DEBUG'}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        import json
        self.assertEqual(json.loads(result.stdout)['status'], 'scaffold')

    def test_service_templates_set_default(self):
        for name in ('system.template.service','agents_manager.template.service'):
            content = (ROOT/'resources'/name).read_text()
            self.assertIn('Environment="AGENTS_MANAGER_LOG_LEVEL=INFO"', content)
            self.assertIn('StandardError=journal', content)

    def test_ipc_debug_output_is_logging_only(self):
        from lib.unix_socket.codec import MessageCodec
        from lib.unix_socket.exceptions import UnixSocketProtocolException
        from lib.unix_socket.models import Request
        output = io.StringIO()
        logs = io.StringIO()
        with patch.dict(os.environ, {'AGENTS_MANAGER_LOG_LEVEL':'DEBUG'}), contextlib.redirect_stdout(output), contextlib.redirect_stderr(logs):
            configure_logging('test-app')
            codec = MessageCodec()
            codec.encode_request(Request('module.execute', {'secret':'do-not-log'}))
            with self.assertRaises(UnixSocketProtocolException):
                codec.decode_response(b'{"secret":"do-not-log"}\n')
        self.assertEqual(output.getvalue(), '')
        self.assertIn('Invalid IPC response', logs.getvalue())
        self.assertNotIn('do-not-log', logs.getvalue())

    def test_runtime_capture_does_not_capture_process_logs(self):
        process_stderr = io.StringIO()
        adapter_stderr = io.StringIO()
        with patch.dict(os.environ, {'AGENTS_MANAGER_LOG_LEVEL':'INFO'}), contextlib.redirect_stderr(process_stderr):
            configure_logging('runtime')
            with contextlib.redirect_stderr(adapter_stderr):
                logging.getLogger('runtime.dispatch').info('operation completed')
        self.assertEqual(adapter_stderr.getvalue(), '')
        self.assertIn('operation completed', process_stderr.getvalue())

    def test_message_service_logs_acceptance_without_message_content(self):
        from agents_data.app.services.app_comm import AppCommService
        from unittest.mock import MagicMock
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"messageId":"message-123","status":"accepted"}'
        with patch('urllib.request.urlopen', return_value=response), self.assertLogs('agents_data.app.services.app_comm', level='DEBUG') as captured:
            result = AppCommService('http://localhost').send_message({'messages':[{'content':'private-message-content'}]})
        self.assertEqual(result.message_id, 'message-123')
        logs = '\n'.join(captured.output)
        self.assertIn('Message accepted: message_id=message-123', logs)
        self.assertNotIn('private-message-content', logs)

    def test_manager_failure_logs_operation_and_preserves_result(self):
        from agents_manager.app.services.agents_service import AgentsService
        from unittest.mock import Mock
        service = AgentsService(Mock(), **{name:Mock() for name in ('installer','executor','deleter','updater','lister','status','tools','wakeup')})
        service._status.execute.side_effect = ValueError('operation rejected')
        with self.assertLogs('agents_manager.app.services.agents_service', level='ERROR') as captured:
            result = service.status({'name':'example'})
        self.assertEqual(result, {'message':'operation rejected'})
        self.assertIn('operation=status', captured.output[0])


if __name__ == '__main__':
    unittest.main()
