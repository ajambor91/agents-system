"""Console routing through the Agents System execute/help API."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from agents_system_cli.app.application import AgentsSystemCLI
from agents_system_cli.app.services.module_dispatcher import ModuleDispatcher
from agents_system_cli.app.services.console_argument_parser import ConsoleArgumentParser
from lib.modules_catalog import Module, Command, Flag
from agents_system_cli.app.exceptions import ApiError


class SystemDispatchTests(unittest.TestCase):
    def setUp(self):
        self.flag = Flag('name', '-n', '--name', [], '', '', True, 'string', False)
        self.command = Command('inspect', 'read', '', '', 'implemented', [self.flag])
        self.module = Module('example', '/unused', 'modules', '', '', {'inspect': self.command})
        self.system = Module('agents_system', '/system', 'system', '', '', {})
        self.catalog = SimpleNamespace(modules={'example': self.module, 'agents_system': self.system}, modules_by_section={'modules': self.module, 'system': self.system})
        self.socket = Mock(is_connected=True)
        self.socket.is_healthy.return_value = True
        self.socket.send.return_value = SimpleNamespace(successful=True, result={'ok': True})
        self.dispatcher = ModuleDispatcher(None, self.socket, self.catalog)
        self.application = AgentsSystemCLI.__new__(AgentsSystemCLI)
        self.application.catalog = self.catalog
        self.application.dispatcher = self.dispatcher
        self.application.renderers_factory = Mock()

    def test_command_without_flags_requests_help(self):
        self.application.run(['modules', 'inspect'])
        self.socket.send.assert_called_once_with('agents_system', 'help', kwargs={'module_name': 'example', 'method_name': 'read', 'flags': {}})

    def test_section_help(self):
        for argv in (['modules'], ['modules', '--help'], ['system']):
            self.socket.send.reset_mock()
            self.application.run(argv)
            self.socket.send.assert_called_once_with('agents_system', 'help', kwargs={'module_name': 'agents_system' if argv[0] == 'system' else 'example', 'method_name': argv[0], 'flags': {}})

    def test_typed_flags_and_help(self):
        for suffix, method in (([], 'execute'), (['--help'], 'help')):
            self.socket.send.reset_mock()
            self.application.run(['modules', 'inspect', '--name', 'two words'] + suffix)
            args = self.socket.send.call_args.args
            self.assertEqual(args, ('agents_system', method))
            payload = self.socket.send.call_args.kwargs['kwargs']
            self.assertEqual(payload['module_name'], 'example')
            self.assertEqual(payload['method_name'], 'read')
            self.assertEqual(self.socket.send.call_args.kwargs['kwargs']['flags']['name'], 'two words')

    def test_root_help_stays_local(self):
        self.application.run(['--help'])
        self.socket.send.assert_not_called()

    def test_console_option_as_flag_value(self):
        options = ConsoleArgumentParser.parse(self.catalog, ['modules', 'inspect', '--name', '--help'])
        self.assertFalse(options.help_requested)
        self.assertEqual(options.remaining[-1], '--help')

    def test_local_loads_selected_module(self):
        self.socket.is_connected = False
        self.dispatcher.loader = Mock()
        self.dispatcher.dispatch(self.module, self.command, [])
        self.dispatcher.loader.load.assert_called_once_with(self.module)
        self.dispatcher.loader.load.return_value.execute.assert_called_once_with(method_name='read', flags={})

    def test_transport_error_never_retries(self):
        self.socket.send.side_effect = RuntimeError('lost response')
        self.dispatcher.loader = Mock()
        with self.assertRaises(ApiError):
            self.dispatcher.dispatch(self.module, self.command, [])
        self.dispatcher.loader.load.assert_not_called()

    def test_unknown_command_returns_error(self):
        self.application.run(['modules', 'unknown'])
        self.socket.send.assert_not_called()
        self.application.renderers_factory.create_renderer.return_value.error.assert_called_once()

    def test_local_help_uses_selected_module_and_preserves_flags(self):
        self.socket.is_connected = False
        self.dispatcher.loader = Mock()
        self.dispatcher.dispatch_help(self.module, 'read', [self.flag])
        self.dispatcher.loader.load.assert_called_once_with(self.module)
        self.dispatcher.loader.load.return_value.help.assert_called_once_with(method_name='read', flags={'name': None})
        self.socket.send.assert_not_called()

    def test_local_execution_passes_flag_dictionary(self):
        self.socket.is_connected = False
        self.dispatcher.loader = Mock()
        self.dispatcher.dispatch(self.module, self.command, [self.flag])
        self.dispatcher.loader.load.return_value.execute.assert_called_once_with(method_name='read', flags={'name': None})

    def test_system_modules_without_flags_requests_help(self):
        self.system.commands['modules'] = Command('modules', None, '', '', 'implemented', [])
        self.application.run(['system', 'modules'])
        self.socket.send.assert_called_once_with('agents_system', 'help', kwargs={
            'module_name': 'agents_system', 'method_name': 'modules', 'flags': {},
        })

    def test_no_flags_help_skips_required_validation_even_with_output_mode(self):
        self.flag.required = True
        self.application.run(['--json', 'modules', 'inspect'])
        self.socket.send.assert_called_once_with('agents_system', 'help', kwargs={
            'module_name': 'example', 'method_name': 'read', 'flags': {},
        })

    def test_command_without_flags_requests_local_help(self):
        self.socket.is_connected = False
        self.dispatcher.loader = Mock()
        self.application.run(['modules', 'inspect'])
        self.dispatcher.loader.load.assert_called_once_with(self.module)
        instance = self.dispatcher.loader.load.return_value
        instance.help.assert_called_once_with(method_name='read', flags={})
        instance.execute.assert_not_called()

    def test_default_flags_do_not_select_execute(self):
        self.flag.default = 'default name'
        self.application.run(['modules', 'inspect'])
        self.assertEqual(self.socket.send.call_args.args, ('agents_system', 'help'))
        self.assertEqual(self.socket.send.call_args.kwargs['kwargs']['flags']['name'], 'default name')

    def test_boolean_flags_are_values_without_metadata(self):
        installed = Flag('installed', None, '--installed', [], '', '', False, 'boolean', False, default=False)
        running = Flag('running', None, '--running', [], '', '', False, 'boolean', False, default=False)
        self.command.flags = [installed, running]
        for local in (False, True):
            self.socket.is_connected = not local
            self.dispatcher.loader = Mock()
            self.application.run(['modules', 'inspect', '--installed'])
            if local:
                flags = self.dispatcher.loader.load.return_value.execute.call_args.kwargs['flags']
            else:
                flags = self.socket.send.call_args.kwargs['kwargs']['flags']
            self.assertEqual(flags, {'installed': True, 'running': False})
            self.assertIs(flags['installed'], True)
            self.assertIs(flags['running'], False)
