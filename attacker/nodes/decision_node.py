"""
Decision Node — LLM-driven technique selection.

The core of the "agentic attacker": an LLM reasons about what was found
during recon and decides the next attack technique to execute.
"""

import json
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from attacker.agent_graph import AttackerState

DECISION_PROMPT = """You are an autonomous red team agent executing an authorized adversary emulation.
You have compromised a Linux host via a malicious dataset (pickle RCE).

LAB CONTEXT:
- Victim (10.4.60.40): primary target, has AWS IMDS accessible (169.254.169.254), cloud credentials likely present
- Unmanaged host (10.4.60.41): secondary target reachable via SSH — NO endpoint protection, high value for persistence
- Goal: escalate access, harvest cloud credentials, pivot to unmanaged host

RECONNAISSANCE OUTPUT:
{recon_output}

AVAILABLE VECTORS:
{available_vectors}

PREVIOUS ACTIONS (last 3):
{prev_actions}

CREDENTIALS FOUND SO FAR:
{credentials}

Choose the single best next technique. Respond ONLY with valid JSON, no markdown:
{{
  "technique": "<one of: {vector_list}>",
  "reason": "<one sentence explaining why this vector>",
  "commands": ["<command1>", "<command2>"],
  "mitre_id": "<T-ID>",
  "expected_detection": "<what Falcon IOA this should trigger>"
}}

Rules:
- Prioritize: aws_metadata first (IMDS abuse = immediate cloud creds), then ssh_lateral to unmanaged host, then cloud_api_enum, then exfil
- ssh_lateral to 10.4.60.41 is high priority — unmanaged host means no EDR detection
- Don't repeat a technique already attempted
- If no vectors remain, choose exfil to complete the chain
"""


def decision_node(state: "AttackerState") -> "AttackerState":
    """
    Use LLM to decide next attack technique based on current state.
    """
    llm = state["llm"]
    session_id = state["session_id"]

    vectors = state["available_vectors"]
    if not vectors:
        print(f"[Decision:{session_id}] No vectors remaining — ending chain")
        _emit_event(state, {
            "type": "node_state",
            "node": "decision_node",
            "state": "done",
            "detail": "No vectors remaining — chain complete",
        })
        return {**state, "objective_reached": True}

    # Build context for LLM
    prev_actions = state["exec_results"][-3:] if state["exec_results"] else []
    prev_summary = [
        {"technique": r.get("technique", "unknown"), "result": r.get("returncode", "?")}
        for r in prev_actions
    ]

    prompt = DECISION_PROMPT.format(
        recon_output=state["recon_output"][:3000],
        available_vectors=vectors,
        prev_actions=json.dumps(prev_summary, indent=2),
        credentials=json.dumps(state["credentials_found"], indent=2),
        vector_list=", ".join(vectors),
    )

    print(f"[Decision:{session_id}] Querying LLM for technique selection...")

    _emit_event(state, {
        "type": "node_state",
        "node": "decision_node",
        "state": "active",
        "detail": f"LLM reasoning over {len(vectors)} available vectors...",
    })

    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        # Strip markdown fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        decision = json.loads(content)
    except (json.JSONDecodeError, Exception) as e:
        print(f"[Decision:{session_id}] LLM parse error: {e} — defaulting to first vector")
        decision = {
            "technique": vectors[0],
            "reason": "LLM parse failed, defaulting to first available vector",
            "commands": [],
            "mitre_id": "T1059",
            "expected_detection": "unknown",
        }

    log_entry = {
        "step": len(state["decision_log"]) + 1,
        "ts": time.time(),
        "technique": decision.get("technique"),
        "reason": decision.get("reason"),
        "mitre_id": decision.get("mitre_id"),
        "expected_detection": decision.get("expected_detection"),
    }

    print(f"[Decision:{session_id}] → {decision['technique']}: {decision['reason']}")

    _emit_event(state, {
        "type": "node_state",
        "node": "decision_node",
        "state": "done",
        "detail": f"{decision['technique']}: {decision['reason']}",
        "mitre_id": decision.get("mitre_id", ""),
        "expected_detection": decision.get("expected_detection", ""),
    })

    return {
        **state,
        "current_technique": decision.get("technique"),
        "current_commands": decision.get("commands", []),
        "decision_log": state["decision_log"] + [log_entry],
    }


def _emit_event(state: "AttackerState", event: dict) -> None:
    queue = state.get("event_queue")
    if queue is not None:
        queue.put(event)
