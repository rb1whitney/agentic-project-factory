#!/usr/bin/env python3
"""
Canonical Skill Consolidation Map (SaP §3.5, §5.6).
Records the 15 Core Parent Skills and the 42 absorbed child skills.
One-time physical migration is complete and locked so cleaned references/ cannot be overwritten.
"""

import sys

CONSOLIDATION_MAP = {
    "skill-code-map": [
        "skill-context-master",
        "skill-codebase-recon",
    ],
    "skill-graphify": [
        "skill-crossplane",
    ],
    "skill-kubernetes": [
        "skill-kubernetes-local",
    ],
    "skill-aws": [
        "skill-aws-foundation",
        "skill-aws-serverless",
        "skill-aws-sagemaker",
        "skill-aws-migration",
        "skill-finops",
    ],
    "skill-gcp": [
        "skill-gcp-setup",
        "skill-gcp-mcp-setup",
        "skill-gcp-playbooks",
    ],
    "skill-sre-investigation": [
        "skill-sre-advanced",
        "skill-sre-governance",
        "skill-observability",
        "skill-data-ingestion",
    ],
    "skill-terraform": [
        "skill-packer",
        "skill-network",
        "skill-certificate-manager",
        "skill-on-prem-provisioning",
    ],
    "skill-github": [
        "skill-pr-creator",
        "skill-ci-replicator",
        "skill-review-suite",
        "skill-docs",
    ],
    "skill-compliance-auditor": [
        "skill-behavioral-evals",
    ],
    "skill-conductor": [
        "skill-swarm",
        "skill-swarm-agents",
        "skill-swarm-management",
        "skill-ddd",
        "skill-architecture",
        "skill-product_blueprint",
    ],
    "skill-factory-compiler": [
        "skill-harness-models",
        "skill-nexus-sync",
        "skill-webhook-autoload",
        "skill-agentic-initializer",
    ],
    "skill-always-on-memory": [
        "skill-episodic-memory",
        "skill-graph-memory",
    ],
    "skill-platform-admin": [
        "skill-mcp-manager",
        "skill-opencode",
        "skill-gemini",
        "skill-msbuild",
        "skill-frontend",
    ],
    "skill-presentation-architect": [],
    "skill-factory-creator": [],
}


def main() -> None:
    print(
        f"Consolidation locked ({len(CONSOLIDATION_MAP)} Core Parent Skills). "
        "Destructive file migration is disabled to protect sanitized references/."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
