"""The manager package works from a checkout and a standalone wheel."""
from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


class AgentsManagerPackagingTests(unittest.TestCase):
    def test_entrypoint_delegates_with_configuration(self):
        entrypoint = importlib.import_module('agents_manager.__main__')
        configuration = object()
        with patch.object(entrypoint, 'get_config', return_value=configuration), patch.object(entrypoint, 'AgentApplication') as application:
            application.return_value.run.return_value = 17
            self.assertEqual(entrypoint.main(), 17)
            application.assert_called_once_with(configuration)
            application.return_value.run.assert_called_once_with()

    def test_wheel_contains_services_metadata_and_help_and_imports_without_generic_app(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / 'source'
            shutil.copytree(ROOT / 'src/agents_manager', source, ignore=shutil.ignore_patterns('__pycache__', '*.egg-info', 'build'))
            wheels = base / 'wheels'
            wheels.mkdir()
            result = subprocess.run([sys.executable, '-c', 'from setuptools.build_meta import build_wheel; import sys; build_wheel(sys.argv[1])', str(wheels)], cwd=source, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            wheel = next(wheels.glob('*.whl'))
            with zipfile.ZipFile(wheel) as archive:
                names = set(archive.namelist())
                for name in ('agents_manager/__init__.py', 'agents_manager/__main__.py', 'agents_manager/app/services/__init__.py', 'agents_manager/meta.json', 'agents_manager/resources/agents_manager.module.json'):
                    self.assertIn(name, names)
                target = base / 'installed'
                archive.extractall(target)
            environment = dict(os.environ, PYTHONPATH=os.pathsep.join((str(target), str(ROOT / 'src'))), PYTHONDONTWRITEBYTECODE='1')
            result = subprocess.run([sys.executable, '-c', 'import agents_manager, agents_manager.__main__; import sys; assert "app" not in sys.modules; print(agents_manager.__file__)'], cwd=base, env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(target), result.stdout)
            metadata = json.loads((source / 'meta.json').read_text())
            self.assertEqual(metadata['entrypoint'], '__main__.py')
            settings = tomllib.loads((source / 'pyproject.toml').read_text())
            self.assertEqual(settings['project']['scripts']['agent-manager'], 'agents_manager.__main__:main')
