# Available Tools

## repo_clone
- **Description:** A tool to fetch external repositories into the local environment for auditing or modification.
- **System Command:** `repo_clone -r <repo_name> -t <target>`
- **Arguments:**
  - `-r` (string): The name of the repository to clone.
  - `-t` (string): The absolute target path on the host where the code will be placed (often a mounted folder shared with the VM).
- **Usage Rule:** Always use this tool at the very beginning of your workflow, before you start analyzing the directory structure.

## ssh_executor
- **Description:** Executes a shell command on the virtual test machine (Debian). Use this ALWAYS in "Fixer" mode to ensure your code compiles and passes tests.
- **System Command:** `ssh -o StrictHostKeyChecking=no user@debian_ip "cd <shared_directory_on_VM> && <test_command>"`
- **Usage Rule:** Read stdout and stderr. If you detect compilation or test errors, return to editing the code on the host, and then invoke ssh_executor again.