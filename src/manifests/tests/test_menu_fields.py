"""Menu metadata is required only for visible modules."""

import copy
import json
from pathlib import Path
import unittest

from manifests import ManifestValidator
from manifests.app.exceptions import ManifestValidationError
from lib.modules_catalog import ModulesFactory
from manifests import ManifestsApp

resolve_module_manifests = ManifestsApp().resolve_module_manifests


TEMPLATE = Path(__file__).resolve().parents[3] / "resources/agents-system.module.template.json"


class MenuFieldsTests(unittest.TestCase):
    def setUp(self):
        source = TEMPLATE.read_text(encoding="utf-8").replace(
            "${MODULES_DIR}", str(TEMPLATE.parent.parent / "src")
        )
        self.document = resolve_module_manifests(json.loads(source))

    def test_template_validates(self):
        self.assertTrue(ManifestValidator.validate(self.document))

    def test_visible_module_requires_both_names(self):
        for field in ("section_name", "menu_name"):
            for value in (None, "", " ", 42):
                with self.subTest(field=field, value=value):
                    document = copy.deepcopy(self.document)
                    document["children"][0][field] = value
                    with self.assertRaises(ManifestValidationError):
                        ManifestValidator.validate(document)

    def test_hidden_module_accepts_null_or_nonempty_name(self):
        for value in (None, "Internal"):
            document = copy.deepcopy(self.document)
            for field in ("section_name", "menu_name"):
                document["children"][1][field] = value
            self.assertTrue(ManifestValidator.validate(document))

    def test_hidden_module_rejects_invalid_names_and_missing_fields(self):
        for field in ("section_name", "menu_name"):
            for value in ("", " ", 42):
                with self.subTest(field=field, value=value):
                    document = copy.deepcopy(self.document)
                    document["children"][1][field] = value
                    with self.assertRaises(ManifestValidationError):
                        ManifestValidator.validate(document)
            document = copy.deepcopy(self.document)
            del document["children"][1][field]
            with self.assertRaises(ManifestValidationError):
                ManifestValidator.validate(document)

    def test_catalog_keeps_hidden_modules_out_of_section_index(self):
        catalog = ModulesFactory.create_modules_from_dict(self.document)
        self.assertEqual(set(catalog.modules), {
            module["module_name"] for module in self.document["children"]
        })
        self.assertEqual(set(catalog.modules_by_section), {"agents", "system"})
        self.assertNotIn(None, catalog.modules_by_section)
        self.assertIs(catalog.modules_by_section["system"], catalog.modules["agents_system"])
