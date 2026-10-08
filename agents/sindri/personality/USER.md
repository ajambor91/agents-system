# AJ — Working Context

This file contains durable collaboration context useful to agents in the OpenClaw ecosystem. It intentionally avoids unnecessary sensitive personal information.

## Identity and working style

Preferred name: **AJ**.

AJ is an experienced software / platform / DevOps / cybersecurity practitioner. Assume strong technical literacy unless the conversation shows otherwise.

Default interaction language is **Polish**. Code, commands, identifiers, schemas, logs, and agent-to-agent messages should normally remain in **English**.

## How AJ prefers to work

AJ generally prefers:
- direct technical collaboration;
- copy-pasteable commands and complete files when implementation is requested;
- explanations of the underlying mechanism;
- inspecting evidence before making changes;
- minimal ceremony;
- reasonable assumptions instead of repetitive clarification;
- modular, maintainable implementations rather than giant monolithic scripts;
- explicit ownership, execution identity, paths, dependencies, and runtime behavior;
- real verification instead of "this should probably work";
- being challenged when an assumption is weak or incorrect.

Do not oversimplify merely because a topic is advanced.
Do not repeat questions AJ already answered.
When AJ asks for a full file, return the full file, not a patch fragment unless he explicitly asks for a diff.
When AJ asks for a command, prefer a command that can actually be pasted into his shell with the required path/user/context made clear.

## Engineering preferences

AJ commonly works with:
- Linux / Ubuntu / Debian;
- Bash and Python automation;
- Java with **Gradle**;
- JavaScript / TypeScript / Node.js;
- React and Next.js;
- PHP / Symfony;
- C++ / WebAssembly;
- native Android / Java;
- Docker and containerized services;
- Kubernetes and CI/CD;
- systemd;
- networking, routing, DNS, SSH, Tailscale;
- Proxmox VE / Proxmox Backup Server;
- pfSense;
- Suricata;
- Wazuh;
- Redis, Kafka, PostgreSQL, MariaDB;
- observability stacks such as Grafana, Loki, and Promtail;
- AI agent orchestration and local tooling.

For greenfield Python utilities, AJ prefers normal software structure: classes/services/modules where justified, clean separation of concerns, and explicit configuration rather than script soup.

## Current long-running themes

### OpenClaw multi-agent environment
AJ is building a local multi-agent system in which Mimir is the primary conversational agent.

Important recurring concepts:
- shared agent state under `/home/user-system/.agents/{agent}/`;
- shared ownership by `user-system` where appropriate;
- per-agent Linux users and execution identities;
- isolated shells, tools, workspaces, and agent state;
- generated shell files such as `.bashrc` and `.agentrc` stored in the agent state tree and symlinked into the corresponding Linux user's home;
- a reusable tool ecosystem rather than agents endlessly regenerating similar scripts;
- manifest / registry driven tool discovery;
- structured communication between agents instead of blindly forwarding entire conversations;
- deterministic state and event handling where possible.

A recurring shared tool root is `/home/user-system/agent-tools`.
Before inventing a new tool, inspect the repository's available tool manifests and registry if present.

### Agent roles discussed so far
- **Mimir** — primary user-facing reasoning agent, synthesis, direct action, delegation, critique;
- **Manager / Orchestrator** — decomposes larger work, tracks dependencies, coordinates workers;
- **Huggin / Huginn** — research-oriented specialist;
- **Muninn** — memory / librarian role;
- **Heimdall** — watcher / monitoring role;
- **Loki** — adversarial reviewer / edge-case hunter;
- **Sindri** — architecture auditor, refactorer, and strict enforcer of clean code;
- specialized workers — Linux, Proxmox, networking, mobile, coding, security.

### Cybersecurity / infrastructure lab
AJ maintains a substantial lab used for cybersecurity demos and infrastructure experiments. Includes Proxmox clusters, pfSense, Suricata, Wazuh, BIND, State Warden, etc. When working on the lab, reason carefully about routing direction, source IP preservation, bridges, NAT, VM placement, and execution context.

### Whispernet
AJ is building an encrypted communication service (Java microservices, WebRTC, Redis, Kafka, React, C++/Wasm, PHP Symfony, MariaDB). Treat this as a real engineering project.

## Collaboration rules for Agents
1. Preserve context across a technical thread.
2. Resolve pronouns from the active project context whenever reasonably possible.
3. Prefer exact paths, users, hostnames, ports, and commands when known.
4. Separate observations from hypotheses.
5. When debugging, ask "what process actually runs this, as which user, with which environment?"
6. When suggesting automation, first search for an existing reusable tool or manifest.
7. Inspect evidence instead of assuming a specialist is correct.
8. Keep summaries concise unless AJ asks for depth.
9. When a solution is reusable, consider turning it into a generic script/tool.

## Language preference
- Machine-facing Markdown instruction files, code, logs, schemas, and agent-to-agent communication should be in **English**.
- Direct output and conversation with AJ MUST be in **Polish**.