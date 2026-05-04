import json
import logging
import sys
import argparse
from pathlib import Path
from typing import Any, List, Dict
from schemas import UnifiedSecurityRule, BoundaryViolation
from policies import PolicyEngine

# --- SRE Configuration: Structured JSON Logging ---
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }
        if hasattr(record, "violation"):
            log_entry["violation"] = record.violation
        return json.dumps(log_entry)

logger = logging.getLogger("nit-fabric.scanner")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class SecurityScanner:
    def __init__(self, context_path: str = "context.json"):
        self.rules = []
        self.violations = []
        self.policy_engine = PolicyEngine()
        self.context = {
            "rules": [],
            "aws_cidrs": [],
            "gcp_cidrs": [],
            "aws_s3_buckets": [],
            "gcp_instances": [],
            "vpcs": [],
            "gke_clusters": []
        }
        if Path(context_path).exists():
            logger.info(f"Loading context from {context_path}")
            with open(context_path, "r") as f:
                self.context.update(json.load(f))

    def ingest_rule(self, rule: UnifiedSecurityRule):
        self.rules.append(rule)
        self.context["rules"].append(rule)

    def audit(self):
        """Unified cross-cloud security logic using Deterministic Policy Engine"""
        logger.info("Starting security audit scan...")
        self.violations = self.policy_engine.run_all(self.context)
        
        for v in self.violations:
            v_dict = v.model_dump()
            log_msg = f"Violation detected: {v.violation_type}"
            if v.severity == "CRITICAL":
                log_msg = f"[ALERT] CRITICAL VIOLATION: {v.violation_type}"
                logger.error(log_msg, extra={"violation": v_dict})
            else:
                logger.warning(log_msg, extra={"violation": v_dict})
        
        logger.info(f"Audit complete. Total violations: {len(self.violations)}")

    def propose_excision(self):
        """Standardizes the 'Proposal-Only Excision' report"""
        return [v.model_dump() for v in self.violations]

def main():
    parser = argparse.ArgumentParser(description="nit-fabric Security Graph Enforcer")
    parser.add_argument("--context", default="context.json", help="Path to discovery context")
    parser.add_argument("--output", default="violations.json", help="Path to save violations")
    parser.add_argument("--quiet", action="store_true", help="Suppress stdout output")
    args = parser.parse_args()

    scanner = SecurityScanner(context_path=args.context)
    scanner.audit()
    
    findings = scanner.propose_excision()
    with open(args.output, "w") as f:
        json.dump(findings, f, indent=2)
    
    logger.info(f"Findings archived to {args.output}")
    
    if not args.quiet:
        # Machine-readable output to stdout remains for pipe-ability
        sys.stdout.write(json.dumps(findings, indent=2) + "\n")

if __name__ == "__main__":
    main()
