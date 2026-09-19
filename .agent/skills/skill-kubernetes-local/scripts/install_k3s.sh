#!/bin/bash
set -euo pipefail
LOG_FILE="/var/log/homelab/provision.log"
mkdir -p /var/log/homelab

echo "Provisioning started" | tee -a "$LOG_FILE"

if ! command -v k3s >/dev/null; then
    curl -sfL https://get.k3s.io | sh -
fi

mkdir -p /etc/rancher/k3s
k3s server --write-kubeconfig-mode 644 --data-dir /var/lib/rancher/k3s &
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

echo "Waiting for node readiness..." | tee -a "$LOG_FILE"
for i in {1..12}; do
  if kubectl get nodes | grep -q " Ready "; then
    echo "Node ready." | tee -a "$LOG_FILE"
    exit 0
  fi
  sleep 5
done
echo "Node failed to become ready." | tee -a "$LOG_FILE"
exit 1
