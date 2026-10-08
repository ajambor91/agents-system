"""Strategies only select models; models own recursive validation and errors."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from manifests import ManifestValidator
from manifests.app.exceptions import ManifestValidationError
from manifests.app.helpers.manifests_validator import (
    EnvironmentManifestValidationStrategy, ModuleManifestValidationStrategy,
    ModulesManifestValidationStrategy,
)
from manifests.app.models.environment import EnvironmentManifest, EnvironmentVariableManifest
from manifests.app.models.modules.module_manifest import ModuleManifest
from manifests.app.models.modules.modules_manifest_module_manifest import ModulesManifestModuleManifest

ROOT = Path(__file__).resolve().parents[3]


class ModelStrategyTests(unittest.TestCase):
    def test_each_strategy_constructs_the_expected_model_without_validation(self):
        for strategy, model_class in (
            (EnvironmentManifestValidationStrategy(), EnvironmentManifest),
            (ModuleManifestValidationStrategy(), ModuleManifest),
            (ModulesManifestValidationStrategy(), ModulesManifestModuleManifest),
        ):
            with self.subTest(kind=strategy.kind):
                model = strategy.create_model({'kind': strategy.kind})
                self.assertIsInstance(model, model_class)
                self.assertEqual(model.errors, [])
                with self.assertRaises(ManifestValidationError):
                    model.validate()
                self.assertGreater(len(model.errors), 1)
                with patch.object(model_class, 'validate', autospec=True) as validate:
                    self.assertTrue(ManifestValidator.validate({'kind': strategy.kind}))
                    validate.assert_called_once()

    def test_environment_variable_validates_itself(self):
        for name in ('APP_DIR', 'USER_SYSTEM_HOME'):
            model = EnvironmentVariableManifest.from_dict({'name': name, 'value': '../bad', 'description': '', 'example': ''})
            with self.assertRaises(ManifestValidationError):
                model.validate()
            self.assertGreater(len(model.errors), 2)

    def test_module_model_validates_nested_flags_without_strategy(self):
        path = ROOT / 'src/agents_manager/resources/agents_manager.module.json'
        data = json.loads(path.read_text())
        data['commands'][0]['flags'][0]['takes_value'] = 'yes'
        model = ModuleManifest.from_dict(data)
        with self.assertRaises(ManifestValidationError) as caught:
            model.validate()
        self.assertTrue(any('commands[0].flags[0].takes_value' in issue.path for issue in caught.exception.errors))

    def test_environment_model_validates_required_values_and_paths(self):
        model = EnvironmentManifest.from_dict({'schema_version': 1, 'kind': 'agents-system-environment', 'variables': []})
        with self.assertRaises(ManifestValidationError):
            model.validate()
        self.assertTrue(any(issue.path == 'variables.APP_DIR' for issue in model.errors))


if __name__ == '__main__':
    unittest.main()
