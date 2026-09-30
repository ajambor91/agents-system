from __future__ import annotations

import argparse
import shutil

from pathlib import Path

from app.commands.base import (
    Command,
)
from app.services.agent_catalog import (
    AgentCatalog,
)
from app.services.agent_config import (
    AgentConfigService,
)
from app.services.agent_executor import (
    AgentExecutor,
    AgentRuntime,
)
from app.services.agent_registry import (
    AgentRegistryService,
)
from app.services.linux_user import (
    LinuxUserService,
)
from app.services.openclaw import (
    OpenClawService,
)
from app.services.process import (
    ProcessRunner,
)
from app.services.runtime_config import (
    RuntimeConfigService,
)
from app.services.shell import (
    ShellService,
)
from app.services.shared_tools import (
    SharedToolsService,
)
from app.services.state import (
    AgentStateService,
)
from app.services.sudo_policy import (
    SudoPolicyService,
)
from app.services.symlink import (
    ShellLinkService,
)


class InstallCommand(Command):

    def execute(
        self,
        args: argparse.Namespace,
    ) -> int:

        runner = ProcessRunner(
            verbose=args.verbose
        )

        catalog = AgentCatalog(
            self.context.agents_root
        )

        definition_config = (
            AgentConfigService(catalog)
            .resolve(args.name)
        )
        args.name = definition_config.name
        if args.user is None:
            args.user = definition_config.user
        if args.model is None:
            args.model = definition_config.model

        agent_root = (
            catalog.get_agent_root(
                args.name
            )
        )

        state = AgentStateService(
            self.context,
            runner,
        )

        state_paths = state.prepare(
            args.name,
            dry_run=args.dry_run,
        )

        linux_users = LinuxUserService(
            runner
        )

        dedicated_user = (
            args.user is not None
        )

        if dedicated_user:

            runtime_user = (
                linux_users
                .resolve_or_create(
                    args.user,
                    dry_run=args.dry_run,
                )
            )

            linux_users.prepare_home(
                runtime_user,
                dry_run=args.dry_run,
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
                self.context.gateway_user,
                dry_run=args.dry_run,
            )

        else:

            runtime_user = (
                linux_users
                .resolve_or_create(
                    self.context.gateway_user,
                    dry_run=args.dry_run,
                )
            )

            agent_home = (
                runtime_user.home
            )

            workspace = (
                self.context.gateway_home
                / ".openclaw"
                / f"{args.name}_workspace"
            )

            if args.dry_run:
                print(
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
            force=args.force,
            dry_run=args.dry_run,
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
            force=args.force,
            dry_run=args.dry_run,
            runner=runner,
            privileged=dedicated_user,
        )

        shared_tools = SharedToolsService(
            runner
        )
        shared_tools.deploy(
            source=(
                self.context.repo_root
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
            replace_existing=args.force,
            privileged=dedicated_user,
            dry_run=args.dry_run,
        )

        shell_template = (
            agent_root
            / "resources"
            / "shell.template.json"
        )

        if not shell_template.is_file():
            raise FileNotFoundError(
                "Missing shell template: "
                f"{shell_template}"
            )

        variables = {
            "AGENT_NAME": (
                args.name
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
                self.context.gateway_user
            ),
        }

        ShellService(
            state
        ).generate(
            shell_template,
            state_paths,
            variables,
            dry_run=args.dry_run,
        )

        runtime = AgentRuntime(
            agent_name=args.name,
            linux_user=runtime_user.name,
            home=agent_home,
            workspace=workspace,
            shell=Path("/bin/bash"),
            agentrc=state_paths.agentrc,
        )

        AgentExecutor(
            runner
        ).prepare_history(
            runtime,
            dry_run=args.dry_run,
        )

        RuntimeConfigService(
            state
        ).write(
            state_paths,
            runtime,

            gateway_user=(
                self.context.gateway_user
            ),

            dry_run=args.dry_run,
        )

        state.write_json(
            state_paths.config_json,
            definition_config.effective_document(
                linux_user=runtime_user.name,
                model=args.model,
                gateway_user=self.context.gateway_user,
                workspace=workspace,
            ),
            dry_run=args.dry_run,
        )

        # Gateway needs runtime.json
        # so AgentExecutor can resolve
        # huggin -> huginn.
        state.grant_runtime_reader(
            self.context.gateway_user,
            state_paths,
            dry_run=args.dry_run,
        )

        state.grant_config_reader(
            self.context.gateway_user,
            state_paths,
            dry_run=args.dry_run,
        )

        if dedicated_user:
            state.grant_config_reader(
                runtime_user.name,
                state_paths,
                dry_run=args.dry_run,
            )

        gateway_start = self.context.repo_root / "host_scripts" / "agents-gateway-start.sh"
        if args.dry_run:
            print(f"[DRY] ensure Agents Manager gateway via {gateway_start}")
        else:
            runner.run_privileged(["bash", str(gateway_start)])

        links = ShellLinkService(
            runner
        )

        links.link_file(
            runtime_user,
            state_paths.config_json,
            workspace / "config.json",
            replace_existing=args.force,
            dry_run=args.dry_run,
        )

        if dedicated_user:

            # huginn can read only the
            # generated shell files.
            state.grant_shell_reader(
                runtime_user.name,
                state_paths,
                dry_run=args.dry_run,
            )

            links.link(
                runtime_user,
                state_paths,

                replace_existing=(
                    runtime_user.created
                    or args.force
                ),

                dry_run=args.dry_run,
            )

            SudoPolicyService(
                runner
            ).install(
                agent_name=args.name,

                gateway_user=(
                    self.context
                    .gateway_user
                ),

                agent_user=(
                    runtime_user.name
                ),

                shell=runtime.shell,

                dry_run=args.dry_run,
            )

        openclaw = OpenClawService(
            binary=(
                self.context.openclaw_bin
            ),
            gateway_user=(
                self.context.gateway_user
            ),
            process_runner=runner,
        )

        openclaw.add_agent(
            name=args.name,
            workspace=workspace,
            model=args.model,
            force=args.force,
            dry_run=args.dry_run,
        )

        openclaw.apply_identity(
            name=args.name,
            workspace=workspace,
            dry_run=args.dry_run,
        )

        if (
            definition_config.execution is not None
            and definition_config.execution.backend == "agent-executor"
        ):
            openclaw.install_executor_plugin(
                self.context.repo_root
                / "provider_plugins"
                / "openclaw"
                / "agent-executor",
                snapshot_root=(
                    self.context.state_root
                    / "openclaw_plugins"
                    / "agent-executor"
                ),
                dry_run=args.dry_run,
            )

        tool_policy = definition_config.openclaw_tools_document()
        if tool_policy is not None:
            openclaw.set_agent_tools(
                args.name,
                tool_policy,
                dry_run=args.dry_run,
            )

        shared_tools.start_bootstrap(
            destination=(tools_root / "bin"),
            owner=runtime_user.name,
            environment=variables,
            configured=bool(definition_config.bootstrap),
            dry_run=args.dry_run,
        )

        if args.dry_run:
            print(
                f"[DRY] synchronize "
                f"{self.context.state_root / 'agents.json'}"
            )
        else:
            AgentRegistryService(
                self.context,
                state,
                openclaw,
            ).sync()

        print()

        if args.dry_run:
            print(
                "[OK] Dry run complete"
            )
        else:
            print(
                "[OK] Agent updated"
                if getattr(args, "operation", "install") == "update"
                else "[OK] Agent installed"
            )

        print(
            f"     agent:      "
            f"{args.name}"
        )

        print(
            f"     linux user: "
            f"{runtime_user.name}"
        )

        print(
            f"     workspace:  "
            f"{workspace}"
        )

        print(
            f"     state:      "
            f"{state_paths.agent_dir}"
        )

        print(
            f"     agentrc:    "
            f"{state_paths.agentrc}"
        )

        if dedicated_user:

            print(
                f"     ~/.bashrc  -> "
                f"{state_paths.bashrc}"
            )

            print(
                f"     ~/.agentrc -> "
                f"{state_paths.agentrc}"
            )

        return 0

    @staticmethod
    def _copy_personality(
        *,
        source: Path,
        destination: Path,
        force: bool,
        dry_run: bool,
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
                print(
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
            print(
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
