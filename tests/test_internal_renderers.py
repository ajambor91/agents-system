"""Contract tests for installation-time internal renderers."""

from __future__ import annotations

import grp
import json
import os
import pwd
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from internal_scripts.common import RenderError  # noqa: E402
from internal_scripts.render_app_env import _selected, render as render_environment  # noqa: E402
from internal_scripts.render_modules_manifest import render as render_modules  # noqa: E402


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class InternalRendererTests(unittest.TestCase):
    def test_modules_manifest_renders_paths_and_preserves_template(self) -> None:
        template = ROOT / "resources" / "agents-system.module.template.json"
        before = template.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            output = base / "agents-system.module.json"
            manifest_path = base / "config" / "agents-system.module.json"
            result = render_modules(
                package_dir=ROOT,
                app_dir=ROOT,
                modules_dir=ROOT / "src",
                manifest_path=manifest_path,
                output=output,
                force=False,
            )
            rendered = read_json(output)
            self.assertEqual(result["count"], len(rendered["children"]))
            self.assertEqual(rendered["absolute_path"], str(ROOT / "src"))
            self.assertEqual(rendered["app_dir"], str(ROOT))
            self.assertEqual(rendered["manifest_absolute_path"], str(manifest_path))
            self.assertEqual(
                {
                    item["module_name"]
                    for item in rendered["children"]
                    if item["is_menu_option"]
                },
                {"agents-manager", "agents-system"},
            )
            self.assertEqual(
                {
                    item["module_name"]
                    for item in rendered["children"]
                    if item["is_runtime"]
                },
                {"runtime", "agents-data-runtime"},
            )
            for item in rendered["children"]:
                self.assertEqual(
                    Path(item["absolute_module_path"]),
                    ROOT / "src" / ("_runtime" if item["module_name"] == "runtime" else item["module_name"]),
                )
            self.assertNotIn("${", json.dumps(rendered))
            source_system = next(item for item in read_json(template)["children"] if item["module_name"] == "agents-system")
            rendered_system = next(item for item in rendered["children"] if item["module_name"] == "agents-system")
            self.assertEqual(rendered_system["commands"], source_system["commands"])
            self.assertEqual(rendered_system["commands"][0]["method"], "modules")
            with self.assertRaisesRegex(RenderError, "--force"):
                render_modules(
                    package_dir=ROOT,
                    app_dir=ROOT,
                    modules_dir=ROOT / "src",
                    manifest_path=manifest_path,
                    output=output,
                    force=False,
                )
            render_modules(
                package_dir=ROOT,
                app_dir=ROOT,
                modules_dir=ROOT / "src",
                manifest_path=manifest_path,
                output=output,
                force=True,
            )
        self.assertEqual(template.read_bytes(), before)

    def test_environment_renders_dev_and_system_layouts(self) -> None:
        account = pwd.getpwuid(os.getuid())
        group = grp.getgrgid(account.pw_gid).gr_name
        for mode in ("dev", "system"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "app_env.json"
                result = render_environment(
                    mode=mode,
                    package_dir=ROOT,
                    install_dir=ROOT,
                    output=output,
                    force=False,
                    user_system=account.pw_name,
                    user_group=group,
                    user_system_home=account.pw_dir,
                    environment={},
                    value_resolver=lambda _name: None,
                )
                values = {
                    item["name"]: item["value"] for item in read_json(output)["variables"]
                }
                self.assertEqual(result["mode"], mode)
                self.assertEqual(values["INSTALLED_MODULES_DIR"], values["APP_DATA_DIR"] + "/installed_modules")
                self.assertFalse(set(values) & {
                    "REPOSITORIES_DIR", "REPOSITORY_HISTORY_PATH", "AGENT_METADATA",
                    "AGENT_METADATA_FULL", "APP_DATA_FULL_DIR",
                })
                self.assertEqual(
                    values["AGENT_CONFIG_PATH_TEMPLATE"],
                    "/home/{{agent_name}}/.agents/config.json",
                )
                self.assertEqual(
                    values["AGENT_COMMUNICATION_PATH_TEMPLATE"],
                    "/home/{{agent_name}}/.inbox/communication.json",
                )
                if mode == "dev":
                    self.assertEqual(values["APP_RUNTIME_DIR"], f"{account.pw_dir}/.agents-system/run")
                else:
                    self.assertEqual(values["APP_CONFIG_DIR"], "/etc/agents-system")
                    self.assertEqual(values["APP_DATA_DIR"], "/var/lib/agents-system")
                    self.assertEqual(values["APP_RUNTIME_DIR"], "/run/agents-system")

    def test_environment_uses_template_values_and_preserves_placeholders(self) -> None:
        source = read_json(ROOT / "resources" / "app_env.template.json")
        source_values = {item["name"]: item["value"] for item in source["variables"]}
        self.assertEqual(source_values["APP_ENV_PATH"], "${APP_CONFIG_DIR}/${APP_ENV_FILE}")
        self.assertEqual(source_values["INSTALL_MODE"], "{{INSTALL_MODE}}")
        self.assertEqual(source_values["BASH_SOURCE"], "{{BASH_SOURCE}}")
        self.assertEqual(source_values["INSTALL_DIR"], "{{INSTALL_DIR}}")
        self.assertEqual(source_values["APP_CONFIG_DIR"], "{{APP_CONFIG_DIR}}")
        self.assertEqual(source_values["APP_DATA_DIR"], "{{APP_DATA_DIR}}")
        self.assertEqual(
            source_values["AGENT_CONFIG_PATH_TEMPLATE"],
            "${AGENT_CONFIG_DIR_TEMPLATE}/${AGENT_CONFIG_FILE}",
        )

        account = pwd.getpwuid(os.getuid())
        group = grp.getgrgid(account.pw_gid).gr_name
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary) / "package"
            (package / "resources").mkdir(parents=True)
            (package / "internal_scripts").mkdir()
            (package / "install").mkdir()
            shutil.copy2(ROOT / "install" / "default_install.json", package / "install")
            shutil.copy2(ROOT / "internal_scripts" / "render-app-env.json", package / "internal_scripts")
            custom = json.loads(json.dumps(source))
            next(
                item for item in custom["variables"]
                if item["name"] == "AGENTS_DATA_COMMUNICATION_APP"
            )["value"] = "http://template.example:3456"
            (package / "resources" / "app_env.template.json").write_text(
                json.dumps(custom), encoding="utf-8"
            )
            output = Path(temporary) / "rendered.json"
            render_environment(
                mode="dev", package_dir=package, install_dir=ROOT, output=output,
                force=False, user_system=account.pw_name, user_group=group,
                user_system_home=account.pw_dir, environment={},
                value_resolver=lambda _name: None,
            )
            rendered = {
                item["name"]: item["value"]
                for item in read_json(output)["variables"]
            }
            self.assertEqual(
                rendered["AGENTS_DATA_COMMUNICATION_APP"],
                "http://template.example:3456",
            )

    def test_environment_value_precedence_is_mode_aware(self) -> None:
        resolver = lambda _name: "json"
        self.assertEqual(
            _selected(
                "VALUE", "cli", {"VALUE": "shell"}, resolver, {},
                prefer_environment=True,
            ),
            "shell",
        )
        self.assertEqual(
            _selected(
                "VALUE", "cli", {"VALUE": "shell"}, resolver, {},
                prefer_environment=False,
            ),
            "cli",
        )
        self.assertEqual(
            _selected(
                "VALUE", None, {"VALUE": "shell"}, resolver, {},
                prefer_environment=False,
            ),
            "json",
        )

    def test_api_manifests_match_contract_flags(self) -> None:
        for name in ("render-modules-manifest", "render-app-env"):
            with self.subTest(script=name):
                contract = read_json(ROOT / "internal_scripts" / f"{name}.json")
                api = read_json(ROOT / "internal_scripts" / f"{name}.api.json")
                contract_flags = [(item["short"], item["long"]) for item in contract["flags"]]
                api_flags = [(item["short"], item["long"]) for item in api["flags"]]
                self.assertEqual(api_flags, contract_flags)
                flattened = [flag for pair in api_flags for flag in pair if flag]
                self.assertEqual(api["flag_names"], flattened)

    def test_wrappers_expose_help(self) -> None:
        for name in ("render-modules-manifest", "render-app-env"):
            completed = subprocess.run(
                ["bash", str(ROOT / "internal_scripts" / f"{name}.sh"), "--help"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("--help", completed.stdout)


    def test_installed_modules_directory_follows_explicit_data_directory(self) -> None:
        account = pwd.getpwuid(os.getuid())
        group = grp.getgrgid(account.pw_gid).gr_name
        for mode in ("dev", "system"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                data = root / "custom-data"
                output = root / "rendered.json"
                render_environment(
                    mode=mode, package_dir=ROOT, install_dir=ROOT, output=output,
                    force=False, data_dir=str(data), user_system=account.pw_name,
                    user_group=group, user_system_home=account.pw_dir,
                    environment={}, value_resolver=lambda _name: None,
                )
                variables = {item["name"]: item for item in read_json(output)["variables"]}
                self.assertEqual(variables["INSTALLED_MODULES_DIR"]["value"], str(data / "installed_modules"))
                self.assertTrue(variables["INSTALLED_MODULES_DIR"]["description"])
                self.assertTrue(variables["INSTALLED_MODULES_DIR"]["example"])
                from lib.configuration import Configuration
                self.assertEqual(set(variables), set(Configuration.schema()))


    def test_modules_renderer_rejects_paths_outside_modules_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            package = base / "package"
            (package / "resources").mkdir(parents=True)
            document = read_json(ROOT / "resources/agents-system.module.template.json")
            runtime = next(child for child in document["children"] if child["module_name"] == "runtime")
            for suffix in ("../outside", "/tmp/outside", ""):
                runtime["absolute_module_path"] = "${MODULES_DIR}/" + suffix
                (package / "resources/agents-system.module.template.json").write_text(json.dumps(document))
                output = base / "output.json"
                with self.assertRaises(RenderError):
                    render_modules(package_dir=package, app_dir=ROOT, modules_dir=ROOT / "src",
                        manifest_path=output, output=output, force=False)
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
