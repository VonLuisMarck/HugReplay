# Phantom Pipeline

**Autonomous AI Attacker Framework** — Adversary emulation inspired by the HuggingFace July 2026 security incident.

---

## What This Is

On July 2026, HuggingFace disclosed an intrusion driven end-to-end by an autonomous AI agent. The attack started where AI platforms are uniquely exposed: the data-processing pipeline. A malicious dataset abused Python deserialization to execute code on a processing worker. From there, an autonomous agent framework harvested cloud credentials and moved laterally across clusters.

**Phantom Pipeline** replicates this attack pattern in an authorized lab environment to:
- Generate real CrowdStrike Falcon telemetry (IOAs/alerts)
- Demonstrate the "agentic attacker" threat model to customers
- Validate that Falcon detects autonomous, adaptive attack chains

---

## Architecture

```
victim/loader.py          → Simulates data scientist loading malicious dataset
        ↓
attacker/techniques/      → Initial access (pickle RCE / YAML injection)
        ↓
attacker/agent_graph.py   → LangGraph autonomous attacker (ReconNode → DecisionNode → ExecNode → EvalNode)
        ↓
attacker/c2/gist_c2.py    → C2 channel via GitHub Gist (self-migrating, like the real incident)
        ↓
dashboard/app.py          → Real-time visualization of agent decisions + Falcon detections
```

---

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai) with `llama3.1` pulled: `ollama pull llama3.1`
  - Or Anthropic API key (set `llm.provider: anthropic` in config)
- Lab access: victim Linux at `10.4.60.40`, SSH key configured
- Attacker host reachable from victim on `attacker_port` (default `8080`) — victim downloads `implant.py` over HTTP
- **GitHub Personal Access Token** — scope: `gist` only
  - Create at: https://github.com/settings/tokens/new → check `gist`
- Falcon API credentials — scope: `Alerts > Read`
- (Optional) `minikube` on victim for Kubernetes attack path

---

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure
cp config.example.yaml config.yaml
# Edit config.yaml with your lab IPs, GitHub token, Falcon credentials
# Key lab fields:
#   attacker_ip    — IP of your attacker machine (dashboard + SSH)
#   attacker_host  — optional domain/IP for implant C2 callbacks (defaults to attacker_ip)
#   attacker_port  — HTTP port for implant delivery and beacons (default: 8080)

# 3. Generate malicious dataset (runs locally, no victim needed)
python -m attacker.techniques.dataset_poison --output /tmp/imagenet_labels.pkl
# → Creates: /tmp/imagenet_labels.pkl (malicious pickle)
# → Creates: /tmp/dataset_config.yaml (YAML injection variant)
```

---

## Running the Demo

### Terminal 1 — Start dashboard
```bash
python dashboard/app.py
# → http://localhost:5001
```

### Terminal 2 — Start attacker agent
```bash
python -m attacker.agent_graph
# Agent waits for victim callback...
```

### On victim Linux (simulates the data scientist)
```bash
# Copy the malicious dataset to victim
scp /tmp/imagenet_labels.pkl ubuntu@10.4.60.40:/tmp/

# Victim "downloads and loads a dataset" — triggers the attack
ssh ubuntu@10.4.60.40 "python3 -" << 'EOF'
import pickle
data = pickle.load(open("/tmp/imagenet_labels.pkl", "rb"))
EOF
```

### Watch it happen
- **http://localhost:5001** — Attack graph animates as agent makes decisions
- **Falcon Console** — Detections fire within 30-90 seconds
- **GitHub Gists** — C2 channel visible at github.com/gists

---

## Attack Phases

| Phase | Technique | MITRE | Expected Falcon IOA |
|-------|-----------|-------|---------------------|
| 1. Dataset loads | Python pickle RCE | T1059.006 | Suspicious Python spawning shell/network | HIGH |
| 2. Environment recon | Env variable harvest | T1082 | System information discovery | MEDIUM |
| 3. Credential harvest | ML/cloud token access | T1552.007 | Cloud credential file access | HIGH |
| 4. Cloud API abuse | AWS/GCloud enumeration | T1530 | Suspicious cloud API calls | MEDIUM |
| 4b. K8s escalation | kubectl exec + privileged pod | T1610 | K8s privileged container | CRITICAL |
| 5. Lateral movement | SSH pivot to second host | T1021.004 | SSH from non-interactive process | HIGH |
| 6. C2 establishment | GitHub Gist polling | T1102 | Suspicious outbound to api.github.com | MEDIUM |
| 7. Exfiltration | HTTP POST credentials | T1048.003 | Large outbound POST | MEDIUM |

---

## The Asymmetry Point (Key Demo Talking Point)

> The attacker's agent had no guardrails — it could submit attack commands to any LLM freely.
> HuggingFace's defenders were blocked by commercial LLM safety filters when trying to analyze real attack logs.
> They had to switch to an open-weight model running locally.

**This is why Phantom Pipeline uses Ollama locally** — same operational security as the real attacker.

---

## C2 Channel Details

The GitHub Gist C2 replicates the "self-migrating C2 staged on public services" described in the incident:

- Each session creates a **new private Gist** (different ID every run)
- Commands are base64-encoded in the Gist content
- Implant polls every 30 seconds
- On session end, Gist is deleted (self-cleaning)
- If Gist is blocked/detected, agent creates a new one and updates implant

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Ollama not responding | `ollama serve` then `ollama pull llama3.1` |
| GitHub 401 | Token needs `gist` scope, not just `repo` |
| Victim not reachable | Check SSH key path in config.yaml, verify 10.4.60.40 is up |
| Implant not downloaded by victim | Check `attacker_port` is open on attacker host; victim must reach `http://{attacker_host}:{attacker_port}/implant.py` |
| Falcon detections not appearing | API poll interval default is 10s, detections have 30-90s lag |
| Pickle not triggering | Victim needs Python 3 with `pickle` module (standard lib) |
| K8s path not taken | Set `attack.k8s_enabled: true` in config.yaml, install minikube on victim |

---

## File Structure

```
phantom-pipeline/
├── attacker/
│   ├── agent_graph.py          # LangGraph orchestrator
│   ├── nodes/
│   │   ├── recon_node.py       # Environment reconnaissance
│   │   ├── decision_node.py    # LLM-driven technique selection
│   │   ├── exec_node.py        # Command execution on victim
│   │   └── eval_node.py        # Result evaluation + loop control
│   ├── techniques/
│   │   ├── dataset_poison.py   # Malicious pickle / YAML generator
│   │   ├── env_harvest.py      # ML/cloud credential harvesting
│   │   ├── k8s_attack.py       # Kubernetes attack path
│   │   └── lateral_ssh.py      # SSH lateral movement
│   └── c2/
│       ├── gist_c2.py          # GitHub Gist C2 (attacker side)
│       └── victim_shell.py     # SSH-based command execution
├── victim/
│   └── loader.py               # Simulates data scientist loading dataset
├── dashboard/
│   ├── app.py                  # Flask + SSE event server
│   ├── templates/index.html    # Main dashboard (D3.js)
│   └── static/
│       ├── js/
│       │   ├── attack_graph.js # LangGraph node visualization
│       │   ├── network_map.js  # Network topology animation
│       │   └── detections.js   # Falcon detections feed
│       └── css/dashboard.css   # Dark theme
├── config.example.yaml         # Config template
├── config.yaml                 # Your config (gitignored)
├── requirements.txt
└── README.md
```

---

## Demo Script (for SEs)

**Setup (5 min before demo):**
1. Start dashboard: `python dashboard/app.py` → keep browser open on http://localhost:5001
2. Start agent: `python -m attacker.agent_graph` → "Waiting for victim callback..."
3. Have Falcon Console open in another tab, Alerts view

**Narrative (during demo):**

> "What you're looking at is a simulation of the HuggingFace attack from two weeks ago.
> An AI company's data pipeline downloaded what looked like a normal ML dataset.
> Watch what happens when their data scientist loads it."

→ Run victim/loader.py

> "The dataset contained a Python pickle exploit. No user clicked a link, no email was opened.
> The attack triggered the moment their pipeline processed the data.
>
> Now watch the agent. It's not following a script — it's reasoning about what it found."

→ Point to DecisionNode in dashboard: *"Found HF_TOKEN and kubeconfig → escalating via kubectl"*

> "This is what makes agentic attackers different. The attack adapts.
> If it finds Kubernetes, it takes the k8s path. If it finds SSH keys, it pivots laterally.
> The defender has to detect behavior, not just signatures."

→ Falcon detections appear in sidebar

> "Falcon caught it. Four detections across the kill chain.
> But notice the attacker's agent made 12 decisions before being stopped.
> This is the speed asymmetry problem — machine speed offense, human speed defense.
> This is why AI-native detection matters."
