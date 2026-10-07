"""The manager boundary returns data through the same local and runtime API."""
from __future__ import annotations

import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))

from agents_manager import AgentsApplication
from agents_manager import __main__ as entrypoint
from agents_manager.app.services.agents_service import AgentsService
from agents_manager.app.services.help_service import HelpService


class AgentsServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.configuration = type('Configuration', (), {'APP_DIR': str(self.root)})()
        self.factory = Mock()
        self.context = SimpleNamespace(repo_root=self.root, gateway_user='gateway-default')
        self.factory.create_context.return_value = self.context
        self.services = {name: Mock() for name in ('installer', 'executor', 'deleter', 'updater', 'lister', 'status', 'tools', 'wakeup')}
        self.service = AgentsService(self.factory, **self.services)

    def test_application_only_exposes_help_and_execute_and_composes_dependencies(self):
        public = [name for name, method in inspect.getmembers(AgentsApplication, inspect.isfunction) if not name.startswith('_')]
        self.assertEqual(public, ['execute', 'help'])
        with patch('agents_manager.app.application.AgentsService') as service_class, patch('agents_manager.app.application.HelpService') as help_service:
            application = AgentsApplication(self.configuration, services_factory=self.factory)
            self.assertEqual(service_class.call_args.args, (self.factory,))
            dependencies = service_class.call_args.kwargs
            self.assertIs(dependencies['updater']._installer, dependencies['installer'])
            for name in ('installer','executor','lister','status','tools','wakeup'):
                self.assertIs(dependencies[name]._services_factory, self.factory)
            payload = {'name': 'example'}
            self.assertIs(application.execute('install', payload, None), service_class.return_value.exec.return_value)
            service_class.return_value.exec.assert_called_once_with('install', payload, None)
            self.assertIs(application.help('install', {}, None), help_service.return_value.help.return_value)
            help_service.return_value.help.assert_called_once_with('install')

    def test_help_returns_manifest_data_without_request_context(self):
        document = json.loads((ROOT / 'src/agents_manager/resources/agents_manager.module.json').read_text())
        application = AgentsApplication(self.configuration, document, services_factory=self.factory)
        self.assertIs(application.help(), document)
        result = application.help('install')
        self.assertEqual(result['command']['name'], 'install')
        json.dumps(result)
        self.factory.create_context.assert_not_called()
        self.factory.create.assert_not_called()
        self.assertEqual(HelpService(document).help('missing'), {'message': 'Method not found'})

    def test_all_operations_preserve_flag_dictionary_and_return_payload(self):
        cases = {'install':'installer','update':'updater','exec':'executor','delete':'deleter',
                 'list':'lister','status':'status','tools':'tools','wakeup':'wakeup'}
        for operation, dependency in cases.items():
            with self.subTest(operation=operation):
                flags = {'name':'example', 'show':True}
                response = {'operation':operation, 'agent':'example'}
                self.services[dependency].execute.return_value = response
                self.assertIs(self.service.exec(operation, flags, None), response)
                self.services[dependency].execute.assert_called_once_with(flags, self.context)
                self.factory.create_context.assert_called_with(flags)

    def test_both_two_and_three_argument_application_calls_return_same_data(self):
        application = AgentsApplication(self.configuration, services_factory=self.factory)
        with patch.object(application._agents_service, 'list', return_value={'agents':{}}):
            local = application.execute(method_name='list', flags={'show':True})
            runtime = application.execute('list', {'show':True}, None)
            self.assertEqual(local, runtime)
            # Existing control plane callers may still supply a module name.
            self.assertEqual(application.execute('list', {}, 'agents_manager'), local)
            json.dumps(runtime)

    def test_service_and_context_errors_are_returned_as_dicts(self):
        self.services['status'].execute.side_effect = ValueError('Invalid agent name')
        self.assertEqual(self.service.exec('status', {'name':'../bad'}), {'message':'Invalid agent name'})
        self.factory.create_context.side_effect = RuntimeError('context unavailable')
        self.assertEqual(self.service.exec('list'), {'message':'context unavailable'})

    def test_getattr_dispatch_rejects_missing_private_and_non_dict_results(self):
        self.assertEqual(self.service.exec('missing'), {'message':'Method not found'})
        self.assertEqual(self.service.exec('_create_context'), {'message':'Method not found'})
        self.service.custom_operation = Mock(return_value={'message':'done'})
        self.assertEqual(self.service.exec('custom_operation', {'value':1}), {'message':'done'})
        self.service.custom_operation.assert_called_once_with({'value':1})
        self.service.custom_operation.return_value = 0
        self.assertEqual(self.service.exec('custom_operation'), {'message':'Method must return a dictionary'})
        self.assertFalse(hasattr(self.service, 'run'))

    def test_entrypoint_and_runtime_metadata_select_same_class(self):
        self.assertFalse(hasattr(entrypoint, 'main'))
        metadata = json.loads((ROOT/'src/agents_manager/meta.json').read_text())
        self.assertEqual(metadata['application']['class'], 'AgentsApplication')
        with patch.object(entrypoint, 'ManifestsLoader') as loader, patch.object(entrypoint.ManifestValidator, 'validate', return_value=True):
            type(self.configuration).MODULES_DIR = str(ROOT/'src')
            loader.load_manifest.return_value = {}
            self.assertIsInstance(entrypoint.get_main_app(self.configuration), AgentsApplication)

    def test_actual_cli_loader_and_runtime_builder_use_dictionary_api(self):
        from agents_system_cli.app.services.module_loader import ModuleLoader
        from _runtime.app.class_loader import ClassLoader
        from _runtime.app.class_builder import ClassBuilder
        directory = ROOT/'src/agents_manager'
        type(self.configuration).MODULES_DIR = str(ROOT/'src')
        local = ModuleLoader(self.configuration).load(SimpleNamespace(absolute_module_path=str(directory)))
        document = json.loads((directory/'resources/agents_manager.module.json').read_text())
        document.update(absolute_module_path=str(directory), runtime=['main'], is_runtime=False)
        managed = ClassBuilder(ClassLoader({'children':[document]}), self.configuration).build_class_tree()
        remote = managed['agents_manager'].instance_object
        registry = {'schema_version':1, 'agents':{}}
        for application in (local, remote):
            factory = application._agents_service._services_factory
            factory.create_context = Mock(return_value=self.context)
            factory.create = Mock()
            factory.create.return_value.registry.sync.return_value = registry
        self.assertEqual(local.execute(method_name='list', flags={'show':True}), registry)
        self.assertEqual(remote.execute('list', {'show':True}, None), registry)
        self.assertEqual(local.help('list')['command'], remote.help('list', {}, None)['command'])

    def test_wheel_packages_factory_and_adapter(self):
        import shutil
        import zipfile
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base/'source'
            shutil.copytree(ROOT/'src/agents_manager', source, ignore=shutil.ignore_patterns('__pycache__', '*.egg-info', 'build'))
            wheels = base/'wheels'
            wheels.mkdir()
            result = subprocess.run([sys.executable, '-c', 'from setuptools.build_meta import build_wheel; import sys; build_wheel(sys.argv[1])', str(wheels)], cwd=source, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(next(wheels.glob('*.whl'))) as archive:
                for relative in ('app/services/agent_services_factory.py', 'open_claw/facade.py'):
                    self.assertIn('agents_manager/'+relative, archive.namelist())
                self.assertFalse(any('/tests/' in name or '/commands/' in name for name in archive.namelist()))
                self.assertFalse(any(name.endswith('entry_points.txt') for name in archive.namelist()))
