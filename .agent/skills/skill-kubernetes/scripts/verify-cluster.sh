#!/bin/bash
set -euo pipefail
LOG_FILE="/var/log/homelab/verify.log"
mkdir -p /var/log/homelab
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

echo "Starting Verification..." | tee -a "$LOG_FILE"

# 1. Connectivity Check
kubectl run connectivity-test --image=docker.io/library/busybox:latest --restart=Never -- sleep 60 >> "$LOG_FILE" 2>&1
sleep 10
if kubectl get pod connectivity-test | grep -q "Running"; then
    echo "Connectivity Test: PASSED" | tee -a "$LOG_FILE"
else
    echo "Connectivity Test: FAILED" | tee -a "$LOG_FILE"
    exit 1
fi
kubectl delete pod connectivity-test >> "$LOG_FILE" 2>&1

# 2. Operator Readiness
if kubectl get pods -A --field-selector=status.phase!=Running | grep -v "NAMESPACE"; then
    echo "Some pods failing" | tee -a "$LOG_FILE"
    exit 1
else
    echo "All pods healthy" | tee -a "$LOG_FILE"
fi
exit 0
