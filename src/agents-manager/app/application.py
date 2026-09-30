from __future__ import annotations

import argparse
import sys

from pathlib import Path
from typing import Optional

from app.commands.delete import (
    DeleteCommand,
)
from app.commands.execute import (
    ExecuteCommand,
)
from app.commands.install import (
    InstallCommand,
)
from app.commands.list import (
    ListCommand,
)
from app.commands.status import (
    StatusCommand,
)
from app.commands.tools import (
    ToolsCommand,
)
from app.commands.update import (
    UpdateCommand,
)
from app.commands.wakeup import WakeupCommand
from app.context import (
    ApplicationContext,
)
from app.services.agent_catalog import (
    AgentCatalog,
)
from shared.configuration import ApplicationEnvironment


class AgentApplication:

    _instance: Optional[
        "AgentApplication"
    ] = None

    _initialized = False

    def __new__(
        cls,
    ) -> "AgentApplication":

        if cls._instance is None:
            cls._instance = (
                super().__new__(cls)
            )

        return cls._instance

    def __init__(
        self,
    ) -> None:

        if self._initialized:
            return

        self._initialized = True

        self._context: (
            ApplicationContext
            | None
        ) = None
        self._repo_root = Path(__file__).resolve().parents[3]
        self._configuration = ApplicationEnvironment.discover(self._repo_root)

    @classmethod
    def instance(
        cls,
    ) -> "AgentApplication":

        return cls()

    def run(
        self,
    ) -> int:

        try:

            self._context = (
                ApplicationContext.create(
                    self._resolve_repo_root(), configuration=self._configuration
                )
            )

            parser = (
                self._build_parser()
            )

            args = parser.parse_args()

            return self._dispatch(
                args
            )

        except KeyboardInterrupt:

            print(
                "\n[ERROR] Interrupted.",
                file=sys.stderr,
            )

            return 130

        except Exception as exc:

            print(
                f"[ERROR] {exc}",
                file=sys.stderr,
            )

            return 1

    def _resolve_repo_root(
        self,
    ) -> Path:

        return self._repo_root

    def _build_parser(
        self,
    ) -> argparse.ArgumentParser:

        assert (
            self._context
            is not None
        )

        agents = (
            AgentCatalog(
                self._context.agents_root
            )
            .list_agents()
        )

        parser = argparse.ArgumentParser(
            prog="agent-manager"
        )

        subparsers = (
            parser.add_subparsers(
                dest="command",
                required=True,
            )
        )

        install = (
            subparsers.add_parser(
                "install"
            )
        )

        install.add_argument(
            "-n",
            "--name",
            choices=agents,
            help=(
                "Agent definition. Without this option, use the single "
                "config.json entry with default=true."
            ),
        )

        install.add_argument(
            "-u",
            "--user",
        )

        install.add_argument(
            "-m",
            "--model",
        )

        install.add_argument(
            "-g",
            "--gateway",
            "--gateway-user",
            dest="gateway_user",
            metavar="USER",
            default=(
                self._context.gateway_user
            ),
            help=(
                "Linux user running the "
                "OpenClaw gateway "
                "(default: %(default)s)."
            ),
        )

        install.add_argument(
            "--force",
            action="store_true",
        )

        install.add_argument(
            "--dry-run",
            action="store_true",
        )

        install.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help=(
                "Print commands executed by "
                "the installer."
            ),
        )

        install.set_defaults(
            handler="install"
        )

        execute = (
            subparsers.add_parser(
                "exec"
            )
        )

        execute.add_argument(
            "-n",
            "--name",
            required=True,
            choices=agents,
        )

        execute.add_argument(
            "-c",
            "--command",
            required=True,
        )

        execute.add_argument(
            "-r",
            "--requested-by",
            default=(
                self._context.gateway_user
            ),
            help=(
                "Name of the user or agent "
                "that requested the command "
                "(default: %(default)s)."
            ),
        )

        execute.set_defaults(
            handler="exec"
        )

        delete = (
            subparsers.add_parser(
                "delete"
            )
        )

        delete.add_argument(
            "-n",
            "--name",
            required=True,
            choices=agents,
        )

        delete.set_defaults(
            handler="delete"
        )

        update = (
            subparsers.add_parser(
                "update"
            )
        )

        update.add_argument(
            "-n",
            "--name",
            required=True,
            choices=agents,
        )

        update.add_argument(
            "-g",
            "--gateway",
            "--gateway-user",
            dest="gateway_user",
            metavar="USER",
            default=self._context.gateway_user,
        )

        update.add_argument(
            "--dry-run",
            action="store_true",
        )

        update.add_argument(
            "-v",
            "--verbose",
            action="store_true",
        )

        update.set_defaults(
            handler="update"
        )

        list_command = (
            subparsers.add_parser(
                "list"
            )
        )

        list_command.add_argument(
            "--json",
            action="store_true",
        )

        list_command.set_defaults(
            handler="list"
        )

        status = (
            subparsers.add_parser(
                "status"
            )
        )

        status.add_argument(
            "-n",
            "--name",
            required=True,
        )

        status.add_argument(
            "--json",
            action="store_true",
        )

        status.set_defaults(
            handler="status"
        )

        tools = subparsers.add_parser("tools")
        tools.add_argument("-n", "--name", required=True)
        tools.add_argument("--json", action="store_true")
        tools.set_defaults(handler="tools")

        wakeup = subparsers.add_parser("wakeup")
        wakeup.add_argument("-n", "--name", required=True, choices=agents)
        wakeup.add_argument(
            "-g",
            "--gateway-user",
            default=self._context.gateway_user,
        )
        wakeup.add_argument("--timeout", type=int, default=600)
        wakeup.add_argument("-v", "--verbose", action="store_true")
        wakeup.set_defaults(handler="wakeup")

        return parser

    def _dispatch(
        self,
        args: argparse.Namespace,
    ) -> int:

        assert (
            self._context
            is not None
        )

        match args.handler:

            case "install":

                return InstallCommand(
                    ApplicationContext.create(
                        self._context.repo_root,
                        gateway_user=(
                            args.gateway_user
                        ),
                    )
                ).execute(
                    args
                )

            case "exec":

                return ExecuteCommand(
                    self._context
                ).execute(
                    args
                )

            case "delete":

                return DeleteCommand(
                    self._context
                ).execute(
                    args
                )

            case "update":

                return UpdateCommand(
                    ApplicationContext.create(
                        self._context.repo_root,
                        gateway_user=args.gateway_user,
                    )
                ).execute(
                    args
                )

            case "list":

                return ListCommand(
                    self._context
                ).execute(
                    args
                )

            case "status":

                return StatusCommand(
                    self._context
                ).execute(
                    args
                )

            case "tools":

                return ToolsCommand(
                    self._context
                ).execute(
                    args
                )

            case "wakeup":

                if args.timeout <= 0:
                    raise ValueError("--timeout must be greater than zero.")
                return WakeupCommand(
                    self._context
                ).execute(
                    args
                )

            case _:

                raise RuntimeError(
                    "Unknown command: "
                    f"{args.handler}"
                )
