"""Requests own their dependencies and diagnostics; nothing renders domain data."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from agents_manager.app.services.agent_services_factory import AgentServicesFactory
from agents_manager.app.services.process import ProcessRunner


class RequestServicesTests(unittest.TestCase):
    def test_factory_builds_isolated_request_graphs_without_host_operations(self):
        configuration = type('Configuration', (), {'APP_DIR':'/tmp/application'})()
        adapter = Mock()
        factory = AgentServicesFactory(configuration, adapter)
        first = SimpleNamespace(agents_root=Path('/tmp/agents'), state_root=Path('/tmp/state'), gateway_user='first')
        second = SimpleNamespace(agents_root=first.agents_root, state_root=first.state_root, gateway_user='second')
        one = factory.create(first, {'verbose':True})
        two = factory.create(second, {'verbose':False})
        with contextlib.redirect_stdout(io.StringIO()) as stdout, contextlib.redirect_stderr(io.StringIO()) as stderr:
            one.runner.report('first request')
            two.runner.report('second request')
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(stderr.getvalue(), '')
        self.assertEqual(one.messages, ['first request'])
        self.assertEqual(two.messages, ['second request'])
        self.assertIsNot(one.runner, two.runner)
        self.assertIs(one.state.context, first)
        self.assertIs(two.state.context, second)
        self.assertTrue(one.runner.verbose)
        self.assertFalse(two.runner.verbose)
        self.assertIs(one.registry.state, one.state)
        self.assertIs(one.runtime.state, one.state)
        self.assertIs(one.links.runner, one.runner)
        adapter.for_user.assert_any_call('first', one.runner)
        adapter.for_user.assert_any_call('second', two.runner)

    def test_subprocess_output_goes_to_request_diagnostics(self):
        messages = []
        runner = ProcessRunner(verbose=True, reporter=messages.append)
        process = subprocess.CompletedProcess(['tool'], 0, 'result\n', 'diagnostic\n')
        with patch('agents_manager.app.services.process.subprocess.run', return_value=process) as run:
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertIs(runner.run(['tool']), process)
        self.assertEqual(stdout.getvalue(), '')
        self.assertTrue(run.call_args.kwargs['capture_output'])
        self.assertEqual(messages, ['+ tool','result','diagnostic'])

    def test_timeout_outputs_are_strings_for_json_serialization(self):
        timeout = subprocess.TimeoutExpired(['tool'], 1, output=b'partial\xff', stderr=b'error')
        runner = ProcessRunner(reporter=Mock())
        with patch('agents_manager.app.services.process.subprocess.run', side_effect=timeout):
            result = runner.run(['tool'], check=False, capture=True, timeout=1)
        payload = {'returncode':result.returncode, 'stdout':result.stdout, 'stderr':result.stderr}
        self.assertEqual(result.returncode, 124)
        self.assertEqual(result.stderr, 'error')
        self.assertIn('partial', result.stdout)
        json.dumps(payload, allow_nan=False)
