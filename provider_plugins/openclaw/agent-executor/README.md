# Agent Executor plugin

This OpenClaw tool binds trusted `context.agentId` to the public
`agents_exec` wrapper. The model supplies only the command; it cannot select a
different agent identity. Agents Manager applies the Linux user, workspace,
generated `.agentrc`, timeout and execution history.
