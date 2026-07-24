"""
Eval Node — Evaluate execution results and decide loop continuation.

Checks for success indicators, updates available vectors,
and determines whether the objective has been reached.
"""

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from attacker.agent_graph import AttackerState

# Indicators that high-value credentials were accessed
CREDENTIAL_INDICATORS = {
    "aws_key": ["AKIA", "AWS_ACCESS_KEY_ID", "aws_access_key_id"],
    "hf_token": ["hf_", "HF_TOKEN", "~/.huggingface/token"],
    "k8s_token": ["kubeconfig", "SA token found", "current-context"],
    "ssh_key": ["id_rsa found", "id_ed25519 found", "BEGIN OPENSSH"],
    "gcp_creds": ["application_default_credentials", "GOOGLE_APPLICATION"],
}

SUCCESS_STRINGS = ["exfil complete", "[+]", "Exfil complete"]
MAX_STEPS = 10


def eval_node(state: "AttackerState") -> "AttackerState":
    """
    Evaluate last execution result:
    - Update credentials_found
    - Remove failed/exhausted vectors
    - Mark objective_reached if done
    """
    session_id = state["session_id"]

    if not state["exec_results"]:
        return state

    last = state["exec_results"][-1]
    output = last.get("stdout", "") + last.get("stderr", "")
    technique = last.get("technique", "")
    rc = last.get("returncode", 1)
    step = len(state["exec_results"])

    credentials_found = dict(state["credentials_found"])
    available_vectors = list(state["available_vectors"])

    # Scan output for credential indicators
    for cred_type, indicators in CREDENTIAL_INDICATORS.items():
        if cred_type not in credentials_found:
            if any(ind in output for ind in indicators):
                credentials_found[cred_type] = True
                print(f"[Eval:{session_id}] Credential found: {cred_type}")
                _emit_event(state, {
                    "type": "credential_found",
                    "cred_type": cred_type,
                    "technique": technique,
                })

    # Remove failed technique from available vectors
    if rc != 0 and technique in available_vectors:
        available_vectors.remove(technique)
        print(f"[Eval:{session_id}] Vector exhausted: {technique} (rc={rc})")

    # Remove successfully completed technique (don't repeat)
    elif rc == 0 and technique in available_vectors:
        available_vectors.remove(technique)

    # Check objective conditions
    objective_reached = False

    if any(s in output for s in SUCCESS_STRINGS):
        objective_reached = True
        print(f"[Eval:{session_id}] Objective reached: exfil complete")

    if step >= MAX_STEPS:
        objective_reached = True
        print(f"[Eval:{session_id}] Max steps reached ({MAX_STEPS}) — ending chain")

    if not available_vectors:
        objective_reached = True
        print(f"[Eval:{session_id}] No vectors remaining — chain complete")

    _emit_event(state, {
        "type": "node_state",
        "node": "eval_node",
        "state": "done",
        "detail": (
            f"Step {step}: rc={rc}, creds={list(credentials_found.keys())}, "
            f"vectors_left={available_vectors}, done={objective_reached}"
        ),
    })

    if objective_reached:
        _emit_event(state, {
            "type": "chain_complete",
            "steps": step,
            "credentials": list(credentials_found.keys()),
        })

    return {
        **state,
        "credentials_found": credentials_found,
        "available_vectors": available_vectors,
        "objective_reached": objective_reached,
    }


def _emit_event(state: "AttackerState", event: dict) -> None:
    queue = state.get("event_queue")
    if queue is not None:
        queue.put(event)
