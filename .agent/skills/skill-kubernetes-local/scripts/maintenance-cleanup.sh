#!/bin/bash
set -euo pipefail
# Log to /var/log/homelab/maintenance.log
LOG_FILE="/var/log/homelab/maintenance.log"
mkdir -p /var/log/homelab

echo "Starting cleanup at $(date)" | tee -a "$LOG_FILE"
# Prune succeeded jobs
kubectl delete job --field-selector status.phase=Succeeded -A >> "$LOG_FILE" 2>&1
echo "Cleanup complete at $(date)" | tee -a "$LOG_FILE"
