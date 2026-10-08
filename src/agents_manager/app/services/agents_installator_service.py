from __future__ import annotations

import logging

from ..context import ApplicationContext
from .agent_services_factory import AgentServicesFactory

from collections.abc import Mapping
from typing import Any
import json
import shutil

from pathlib import Path

from .agent_catalog import AgentCatalog
from .agent_executor import AgentRuntime
from .process import (
    ProcessRunner,
)


LOGGER = logging.getLogger(__name__)


class AgentsInstallatorService:

    def __init__(self, services_factory: AgentServicesFactory) -> None:
        self._services_factory = services_factory


    def execute(
        self,
        flags: Mapping[str, Any],
        context: ApplicationContext,
    ) -> dict[str, Any]:

        LOGGER.info('Installing agent agent=%s dry_run=%s', (flags or {}).get('name'), (flags or {}).get('dry_run', False))
        flags = dict(flags)
        agent_root = self._definition_path(flags, context)
        flags['path'] = str(agent_root)
        services = self._services_factory.create(context, flags)
        runner = services.runner
        definition_config = (
            services.configuration
            .resolve(agent_root.name)
        )
        flags["name"] = definition_config.name
        if flags.get("user") is None:
            flags["user"] = definition_config.user
        if flags.get("model") is None:
            flags["model"] = definition_config.model

        shell_template = agent_root / "resources" / "shell.template.json"
        if not shell_template.is_file():
            raise FileNotFoundError(f"Missing shell template: {shell_template}")

        state = services.state

        state_paths = state.prepare(
            flags.get('name'),
            dry_run=flags.get("dry_run", False),
        )

        linux_users = services.linux_users

        dedicated_user = (
            flags.get("user") is not None
        )

        if dedicated_user:

            runtime_user = (
                linux_users
                .resolve_or_create(
                    flags.get("user"),
                    dry_run=flags.get("dry_run", False),
                )
            )

            linux_users.prepare_home(
                runtime_user,
                dry_run=flags.get("dry_run", False),
            )

            agent_home = (
                runtime_user.home
            )

            workspace = (
                agent_home
                / "workspace"
            )

            linux_users.prepare_workspace(
                runtime_user,
                workspace,
                context.gateway_user,
                dry_run=flags.get("dry_run", False),
            )

        else:

            runtime_user = (
                linux_users
                .resolve_or_create(
                    context.gateway_user,
                    dry_run=flags.get("dry_run", False),
                )
            )

            agent_home = (
                runtime_user.home
            )

            workspace = (
                context.gateway_home
                / ".openclaw"
                / f"{flags.get('name')}_workspace"
            )

            if flags.get("dry_run", False):
                runner.report(
                    f"[DRY] mkdir "
                    f"{workspace}"
                )
            else:
                workspace.mkdir(
                    parents=True,
                    exist_ok=True,
                )

        self._copy_personality(
            source=(
                agent_root
                / "personality"
            ),
            destination=workspace,
            force=flags.get("force", False),
            dry_run=flags.get("dry_run", False),
            runner=runner,
        )

        if dedicated_user:
            scripts_destination = (
                agent_home
                / "scripts"
            )
            tools_root = (
                agent_home
                / "tools"
            )
        else:
            scripts_destination = (
                workspace
                / "scripts"
            )
            tools_root = (
                workspace
                / "tools"
            )

        self._copy_scripts(
            source=(
                agent_root
                / "scripts"
            ),
            destination=(
                scripts_destination
            ),
            owner=runtime_user.name,
            force=flags.get("force", False),
            dry_run=flags.get("dry_run", False),
            runner=runner,
            privileged=dedicated_user,
        )

        shared_tools = services.shared_tools
        shared_tools.deploy(
            source=(
                context.repo_root
                / "agents"
                / "shared"
                / "scripts"
            ),
            destination=(
                tools_root
                / "bin"
            ),
            owner=runtime_user.name,
            bootstrap=definition_config.bootstrap,
            replace_existing=flags.get("force", False),
            privileged=dedicated_user,
            dry_run=flags.get("dry_run", False),
        )

        variables = {
            "AGENT_NAME": (
                flags.get('name')
            ),

            "AGENT_USER": (
                runtime_user.name
            ),

            "AGENT_HOME": str(
                agent_home
            ),

            "AGENT_WORKSPACE": str(
                workspace
            ),

            "AGENT_SCRIPTS": str(
                scripts_destination
            ),

            "AGENT_TOOLS": str(
                tools_root
            ),

            "AGENT_STATE_DIR": str(
                state_paths.agent_dir
            ),

            "AGENT_GATEWAY_USER": (
                context.gateway_user
            ),
        }

        services.shell.generate(
            shell_template,
            state_paths,
            variables,
            dry_run=flags.get("dry_run", False),
        )

        runtime = AgentRuntime(
            agent_name=flags.get('name'),
            linux_user=runtime_user.name,
            home=agent_home,
            workspace=workspace,
            shell=Path("/bin/bash"),
            agentrc=state_paths.agentrc,
        )

        services.executor.prepare_history(
            runtime,
            dry_run=flags.get("dry_run", False),
        )

        services.runtime.write(
            state_paths,
            runtime,

            gateway_user=(
                context.gateway_user
            ),

            dry_run=flags.get("dry_run", False),
        )

        effective_config = definition_config.effective_document(
            linux_user=runtime_user.name,
            model=flags.get("model"),
            gateway_user=context.gateway_user,
            workspace=workspace,
        )
        effective_config["definition_path"] = str(agent_root)
        state.write_json(
            state_paths.config_json, effective_config,
            dry_run=flags.get("dry_run", False),
        )

        # Gateway needs runtime.json
        # so AgentExecutor can resolve
        # huggin -> huginn.
        state.grant_runtime_reader(
            context.gateway_user,
            state_paths,
            dry_run=flags.get("dry_run", False),
        )

        state.grant_config_reader(
            context.gateway_user,
            state_paths,
            dry_run=flags.get("dry_run", False),
        )

        if dedicated_user:
            state.grant_config_reader(
                runtime_user.name,
                state_paths,
                dry_run=flags.get("dry_run", False),
            )

        gateway_start = context.repo_root / "host_scripts" / "agents-gateway-start.sh"
        if flags.get("dry_run", False):
            runner.report(f"[DRY] ensure Agents Manager gateway via {gateway_start}")
        else:
            runner.run_privileged(["bash", str(gateway_start)])

        links = services.links

        links.link_file(
            runtime_user,
            state_paths.config_json,
            workspace / "config.json",
            replace_existing=flags.get("force", False),
            dry_run=flags.get("dry_run", False),
        )

        if dedicated_user:

            # huginn can read only the
            # generated shell files.
            state.grant_shell_reader(
                runtime_user.name,
                state_paths,
                dry_run=flags.get("dry_run", False),
            )

            links.link(
                runtime_user,
                state_paths,

                replace_existing=(
                    runtime_user.created
                    or flags.get("force", False)
                ),

                dry_run=flags.get("dry_run", False),
            )

            services.sudo_policy.install(
                agent_name=flags.get('name'),

                gateway_user=(
                    context
                    .gateway_user
                ),

                agent_user=(
                    runtime_user.name
                ),

                shell=runtime.shell,

                dry_run=flags.get("dry_run", False),
            )

        openclaw = services.agent_tool

        openclaw.add_agent(
            name=flags.get('name'),
            workspace=workspace,
            model=flags.get("model"),
            force=flags.get("force", False),
            dry_run=flags.get("dry_run", False),
        )

        openclaw.apply_identity(
            name=flags.get('name'),
            workspace=workspace,
            dry_run=flags.get("dry_run", False),
        )

        if (
            definition_config.execution is not None
            and definition_config.execution.backend == "agent-executor"
        ):
            openclaw.install_executor_plugin(
                context.repo_root
                / "provider_plugins"
                / "openclaw"
                / "agent-executor",
                snapshot_root=(
                    context.state_root
                    / "openclaw_plugins"
                    / "agent-executor"
                ),
                dry_run=flags.get("dry_run", False),
            )

        tool_policy = definition_config.tools.to_document() if definition_config.tools is not None else None
        if tool_policy is not None:
            openclaw.set_agent_tools(
                flags.get('name'),
                tool_policy,
                dry_run=flags.get("dry_run", False),
            )

        shared_tools.start_bootstrap(
            destination=(tools_root / "bin"),
            owner=runtime_user.name,
            environment=variables,
            configured=bool(definition_config.bootstrap),
            dry_run=flags.get("dry_run", False),
        )

        if flags.get("dry_run", False):
            runner.report(
                f"[DRY] synchronize "
                f"{context.state_root / 'agents.json'}"
            )
        else:
            services.registry.sync()

        operation = flags.get("operation", "install")
        return {
            "status": "dry-run" if flags.get("dry_run", False) else "updated" if operation == "update" else "installed",
            "operation": operation,
            "agent": flags["name"],
            "linux_user": runtime_user.name,
            "gateway_user": context.gateway_user,
            "workspace": str(workspace),
            "state_dir": str(state_paths.agent_dir),
            "agentrc": str(state_paths.agentrc),
            "messages": services.messages,
        }

    @staticmethod
    def _definition_path(flags: Mapping[str, Any], context: ApplicationContext) -> Path:
        raw_path = flags.get("path")
        if raw_path is None and flags.get("operation") == "update":
            name = flags.get("name")
            if not isinstance(name, str) or not AgentCatalog.AGENT_PATTERN.fullmatch(name):
                raise ValueError(f"Invalid agent name: {name}")
            # Older installations have no recorded source directory.
            raw_path = context.agents_root / name
            config_path = context.state_root / name / "config.json"
            try:
                document = json.loads(config_path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                pass
            else:
                if not isinstance(document, dict):
                    raise ValueError(f"Invalid installed agent config: {config_path}")
                raw_path = document.get("definition_path", raw_path)
        if not isinstance(raw_path, (str, Path)) or not str(raw_path).strip():
            raise ValueError("Missing required flag: --path")
        directory = Path(raw_path).expanduser().resolve(strict=True)
        if not directory.is_dir():
            raise NotADirectoryError(f"Agent path is not a directory: {directory}")
        if not AgentCatalog.AGENT_PATTERN.fullmatch(directory.name):
            raise ValueError(f"Invalid agent directory name: {directory.name}")
        name = flags.get("name")
        if name is not None and name != directory.name:
            raise ValueError(f"Agent name must match directory '{directory.name}'")
        return directory

    @staticmethod
    def _copy_personality(
        *,
        source: Path,
        destination: Path,
        force: bool,
        dry_run: bool,
        runner: ProcessRunner,
    ) -> None:

        if not source.is_dir():
            return

        if not dry_run:
            destination.mkdir(
                parents=True,
                exist_ok=True,
            )

        for item in source.iterdir():

            target = (
                destination
                / item.name
            )

            if (
                target.exists()
                or target.is_symlink()
            ):

                if not force:
                    raise FileExistsError(
                        f"{target} already "
                        "exists; use --force."
                    )

                if not dry_run:

                    if (
                        target.is_dir()
                        and not target.is_symlink()
                    ):
                        shutil.rmtree(
                            target
                        )
                    else:
                        target.unlink()

            if dry_run:
                runner.report(
                    f"[DRY] copy "
                    f"{item} -> {target}"
                )
                continue

            if item.is_dir():

                shutil.copytree(
                    item,
                    target,
                    symlinks=True,
                )

            else:

                shutil.copy2(
                    item,
                    target,
                    follow_symlinks=False,
                )

    @staticmethod
    def _copy_scripts(
        *,
        source: Path,
        destination: Path,
        owner: str,
        force: bool,
        dry_run: bool,
        runner: ProcessRunner,
        privileged: bool,
    ) -> None:

        if not source.is_dir():
            return

        if dry_run:
            runner.report(
                f"[DRY] copy "
                f"{source}/ -> "
                f"{destination}/"
            )
            return

        if privileged:

            runner.run_privileged([
                "install",
                "-d",

                "-o",
                owner,

                "-g",
                owner,

                "-m",
                "0700",

                str(destination),
            ])

        else:

            destination.mkdir(
                parents=True,
                exist_ok=True,
            )

        for item in source.iterdir():

            target = (
                destination
                / item.name
            )

            if (
                target.exists()
                or target.is_symlink()
            ):

                if not force:
                    raise FileExistsError(
                        f"{target} already "
                        "exists; use --force."
                    )

                if privileged:

                    runner.run_privileged([
                        "rm",
                        "-rf",
                        str(target),
                    ])

                elif (
                    target.is_dir()
                    and not target.is_symlink()
                ):

                    shutil.rmtree(
                        target
                    )

                else:

                    target.unlink()

            if privileged:

                runner.run_privileged([
                    "cp",
                    "-a",
                    str(item),
                    str(target),
                ])

                runner.run_privileged([
                    "chown",
                    "-R",
                    f"{owner}:{owner}",
                    str(target),
                ])

            elif item.is_dir():

                shutil.copytree(
                    item,
                    target,
                    symlinks=True,
                )

            else:

                shutil.copy2(
                    item,
                    target,
                    follow_symlinks=False,
                )
