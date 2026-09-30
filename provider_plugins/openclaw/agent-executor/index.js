import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { defineToolPlugin } from "openclaw/plugin-sdk/tool-plugin";

const execFileAsync = promisify(execFile);
const DEFAULT_EXECUTABLE = "/usr/local/bin/agents_exec";

const parameters = {
  type: "object",
  additionalProperties: false,
  required: ["command"],
  properties: {
    command: {
      type: "string",
      minLength: 1,
      description: "Shell command to execute through AgentExecutor."
    }
  }
};

function createTool(toolContext) {
  const agentId = toolContext.agentId;
  if (typeof agentId !== "string" || agentId.length === 0) {
    return null;
  }

  return {
    name: "agent_exec",
    label: "Agent Executor",
    description:
      "Execute a shell command as this agent through Agents Manager. " +
      "The command runs in the agent workspace and is recorded in its history.",
    parameters,
    async execute(_toolCallId, parameters) {
      const command = parameters?.command;
      if (typeof command !== "string" || command.trim().length === 0) {
        throw new Error("agent_exec requires a non-empty command.");
      }

      const executable = process.env.AGENTS_EXEC_BIN || DEFAULT_EXECUTABLE;
      try {
        const result = await execFileAsync(
          executable,
          [
            `--name=${agentId}`,
            `--command=${command}`,
            `--requested-by=openclaw:${agentId}`
          ],
          {
            encoding: "utf8",
            maxBuffer: 8 * 1024 * 1024,
            timeout: 3_700_000
          }
        );
        const output = `${result.stdout || ""}${result.stderr || ""}`;
        return {
          content: [{ type: "text", text: output || "Command completed." }],
          details: { agent: agentId, returnCode: 0 }
        };
      } catch (error) {
        const stdout = typeof error?.stdout === "string" ? error.stdout : "";
        const stderr = typeof error?.stderr === "string" ? error.stderr : "";
        const detail = `${stdout}${stderr}`.trim() || String(error?.message || error);
        throw new Error(`AgentExecutor failed for ${agentId}: ${detail}`);
      }
    }
  };
}

export default defineToolPlugin({
  id: "agent-executor",
  name: "Agent Executor",
  description: "Routes host shell commands through Agents Manager.",
  tools: (tool) => [
    tool({
      name: "agent_exec",
      label: "Agent Executor",
      description:
        "Execute a shell command as this agent through Agents Manager. " +
        "The command runs in the agent workspace and is recorded in its history.",
      parameters,
      optional: true,
      factory({ toolContext }) {
        return createTool(toolContext);
      }
    })
  ]
});
