"""Operation results are JSON documents, without terminal presentation."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from agents_manager.app.services.agents_delete_service import AgentsDeleteService
from agents_manager.app.services.agents_executor_service import AgentsExecutorService
from agents_manager.app.services.agents_installator_service import AgentsInstallatorService
from agents_manager.app.services.agents_list_service import AgentsListService
from agents_manager.app.services.agents_status_service import AgentsStatusService
from agents_manager.app.services.agents_tools_service import AgentsToolsService
from agents_manager.app.services.agents_update_service import AgentsUpdateService
from agents_manager.app.services.agents_wakeup_service import AgentsWakeupService


class OperationResultTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.context = SimpleNamespace(
            repo_root=self.root,
            agents_root=self.root / "agents",
            gateway_user="gateway",
            gateway_home=self.root / "gateway",
            state_root=self.root / "state",
        )
        self.factory = Mock()

    def invoke(self, service, flags):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = service.execute(flags, self.context)
        self.assertIsInstance(result, dict)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        json.dumps(result)
        return result

    def test_list_returns_complete_registry_including_empty_inventory(self):
        for agents in ({}, {"example": {"name": "example", "status": "running"}}):
            with self.subTest(agents=agents):
                document = {"agents": agents, "updated_at": "2026-10-06T12:00:00Z"}
                registry = Mock()
                registry.sync.return_value = document
                self.factory.create.return_value = SimpleNamespace(registry=registry)
                flags = {"json": bool(agents)}
                result = self.invoke(AgentsListService(self.factory), flags)
                self.assertIs(result, document)
                registry.sync.assert_called_once_with()
                self.factory.create.assert_called_with(self.context, flags)

    def test_status_returns_the_selected_record(self):
        record = {"name": "example", "status": "idle", "tasks": {"total": 0}}
        registry = Mock()
        registry.sync.return_value = {"agents": {"example": record}}
        self.factory.create.return_value = SimpleNamespace(registry=registry)
        flags = {"name": "example", "json": False}
        self.assertIs(self.invoke(AgentsStatusService(self.factory), flags), record)
        self.factory.create.assert_called_once_with(self.context, flags)

    def test_tools_returns_policy_without_rendering(self):
        tool = Mock()
        policy = {"profile": "minimal", "allow": ["read"]}
        tool.get_agent_tools.return_value = policy
        self.factory.create.return_value = SimpleNamespace(agent_tool=tool)
        flags = {"name": "example", "json": False}
        result = self.invoke(AgentsToolsService(self.factory), flags)
        self.assertEqual(result, {"agent": "example", "tools": policy})
        tool.get_agent_tools.assert_called_once_with("example")
        self.factory.create.assert_called_once_with(self.context, flags)

    def test_delete_reports_unimplemented_without_deleting(self):
        result = self.invoke(AgentsDeleteService(), {"name": "example"})
        self.assertEqual(result, {
            "status": "not-implemented",
            "agent": "example",
            "message": "Delete agent is not implemented.",
        })

    def test_executor_captures_nonzero_process_result_and_preserves_command(self):
        configuration_path = self.root / "config.json"
        configuration_path.write_text(json.dumps({"execution": {"timeout_seconds": 17}}))
        state, runtime_service, executor = Mock(), Mock(), Mock()
        state.paths.return_value = SimpleNamespace(config_json=configuration_path)
        runtime = SimpleNamespace(agent_name="example")
        runtime_service.load.return_value = runtime
        executor.execute.return_value = subprocess.CompletedProcess(
            ["bash", "-c", "exit 9"], 9, stdout="result\n", stderr="failure\n",
        )
        self.factory.create.return_value = SimpleNamespace(
            state=state, runtime=runtime_service, executor=executor,
        )
        command = "printf '%s' 'literal argument with spaces'; exit 9"
        flags = {"name": "example", "command": command, "requested_by": "operator"}
        result = self.invoke(AgentsExecutorService(self.factory), flags)
        self.assertEqual(result, {
            "agent": "example", "returncode": 9,
            "stdout": "result\n", "stderr": "failure\n",
        })
        executor.execute.assert_called_once_with(
            runtime, command, requested_by="operator", capture=True, timeout_seconds=17,
        )
        self.factory.create.assert_called_once_with(self.context, flags)

    def test_executor_returns_strings_when_process_output_is_missing(self):
        state, runtime_service, executor = Mock(), Mock(), Mock()
        state.paths.return_value = SimpleNamespace(config_json=self.root / "missing.json")
        runtime_service.load.return_value = SimpleNamespace(agent_name="example")
        executor.execute.return_value = subprocess.CompletedProcess(["true"], 0)
        self.factory.create.return_value = SimpleNamespace(
            state=state, runtime=runtime_service, executor=executor,
        )
        result = self.invoke(AgentsExecutorService(self.factory), {
            "name": "example", "command": "true",
        })
        self.assertEqual(result["stdout"], "")
        self.assertEqual(result["stderr"], "")
        self.assertEqual(executor.execute.call_args.kwargs["timeout_seconds"], 300)
        self.assertEqual(executor.execute.call_args.kwargs["requested_by"], "gateway")

    def test_wakeup_preserves_envelope_and_returns_captured_result(self):
        wakeup = Mock()
        wakeup.execute.return_value = SimpleNamespace(stdout="accepted\n", stderr="")
        self.factory.create.return_value = SimpleNamespace(wakeup=wakeup)
        envelope = {"message": "Zażółć", "metadata": {"priority": 2}}
        flags = {"name": "example", "envelope": envelope, "timeout": 42}
        with patch.dict("os.environ", {"SUDO_USER": "operator"}):
            result = self.invoke(AgentsWakeupService(self.factory), flags)
        self.assertEqual(result, {"agent": "example", "stdout": "accepted\n", "stderr": ""})
        wakeup.execute.assert_called_once_with(
            agent_name="example", envelope=envelope, caller_user="operator", timeout=42,
        )
        self.factory.create.assert_called_once_with(self.context, flags)

    def test_wakeup_rejects_invalid_envelope_before_creating_dependencies(self):
        service = AgentsWakeupService(self.factory)
        for envelope in ([], "message", {"message": "x" * service.MAX_ENVELOPE_BYTES}):
            with self.subTest(envelope_type=type(envelope).__name__):
                with self.assertRaises(ValueError):
                    service.execute({"name": "example", "envelope": envelope}, self.context)
        self.factory.create.assert_not_called()

    def installation_dependencies(self):
        agent_root = self.root / "external definitions" / "example"
        (agent_root / "resources").mkdir(parents=True)
        (agent_root / "resources" / "shell.template.json").write_text("{}")
        (agent_root / "personality").mkdir()
        (agent_root / "personality" / "SOUL.md").write_text("Agent personality")
        (agent_root / "scripts").mkdir()
        (agent_root / "scripts" / "task.sh").write_text("#!/bin/bash\ntrue\n")
        configuration = Mock()
        definition = SimpleNamespace(
            name="example", user=None, model="example-model", bootstrap=[],
            execution=SimpleNamespace(backend="agent-executor"),
            tools=SimpleNamespace(to_document=lambda: {"profile": "minimal"}),
            effective_document=Mock(return_value={"name": "example"}),
        )
        configuration.resolve.return_value = definition
        state_paths = SimpleNamespace(
            agent_dir=self.root / "state" / "example",
            agentrc=self.root / "state" / "example" / "agentrc.sh",
            config_json=self.root / "state" / "example" / "config.json",
        )
        catalog, state, linux_users = Mock(), Mock(), Mock()
        catalog.get_agent_root.return_value = agent_root
        state.prepare.return_value = state_paths
        linux_users.resolve_or_create.return_value = SimpleNamespace(
            name="gateway", home=self.context.gateway_home, created=False,
        )
        messages = []
        runner = Mock()
        runner.report.side_effect = messages.append
        services = SimpleNamespace(
            runner=runner, catalog=catalog, configuration=configuration, state=state,
            linux_users=linux_users, shared_tools=Mock(), shell=Mock(), executor=Mock(),
            runtime=Mock(), links=Mock(), sudo_policy=Mock(), agent_tool=Mock(),
            registry=Mock(), messages=messages,
        )
        self.factory.create.return_value = services
        return services, state_paths

    def test_installer_returns_completed_installation_document_using_injected_services(self):
        services, paths = self.installation_dependencies()
        source = self.root / "external definitions" / "example"
        flags = {"path": str(source), "dry_run": False}
        result = self.invoke(AgentsInstallatorService(self.factory), flags)
        workspace = self.context.gateway_home / ".openclaw" / "example_workspace"
        self.assertEqual(result, {
            "status": "installed", "operation": "install", "agent": "example",
            "linux_user": "gateway", "gateway_user": "gateway", "workspace": str(workspace),
            "state_dir": str(paths.agent_dir), "agentrc": str(paths.agentrc), "messages": [],
        })
        self.assertEqual((workspace / "SOUL.md").read_text(), "Agent personality")
        self.assertTrue((workspace / "scripts" / "task.sh").is_file())
        services.configuration.resolve.assert_called_once_with("example")
        services.shell.generate.assert_called_once_with(
            source / "resources" / "shell.template.json", paths,
            services.shell.generate.call_args.args[2], dry_run=False,
        )
        saved_config = services.state.write_json.call_args.args[1]
        self.assertEqual(saved_config["definition_path"], str(source))
        services.registry.sync.assert_called_once_with()
        services.runner.run_privileged.assert_called_once_with([
            "bash", str(self.root / "host_scripts" / "agents-gateway-start.sh"),
        ])
        services.agent_tool.add_agent.assert_called_once_with(
            name="example", workspace=workspace, model="example-model", force=False, dry_run=False,
        )
        services.agent_tool.set_agent_tools.assert_called_once_with(
            "example", {"profile": "minimal"}, dry_run=False,
        )
        self.assertEqual(flags, {"path": str(source), "dry_run": False})

    def test_installer_dry_run_returns_plan_without_workspace_or_gateway_execution(self):
        services, paths = self.installation_dependencies()
        result = self.invoke(AgentsInstallatorService(self.factory), {
            "name": "example", "path": str(self.root / "external definitions" / "example"), "dry_run": True,
        })
        workspace = self.context.gateway_home / ".openclaw" / "example_workspace"
        self.assertEqual(result["status"], "dry-run")
        self.assertEqual(result["state_dir"], str(paths.agent_dir))
        self.assertEqual(result["workspace"], str(workspace))
        self.assertFalse(workspace.exists())
        self.assertTrue(result["messages"])
        self.assertTrue(all(message.startswith("[DRY]") for message in result["messages"]))
        services.runner.run_privileged.assert_not_called()
        services.registry.sync.assert_not_called()
        services.state.prepare.assert_called_once_with("example", dry_run=True)
        self.assertTrue(services.shell.generate.call_args.kwargs["dry_run"])
        self.assertTrue(services.agent_tool.add_agent.call_args.kwargs["dry_run"])

    def test_update_delegates_dictionary_result_without_mutating_input(self):
        installer = Mock()
        document = {"status": "updated", "operation": "update", "agent": "example"}
        installer.execute.return_value = document
        flags = {"name": "example", "user": "old", "model": "old", "dry_run": True}
        result = self.invoke(AgentsUpdateService(installer), flags)
        self.assertIs(result, document)
        installer.execute.assert_called_once_with({
            "name": "example", "user": None, "model": None, "dry_run": True,
            "force": True, "operation": "update", "gateway_user": "gateway",
        }, self.context)
        self.assertEqual(flags["user"], "old")
        self.assertEqual(flags["model"], "old")


if __name__ == "__main__":
    unittest.main()
