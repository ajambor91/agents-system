"""External module help is shared by runtime and console catalogs."""
import copy
import json
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from internal_scripts.render_modules_manifest import render
from internal_scripts.common import RenderError
from lib.modules_catalog import ModulesFactory
from manifests import ManifestsApp

resolve_module_manifests = ManifestsApp().resolve_module_manifests
from manifests.app.helpers.manifest_validator import ManifestValidator
from manifests.app.exceptions import ManifestValidationError
from agents_system_cli.app.services.renderer import Renderer
from agents_system_cli.app.services.flag_parser import FlagParser
from unittest.mock import patch
from _runtime.app.runtime_app import RuntimeApp


class SplitManifestTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name) / 'modules.json'
        render(package_dir=ROOT, app_dir=ROOT, modules_dir=ROOT / 'src',
               manifest_path=self.output, output=self.output, force=False)
        self.data = json.loads(self.output.read_text())

    def test_catalog_and_validator_load_external_help_without_changing_sources(self):
        before = copy.deepcopy(self.data)
        self.assertTrue(ManifestValidator.validate(self.data))
        catalog = ModulesFactory.create_modules_from_json_file(self.output)
        system = catalog.modules['agents_system']
        self.assertIn('modules', system.commands)
        self.assertEqual(system.commands['modules'].method, 'modules')
        self.assertTrue(system.commands['modules'].flags)
        self.assertEqual(system.usage, 'asystem system <command> [flags]')
        resolved = resolve_module_manifests(self.data)
        self.assertTrue(ManifestValidator.validate(resolved))
        self.assertEqual(ModulesFactory.create_modules_from_dict(resolved).commands.keys(), catalog.commands.keys())
        self.assertEqual(self.data, before)
        for child in self.data['children']:
            self.assertFalse(set(child) & {'commands', 'description', 'usage', 'menu_name'})
            self.assertTrue(Path(child['manifest_path']).is_file())

    def test_installed_tree_uses_its_own_module_documents(self):
        installed = Path(self.temporary.name) / 'installed'
        installed.mkdir()
        modules = installed / 'src'
        modules.mkdir()
        for child in self.data['children']:
            relative = Path(child['absolute_module_path']).relative_to(ROOT / 'src')
            target = modules / relative / 'resources'
            target.mkdir(parents=True)
            shutil.copy2(child['manifest_path'], target)
        output = installed / 'config' / 'modules.json'
        render(package_dir=ROOT, app_dir=installed, modules_dir=modules,
               manifest_path=output, output=output, force=False)
        document = json.loads(output.read_text())
        self.assertTrue(ManifestValidator.validate(document))
        for child in document['children']:
            self.assertTrue(Path(child['manifest_path']).is_relative_to(modules))
        self.assertIn('system.modules', ModulesFactory.create_modules_from_json_file(output).commands)

    def test_flag_parser_uses_external_flags(self):
        command = ModulesFactory.create_modules_from_dict(self.data).commands['system.modules']
        flags = FlagParser.parse(command, ['--installed'])
        self.assertTrue(next(flag for flag in flags if flag.name == 'installed').value)

    def test_runtime_bootstrap_builds_the_same_catalog(self):
        config = Path(self.temporary.name) / 'app_env.json'
        config.write_text(json.dumps({'variables': [
            {'name': 'MODULES_MANIFEST_PATH', 'value': str(self.output)}
        ]}))
        class Configuration:
            MODULES_MANIFEST_PATH = str(self.output)
            def __init__(self, variables):
                pass
        with patch.dict('os.environ', {'ABSOLUTE_CONFIG_PATH': str(config)}), \
             patch('_runtime.app.runtime_app.Configuration', Configuration), \
             patch('_runtime.app.runtime_app.ConfigurationWrapper'), \
             patch('_runtime.app.runtime_app.ClassBuilder') as builder, \
             patch('_runtime.app.runtime_app.InstanceManager') as manager:
            builder.return_value.build_class_tree.return_value = {}
            runtime = RuntimeApp()
            bootstrap = manager.return_value.initialize_main_application.call_args
            self.assertIs(bootstrap.args[0], runtime.configuration)
            source = builder.call_args.args[0]._modules_list
            self.assertIn('commands', source['children'][0])
            self.assertEqual(ModulesFactory.create_modules_from_dict(source).commands.keys(),
                             ModulesFactory.create_modules_from_dict(self.data).commands.keys())

    def test_human_help_uses_module_usage_and_command_flags(self):
        catalog = ModulesFactory.create_modules_from_dict(self.data)
        renderer = Renderer(object(), 'human-raw')
        renderer.init_mode()
        system = catalog.modules['agents_system']
        self.assertIn(system.usage, renderer.section_help('system', system).stdout)
        help_text = renderer.command_help('system', system.commands['modules']).stdout
        self.assertIn('--installed', help_text)
        self.assertIn('--running', help_text)

    def test_json_help_includes_module_usage_commands_and_flags(self):
        system = ModulesFactory.create_modules_from_dict(self.data).modules['agents_system']
        for mode in ('json', 'agent'):
            renderer = Renderer(object(), mode)
            section = json.loads(renderer.section_help('system', system).stdout)
            self.assertEqual(section['usage'], system.usage)
            self.assertEqual(section['commands'][0]['name'], 'modules')
            self.assertTrue(section['commands'][0]['flags'])
            command = json.loads(renderer.command_help('system', system.commands['modules']).stdout)
            self.assertEqual(command['path'], ['system', 'modules'])
            self.assertTrue(command['command']['flags'])

    def test_missing_malformed_and_mismatched_module_fail(self):
        child = self.data['children'][0]
        original = json.loads(Path(child['manifest_path']).read_text())
        path = Path(self.temporary.name) / 'detail.json'
        child['manifest_path'] = str(path)
        with self.assertRaises(ManifestValidationError) as caught:
            ModulesFactory.create_modules_from_dict(self.data)
        self.assertIsInstance(caught.exception.errors[0].error, FileNotFoundError)
        path.write_text('{broken')
        with self.assertRaises(ValueError):
            ModulesFactory.create_modules_from_dict(self.data)
        for field, value in [('module_name', 'wrong'), ('schema_version', 2), ('kind', 'wrong'), ('commands', {})]:
            with self.subTest(field=field):
                detail = dict(original, **{field: value})
                path.write_text(json.dumps(detail))
                with self.assertRaises(ValueError):
                    ModulesFactory.create_modules_from_dict(self.data)
        detail = copy.deepcopy(original)
        detail['commands'].append(detail['commands'][0])
        path.write_text(json.dumps(detail))
        with self.assertRaisesRegex(ValueError, 'duplicate name'):
            ModulesFactory.create_modules_from_dict(self.data)

    def test_unsafe_paths_and_duplicate_modules_fail(self):
        for path in ('relative.json', '/tmp/../detail.json'):
            self.data['children'][0]['manifest_path'] = path
            with self.assertRaises(ValueError):
                ModulesFactory.create_modules_from_dict(self.data)
        self.data['children'].append(copy.deepcopy(self.data['children'][0]))
        with self.assertRaises(ValueError):
            ModulesFactory.create_modules_from_dict(self.data)

    def test_inline_help_cannot_override_module_document(self):
        self.data['children'][0]['commands'] = []
        with self.assertRaisesRegex(ValueError, 'only in the module manifest'):
            ModulesFactory.create_modules_from_dict(self.data)

    def test_wrapper_renders_explicit_paths_and_refuses_overwrite(self):
        argv = [str(ROOT / 'internal_scripts/render-modules-manifest.sh'),
                '--app-dir', str(ROOT), '--modules-dir', str(ROOT / 'src'),
                '--manifest-path', str(self.output), '--output', str(self.output)]
        result = subprocess.run(argv, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--force', result.stderr)
        result = subprocess.run([*argv, '--force'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
