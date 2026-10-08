from __future__ import annotations

import logging
import json
import os
import pwd
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..app.services.process import ProcessRunner
from .shell import OpenClawShell

LOGGER = logging.getLogger(__name__)


class OpenClawBackend:
    EXECUTOR_PLUGIN_ID = 'agent-executor'

    def __init__(self, *, gateway_user: str, process_runner: ProcessRunner | None) -> None:
        self.binary = 'openclaw'
        self.gateway_user = gateway_user
        if process_runner is None:
            from ..app.services.process import ProcessRunner
            process_runner = ProcessRunner()
        self.process_runner = process_runner
        self._shell = OpenClawShell(gateway_user, self.process_runner)

    def add_agent(self, *, name: str, workspace: Path, model: str | None=None, force: bool=False, dry_run: bool=False) -> None:
        LOGGER.debug('Starting backend.add_agent name=%s force=%s dry_run=%s', name, force, dry_run)
        existing = self._find_agent(name)
        if existing is not None:
            if not force:
                raise RuntimeError(f'OpenClaw agent already exists: {name}. Use --force to update its registration.')
            self._update_agent(name=name, existing=existing, workspace=workspace, model=model, dry_run=dry_run)
            return
        command = [str(self.binary), 'agents', 'add', name, '--workspace', str(workspace), '--non-interactive', '--json']
        if model:
            command.extend(['--model', model])
        if dry_run:
            self.process_runner.report('[DRY] ' + self.process_runner.printable(command))
            return
        result = self._shell.run(command, capture=True)
        output = result.stdout.strip()
        if not output:
            return
        try:
            payload = json.loads(output)
            self.process_runner.report(json.dumps(payload, indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            self.process_runner.report(output)

    def _find_agent(self, name: str) -> dict | None:
        agents = self.list_agents()
        for agent in agents:
            if agent.get('id') == name:
                return agent
        return None

    def list_agents(self) -> list[dict]:
        LOGGER.debug('Starting backend.list_agents')
        result = self._shell.run([str(self.binary), 'agents', 'list', '--json'], capture=True)
        try:
            agents = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError('OpenClaw returned invalid JSON while listing agents.') from exc
        if not isinstance(agents, list):
            raise RuntimeError('OpenClaw returned an invalid agent list.')
        return [agent for agent in agents if isinstance(agent, dict)]

    def _update_agent(self, *, name: str, existing: dict, workspace: Path, model: str | None, dry_run: bool) -> None:
        updates = [('workspace', str(workspace), existing.get('workspace'))]
        if model is not None:
            updates.append(('model', model, existing.get('model')))
        changed = False
        for field, value, current in updates:
            if current == value:
                continue
            changed = True
            command = [str(self.binary), 'config', 'set', f'agents.entries.{name}.{field}', json.dumps(value), '--strict-json']
            if dry_run:
                self.process_runner.report('[DRY] ' + self.process_runner.printable(command))
                continue
            self._shell.run(command)
        if not changed:
            self.process_runner.report(f'[+] OpenClaw agent already registered: {name}')

    def apply_identity(self, *, name: str, workspace: Path, dry_run: bool=False) -> None:
        LOGGER.debug('Starting backend.apply_identity name=%s dry_run=%s', name, dry_run)
        identity = workspace / 'IDENTITY.md'
        if not identity.is_file():
            return
        command = [str(self.binary), 'agents', 'set-identity', '--agent', name, '--identity-file', str(identity)]
        if dry_run:
            self.process_runner.report('[DRY] ' + self.process_runner.printable(command))
            return
        self._shell.run(command)

    def install_executor_plugin(self, plugin_root: Path, *, snapshot_root: Path, dry_run: bool=False) -> None:
        """Install a root-owned snapshot accepted by OpenClaw's trust checks."""
        LOGGER.debug('Starting backend.install_executor_plugin dry_run=%s', dry_run)
        if not (plugin_root / 'openclaw.plugin.json').is_file():
            raise FileNotFoundError(f'Missing OpenClaw plugin manifest: {plugin_root}')
        if snapshot_root.name != self.EXECUTOR_PLUGIN_ID:
            raise ValueError(f'Plugin snapshot must end with {self.EXECUTOR_PLUGIN_ID}: {snapshot_root}')
        if dry_run:
            self.process_runner.report(f'[DRY] synchronize plugin {plugin_root} -> {snapshot_root}')
        else:
            self._sync_plugin_snapshot(plugin_root, snapshot_root)
        commands = [[str(self.binary), 'plugins', 'install', '--link', '--force', str(snapshot_root)], [str(self.binary), 'plugins', 'enable', self.EXECUTOR_PLUGIN_ID]]
        for command in commands:
            if dry_run:
                self.process_runner.report('[DRY] ' + self.process_runner.printable(command))
            else:
                self._shell.run(command)

    def _sync_plugin_snapshot(self, source: Path, destination: Path) -> None:
        """Replace one managed plugin tree with trusted ownership and modes."""
        source = source.resolve(strict=True)
        destination = Path(os.path.abspath(destination.expanduser()))
        if source == destination or destination.name != self.EXECUTOR_PLUGIN_ID:
            raise ValueError(f'Unsafe plugin snapshot destination: {destination}')
        gateway = pwd.getpwnam(self.gateway_user)
        current_uid = os.geteuid()
        if current_uid not in {0, gateway.pw_uid}:
            raise PermissionError('Plugin snapshot must be created by root or the gateway user.')
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=f'.{self.EXECUTOR_PLUGIN_ID}.', dir=destination.parent))
        try:
            shutil.copytree(source, temporary, dirs_exist_ok=True)
            owner_uid = 0 if current_uid == 0 else gateway.pw_uid
            for item in [temporary, *temporary.rglob('*')]:
                if item.is_symlink():
                    raise RuntimeError(f'Plugin snapshot cannot contain symlinks: {item}')
                os.chown(item, owner_uid, gateway.pw_gid)
                item.chmod(488 if item.is_dir() else 416)
            if destination.is_symlink() or destination.is_file():
                destination.unlink()
            elif destination.exists():
                shutil.rmtree(destination)
            temporary.replace(destination)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)

    def set_agent_tools(self, name: str, policy: dict, *, dry_run: bool=False) -> None:
        """Persist one validated per-agent tool policy in OpenClaw."""
        LOGGER.debug('Starting backend.set_agent_tools name=%s dry_run=%s', name, dry_run)
        policy = dict(policy)
        if 'also_allow' in policy:
            policy['alsoAllow'] = policy.pop('also_allow')
        command = [str(self.binary), 'config', 'set', f'agents.entries.{name}.tools', json.dumps(policy, ensure_ascii=False, separators=(',', ':')), '--strict-json']
        if dry_run:
            self.process_runner.report('[DRY] ' + self.process_runner.printable(command))
            return
        self._shell.run(command)

    def get_agent_tools(self, name: str) -> dict:
        """Read the currently authored OpenClaw tool policy for one agent."""
        LOGGER.debug('Starting backend.get_agent_tools name=%s', name)
        result = self._shell.run([str(self.binary), 'config', 'get', f'agents.entries.{name}.tools'], check=False, capture=True)
        if result.returncode != 0:
            combined = f'{result.stdout or ''}\n{result.stderr or ''}'
            if 'Config path is valid but unset' in combined:
                return {}
            raise RuntimeError('OpenClaw could not read the agent tool policy: ' + combined.strip())
        try:
            policy = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError('OpenClaw returned an invalid tool policy.') from exc
        if not isinstance(policy, dict):
            raise RuntimeError('OpenClaw tool policy must be a JSON object.')
        return policy

    def run_agent(self, *, agent_name: str, session_key: str, message_file: Path, timeout: int):
        LOGGER.debug('Starting backend.run_agent agent_name=%s timeout=%s', agent_name, timeout)
        return self._shell.run(['openclaw', 'agent', '--agent', agent_name,
                                '--session-key', session_key, '--message-file', str(message_file),
                                '--timeout', str(timeout), '--json'], capture=True, timeout=timeout + 30)

