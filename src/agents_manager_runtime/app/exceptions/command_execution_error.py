import subprocess


class CommandExecutionError(RuntimeError):
    def __init__(self, error: subprocess.CalledProcessError):
        self.command = error.cmd
        self.returncode = error.returncode
        self.stdout = error.stdout
        self.stderr = error.stderr

        super().__init__(
            f"Command {self.command!r} failed "
            f"with exit code {self.returncode}\n"
            f"STDOUT: {self.stdout or '<empty>'}\n"
            f"STDERR: {self.stderr or '<empty>'}"
        )