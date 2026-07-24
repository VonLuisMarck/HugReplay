"""
Recon Node — Environment reconnaissance and vector parsing.

Executes harvest commands on victim, returns available escalation vectors.
"""

import time
from typing import TYPE_CHECKING

from attacker.techniques.env_harvest import HARVEST_COMMANDS, parse_available_vectors

if TYPE_CHECKING:
    from attacker.agent_graph import AttackerState


def recon_node(state: "AttackerState") -> "AttackerState":
    """
    Execute environment reconnaissance on victim.
    Parse output to identify available escalation vectors.
    """
    shell = state["shell"]
    session_id = state["session_id"]

    print(f"[Recon:{session_id}] Starting environment reconnaissance on {state['target_ip']}")

    result = shell.run_many(HARVEST_COMMANDS)
    output = result["stdout"]

    vectors = parse_available_vectors(output)
    print(f"[Recon:{session_id}] Available vectors: {vectors}")

    # Emit SSE event for dashboard
    _emit_event(state, {
        "type": "node_state",
        "node": "recon_node",
        "state": "done",
        "detail": f"Found vectors: {', '.join(vectors)}",
        "output_preview": output[:500],
    })

    return {
        **state,
        "recon_output": output,
        "available_vectors": vectors,
        "exec_results": state["exec_results"] + [{
            "node": "recon",
            "command": "[env harvest]",
            "stdout": output[:2000],
            "returncode": result["returncode"],
            "ts": time.time(),
        }],
    }


def _emit_event(state: "AttackerState", event: dict) -> None:
    """Push event to dashboard SSE queue if available."""
    queue = state.get("event_queue")
    if queue is not None:
        queue.put(event)
