"""Build and import the distribution outside the repository without dependencies."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile


class PackagingTests(unittest.TestCase):
    def test_wheel_imports_and_factory_work_in_isolation(self):
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='modules-catalog-package-') as directory:
            root = Path(directory)
            shutil.copytree(source, root / 'source', ignore=shutil.ignore_patterns(
                '__pycache__', '*.egg-info', 'build',
            ))
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'wheel', '--no-deps',
                '--no-build-isolation', '--no-index', '--no-cache-dir',
                '--wheel-dir', str(root / 'wheels'), str(root / 'source'),
            ], cwd=root, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            wheel = next((root / 'wheels').glob('*.whl'))
            with zipfile.ZipFile(wheel) as archive:
                self.assertFalse(any('/tests/' in name for name in archive.namelist()))
                archive.extractall(root / 'installed')
            document = {
                'schema_version': 1, 'version': '1', 'kind': 'modules-catalog',
                'app_name': 'test', 'absolute_path': '/tmp/test',
                'menu_name': 'test', 'description': 'test', 'sections': {},
            }
            script = '''
import importlib
import sys
sys.path.insert(0, sys.argv[1])
expected = ['Flag', 'Module', 'Command', 'ModulesCatalog', 'ExclusiveGroup', 'CommandInput', 'ModulesFactory']
for name in ('modules_catalog', 'lib.modules_catalog'):
    package = importlib.import_module(name)
    assert package.__all__ == expected
    catalog = package.ModulesFactory.create_modules_from_json(sys.argv[2])
    assert isinstance(catalog, package.ModulesCatalog)
    assert catalog.modules == [] and catalog.commands == {}
assert 'shared' not in sys.modules
assert 'attr' not in sys.modules
'''
            environment = dict(os.environ)
            environment.pop('PYTHONPATH', None)
            environment['PYTHONDONTWRITEBYTECODE'] = '1'
            result = subprocess.run([
                sys.executable, '-S', '-c', script, str(root / 'installed'),
                json.dumps(document),
            ], cwd=root, env=environment, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
