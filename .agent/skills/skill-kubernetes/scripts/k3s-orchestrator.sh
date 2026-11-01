#!/bin/bash
# High-level orchestrator for K3s local cluster operations
# Usage: ./k3s-orchestrator.sh [create|manage|debug]

case $1 in
  create)
    ./scripts/install_k3s.sh
    ;;
  manage)
    echo "Running maintenance..."
    helm repo update
    ;;
  debug)
    echo "Running diagnostic suite..."
    kubectl get events -A --sort-by='.lastTimestamp' | tail -n 20
    ;;
  *)
    echo "Usage: $0 {create|manage|debug}"
    exit 1
esac
