from pathlib import Path
import tempfile
import unittest

import yaml

from lib.compose_loader import ComposeLoader
from lib.compose_loader.models import (
    Build, ComposeData, Dependency, EnvironmentVariable, Healthcheck, Network,
    Port, Ports, Resource, ResourceReference, Service, ServiceNetwork,
    Volume, VolumeDefinition,
)


class ComposeLoaderTests(unittest.TestCase):
    def load(self, content: str, *, as_string: bool = False) -> ComposeData:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "compose.yml"
            path.write_text(content, encoding="utf-8")
            before = path.read_bytes()
            result = ComposeLoader.loadYaml(str(path) if as_string else path)
            self.assertEqual(path.read_bytes(), before)
            return result

    def test_short_forms_become_nested_models(self) -> None:
        data = self.load('''
name: przykład
services:
  web:
    build: ./web
    ports: ["127.0.0.1:8080:80/tcp", 443, "9000-9005:9000-9005/udp"]
    volumes: ["./data:/data:ro,z", "db:/db", "/cache"]
    environment: ["URL=http://example.test/?a=b", "TOKEN", "EMPTY="]
    depends_on: [db]
    networks: [backend]
    secrets: [password]
    configs: [settings]
    command: [echo, hello]
  db:
    image: postgres
volumes:
  db:
networks:
  backend:
    driver: bridge
secrets:
  password:
    file: ./password.txt
configs:
  settings:
    file: ./settings.conf
''')
        self.assertIsInstance(data, ComposeData)
        self.assertEqual(data.name, "przykład")
        web = data.services["web"]
        self.assertIsInstance(web, Service)
        self.assertIsInstance(web.build, Build)
        self.assertEqual(web.build.context, "./web")
        self.assertIsInstance(web.ports, Ports)
        self.assertEqual(web.ports[0], Port(target=80, published=8080, host_ip="127.0.0.1"))
        self.assertEqual(web.ports[1].target, 443)
        self.assertIsNone(web.ports[1].published)
        self.assertEqual(web.ports[2].published, "9000-9005")
        self.assertEqual(web.ports[2].protocol, "udp")
        self.assertIsInstance(web.volumes[0], Volume)
        self.assertEqual(web.volumes[0].type, "bind")
        self.assertTrue(web.volumes[0].read_only)
        self.assertEqual(web.volumes[1].source, "db")
        self.assertIsNone(web.volumes[2].source)
        self.assertIsInstance(web.environment["URL"], EnvironmentVariable)
        self.assertEqual(web.environment["URL"].value, "http://example.test/?a=b")
        self.assertIsNone(web.environment["TOKEN"].value)
        self.assertEqual(web.environment["EMPTY"].value, "")
        self.assertIsInstance(web.depends_on["db"], Dependency)
        self.assertEqual(web.depends_on["db"].condition, "service_started")
        self.assertIsInstance(web.networks["backend"], ServiceNetwork)
        self.assertIsInstance(data.networks["backend"], Network)
        self.assertIsInstance(data.volumes["db"], VolumeDefinition)
        self.assertIsInstance(data.secrets["password"], Resource)
        self.assertIsInstance(web.configs[0], ResourceReference)
        self.assertEqual(web.command, ["echo", "hello"])

    def test_long_forms_and_unknown_options_are_preserved(self) -> None:
        data = self.load('''
x-metadata: {owner: team}
services:
  web:
    build:
      context: ${SOURCE:-.}
      dockerfile: Dockerfile.dev
      args: ["FLAG=a=b", "TOKEN"]
      cache_from: [example/cache]
    ports:
      - target: 80
        published: "8080"
        protocol: tcp
        mode: host
        app_protocol: http
        x-option: keep
    volumes:
      - type: bind
        source: ./data
        target: /data
        read_only: true
        bind: {create_host_path: false}
    environment: {COUNT: 2, TOKEN: null, EMPTY: ""}
    depends_on:
      db: {condition: service_healthy, restart: true, required: false}
    networks:
      backend: {aliases: [www], ipv4_address: 172.20.0.2, priority: 10}
    healthcheck: {test: [CMD, curl, localhost], interval: 10s, retries: 3}
    secrets: [{source: password, target: token, uid: "1000", mode: 0400}]
    deploy: {replicas: 2}
networks:
  backend: {driver: bridge, ipam: {driver: default}}
volumes:
  db: {external: true, name: actual-db}
''', as_string=True)
        web = data.services["web"]
        self.assertEqual(web.build.context, "${SOURCE:-.}")
        self.assertEqual(web.build.args, {"FLAG": "a=b", "TOKEN": None})
        self.assertEqual(web.build.extra["cache_from"], ["example/cache"])
        self.assertEqual(web.ports[0].published, "8080")
        self.assertEqual(web.ports[0].extra["x-option"], "keep")
        self.assertFalse(web.volumes[0].extra["bind"]["create_host_path"])
        self.assertEqual(web.environment["COUNT"].value, 2)
        self.assertFalse(web.depends_on["db"].required)
        self.assertEqual(web.networks["backend"].aliases, ["www"])
        self.assertEqual(web.networks["backend"].extra["priority"], 10)
        self.assertIsInstance(web.healthcheck, Healthcheck)
        self.assertEqual(web.healthcheck.interval, "10s")
        self.assertEqual(web.secrets[0].mode, 0o400)
        self.assertEqual(web.extra["deploy"], {"replicas": 2})
        self.assertEqual(data.extra["x-metadata"], {"owner": "team"})
        self.assertEqual(data.networks["backend"].extra["ipam"], {"driver": "default"})
        self.assertTrue(data.volumes["db"].external)

    def test_ipv6_and_unresolved_port_variables(self) -> None:
        web = self.load('''
services:
  web:
    ports: ["[::1]:8080:80", "${PORT}:80", "53/udp"]
''').services["web"]
        self.assertEqual(web.ports[0].host_ip, "::1")
        self.assertEqual(web.ports[0].published, 8080)
        self.assertEqual(web.ports[1].published, "${PORT}")
        self.assertEqual(web.ports[2].protocol, "udp")

    def test_anchors_merge_and_defaults(self) -> None:
        data = self.load('''
x-defaults: &defaults
  image: example:latest
services:
  first:
    <<: *defaults
  second:
    <<: *defaults
''')
        self.assertEqual(data.services["first"].image, "example:latest")
        data.services["first"].ports.append(Port(target=80))
        self.assertEqual(data.services["second"].ports, [])
        self.assertEqual(self.load("{}"), ComposeData())

    def test_malformed_shapes_raise_value_error(self) -> None:
        for content in (
            "", "[]", "services: []", "services: {web: null}",
            "services: {web: {ports: '80:80'}}",
            "services: {web: {ports: [{published: 80}]}}",
            "services: {web: {volumes: [false]}}",
            "services: {web: {environment: [false]}}",
            "services: {web: {environment: {KEY: []}}}",
            "services: {web: {depends_on: [{}]}}",
            "networks: []",
        ):
            with self.subTest(content=content), self.assertRaises(ValueError):
                self.load(content)

    def test_yaml_errors_and_python_tags_are_rejected(self) -> None:
        for content in ("services: [", "!!python/object:builtins.object {}"):
            with self.subTest(content=content), self.assertRaises(yaml.YAMLError):
                self.load(content)

    def test_missing_file_propagates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                ComposeLoader.loadYaml(Path(directory) / "missing.yml")


if __name__ == "__main__":
    unittest.main()
