# Agents System

**An experimental, modular environment for building, running, and connecting autonomous AI agents on Linux.**

Agents System is a personal, passion-driven engineering project. Its long-term goal is to give AI agents their own identities, execution environments, tools, memory, and ways to collaborate, while keeping the underlying infrastructure under the operator's control.

**Everyone interested in collaborating is warmly welcome, regardless of background or experience level.**

> [!CAUTION]
> **Experimental research and development project. Not production-ready.**
>
> This repository is a large, evolving solo project built primarily out of curiosity and a passion for systems programming, infrastructure, and AI. **Significant parts are incomplete, undergoing refactoring, insufficiently tested, or may not work at all in the current revision.** Some components have been exercised independently, but that does **not** mean the entire system is integrated or reliably runnable.
>
> Expect breaking changes, inconsistent interfaces, unfinished features, and outdated documentation. **Do not treat this repository as a secure sandbox, a supported product, or a ready-to-deploy platform.** In particular, parts of the installer and agent manager modify Linux accounts, permissions, files, and services. Explore it in a disposable VM or another isolated development environment, not on a valuable host.

## The idea

The original goal was simple: build a personal AI agent. That idea grew into an experiment in creating an **operating environment for agents**, rather than another chat interface or a wrapper around a single model provider.

An agent should eventually be able to:

- Have its own Linux identity, home directory, configuration, and tools.
- Run tasks through a controlled execution interface.
- Communicate with a person and with other agents.
- Maintain short-term working context and long-term records of its activities.
- Recall prior tasks, commands, outcomes, and learned information.
- Use interchangeable AI backends, including local models and external coding-agent runtimes.
- Work on explicitly assigned directories without unrestricted access to the host.

**This is the design direction, not a list of completed features.** The project is as much about investigating architectural trade-offs as it is about shipping software.

## Architecture at a glance

```text
                        Human / CLI / other agents
                                   |
                         Manifest-driven CLI
                                   |
                     Agents System control plane
                                   |
                       Shared application runtime
                       (Unix sockets, module loading)
                                   |
               +-------------------+--------------------+
               |                   |                    |
         Agent management    Pluggable providers    Agent data layer
               |                   |                    |
          Linux users          OpenClaw adapter     Redis Streams
          Home directories     Future adapters      Redis Cache
          Agent lifecycle      Local AI (planned)   MongoDB
               |                                        |
          Controlled tools                       Memory (evolving)
          Sandboxes (planned)                    Vector search (planned)
```

This diagram describes the intended relationship between subsystems. **It is not a claim that every connection or workflow is implemented end-to-end.**

## What's in the repository

| Area | Location | Current scope |
| --- | --- | --- |
| CLI | `src/agents_system_cli/` | Manifest-driven commands, argument parsing, rendering, and local/runtime dispatch. |
| Control plane | `src/agents_system/` | System-facing application logic and module access. |
| Shared runtime | `src/_runtime/` | Dynamic Python module loading, managed instances, execution dispatch, and Unix-socket API. |
| Agent management API | `src/agents_manager/` | Commands forwarded to the manager runtime. |
| Agent manager runtime | `src/agents_manager_runtime/` | Agent installation/removal/execution experiments, Linux account operations, OpenClaw integration, and communication-related code. |
| Agent data client | `src/agents_data/` | Local messaging and data application under migration. |
| Data backend | `src/agents_data_backend/` | Evolving Docker/Compose management and a transitional Redis/MongoDB service stack. |
| Shared libraries | `src/lib/` | Unix-socket client, Compose parser, configuration, JSON and manifest loaders, and module catalog. |
| OpenClaw tool plugin | `provider_plugins/openclaw/agent-executor/` | `agent_exec` integration with the Agents System command wrapper. |
| Installer | `install/` | Development/system installation, configuration, and rollback experiments. |

The codebase is actively being consolidated from earlier components. Some documentation, tests, and migration artifacts reflect previous implementations.

## Design highlights

### Modular runtime and plugins

Applications can be described by JSON manifests and loaded dynamically into a resident Python runtime. The CLI derives commands and help from module metadata and can route requests to the runtime over Unix-domain sockets or use a local module path where supported.

The intention is to make new functionality available through modules without hard-coding every integration into the core. **Loading Python code into the shared process is not a security boundary:** only trusted modules should run there.

### Replaceable AI runtimes

The current code contains an **OpenClaw adapter and facade** for agent lifecycle operations and invocation. The adapter layer is intended to make OpenClaw replaceable rather than a permanent dependency of the system design.

A companion OpenClaw plugin exposes an `agent_exec` tool. It obtains an agent ID from OpenClaw's tool context and forwards commands to the `agents_exec` wrapper. This is an integration point, **not a guarantee of complete command auditing or isolation**.

Future providers may include a custom agent runtime, locally hosted models, and integrations with external coding agents where suitable interfaces are available.

### Three roles for data

The experimental data stack separates responsibilities:

| Component | Intended purpose |
| --- | --- |
| **Redis Streams** | Events, messages, and asynchronous communication between agents. |
| **Redis Cache** | Fast access to working memory, transient state, and cached data. |
| **MongoDB** | Persistent messages, activity records, and longer-term agent memory. |

A Compose definition with **two Redis instances and MongoDB**, alongside transitional TypeScript services, lives in [`src/agents_data_backend/docker/docker_files/docker-compose.yml`](src/agents_data_backend/docker/docker_files/docker-compose.yml).

**Important:** the checked-in Compose configuration is for experimentation. It includes example credentials and exposed ports; both Redis instances currently disable disk persistence. `noeviction` on the Streams instance does not make messages durable across restarts. Do not deploy these defaults on an exposed or production host.

JSON manifests are used extensively so application configuration and state have explicit, portable structures. Persisting those structures into MongoDB is part of the longer-term direction, not a completed universal storage layer.

### Agent identity and lifecycle

The manager code explores per-agent Linux users, home directories, permissions, staged installation, status tracking, and cleanup after failed operations. This provides the groundwork for more controlled execution, but it does **not** yet establish comprehensive host isolation.

### Planned task sandboxes

The intended execution model gives an agent access to its own home directory and an explicitly assigned task workspace. Future work may combine mount namespaces, OverlayFS copy-on-write layers, allowlisted mounts, filesystem restrictions, and resource limits to make changes reviewable before applying them to the original workspace.

**OverlayFS alone is not a security sandbox.** These controls are a proposed direction, not a feature that can currently be relied upon.

## Project maturity

The following is a deliberately conservative snapshot of the repository:

| Capability | Status |
| --- | --- |
| Manifest-based CLI and module catalog | Implemented in parts; evolving |
| Dynamic module loading and shared runtime | Implemented in parts; integration still evolving |
| Unix-domain-socket communication library | Implemented with focused tests; interfaces may change |
| Linux agent account and lifecycle management | Partially implemented; host-affecting operations |
| OpenClaw adapter and tool plugin | Present; integration and hardening ongoing |
| Two-Redis / MongoDB Compose stack | Present for experimentation; not production-configured |
| Docker desired-state management | Under active development |
| Reliable end-to-end agent messaging and durable memory | In progress / incomplete |
| Fully controlled shell and comprehensive activity history | Planned / incomplete |
| Local LLM providers and model orchestration | Planned |
| Vector or semantic memory | Planned |
| OverlayFS-based task isolation | Planned |
| General-purpose autonomous multi-agent workflows | Long-term goal |

Some individual paths work and have been tested during development. **No repository-wide correctness, compatibility, or security guarantee is implied by this table.**

## Exploring the code

**Target environment:** Linux. Different modules may require Python 3, Bash, Docker/Compose, systemd, Redis, MongoDB, Node.js, or an installed OpenClaw environment. There is no single, verified one-command setup for the whole system at this stage.

To inspect the development branch:

```bash
git clone --branch agents-data/create-datastore \
  https://github.com/ajambor91/agents-system.git
cd agents-system
```

Start with the architecture and the installer's help, without making system changes:

```bash
cat ARCHITECTURE.md
./install/install.sh --help
```

The installer documents a development mode, for example:

```bash
sudo ./install/install.sh --yes --mode dev --invoker "$USER"
```

**Do not run that command casually.** It may alter accounts, permissions, directories, installed commands, and service-related state. Read [`install/README.md`](install/README.md), review the source, and use an isolated test machine first. It may also fail on the current branch.

For lightweight checks, if dependencies are installed:

```bash
python3 -m compileall -q src tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

These are diagnostic commands, **not a currently guaranteed passing test suite**. Some package-local tests and older test contracts require separate attention.

To inspect the experimental container configuration without starting services:

```bash
docker compose -f src/agents_data_backend/docker/docker_files/docker-compose.yml config
```

## Roadmap and open questions

Priorities and experiments include:

1. Stabilize interfaces and end-to-end workflows across existing runtimes and modules.
2. Strengthen authorization, privilege separation, tests, and recovery behavior.
3. Complete the data/backend migration and define reliable message delivery and persistence semantics.
4. Build first-class agent activity records and memory retrieval, with optional local ML/LLM summarization and vector search.
5. Support additional model providers and eventually an independent agent runtime.
6. Introduce isolated task workspaces, controlled execution, and explicit change approval.
7. Explore autonomous collaboration, task routing, and delegation between agents.

There is no committed release schedule. The architecture may change substantially as experiments reveal better approaches.

## Development philosophy

This is a **solo, passion project** that deliberately favors exploration, learning, and testing ambitious ideas over feature completeness or uniform polish. It includes hand-written systems code, refactored experiments, and selected AI-assisted implementations. Design decisions, integration contracts, and code remain subject to review and revision.

The goal is not to claim that every subsystem is finished. It is to explore how a modular, extensible, locally controlled agent platform might be built, one working piece at a time.

## Collaboration and contributions

**Everyone is welcome to collaborate on Agents System.** This is a passion project, and any person who wants to help build, explore, improve, or simply discuss it is genuinely welcome, regardless of experience level. You do not have to be an expert in AI, Linux, or distributed systems to contribute something valuable.

Code contributions are appreciated, but collaboration can also mean testing, reporting bugs, reviewing architecture or security, improving documentation, suggesting features, sharing ideas, or experimenting with integrations. **Small contributions matter just as much as ambitious ones.**

If you would like to get involved, feel free to open an issue or propose a pull request. For larger changes, discussing the approach first is encouraged because the architecture is still evolving. Please keep in mind that parts of the repository may be incomplete or broken, and there is no promise of a stable development environment yet.

**This project may have started as a solo experiment, but it does not have to remain a solo effort.**

## Documentation

- [`ARCHITECTURE.md`](ARCHITECTURE.md): architectural intent and consolidation plan.
- [`AGENT_MANAGER_MERGE.md`](AGENT_MANAGER_MERGE.md): agent-manager migration notes.
- [`COMMUNICATION_STACK_MERGE.md`](COMMUNICATION_STACK_MERGE.md): messaging/data migration plan.
- [`install/README.md`](install/README.md): installation and rollback details.
- [`src/agents_system_cli/README.md`](src/agents_system_cli/README.md): CLI details.
- [`src/lib/`](src/lib/): individual shared-library documentation.

Some of these documents are themselves works in progress and may describe intended behavior rather than the current implementation.

## License

No license file was found in the reviewed repository snapshot. **Do not assume permission to redistribute or reuse the source without an applicable license or the author's permission.**
