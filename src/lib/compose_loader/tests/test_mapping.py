from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from lib.compose_loader import (
    Build, ComposeData, ComposeLoader, Environment, EnvironmentVariable,
    Port, Ports, Service, Services, VolumeDefinition,
)
from lib.compose_loader import models


class MappingTests(unittest.TestCase):
    def test_every_public_model_exposes_conversion(self) -> None:
        for name in models.__all__:
            with self.subTest(model=name):
                self.assertTrue(callable(getattr(getattr(models, name), "to_mapping")))

    def test_conversion_is_recursive_and_preserves_false_zero_and_empty_values(self) -> None:
        data = ComposeData(services=Services(web=Service(
            name="web", build=Build(context="."),
            ports=Ports([Port(target=80, published=0)]),
            environment=Environment(
                TOKEN=EnvironmentVariable("TOKEN"),
                EMPTY=EnvironmentVariable("EMPTY", ""),
                FLAG=EnvironmentVariable("FLAG", False),
            ),
        )))
        mapping = data.to_mapping()
        self.assertIs(type(mapping), dict)
        web = mapping["services"]["web"]
        self.assertIs(type(web), dict)
        self.assertEqual(web["build"], {"context": ".", "args": {}})
        self.assertIs(type(web["ports"]), list)
        self.assertIs(type(web["ports"][0]), dict)
        self.assertEqual(web["ports"][0]["published"], 0)
        self.assertNotIn("host_ip", web["ports"][0])
        self.assertEqual(web["environment"], {"TOKEN": None, "EMPTY": "", "FLAG": False})
        self.assertEqual(web["profiles"], [])

    def test_mapping_is_independent_of_model_and_extra_is_flattened(self) -> None:
        service = Service(name="web", command=["echo", "hello"],
                          extra={"deploy": {"replicas": 2}, "name": "cannot-override"})
        result = service.to_mapping()
        self.assertEqual(result["name"], "web")
        self.assertNotIn("extra", result)
        result["deploy"]["replicas"] = 5
        result["command"].append("changed")
        self.assertEqual(service.extra["deploy"]["replicas"], 2)
        self.assertEqual(service.command, ["echo", "hello"])

    def test_empty_definition_uses_compose_key_as_docker_name(self) -> None:
        self.assertEqual(VolumeDefinition().to_docker_kwargs("database"), {"name": "database"})
        with self.assertRaises(ValueError):
            VolumeDefinition().to_docker_kwargs("")

    def test_docker_kwargs_are_filtered_and_labels_are_normalized(self) -> None:
        volume = VolumeDefinition(
            name="actual-db", driver="local", driver_opts={"type": "none"},
            labels=["team=backend", "empty", "url=a=b"], extra={"x-note": "keep"},
        )
        kwargs = volume.to_docker_kwargs("database")
        self.assertEqual(kwargs, {
            "name": "actual-db", "driver": "local", "driver_opts": {"type": "none"},
            "labels": {"team": "backend", "empty": "", "url": "a=b"},
        })
        kwargs["driver_opts"]["type"] = "changed"
        self.assertEqual(volume.driver_opts, {"type": "none"})
        self.assertIn("external", volume.to_mapping())
        self.assertEqual(volume.to_mapping()["x-note"], "keep")
        self.assertEqual(VolumeDefinition(labels={"team": "backend"}).to_docker_kwargs("db"),
                         {"name": "db", "labels": {"team": "backend"}})

    def test_external_volumes_cannot_be_converted_to_creation_kwargs(self) -> None:
        for external in (True, {"name": "legacy-db"}, {}):
            with self.subTest(external=external), self.assertRaisesRegex(ValueError, "External"):
                VolumeDefinition(external=external).to_docker_kwargs("db")

    def test_loaded_definitions_work_with_sdk_call_signature(self) -> None:
        def create(name=None, driver=None, driver_opts=None, labels=None):
            return name

        client = Mock()
        client.volumes.create = Mock(side_effect=create)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "compose.yml"
            path.write_text('''
volumes:
  db:
  cache:
    name: actual-cache
    driver: local
    labels: ["team=backend"]
  shared:
    external: true
    name: existing-shared
''', encoding="utf-8")
            compose = ComposeLoader.loadYaml(path)
        for key, volume in compose.volumes.items():
            if volume.external:
                client.volumes.get(volume.name or key)
            else:
                client.volumes.create(**volume.to_docker_kwargs(key))
        self.assertEqual(client.volumes.create.call_count, 2)
        client.volumes.create.assert_any_call(name="db")
        client.volumes.create.assert_any_call(name="actual-cache", driver="local", labels={"team": "backend"})
        client.volumes.get.assert_called_once_with("existing-shared")


if __name__ == "__main__":
    unittest.main()
