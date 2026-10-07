"""Error contracts for malformed manifests and inaccessible files."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lib.manifests_loader import ManifestsLoader
from manifests import ManifestValidator
from manifests.app.exceptions import (
    ManifestJsonError,
    ManifestReadError,
    ManifestStructureError,
    ManifestValidationError,
    UnsupportedManifestKindError,
)


class ManifestErrorTests(unittest.TestCase):
    def test_loader_errors_and_valid_object(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            with self.assertRaises(FileNotFoundError):
                ManifestsLoader.load_manifest(path)
            for content, error in (
                (b"{", ManifestJsonError),
                (b"\xff", ManifestJsonError),
            ):
                with self.subTest(content=content):
                    path.write_bytes(content)
                    with self.assertRaises(error):
                        ManifestsLoader.load_manifest(path)
            path.write_text('{"kind": "example"}', encoding="utf-8")
            self.assertEqual(ManifestsLoader.load_manifest(path), {"kind": "example"})

    def test_read_error_preserves_cause(self):
        with patch.object(Path, "open", side_effect=PermissionError("denied")):
            with self.assertRaises(ManifestReadError) as caught:
                ManifestsLoader.load_manifest(Path("manifest.json"))
        self.assertIsInstance(caught.exception.__cause__, PermissionError)

    def test_invalid_root(self):
        for data in (None, [], "text"):
            with self.subTest(data=data), self.assertRaises(ManifestStructureError):
                ManifestValidator.validate(data)

    def test_unsupported_kind_including_unhashable_values(self):
        for kind in (None, "unknown", [], {}):
            with self.subTest(kind=kind), self.assertRaises(UnsupportedManifestKindError):
                ManifestValidator.validate({"kind": kind})

    def test_field_errors_remain_aggregated(self):
        with self.assertRaises(ManifestValidationError) as caught:
            ManifestValidator.validate({"kind": "agents-system-modules-manifest"})
        self.assertGreater(len(caught.exception.errors), 1)
