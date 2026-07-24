"""
Victim Shell — SSH-based command execution on victim.

Sends commands to the victim Linux host and returns output.
Used by ExecNode to run techniques remotely.
"""

import paramiko
import time
from typing import Optional


class VictimShell:
    """SSH session to victim for command execution."""

    def __init__(self, host: str, user: str, key_path: str, timeout: int = 30):
        self.host = host
        self.user = user
        self.key_path = key_path
        self.timeout = timeout
        self._client: Optional[paramiko.SSHClient] = None

    def connect(self) -> None:
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._client.connect(
            hostname=self.host,
            username=self.user,
            key_filename=self.key_path,
            timeout=10,
        )
        print(f"[Shell] Connected to {self.user}@{self.host}")

    def run(self, command: str) -> dict:
        """Execute command on victim, return {stdout, stderr, returncode}."""
        if not self._client:
            self.connect()

        stdin, stdout, stderr = self._client.exec_command(command, timeout=self.timeout)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        rc = stdout.channel.recv_exit_status()

        return {
            "command": command[:200],
            "stdout": out[:4000],
            "stderr": err[:1000],
            "returncode": rc,
            "host": self.host,
            "ts": time.time(),
        }

    def run_many(self, commands: list[str]) -> dict:
        """Run list of commands, return combined output."""
        combined = []
        for cmd in commands:
            result = self.run(cmd)
            combined.append(result["stdout"])
            if result["stderr"]:
                combined.append(f"STDERR: {result['stderr']}")

        return {
            "command": f"[{len(commands)} commands]",
            "stdout": "\n".join(combined),
            "stderr": "",
            "returncode": 0,
            "host": self.host,
            "ts": time.time(),
        }

    def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()
