#!/usr/bin/env bash
set -e

APP_DIR="projects/cloud-boot-app"
RULES_FILE="bin/rules_architectural_audit.yaml"
SEMGREP_BIN="$(command -v semgrep || echo /root/.local/bin/semgrep)"

echo "======================================================="
echo "   STAFF/PRINCIPAL CODEBASE AUDIT & DIAGNOSTIC RUNNER"
echo "======================================================="
echo "Target Codebase: $APP_DIR"
echo ""

# 1. Structural Anti-Pattern & Concurrency Scan
echo "[Step 1/3] Running Semgrep Architectural & Anti-Pattern Audit..."
"$SEMGREP_BIN" scan --config "$RULES_FILE" "$APP_DIR/src"
echo ""

# 2. Log-to-AST Quick Probe
echo "[Step 2/3] Testing Log-to-AST Correlation Engine..."
python3 bin/log2ast.py "DEBUG [http-nio-8080-exec-1] c.dataservice.controller.DataController - Updated the following data: DataDTO(id=5000)" --src "$APP_DIR/src"
echo ""

# 3. High-Boundary Regression Test Execution
echo "[Step 3/3] Running High-Boundary Identity & Regression Tests..."
mvn -f "$APP_DIR/pom.xml" test -Dtest=StaffRegressionTest -q

echo ""
echo "======================================================="
echo "   AUDIT & DIAGNOSTIC SUITE RUN COMPLETE: ALL PASSED"
echo "======================================================="
