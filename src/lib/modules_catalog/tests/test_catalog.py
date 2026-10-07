"""Behavioral tests for the seven public catalog classes."""

import copy
import importlib
import json
import tempfile
import unittest
from pathlib import Path

from lib.modules_catalog import (
    Flag, Module, Command, ModulesCatalog, ExclusiveGroup, CommandInput, ModulesFactory,
)


PUBLIC = ['Flag', 'Module', 'Command', 'ModulesCatalog', 'ExclusiveGroup', 'CommandInput', 'ModulesFactory']


def document():
    return {
        'schema_version': 1, 'version': '0.1.0', 'kind': 'modules-catalog',
        'app_name': 'example', 'absolute_path': '/opt/example',
        'menu_name': 'Przykład', 'description': 'Katalog modułów',
        'sections': {'system': {
            'absolute_path': '/opt/example', 'module_name': 'system',
            'absolute_module_path': '/opt/example/system',
            'menu_name': 'System', 'description': 'Commands',
            'commands': [{
                'name': 'status', 'method': 'show_status', 'description': 'Status',
                'usage': 'status --verbose', 'implementation_status': 'implemented',
                'flags': [{
                    'name': 'verbose', 'short': '-v', 'long': '--verbose',
                    'aliases': ['--details'], 'description': 'Detailed output',
                    'usage': '--verbose', 'takes_value': False, 'type': 'boolean',
                    'required': False, 'default': False,
                }],
                'input': {'source': 'stdin', 'type': 'json', 'maximum_bytes': 1024},
                'exclusive_groups': [{'members': ['verbose', 'quiet'], 'minimum': 0, 'maximum': 1}],
            }],
        }},
    }


class CatalogTests(unittest.TestCase):
    def test_exact_public_exports_in_both_namespaces(self):
        for name in ('lib.modules_catalog', 'modules_catalog'):
            with self.subTest(namespace=name):
                package = importlib.import_module(name)
                self.assertEqual(package.__all__, PUBLIC)
                namespace = {}
                exec(f'from {name} import *', namespace)
                self.assertEqual(set(namespace) - {'__builtins__'}, set(PUBLIC))
                catalog = package.ModulesFactory.create_modules_from_dict(document())
                self.assertIsInstance(catalog, package.ModulesCatalog)
                self.assertIsInstance(catalog.modules[0], package.Module)
                self.assertIsInstance(catalog.commands['system.status'], package.Command)

    def test_full_catalog_models_and_owner_link(self):
        catalog = ModulesFactory.create_modules_from_dict(document())
        self.assertIsInstance(catalog, ModulesCatalog)
        self.assertEqual(catalog.menu_name, 'Przykład')
        module = catalog.modules[0]
        command = catalog.commands['system.status']
        self.assertIsInstance(module, Module)
        self.assertIsInstance(command, Command)
        self.assertIs(command, module.commands[0])
        self.assertIs(command.module, module)
        self.assertEqual(command.method, 'show_status')
        self.assertIsInstance(command.flags[0], Flag)
        self.assertEqual(command.flags[0].aliases, ['--details'])
        self.assertIsInstance(command.input, CommandInput)
        self.assertEqual(command.input.maximum_bytes, 1024)
        self.assertIsInstance(command.exclusive_groups[0], ExclusiveGroup)
        self.assertEqual(command.exclusive_groups[0].members, ['verbose', 'quiet'])

    def test_json_text_and_utf8_bytes(self):
        raw = json.dumps(document(), ensure_ascii=False)
        for source in (raw, raw.encode('utf-8')):
            catalog = ModulesFactory.create_modules_from_json(source)
            self.assertEqual(catalog.menu_name, 'Przykład')
            self.assertEqual(list(catalog.commands), ['system.status'])

    def test_json_file_accepts_path_and_string(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'modules.json'
            path.write_text(json.dumps(document(), ensure_ascii=False), encoding='utf-8')
            for source in (path, str(path)):
                catalog = ModulesFactory.create_modules_from_json_file(source)
                self.assertEqual(catalog.description, 'Katalog modułów')
                self.assertEqual(catalog.commands['system.status'].method, 'show_status')

    def test_optional_fields_and_explicit_section_name(self):
        data = document()
        data['sections']['system']['section_name'] = 'admin'
        command = data['sections']['system']['commands'][0]
        for key in ('method', 'flags', 'input', 'exclusive_groups'):
            del command[key]
        result = ModulesFactory.create_modules_from_dict(data).commands['admin.status']
        self.assertIsNone(result.method)
        self.assertIsNone(result.input)
        self.assertEqual(result.flags, [])
        self.assertEqual(result.exclusive_groups, [])

    def test_optional_flag_fields(self):
        data = document()
        flag = data['sections']['system']['commands'][0]['flags'][0]
        for key in ('short', 'long', 'aliases', 'default'):
            del flag[key]
        result = ModulesFactory.create_modules_from_dict(data).commands['system.status'].flags[0]
        self.assertIsNone(result.short)
        self.assertIsNone(result.long)
        self.assertIsNone(result.default)
        self.assertEqual(result.aliases, [])

    def test_empty_catalog_and_module_without_commands(self):
        data = document()
        del data['sections']['system']['commands']
        catalog = ModulesFactory.create_modules_from_dict(data)
        self.assertEqual(catalog.modules[0].commands, [])
        self.assertEqual(catalog.commands, {})
        data['sections'] = {}
        catalog = ModulesFactory.create_modules_from_dict(data)
        self.assertEqual(catalog.modules, [])
        self.assertEqual(catalog.commands, {})

    def test_duplicate_command_in_section_is_rejected(self):
        data = document()
        commands = data['sections']['system']['commands']
        commands.append(copy.deepcopy(commands[0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate command: system.status'):
            ModulesFactory.create_modules_from_dict(data)

    def test_same_name_in_distinct_sections_is_allowed(self):
        data = document()
        data['sections']['other'] = copy.deepcopy(data['sections']['system'])
        catalog = ModulesFactory.create_modules_from_dict(data)
        self.assertEqual(set(catalog.commands), {'system.status', 'other.status'})
        self.assertIsNot(catalog.commands['system.status'].module, catalog.commands['other.status'].module)

    def test_errors_are_propagated(self):
        with self.assertRaises(json.JSONDecodeError):
            ModulesFactory.create_modules_from_json('{invalid')
        with self.assertRaises(KeyError):
            ModulesFactory.create_modules_from_dict({})
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                ModulesFactory.create_modules_from_json_file(Path(directory) / 'missing.json')
        with self.assertRaises(TypeError):
            ModulesFactory()

    def test_input_not_modified_and_new_catalogs_have_independent_owners(self):
        data = document()
        original = copy.deepcopy(data)
        first = ModulesFactory.create_modules_from_dict(data)
        second = ModulesFactory.create_modules_from_dict(data)
        self.assertEqual(data, original)
        self.assertIsNot(first, second)
        self.assertIsNot(first.commands['system.status'], second.commands['system.status'])
        self.assertIs(first.commands['system.status'].module, first.modules[0])
        self.assertIs(second.commands['system.status'].module, second.modules[0])


if __name__ == '__main__':
    unittest.main()
