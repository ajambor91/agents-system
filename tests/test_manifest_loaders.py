"""Shared manifest I/O, installed records and executable package contracts."""
from __future__ import annotations

import ast
import copy
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from lib.json_loader import JsonLoader
from manifests.app.catalog import ManifestCatalog
from manifests import ManifestsApp, ManifestValidator
from lib.manifests_loader import ManifestsLoader
from agents_system.app.services.installed_modules import InstalledModulesReader
from agents_system.app.exceptions import ConfigurationError
from internal_scripts.render_modules_manifest import render


class ManifestsLoaderTests(unittest.TestCase):
    def test_json_library_handles_utf8_and_all_json_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'dokument z polską nazwą.json'
            for document in ({'opis': 'żółć'}, [1, True], 0, False, None):
                with self.subTest(document=document):
                    content = json.dumps(document, ensure_ascii=False)
                    path.write_text(content, encoding='utf-8')
                    self.assertEqual(JsonLoader.load(path), document)
                    self.assertEqual(JsonLoader.loads(content), document)
            with self.assertRaises(RuntimeError):
                JsonLoader.getJsonFileContent(path)

    def test_manifest_reader_delegates_file_and_string_io_to_json_library(self):
        document = {'kind': 'example'}
        with patch.object(JsonLoader, 'load', return_value=document) as load:
            self.assertIs(ManifestsLoader.load_manifest('/tmp/example.json'), document)
            load.assert_called_once_with('/tmp/example.json')
        with patch.object(JsonLoader, 'loads', return_value=document) as loads:
            self.assertIs(ManifestsLoader.parse_manifest('{"kind":"example"}'), document)
            loads.assert_called_once_with('{"kind":"example"}')
        for document in ([], None, 1, {'kind': 'unknown'}):
            with self.subTest(document=document), patch.object(JsonLoader, 'load', return_value=document), patch.object(ManifestValidator, 'validate', side_effect=AssertionError('loader called validator')):
                self.assertIs(ManifestsLoader.load_manifest('/tmp/example.json'), document)

    def test_manifests_application_calls_loader_and_owns_validation(self):
        application = ManifestsApp()
        raw = {'kind': 'unknown'}
        with patch.object(ManifestsLoader, 'load_manifest', return_value=raw) as load, patch.object(ManifestValidator, 'validate') as validate:
            self.assertIs(application.load_manifest('/tmp/example.json'), raw)
            load.assert_called_once_with('/tmp/example.json')
            validate.assert_not_called()
            application.validate_manifest(raw)
            validate.assert_called_once_with(raw)

    def test_menu_reads_resolved_documents_and_leaves_sources_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'modules.json'
            render(package_dir=ROOT, app_dir=ROOT, modules_dir=ROOT / 'src', manifest_path=path, output=path, force=False)
            before = path.read_bytes()
            menu = ManifestCatalog(path).load()
            self.assertEqual(set(menu['sections']), {'agents', 'system'})
            self.assertEqual(menu['sections']['agents']['module_name'], 'agents_manager')
            self.assertEqual(menu['sections']['system']['commands'][0]['name'], 'modules')
            self.assertEqual(path.read_bytes(), before)

    def test_installed_module_records_are_sorted_deduplicated_and_conflicts_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = {'name': 'first', 'dir': 'first'}
            second = {'name': 'second', 'dir': 'second'}
            (root / 'a.json').write_text(json.dumps({'modules': [first, second]}))
            (root / 'b.json').write_text(json.dumps({'modules': [copy.deepcopy(first)]}))
            configuration = type('Settings', (), {'INSTALLED_MODULES_DIR': str(root)})()
            reader = InstalledModulesReader(configuration)
            self.assertEqual(reader.list_modules(), [first, second])
            (root / 'b.json').write_text(json.dumps({'modules': [{'name': 'first', 'dir': 'foreign'}]}))
            with self.assertRaisesRegex(ConfigurationError, 'sprzeczne wpisy'):
                reader.list_modules()
            self.assertEqual(ManifestsLoader.load_directory(root / 'absent'), {})

    def test_manifest_module_help_validates_known_kind_and_reports_failure_without_traceback(self):
        environment = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1')
        with tempfile.TemporaryDirectory() as directory:
            for prefix in ([sys.executable, '-m', 'manifests'], [sys.executable, str(ROOT / 'src/manifests/__main__.py')]):
                result = subprocess.run([*prefix, '--help'], cwd=directory, env=environment, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                result = subprocess.run([*prefix, str(ROOT / 'src/agents_system/resources/agents_system.module.json')], cwd=directory, env=environment, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(json.loads(result.stdout)['valid'])
                invalid = Path(directory) / 'broken.json'
                invalid.write_text('{"kind":"module-manifest"}')
                result = subprocess.run([*prefix, str(invalid)], cwd=directory, env=environment, capture_output=True, text=True)
                self.assertEqual(result.returncode, 1)
                self.assertIn('validation failed', result.stderr)
                self.assertNotIn('Traceback', result.stderr)

    def test_old_loader_locations_and_plain_main_files_are_removed(self):
        self.assertEqual(list((ROOT / 'src').rglob('main.py')), [])
        for filename in ('src/shared/json_loader.py', 'src/lib/modules_catalog/manifest_loader.py', 'src/manifests/app/helpers/manifests_loader.py', 'src/agents_system_cli/app/services/manifests.py'):
            self.assertFalse((ROOT / filename).exists())
        for source in (ROOT / 'src').rglob('*.py'):
            ast.parse(source.read_text(encoding='utf-8'), filename=str(source))


class LoaderPackagingTests(unittest.TestCase):
    def test_loader_wheels_import_without_application_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            wheels = base / 'wheels'
            wheels.mkdir()
            target = base / 'installed'
            for name in ('json_loader', 'manifests_loader'):
                source = base / name
                shutil.copytree(ROOT / 'src/lib' / name, source, ignore=shutil.ignore_patterns('__pycache__', '*.egg-info', 'build'))
                result = subprocess.run([sys.executable, '-c', 'from setuptools.build_meta import build_wheel; import sys; build_wheel(sys.argv[1])', str(wheels)], cwd=source, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            for wheel in wheels.glob('*.whl'):
                with zipfile.ZipFile(wheel) as archive:
                    self.assertFalse(any('/tests/' in name for name in archive.namelist()))
                    archive.extractall(target)
            path = base / 'manifest.json'
            path.write_text('{"opis": "żółć"}', encoding='utf-8')
            environment = dict(os.environ, PYTHONPATH=str(target), PYTHONDONTWRITEBYTECODE='1')
            script = '''from lib.json_loader import JsonLoader
from lib.manifests_loader import ManifestsLoader
from json_loader import JsonLoader as StandaloneJsonLoader
from manifests_loader import ManifestsLoader as StandaloneManifestsLoader
import sys
assert JsonLoader.load(sys.argv[1]) == {'opis': 'żółć'}
assert ManifestsLoader.load_manifest(sys.argv[1]) == StandaloneManifestsLoader.load_manifest(sys.argv[1])
assert StandaloneJsonLoader.loads('null') is None
assert 'manifests' not in sys.modules
'''
            result = subprocess.run([sys.executable, '-c', script, str(path)], cwd=base, env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
