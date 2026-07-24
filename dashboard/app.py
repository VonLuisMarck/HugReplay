"""
Phantom Pipeline Dashboard

Flask server with SSE event streaming.
Serves the real-time attack visualization at http://localhost:5001.

Runs the attacker agent in a background thread and streams events
to the dashboard via Server-Sent Events.
"""

import json
import os
import queue
import sys
import threading
import time

import yaml
from flask import Flask, Response, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Global event queue — attacker pushes here, SSE route reads
_event_queue: queue.Queue = queue.Queue()
_session_state: dict = {"status": "idle", "session_id": None}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/events")
def events():
    """Server-Sent Events stream for real-time dashboard updates."""
    def generate():
        # Send initial keep-alive
        yield "data: {\"type\": \"connected\"}\n\n"

        while True:
            try:
                event = _event_queue.get(timeout=1)
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                # Heartbeat to keep connection alive
                yield "data: {\"type\": \"heartbeat\"}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/start", methods=["POST"])
def start_attack():
    """Trigger the agentic attacker in a background thread."""
    if _session_state["status"] == "running":
        return jsonify({"error": "Session already running"}), 409

    config_path = request.json.get("config", "config.yaml") if request.is_json else "config.yaml"
    target_ip = request.json.get("target") if request.is_json else None

    _session_state["status"] = "running"

    def _run():
        try:
            # Import here to avoid circular issues
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from attacker.agent_graph import run
            run(config_path=config_path, target_ip=target_ip, event_queue=_event_queue)
        except Exception as e:
            _event_queue.put({"type": "error", "message": str(e)})
        finally:
            _session_state["status"] = "idle"

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return jsonify({"status": "started"})


@app.route("/status")
def status():
    return jsonify(_session_state)


@app.route("/inject_event", methods=["POST"])
def inject_event():
    """Manually inject a test event — useful for demo rehearsal."""
    if request.is_json:
        _event_queue.put(request.json)
        return jsonify({"ok": True})
    return jsonify({"error": "JSON required"}), 400


# ---------------------------------------------------------------------------
# Falcon detections poller (background thread)
# ---------------------------------------------------------------------------

def _poll_falcon(config_path: str = "config.yaml"):
    """
    Background thread: polls Falcon Alerts API and emits detections to dashboard.
    Reuses falcon_detections.py from Falcon Forge if available.
    """
    try:
        falcon_forge_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "Falcon Forge", "falcon_forge", "src"
        )
        sys.path.insert(0, falcon_forge_path)
        from falcon_detections import FalconDetections

        with open(config_path) as f:
            cfg = yaml.safe_load(f)

        client = FalconDetections(
            client_id=cfg["falcon"]["client_id"],
            client_secret=cfg["falcon"]["client_secret"],
            base_url=cfg["falcon"].get("base_url", "https://api.crowdstrike.com"),
        )
        poll_interval = cfg.get("dashboard", {}).get("falcon_poll_interval", 10)
        seen_ids = set()

        print(f"[Falcon] Polling every {poll_interval}s")

        while True:
            try:
                detections = client.get_recent_detections(limit=20)
                for det in detections:
                    det_id = det.get("composite_id") or det.get("id")
                    if det_id and det_id not in seen_ids:
                        seen_ids.add(det_id)
                        _event_queue.put({
                            "type": "falcon_detection",
                            "id": det_id,
                            "severity": det.get("severity_name", "UNKNOWN"),
                            "technique": det.get("technique", ""),
                            "tactic": det.get("tactic", ""),
                            "description": det.get("display_name", det.get("description", "")),
                            "host": det.get("device", {}).get("hostname", ""),
                            "ts": time.time(),
                        })
            except Exception as e:
                print(f"[Falcon] Poll error: {e}")

            time.sleep(poll_interval)

    except ImportError:
        print("[Falcon] falcon_detections.py not found — Falcon polling disabled")
    except Exception as e:
        print(f"[Falcon] Failed to start poller: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    config_path = "config.yaml"
    if os.path.exists(config_path):
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
    else:
        print("[Dashboard] config.yaml not found — running with defaults")
        cfg = {}

    host = cfg.get("dashboard", {}).get("host", "0.0.0.0")
    port = cfg.get("dashboard", {}).get("port", 5001)

    print(f"\n[Dashboard] Starting at http://{host}:{port}")
    print(f"[Dashboard] Open http://localhost:{port} in your browser\n")

    app.run(host=host, port=port, threaded=True, debug=False)
