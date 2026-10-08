"""Packaging and import checks that expose existing implementation errors."""

import ast
import importlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_python_sources_have_valid_syntax(self):
        for source in ROOT.rglob('*.py'):
            with self.subTest(source=source.relative_to(ROOT)):
                ast.parse(source.read_text(encoding='utf-8'), filename=str(source))

    def test_public_api_imports(self):
        package = importlib.import_module('manifests')
        self.assertEqual(package.__all__, ['ManifestsApp', 'ManifestValidator'])
        namespace = {}
        exec('from manifests import *', namespace)
        self.assertEqual(set(namespace) - {'__builtins__'}, set(package.__all__))
        self.assertTrue(callable(package.ManifestValidator.validate))

    def test_distribution_builds_and_contains_implementation(self):
        with tempfile.TemporaryDirectory(prefix='manifests-package-') as directory:
            root = Path(directory)
            shutil.copytree(ROOT, root / 'source', ignore=shutil.ignore_patterns(
                '__pycache__', '*.egg-info', 'build',
            ))
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--no-index',
                '--no-build-isolation', '--no-cache-dir', '--wheel-dir',
                str(root / 'wheels'), str(root / 'source'),
            ], cwd=root, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with zipfile.ZipFile(next((root / 'wheels').glob('*.whl'))) as archive:
                files = set(archive.namelist())
                for name in (
                    'manifests/__init__.py', 'manifests/app/manifests_app.py',
                    'manifests/app/helpers/manifest_validator.py',
                    'manifests/app/helpers/manifests_validator/abstract.py',
                    'manifests/app/helpers/manifests_validator/environment.py',
                    'manifests/app/models/environment/environment_manifest.py',
                    'manifests/app/models/modules/module_manifest.py',
                    'manifests/app/consts/__init__.py',
                    'manifests/__main__.py',
                    'manifests/app/models/modules/modules_manifest_module_manifest.py',
                ):
                    self.assertIn(name, files)
                self.assertNotIn('manifests/app/helpers/manifests_validator/validator.py', files)
                self.assertNotIn('manifests/app/helpers/manifests_loader.py', files)
                self.assertFalse(any('/tests/' in name for name in files))


if __name__ == '__main__':
    unittest.main()
