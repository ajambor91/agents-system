"""Test the replaceable adapter and shell execution without host mutations."""
import inspect
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from agents_manager.open_claw import AgentToolAbstract, OpenClawFacade
from agents_manager.open_claw.shell import OpenClawShell
from agents_manager.app.application import AgentsApplication
from agents_manager.app.context import ApplicationContext
from agents_manager.app.services.agents_tools_service import AgentsToolsService


class OpenClawTests(unittest.TestCase):
    def setUp(self):
        self.user = SimpleNamespace(pw_name='gateway', pw_dir='/home/gateway')
        self.runner = Mock()
        self.runner.run_as_user.return_value = subprocess.CompletedProcess([], 0, '[]', '')

    def test_contract_is_abstract_and_facade_implements_it(self):
        self.assertTrue(inspect.isabstract(AgentToolAbstract))
        self.assertIsInstance(OpenClawFacade(), AgentToolAbstract)
        self.assertIsInstance(OpenClawFacade().for_user('gateway', self.runner), AgentToolAbstract)

    def test_list_resolves_in_gateway_shell_and_preserves_arguments(self):
        tool = OpenClawFacade().for_user('gateway', self.runner)
        with patch('agents_manager.open_claw.shell.pwd.getpwnam', return_value=self.user):
            self.assertEqual(tool.list_agents(), [])
        args, kwargs = self.runner.run_as_user.call_args
        self.assertEqual(args[0], 'gateway')
        command = args[1]
        self.assertIn('HOME=/home/gateway', command)
        self.assertIn('-ilc', command)
        self.assertIn('type -P openclaw', command[command.index('-ilc') + 1])
        self.assertEqual(command[-3:], ['agents', 'list', '--json'])
        self.assertTrue(kwargs['capture'])

    def test_message_command_keeps_spaces_and_timeout(self):
        with patch('agents_manager.open_claw.shell.pwd.getpwnam', return_value=self.user):
            OpenClawFacade().for_user('gateway', self.runner).run_agent(
                agent_name='mimir', session_key='session with spaces',
                message_file=Path('/tmp/message with spaces'), timeout=12)
        command = self.runner.run_as_user.call_args.args[1]
        self.assertIn('session with spaces', command)
        self.assertIn('/tmp/message with spaces', command)
        self.assertEqual(self.runner.run_as_user.call_args.kwargs['timeout'], 42)

    def test_shell_script_resolves_executable_and_never_interpolates_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'openclaw'
            path.write_text('#!/usr/bin/python3\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n')
            path.chmod(0o700)
            argument = 'with spaces; $(touch injected)'
            environment = dict(os.environ, PATH=directory + os.pathsep + '/usr/bin:/bin')
            result = subprocess.run(['/bin/bash', '--noprofile', '--norc', '-c', OpenClawShell.SCRIPT, 'openclaw', argument],
                                    env=environment, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout), [argument])
            result = subprocess.run(['/bin/bash', '--noprofile', '--norc', '-c', OpenClawShell.SCRIPT, 'openclaw'],
                                    env=dict(environment, PATH=directory + '/missing'), capture_output=True, text=True)
            self.assertEqual(result.returncode, 127)
            self.assertIn('gateway shell', result.stderr)

    def test_custom_adapter_is_injected_into_all_consumers(self):
        adapter = Mock(spec=AgentToolAbstract)
        configuration = type('Configuration', (), {'APP_DIR': '/tmp/manager'})()
        application = AgentsApplication(configuration, agent_tool=adapter)
        service = application._agents_service
        for name in ('installer', 'lister', 'status', 'tools', 'wakeup'):
            self.assertIs(getattr(service, '_' + name)._services_factory._agent_tool, adapter)
        adapter.for_user.assert_not_called()
        context = SimpleNamespace(gateway_user='gateway')
        factory = Mock()
        factory.create.return_value.agent_tool = adapter.for_user.return_value
        adapter.for_user.return_value.get_agent_tools.return_value = {}
        self.assertEqual(AgentsToolsService(factory).execute({'name': 'mimir'}, context), {'agent': 'mimir', 'tools': {}})
        adapter.for_user.return_value.get_agent_tools.assert_called_once_with('mimir')

    def test_context_uses_configured_user_without_resolving_openclaw(self):
        configuration = type('Configuration', (), {'USER_SYSTEM': 'gateway', 'APP_DATA_DIR': '/tmp/data'})()
        with patch.dict(os.environ, {}, clear=True), patch('agents_manager.app.context.pwd.getpwnam', return_value=self.user):
            context = ApplicationContext.create(Path('/tmp/manager'), configuration=configuration)
        self.assertEqual(context.gateway_user, 'gateway')
        self.assertFalse(hasattr(context, 'openclaw_bin'))

    def test_policy_translation_belongs_to_adapter(self):
        policy = {'also_allow': ['read'], 'profile': 'minimal'}
        with patch('agents_manager.open_claw.shell.pwd.getpwnam', return_value=self.user):
            OpenClawFacade().for_user('gateway', self.runner).set_agent_tools('mimir', policy)
        command = self.runner.run_as_user.call_args.args[1]
        self.assertEqual(json.loads(command[-2]), {'alsoAllow': ['read'], 'profile': 'minimal'})
        self.assertIn('also_allow', policy)
