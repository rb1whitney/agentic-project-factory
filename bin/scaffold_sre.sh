#!/bin/bash
# SRE Golden Signals Scaffolding Script
# Automates the creation of baseline SRE runbooks and Terraform monitoring definitions.

set -e

if [ -z "$1" ]; then
  echo "Error: Target project directory not specified."
  echo "Usage: ./bin/scaffold_sre.sh <path/to/project>"
  exit 1
fi

PROJECT_DIR="$1"

if [ ! -d "$PROJECT_DIR" ]; then
  echo "Error: Directory '$PROJECT_DIR' does not exist."
  exit 1
fi

echo "🚀 Scaffolding SRE standards in $PROJECT_DIR..."

# Create necessary directories
mkdir -p "$PROJECT_DIR/terraform"
mkdir -p "$PROJECT_DIR/runbooks"

# 1. Scaffold Terraform Monitoring (Golden Signals Placeholder)
TF_FILE="$PROJECT_DIR/terraform/sre-monitoring.tf"
if [ ! -f "$TF_FILE" ]; then
  cat << 'EOF' > "$TF_FILE"
# SRE Golden Signals - Auto-Scaffolded Template
# Ensure this is applied to your target Cloud Provider (AWS/GCP)

locals {
  service_name = "example-service"
}

# This is a placeholder structure for Golden Signals.
# Replace with actual resources for aws_cloudwatch_dashboard or google_monitoring_dashboard.
#
# Golden Signals Required:
# 1. Latency: The time it takes to service a request.
# 2. Traffic: A measure of how much demand is being placed on the system.
# 3. Errors: The rate of requests that fail.
# 4. Saturation: How "full" your service is.

output "sre_golden_signals_status" {
  value = "SRE Golden Signals defined for ${local.service_name} (Latency, Traffic, Errors, Saturation)"
}
EOF
  echo "✅ Created $TF_FILE"
else
  echo "⚠️ $TF_FILE already exists, skipping."
fi

# 2. Scaffold Runbooks
RUNBOOK_LATENCY="$PROJECT_DIR/runbooks/high-latency-response.md"
if [ ! -f "$RUNBOOK_LATENCY" ]; then
  cat << 'EOF' > "$RUNBOOK_LATENCY"
# Runbook: High Latency Response

**Trigger**: Latency Golden Signal > threshold.

## Immediate Actions
1. **Verify Metrics**: Check the SRE Dashboard to confirm if the spike is isolated or systemic.
2. **Agentic Hook**: Trigger `skill-anomaly-detection` to correlate logs across services.
3. **Rollback**: If a recent deployment occurred within 30 minutes, initiate an automated rollback.
4. **Escalation**: PagerDuty > L2 On-Call.

## Analysis Steps
- Check Database query performance (RDS / Cloud SQL metrics).
- Check cache hit rates.
- Evaluate network throughput limits (Saturation).
EOF
  echo "✅ Created $RUNBOOK_LATENCY"
else
  echo "⚠️ $RUNBOOK_LATENCY already exists, skipping."
fi

RUNBOOK_NETWORK="$PROJECT_DIR/runbooks/network-isolation.md"
if [ ! -f "$RUNBOOK_NETWORK" ]; then
  cat << 'EOF' > "$RUNBOOK_NETWORK"
# Runbook: Network Isolation (Security Incident)

**Trigger**: Unauthorized CIDR access detected / Security Agent hook.

## Immediate Actions
1. **Agentic Hook**: Invoke `skill-safe-sre-investigator` to capture current state.
2. **Isolate**: Sever external ingress to the compromised VPC/Subnet.
3. **Capture**: Ensure all VPC flow logs are preserved in Cold Storage.

## Analysis Steps
- Review IAM anomalies.
- Analyze `nit-fabric` overlap or violation logs.
EOF
  echo "✅ Created $RUNBOOK_NETWORK"
else
  echo "⚠️ $RUNBOOK_NETWORK already exists, skipping."
fi

# 3. Update README
README_FILE="$PROJECT_DIR/README.md"
if [ -f "$README_FILE" ]; then
  if ! grep -q "## SRE & Operations" "$README_FILE"; then
    echo -e "\n## SRE & Operations\nThis project adheres to the Agentic SRE Protocol. See \`runbooks/\` for incident response guides and \`terraform/sre-monitoring.tf\` for the defined Golden Signals." >> "$README_FILE"
    echo "✅ Appended SRE section to $README_FILE"
  else
    echo "⚠️ SRE section already exists in $README_FILE, skipping."
  fi
fi

echo "🎉 SRE Scaffolding Complete for $PROJECT_DIR."
