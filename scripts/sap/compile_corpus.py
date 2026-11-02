#!/usr/bin/env python3
"""
SaP Corpus Compiler (13 Core Parent Skills, 13 Child Contracts, 15 Canonical Agents).
1. Emits 13 verified child contracts to .agent/contracts/<id>.yaml.
2. Runs the 4-check deterministic verifier (Coverage, Binding, Replacement, Risk) on each contract.
3. Rewrites the 13 Core Parent .agent/skills/*/SKILL.md files into pure Substituted SaP Bundles:
   - Block 1: Action Templates (Concrete How — Read First, including absorbed sub-skill CLI commands)
   - Block 2: Procedural Skeleton (invoke(κ, bindings))
   - Block 3: Inlined Child Contracts (Abstract Guarantees)
   - Block 4: Bundled Scripts & Reference Runbooks Index (auto-indexed from scripts/ and references/)
4. Rewrites all 15 .agent/agents/*.yaml files with clean Core Parent `skills:` bindings (zero orphan skills),
   schema-validated `contract:` blocks, and `prompt: |` SaP pseudocode dispatch blocks.
"""

import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.sap.refactor import verify_rc_bundle  # noqa: E402
from scripts.sap.verifier import _strip_sap_bundle, verify_contract  # noqa: E402


class LiteralStr(str):
    pass


def _literal_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


yaml.add_representer(LiteralStr, _literal_representer)

CM_SCRIPTS = ".agent/skills/skill-code-map/scripts"
GR_SCRIPTS = ".agent/skills/skill-graphify/scripts"

CONTRACTS_CATALOG = [
    {
        "id": "ast-blast-radius-gate",
        "trigger": (
            "Extract AST symbol map, call/import graph, git forensics hotspots, "
            "and PPR blast-radius context for source code directory"
        ),
        "input_schema": {
            "required": {"target_dir": "path", "task_query": "string"},
            "optional": {"max_tokens": "integer", "format": "string"},
        },
        "output_schema": {
            "ranked_context": "string",
            "relationship_graph": "path",
            "evidence_boundary": "string",
        },
        "preconditions": [
            "Run with /usr/bin/python3 (system python with tree_sitter)",
            "Scope target_dir to subsystem",
        ],
        "postconditions": [
            "Context window restricted to AST blast radius",
            "Evidence Boundary stated",
        ],
        "resources": [
            f"{CM_SCRIPTS}/auto_context.py",
            f"{CM_SCRIPTS}/graph_builder.py",
            f"{CM_SCRIPTS}/semantic_query.py",
        ],
        "side_effects": {"filesystem": "writes cache to ~/.cache/skill-code-map/", "network": "none"},
        "source_parents": ["skill-code-map"],
        "action_templates": [
            f'/usr/bin/python3 {CM_SCRIPTS}/auto_context.py "{{task_query}}" --src {{target_dir}} --max-tokens 8000 | bin/rtk',  # noqa: E501
            f"/usr/bin/python3 {CM_SCRIPTS}/semantic_query.py query --src {{target_dir}} | bin/rtk",
            "git log --stat -n 20 -- {target_dir} | bin/rtk",
        ],
    },
    {
        "id": "ast-policy-compliance-audit",
        "trigger": (
            "Execute 6-Pillar Well-Architected AST rules, compliance security checks, and behavioral evaluations"
        ),
        "input_schema": {
            "required": {"target_dir": "path", "pillar_scope": "string"},
            "optional": {"rule_pack": "string"},
        },
        "output_schema": {
            "findings_json": "string",
            "compliance_status": "string",
            "remediation_diff": "string",
        },
        "preconditions": ["ast-grep binary installed", "Read-only static analysis mode"],
        "postconditions": ["Zero secret leak or policy violation unflagged"],
        "resources": [
            f"{CM_SCRIPTS}/well_architected_audit.py",
            f"{CM_SCRIPTS}/local_extract.py",
        ],
        "side_effects": {"filesystem": "none", "network": "none"},
        "source_parents": ["skill-compliance-auditor"],
        "action_templates": [
            f"/usr/bin/python3 {CM_SCRIPTS}/well_architected_audit.py {{target_dir}} --pillar {{pillar_scope}} | bin/rtk",  # noqa: E501
            f"/usr/bin/python3 {CM_SCRIPTS}/local_extract.py {{target_dir}} | bin/rtk",
        ],
    },
    {
        "id": "k8s-graphify-topology",
        "trigger": "Extract Kubernetes, Crossplane XRD/Composition, and code topology into Graphify knowledge graph",
        "input_schema": {
            "required": {"target_dir": "path", "namespace": "string"},
            "optional": {"manifests_dir": "path"},
        },
        "output_schema": {
            "graph_json": "path",
            "lineage_mermaid": "string",
            "evidence_boundary": "string",
        },
        "preconditions": ["Secret/ConfigMap redaction active (NEVER_LIST enforced)", "Non-prod context verified"],
        "postconditions": ["0600 atomic leak-checked graph emitted"],
        "resources": [
            f"{GR_SCRIPTS}/k8s_graphify_extract.py",
            f"{CM_SCRIPTS}/state_graph.py",
        ],
        "side_effects": {"filesystem": "writes 0600 graph.json", "network": "read-only K8s API discovery"},
        "source_parents": ["skill-graphify"],
        "probes": [
            "kubectl get xrd,compositions -o name | bin/rtk",
            "kubectl get providers.pkg.crossplane.io,functions.pkg.crossplane.io | bin/rtk",
            "kubectl get compositions -o json | jq -r '.items[] | select(.spec.mode != \"Pipeline\") | .metadata.name' | bin/rtk",  # noqa: E501
            "kubectl get controllerconfigs.pkg.crossplane.io -o name | bin/rtk",
        ],
        "action_templates": [
            f"/usr/bin/python3 {GR_SCRIPTS}/k8s_graphify_extract.py -n {{namespace}} --manifests {{target_dir}} | bin/rtk",  # noqa: E501
            f"/usr/bin/python3 {CM_SCRIPTS}/semantic_query.py lineage {{namespace}} --src {{target_dir}} --mermaid | bin/rtk",  # noqa: E501
        ],
    },
    {
        "id": "k8s-workload-triage",
        "trigger": (
            "Diagnose Kubernetes pod status, container logs, events, local k3s cluster state, and service mesh routing"
        ),
        "input_schema": {
            "required": {"namespace": "string", "pod_name": "string"},
            "optional": {"container_name": "string", "kubeconfig": "path"},
        },
        "output_schema": {
            "root_cause_category": "string",
            "evidence_log_span": "string",
            "remediation_cmd": "string",
        },
        "preconditions": [
            "kubectl context verified",
            "Reference runbooks indexed in .agent/skills/skill-kubernetes/references/",
        ],
        "postconditions": ["Failure isolated to image, crashloop, probe, resource limit, or network before mutation"],
        "resources": [
            ".agent/skills/skill-kubernetes/references/istio-specialist.md",
            ".agent/skills/skill-kubernetes/references/k9s-specialist.md",
        ],
        "side_effects": {"filesystem": "none", "network": "read-only K8s API GET/LIST"},
        "source_parents": ["skill-kubernetes"],
        "action_templates": [
            "# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file",
            "kubectl get pods -n {namespace} | bin/rtk",
            "kubectl logs {pod_name} -n {namespace} --tail=100 | bin/rtk",
            "kubectl describe pod {pod_name} -n {namespace} | bin/rtk",
            "bash .agent/skills/skill-kubernetes/scripts/verify-cluster.sh 2>/dev/null | bin/rtk",
        ],
    },
    {
        "id": "aws-cloud-architecture-audit",
        "trigger": (
            "AWS capability reference guide and runbook routing "
            "for foundation, serverless, sagemaker, migration, and finops"
        ),
        "input_schema": {
            "required": {"aws_service": "string"},
            "optional": {"aws_region": "string"},
        },
        "output_schema": {
            "reference_file": "string",
            "aws_management_plan": "string",
        },
        "preconditions": ["AWS credentials sourced via environment or gopass", "Read-only describe/list calls first"],
        "postconditions": ["Blast radius and cost delta documented before state mutation"],
        "resources": [".agent/skills/skill-aws/references/"],
        "side_effects": {"filesystem": "none", "network": "read-only AWS API describe/list"},
        "source_parents": ["skill-aws"],
        "probes": [
            "aws sts get-caller-identity | bin/rtk",
            "aws iam get-account-summary --query 'SummaryMap.{RootMFA:AccountMFAEnabled,RootKeys:AccountAccessKeysPresent,Users:Users,Roles:Roles}' | bin/rtk",  # noqa: E501
            "aws accessanalyzer list-analyzers --query 'analyzers[].[name,type,status]' --output text | bin/rtk",
            "aws ec2 describe-flow-logs --query 'FlowLogs[].[ResourceId,TrafficType,LogDestinationType]' --output text | bin/rtk",  # noqa: E501
            'aws s3control get-public-access-block --account-id "$(aws sts get-caller-identity --query Account --output text)" | bin/rtk',  # noqa: E501
            "aws rds describe-db-instances --query 'DBInstances[].[DBInstanceIdentifier,MultiAZ,StorageEncrypted,BackupRetentionPeriod,PubliclyAccessible]' --output text | bin/rtk",  # noqa: E501
            "aws lambda list-functions --query 'Functions[].[FunctionName,Runtime,MemorySize,Timeout]' --output text | bin/rtk",  # noqa: E501
            "aws ec2 describe-security-groups --filters Name=ip-permission.cidr,Values=0.0.0.0/0 --query 'SecurityGroups[].[GroupId,GroupName]' --output text | bin/rtk",  # noqa: E501
        ],
        "action_templates": [
            "# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file",
            "aws sts get-caller-identity | bin/rtk",
            "aws {aws_service} help 2>/dev/null | head -n 30 | bin/rtk",
        ],
    },
    {
        "id": "gcp-cloud-ops-triage",
        "trigger": (
            "Verify GCP ADC identity, configure OneMCP servers, "
            "and execute read-only gcloud GKE, IAM, and playbook inspections"
        ),
        "input_schema": {
            "required": {"project_id": "string", "gcp_zone": "string"},
            "optional": {"cluster_name": "string"},
        },
        "output_schema": {
            "identity_state": "string",
            "resource_diagnostics": "string",
            "remediation_cmd": "string",
        },
        "preconditions": ["gcloud ADC authenticated", "Read-only observation commands executed first"],
        "postconditions": ["GCP project and cluster health verified with zero unmanaged mutation"],
        "resources": [".agent/skills/skill-gcp/references/", ".agent/skills/skill-gcp/scripts/"],
        "side_effects": {"filesystem": "none", "network": "read-only GCP API"},
        "source_parents": ["skill-gcp"],
        "probes": [
            "gcloud config get-value project | bin/rtk",
            "gcloud projects get-ancestors {project_id} | bin/rtk",
            "gcloud container clusters list --project={project_id} --format=json | jq '[.[] | {name, location, channel: .releaseChannel.channel, privateNodes: .privateClusterConfig.enablePrivateNodes, wiPool: .workloadIdentityConfig.workloadPool}]' | bin/rtk",  # noqa: E501
            "gcloud projects get-iam-policy {project_id} --flatten='bindings[].members' --filter='bindings.role:(roles/owner OR roles/editor)' --format='table(bindings.role,bindings.members)' | bin/rtk",  # noqa: E501
            "gcloud compute firewall-rules list --project={project_id} --filter='sourceRanges:0.0.0.0/0' --format='table(name,network.basename(),direction)' | bin/rtk",  # noqa: E501
            "gcloud org-policies list --project={project_id} | bin/rtk",
            "gcloud logging sinks list --project={project_id} | bin/rtk",
            "gcloud monitoring policies list --project={project_id} --format='value(displayName)' | bin/rtk",
        ],
        "action_templates": [
            "# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file",
            "gcloud config get-value project | bin/rtk",
            "gcloud container clusters list --project={project_id} --zone={gcp_zone} | bin/rtk",
            "gcloud logging read 'severity>=ERROR' --project={project_id} --limit=20 --format=json | bin/rtk",
        ],
    },
    {
        "id": "sre-telemetry-incident-response",
        "trigger": (
            "SRE monitoring references and time series description analysis for logs, SLO burn, and anomaly detection"
        ),
        "input_schema": {
            "required": {"monitoring_time": "string"},
            "optional": {"severity_filter": "string"},
        },
        "output_schema": {
            "sre_monitoring_summary": "string",
            "references_playbook": "string",
        },
        "preconditions": ["Read-only telemetry query scope", "Time window bounded to prevent token overflow"],
        "postconditions": ["Root-cause signal correlated across logs, metrics, and traces"],
        "resources": [
            ".agent/skills/skill-sre-investigation/scripts/",
            ".agent/skills/skill-sre-investigation/references/",
        ],
        "side_effects": {"filesystem": "none", "network": "read-only telemetry API"},
        "source_parents": ["skill-sre-investigation"],
        "action_templates": [
            "# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file",
            "gcloud logging read 'severity>=ERROR' --freshness={monitoring_time} --limit=25 --format=json | bin/rtk",
            "python3 .agent/skills/skill-sre-investigation/scripts/detect_zscore.py --help 2>/dev/null | bin/rtk",
        ],
    },
    {
        "id": "iac-infra-provisioning",
        "trigger": (
            "Infrastructure capability implementation and specific skill description validation "
            "for Terraform, Packer, Network, PKI, and On-Prem"
        ),
        "input_schema": {
            "required": {"infrastructure_dir": "path", "specific_target": "string"},
            "optional": {"var_file": "path"},
        },
        "output_schema": {
            "implementation_status": "string",
            "capability_report": "string",
        },
        "preconditions": ["No terraform destroy without explicit user confirmation", "State backend locked/verified"],
        "postconditions": ["Declarative IaC validated and drift checked before apply"],
        "resources": [f"{CM_SCRIPTS}/state_graph.py"],
        "side_effects": {"filesystem": "local .terraform cache only", "network": "provider schema/state read"},
        "source_parents": ["skill-terraform"],
        "action_templates": [
            "# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file",
            "terraform -chdir={infrastructure_dir} fmt -check && terraform -chdir={infrastructure_dir} validate | bin/rtk",  # noqa: E501
            f"/usr/bin/python3 {CM_SCRIPTS}/state_graph.py lint {{infrastructure_dir}} | bin/rtk",
        ],
    },
    {
        "id": "factory-hydration-compiler",
        "trigger": (
            "Hydrate canonical multi-adapter YAML agents, sync Nexus spokes, "
            "verify model tiers, and certify runtime discovery"
        ),
        "input_schema": {
            "required": {"harness_target": "string", "repo_root": "path"},
            "optional": {"write_models": "string"},
        },
        "output_schema": {
            "metadata_path": "path",
            "discovery_status": "string",
            "reconciled_count": "integer",
        },
        "preconditions": [
            "Canonical sources in .agent/agents/*.yaml and .agent/skills/*/SKILL.md",
            "Physical Sovereignty enforced",
        ],
        "postconditions": ["1:1 reconciliation across Claude, Antigravity, and Codex projections"],
        "resources": [
            "scripts/hydrate.sh",
            "bin/compile_metadata.py",
            "bin/verify_runtime_discovery.py",
        ],
        "side_effects": {"filesystem": "writes .claude/, .agents/, .codex/, .agent/metadata.json", "network": "none"},
        "source_parents": ["skill-factory-compiler"],
        "action_templates": [
            "./scripts/hydrate.sh {harness_target} | bin/rtk",
            "./scripts/hydrate.sh models | bin/rtk",
            "python3 bin/compile_metadata.py --repo-root {repo_root} --output .agent/metadata.json | bin/rtk",
            "python3 bin/verify_runtime_discovery.py | bin/rtk",
        ],
    },
    {
        "id": "conductor-swarm-orchestration",
        "trigger": (
            "Define conductor phase implementation and TDD skill description workflow "
            "across Swarm, DDD, Architecture, and Blueprints"
        ),
        "input_schema": {
            "required": {"phase_name": "string", "implementation_scope": "string"},
            "optional": {"template_name": "string"},
        },
        "output_schema": {
            "phase_implementation_path": "path",
            "conductor_tdd_status": "string",
        },
        "preconditions": [
            "Active track registered in conductor/tracks/",
            "Mandatory template selected from conductor/templates/",
        ],
        "postconditions": ["Phase artifact verified before specialist hand-off"],
        "resources": [
            "conductor/templates/STRATEGIC_RECON.md",
            "conductor/templates/EXECUTIVE_PLAN.md",
            "conductor/templates/CERTIFICATION_REPORT.md",
        ],
        "side_effects": {"filesystem": "writes track markdown in conductor/tracks/", "network": "none"},
        "source_parents": ["skill-conductor"],
        "action_templates": [
            "# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file",
            "python3 bin/nexus.py status 2>/dev/null | bin/rtk",
        ],
    },
    {
        "id": "cognitive-memory-archivist",
        "trigger": (
            "Ingest, consolidate, page, and query persistent SQLite session memory, "
            "episodic context, and relational knowledge graph triples"
        ),
        "input_schema": {
            "required": {"memory_action": "string", "query_topic": "string"},
            "optional": {"session_id": "string"},
        },
        "output_schema": {
            "recalled_insights": "string",
            "memory_db_state": "string",
        },
        "preconditions": ["SQLite memory store initialized via bin/memory_agent.py"],
        "postconditions": ["Session insights persisted and deduplicated without context bloat"],
        "resources": ["bin/memory_agent.py"],
        "side_effects": {"filesystem": "updates local SQLite memory db", "network": "none"},
        "source_parents": ["skill-always-on-memory"],
        "action_templates": [
            "# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file",
            'python3 bin/memory_agent.py {memory_action} --query "{query_topic}" 2>/dev/null | bin/rtk',
        ],
    },
    {
        "id": "github-pr-ci-governance",
        "trigger": (
            "Execute specific skill description workflow on current repository state "
            "for PR creation, CI replication, review suite, and docs"
        ),
        "input_schema": {
            "required": {"current_branch": "string", "specific_scope": "string"},
            "optional": {"workflow_run_id": "string"},
        },
        "output_schema": {
            "current_status": "string",
            "specific_description": "string",
        },
        "preconditions": [
            "Active branch MUST NOT be master or main",
            "Never execute gh pr merge (reserved for human operator)",
        ],
        "postconditions": ["Feature branch verified, tests passing, PR changelog formatted"],
        "resources": [".agent/skills/skill-github/references/", ".agent/skills/skill-github/scripts/"],
        "side_effects": {"filesystem": "git working tree", "network": "GitHub API via gh CLI"},
        "source_parents": ["skill-github"],
        "action_templates": [
            "# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file",
            "git branch --show-current | bin/rtk",
            "git status -s | bin/rtk",
            "gh pr list --state open | bin/rtk",
            "gh run list --limit 5 2>/dev/null | bin/rtk",
        ],
    },
    {
        "id": "runtime-tooling-platform-ops",
        "trigger": (
            "Expert skill name and description capability for runtime platform, "
            "MCP servers, OpenCode, Gemini CLI, MSBuild, and Frontend"
        ),
        "input_schema": {
            "required": {"expert_name": "string"},
            "optional": {},
        },
        "output_schema": {
            "skill_description": "string",
            "expert_capability": "string",
        },
        "preconditions": [
            "Secrets sourced from gopass or ~/.mcp-servers/credentials",
            "Sandbox execution verified",
        ],
        "postconditions": ["Tooling endpoint or build artifact verified non-destructively"],
        "resources": [".agent/skills/skill-platform-admin/references/"],
        "side_effects": {"filesystem": "local build/venv artifacts", "network": "local model/MCP healthcheck"},
        "source_parents": ["skill-platform-admin"],
        "action_templates": [
            "# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file",
            "python3 -m unittest discover -s tests -p 'test_*.py' | bin/rtk",
        ],
    },
    {
        "id": "presentation-deck-architect",
        "trigger": (
            "Narrative-first presentation architecture, storyboard validation, "
            "and editable PPTX slide generation from technical docs"
        ),
        "input_schema": {
            "required": {"storyboard_path": "path", "narrative_brief_path": "path"},
            "optional": {"output_pptx": "path"},
        },
        "output_schema": {
            "storyboard_status": "string",
            "deck_artifact_path": "path",
        },
        "preconditions": [
            "Narrative brief and evidence ledger verified before storyboard",
            "Storyboard approved by USER before rendering PPTX",
        ],
        "postconditions": ["Storyboard and narrative brief pass validate_storyboard.py with zero errors"],
        "resources": [
            ".agent/skills/skill-presentation-architect/references/narrative-craft.md",
            ".agent/skills/skill-presentation-architect/references/sap-docs-bridge.md",
            ".agent/skills/skill-presentation-architect/scripts/validate_storyboard.py",
        ],
        "side_effects": {"filesystem": "writes storyboard YAML and PPTX artifacts", "network": "none"},
        "source_parents": ["skill-presentation-architect"],
        "action_templates": [
            "# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file",
            "python3 .agent/skills/skill-presentation-architect/scripts/validate_storyboard.py --brief {narrative_brief_path} | bin/rtk",  # noqa: E501
            "python3 .agent/skills/skill-presentation-architect/scripts/validate_storyboard.py {storyboard_path} | bin/rtk",  # noqa: E501
        ],
    },
    {
        "id": "skill-authoring-taxonomy-gate",
        "trigger": (
            "Skill factory creator operating contract hard rules from docs "
            "skill_as_pseudocode_architecture output format and reference index"
        ),
        "input_schema": {
            "required": {"capability_name": "string", "capability_summary": "string"},
            "optional": {"parent_skill": "string", "script_paths": "string"},
        },
        "output_schema": {
            "tier": "string",
            "artifact_path": "path",
            "registration_status": "string",
        },
        "preconditions": ["Duplicate scan done; USER approval; feature branch"],
        "postconditions": [
            "Artifact at correct tier path; contract not surfaced under .agent/skills/; no orphan skill"
        ],
        "resources": [
            ".agent/skills/skill-factory-creator/references/narrative-for-skills.md",
            ".agent/skills/skill-factory-creator/references/taxonomy-decision.md",
            ".agent/skills/skill-factory-creator/references/sap-authoring.md",
        ],
        "side_effects": {
            "filesystem": "writes under .agent/skills/ or .agent/contracts/",
            "network": "none",
        },
        "source_parents": ["skill-factory-creator"],
        "action_templates": [
            "ls .agent/skills/ .agent/contracts/ | bin/rtk",
            "grep -n '^name:' .agent/skills/*/SKILL.md | bin/rtk",
            "grep -n 'skills:' -A6 .agent/agents/swarm-architect.yaml | bin/rtk",
            "./scripts/hydrate.sh all | bin/rtk",
            "python3 bin/compile_metadata.py --repo-root . --output .agent/metadata.json | bin/rtk",
            "python3 bin/verify_runtime_discovery.py | bin/rtk",
            ".venv/bin/python -m unittest tests/test_sap_pipeline.py | bin/rtk",
        ],
    },
]

# Clean 15 Canonical Agents -> Bound exclusively to the 13 Core Parent Skills (0 orphan skills!)
AGENT_CONTRACTS = {
    "db-migration-agent": {
        "contract_id": "iac-infra-provisioning",
        "skills": ["skill-code-map", "skill-terraform", "skill-conductor"],
        "trigger": "Database schema analysis, SQL query optimization, and zero-downtime migration verification",
        "required": {"infrastructure_dir": "path", "specific_target": "string"},
        "output": {"implementation_status": "string", "capability_report": "string"},
        "templates": [
            f'/usr/bin/python3 {CM_SCRIPTS}/auto_context.py "database schema migration" --src {{infrastructure_dir}} --max-tokens 8000 | bin/rtk',  # noqa: E501
            "git status -s | bin/rtk",
        ],
    },
    "memory-agent": {
        "contract_id": "cognitive-memory-archivist",
        "skills": ["skill-always-on-memory", "skill-conductor"],
        "trigger": (
            "Cross-session memory ingestion, consolidation, episodic paging, graph triples, and insight retrieval"
        ),
        "required": {"memory_action": "string", "query_topic": "string"},
        "output": {"recalled_insights": "string", "memory_db_state": "string"},
        "templates": [
            'python3 bin/memory_agent.py {memory_action} --query "{query_topic}" 2>/dev/null | bin/rtk',
        ],
    },
    "security-reviewer": {
        "contract_id": "ast-policy-compliance-audit",
        "skills": ["skill-compliance-auditor", "skill-code-map", "skill-graphify", "skill-conductor"],
        "trigger": (
            "Hostile security audit, IAM least-privilege review, secret leak detection, "
            "and 6-Pillar SEC/REL verification"
        ),
        "required": {"target_dir": "path", "pillar_scope": "string"},
        "output": {"findings_json": "string", "compliance_status": "string"},
        "templates": [
            f"/usr/bin/python3 {CM_SCRIPTS}/well_architected_audit.py {{target_dir}} --pillar {{pillar_scope}} | bin/rtk",  # noqa: E501
            f"/usr/bin/python3 {CM_SCRIPTS}/local_extract.py {{target_dir}} | bin/rtk",
        ],
    },
    "specialist-aws": {
        "contract_id": "aws-cloud-architecture-audit",
        "skills": ["skill-aws", "skill-terraform", "skill-code-map", "skill-conductor"],
        "trigger": (
            "AWS architecture discovery, IAM/VPC/EC2/RDS/Lambda/SageMaker/FinOps operations, "
            "and Well-Architected review"
        ),
        "required": {"aws_service": "string"},
        "output": {"reference_file": "string", "aws_management_plan": "string"},
        "templates": [
            "# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file",
            "aws sts get-caller-identity | bin/rtk",
        ],
    },
    "specialist-gcp": {
        "contract_id": "gcp-cloud-ops-triage",
        "skills": ["skill-gcp", "skill-kubernetes", "skill-platform-admin", "skill-conductor"],
        "trigger": "GCP GKE, Cloud Armor, IAM, ADC setup, OneMCP, and gcloud infrastructure operations",
        "required": {"project_id": "string", "gcp_zone": "string"},
        "output": {"identity_state": "string", "resource_diagnostics": "string"},
        "templates": [
            "gcloud config get-value project | bin/rtk",
            "gcloud container clusters list --project={project_id} --zone={gcp_zone} | bin/rtk",
        ],
    },
    "specialist-github": {
        "contract_id": "github-pr-ci-governance",
        "skills": ["skill-github", "skill-code-map", "skill-conductor"],
        "trigger": (
            "GitHub issue triage, feature-branch governance, PR creation, CI failure replication, and code review"
        ),
        "required": {"current_branch": "string", "specific_scope": "string"},
        "output": {"current_status": "string", "specific_description": "string"},
        "templates": [
            "git branch --show-current | bin/rtk",
            "gh pr list --state open | bin/rtk",
        ],
    },
    "specialist-k8s": {
        "contract_id": "k8s-workload-triage",
        "skills": ["skill-kubernetes", "skill-graphify", "skill-sre-investigation", "skill-conductor"],
        "trigger": (
            "Kubernetes cluster orchestration, Helm/Kustomize, ArgoCD, Crossplane, "
            "Istio, local k3s, and pod troubleshooting"
        ),
        "required": {"namespace": "string", "pod_name": "string"},
        "output": {"root_cause_category": "string", "remediation_cmd": "string"},
        "templates": [
            "kubectl get pods -n {namespace} | bin/rtk",
            "kubectl logs {pod_name} -n {namespace} --tail=100 | bin/rtk",
            f"/usr/bin/python3 {GR_SCRIPTS}/k8s_graphify_extract.py -n {{namespace}} | bin/rtk",
        ],
    },
    "specialist-opencode": {
        "contract_id": "runtime-tooling-platform-ops",
        "skills": ["skill-platform-admin", "skill-factory-compiler", "skill-conductor"],
        "trigger": (
            "OpenCode model provider administration, local LLM endpoint tuning, "
            "harness models, and MCP server lifecycle"
        ),
        "required": {"expert_name": "string"},
        "output": {"skill_description": "string", "expert_capability": "string"},
        "templates": [
            "# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file",
            "./scripts/hydrate.sh models | bin/rtk",
        ],
    },
    "specialist-sre": {
        "contract_id": "sre-telemetry-incident-response",
        "skills": ["skill-sre-investigation", "skill-kubernetes", "skill-gcp", "skill-conductor"],
        "trigger": (
            "SRE incident response, SLO burn analysis, anomaly detection, "
            "Datadog/Cloud Monitoring, and read-only production investigation"
        ),
        "required": {"monitoring_time": "string"},
        "output": {"sre_monitoring_summary": "string", "references_playbook": "string"},
        "templates": [
            "# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file",
            "gcloud logging read 'severity>=ERROR' --freshness={monitoring_time} --limit=25 --format=json | bin/rtk",
            "kubectl get pods -A | bin/rtk",
        ],
    },
    "specialist-terraform": {
        "contract_id": "iac-infra-provisioning",
        "skills": [
            "skill-terraform",
            "skill-aws",
            "skill-gcp",
            "skill-kubernetes",
            "skill-graphify",
            "skill-code-map",
            "skill-conductor",
        ],
        "trigger": "Terraform module development, state drift analysis, Packer, PKI, Network, and multi-cloud IaC",
        "required": {"infrastructure_dir": "path", "specific_target": "string"},
        "output": {"implementation_status": "string", "capability_report": "string"},
        "templates": [
            "terraform -chdir={infrastructure_dir} fmt -check && terraform -chdir={infrastructure_dir} validate | bin/rtk",  # noqa: E501
            f"/usr/bin/python3 {CM_SCRIPTS}/state_graph.py report {{infrastructure_dir}} | bin/rtk",
        ],
    },
    "swarm-architect": {
        "contract_id": "conductor-swarm-orchestration",
        "skills": [
            "skill-conductor",
            "skill-code-map",
            "skill-graphify",
            "skill-presentation-architect",
            "skill-factory-creator",
        ],
        "trigger": "Phase 3 DDD Strategic-to-Tactical architecture design, C4/LADR diagrams, and EXECUTIVE_PLAN.md",
        "required": {"phase_name": "string", "implementation_scope": "string"},
        "output": {"phase_implementation_path": "path", "conductor_tdd_status": "string"},
        "templates": [
            f'/usr/bin/python3 {CM_SCRIPTS}/auto_context.py "{{phase_name}}" --src . --max-tokens 8000 | bin/rtk',
            "ls conductor/tracks/ conductor/templates/EXECUTIVE_PLAN.md 2>/dev/null | bin/rtk",
        ],
    },
    "swarm-auditor": {
        "contract_id": "ast-policy-compliance-audit",
        "skills": [
            "skill-compliance-auditor",
            "skill-code-map",
            "skill-github",
            "skill-factory-compiler",
            "skill-conductor",
        ],
        "trigger": (
            "Phase 5 quality gate verification, 6-Pillar audit, test suite certification, "
            "and CERTIFICATION_REPORT.md generation"
        ),
        "required": {"target_dir": "path", "pillar_scope": "string"},
        "output": {"findings_json": "string", "compliance_status": "string"},
        "templates": [
            f"/usr/bin/python3 {CM_SCRIPTS}/well_architected_audit.py {{target_dir}} --pillar {{pillar_scope}} | bin/rtk",  # noqa: E501
            "python3 bin/verify_runtime_discovery.py | bin/rtk",
        ],
    },
    "swarm-engineer": {
        "contract_id": "ast-blast-radius-gate",
        "skills": ["skill-code-map", "skill-terraform", "skill-github", "skill-conductor"],
        "trigger": "Phase 4 TDD-first implementation, surgical strict-patch edits, and unit test verification",
        "required": {"target_dir": "path", "task_query": "string"},
        "output": {"ranked_context": "string", "evidence_boundary": "string"},
        "templates": [
            f'/usr/bin/python3 {CM_SCRIPTS}/auto_context.py "{{task_query}}" --src {{target_dir}} --max-tokens 8000 | bin/rtk',  # noqa: E501
            "python3 -m unittest discover -s tests -p 'test_*.py' | bin/rtk",
        ],
    },
    "swarm-scout": {
        "contract_id": "ast-blast-radius-gate",
        "skills": ["skill-code-map", "skill-graphify", "skill-conductor"],
        "trigger": (
            "Phase 1 Strategic Reconnaissance, git forensics, AST blast radius mapping, "
            "and STRATEGIC_RECON.md generation"
        ),
        "required": {"target_dir": "path", "task_query": "string"},
        "output": {"ranked_context": "string", "evidence_boundary": "string"},
        "templates": [
            f'/usr/bin/python3 {CM_SCRIPTS}/auto_context.py "{{task_query}}" --src {{target_dir}} --max-tokens 8000 | bin/rtk',  # noqa: E501
            "git log --stat -n 20 -- {target_dir} | bin/rtk",
        ],
    },
    "swarm-supervisor": {
        "contract_id": "conductor-swarm-orchestration",
        "skills": ["skill-conductor", "skill-factory-compiler", "skill-github"],
        "trigger": (
            "Multi-agent swarm lifecycle orchestration, track gating, hydration verification, "
            "and final authenticated PR push sequence"
        ),
        "required": {"phase_name": "string", "implementation_scope": "string"},
        "output": {"phase_implementation_path": "path", "conductor_tdd_status": "string"},
        "templates": [
            "ls conductor/tracks/ 2>/dev/null | bin/rtk",
            "python3 bin/verify_runtime_discovery.py | bin/rtk",
        ],
    },
}

SAP_SKILL_START = "<!-- SAP_BUNDLE_START -->"
SAP_SKILL_END = "<!-- SAP_BUNDLE_END -->"


def render_skill_sap_block(skill_dir: Path, contract: dict) -> str:
    skill_name = skill_dir.name
    cid = contract["id"]
    req_keys = list(contract["input_schema"]["required"].keys())
    opt_keys = list(contract["input_schema"].get("optional", {}).keys())
    out_keys = list(contract["output_schema"].keys())
    bindings_pairs = [f'{k}: "<{k}>"' for k in req_keys]
    bindings_str = "{" + ", ".join(bindings_pairs) + "}"
    templates_str = "\n".join(contract["action_templates"])
    pre_str = "; ".join(contract["preconditions"])
    post_str = "; ".join(contract["postconditions"])
    se = contract["side_effects"]
    se_str = f"filesystem={se.get('filesystem', 'none')}, network={se.get('network', 'none')}"

    note_hdr = (
        "> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, "
        "not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first."
    )

    return f"""{SAP_SKILL_START}
{note_hdr}

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: {cid}] parent={skill_name} required_inputs={req_keys}
{templates_str}
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_{skill_name.replace("-", "_")}_workflow({", ".join(req_keys)}):
  1. PRE-CHECK: {pre_str}
  2. result <- invoke({cid}, {bindings_str})
  3. POST-CHECK: {post_str}
  4. RETURN {{Location, Problem, Fix, outputs: {out_keys}}}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: {cid}`**
  - `trigger`: {contract["trigger"]}
  - `inputs`: required `{req_keys}`, optional `{opt_keys}`
  - `outputs`: `{out_keys}`
  - `preconditions`: {pre_str}
  - `postconditions`: {post_str}
  - `side_effects`: {se_str}
{SAP_SKILL_END}"""


def inject_skill_bundle(skill_md_path: Path, contract: dict) -> None:
    content = skill_md_path.read_text(encoding="utf-8")
    if SAP_SKILL_START in content and SAP_SKILL_END in content:
        s_idx = content.index(SAP_SKILL_START)
        e_idx = content.index(SAP_SKILL_END) + len(SAP_SKILL_END)
        content = content[:s_idx].rstrip() + "\n\n" + content[e_idx:].lstrip()

    sap_block = render_skill_sap_block(skill_md_path.parent, contract)

    fm_match = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    if fm_match:
        prefix = content[: fm_match.end()]
        rest = content[fm_match.end() :]
    else:
        prefix = ""
        rest = content

    h1_match = re.match(r"^(#\s+[^\n]+\n+)", rest)
    if h1_match:
        new_content = prefix + h1_match.group(1) + sap_block + "\n\n" + rest[h1_match.end() :].lstrip()
    else:
        new_content = prefix + sap_block + "\n\n" + rest.lstrip()

    skill_md_path.write_text(new_content, encoding="utf-8")


def upgrade_agent_yaml(agent_yaml_path: Path, spec: dict) -> None:
    data = yaml.safe_load(agent_yaml_path.read_text(encoding="utf-8"))
    agent_name = data["name"]
    cid = spec["contract_id"]
    req_keys = list(spec["required"].keys())
    out_keys = list(spec["output"].keys())
    bindings_str = "{" + ", ".join(f'{k}: "<{k}>"' for k in req_keys) + "}"
    templates_str = "\n".join(spec["templates"])

    is_readonly = "write" not in data.get("capabilities", [])
    fs_effect = "none (read-only agent)" if is_readonly else "surgical strict-patch edits on feature branch only"
    net_effect = "read-only CLI/API queries piped through bin/rtk"

    data["version"] = "2.2"
    data["skills"] = spec["skills"]
    data["contract"] = {
        "trigger": spec["trigger"],
        "input_schema": {
            "required": spec["required"],
            "optional": {"context_budget": "integer"},
        },
        "output_schema": {
            **spec["output"],
            "resolution": "Location | Problem | Fix",
        },
        "preconditions": [
            "All shell commands piped through bin/rtk",
            "Scope restricted to AST blast radius before file ingestion",
        ],
        "postconditions": [
            "Output formatted in caveman-prose (Location | Problem | Fix)",
            "Evidence Boundary stated (static AST vs manifests vs live state)",
        ],
        "side_effects": {
            "filesystem": fs_effect,
            "network": net_effect,
        },
    }

    prompt = data["prompt"]
    if SAP_SKILL_START in prompt and SAP_SKILL_END in prompt:
        s_idx = prompt.index(SAP_SKILL_START)
        e_idx = prompt.index(SAP_SKILL_END) + len(SAP_SKILL_END)
        prompt = prompt[:s_idx].rstrip() + "\n\n" + prompt[e_idx:].lstrip()

    agent_note = (
        "> **SaP Contract Agent**: `invoke(...)` is structural pseudocode notation, "
        "not an executable shell binary. Execute the concrete CLI templates in **Action Templates** first."
    )

    agent_sap_block = f"""{SAP_SKILL_START}
{agent_note}

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: {cid}] agent={agent_name} required_inputs={req_keys}
{templates_str}
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE dispatch_{agent_name.replace("-", "_")}({", ".join(req_keys)}):
  1. GATHER blast radius context and verify preconditions
  2. out <- invoke({cid}, {bindings_str})
  3. VERIFY postconditions and Evidence Boundary
  4. EMIT Location | Problem | Fix
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: {cid}`**
  - `trigger`: {spec["trigger"]}
  - `inputs`: `{req_keys}` -> `outputs`: `{out_keys}`
  - `side_effects`: filesystem={fs_effect}; network={net_effect}
{SAP_SKILL_END}"""

    h1_match = re.match(r"^(#\s+[^\n]+)", prompt.strip())
    title_line = h1_match.group(1) if h1_match else f"# Agent: {agent_name}"
    bound_skills_list = data.get("skills", [])

    caveman_rule = (
        "- **Caveman-Prose Mandate**: Strip articles, pronouns, preambles, hedging, and emojis. "
        "Format: `Location | Problem | Fix`."
    )
    compact_prompt = f"""{title_line}

{agent_sap_block}

## 4. Guardrails & Output Protocol
- **Reference-Led Execution**: Consult bound `skills` (`{bound_skills_list}`) and `{cid}` before acting.
{caveman_rule}
- **Terminal Proxy**: Pipe all shell commands through `bin/rtk`.
"""

    data["prompt"] = LiteralStr(compact_prompt)

    ordered = {
        "version": data["version"],
        "name": data["name"],
        "description": data["description"],
    }
    if "role" in data:
        ordered["role"] = data["role"]
    ordered["tier"] = data["tier"]
    ordered["capabilities"] = data["capabilities"]
    if "skills" in data:
        ordered["skills"] = data["skills"]
    if "returns" in data:
        ordered["returns"] = data["returns"]
    ordered["contract"] = data["contract"]
    ordered["prompt"] = data["prompt"]

    agent_yaml_path.write_text(
        yaml.dump(ordered, default_flow_style=False, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )


def main():
    contracts_dir = REPO_ROOT / ".agent/contracts"
    skills_dir = REPO_ROOT / ".agent/skills"
    agents_dir = REPO_ROOT / ".agent/agents"
    contracts_dir.mkdir(parents=True, exist_ok=True)

    # 1. Verify and emit each child contract against un-injected parent text + templates
    for c in CONTRACTS_CATALOG:
        units = []
        bindings_map = {}
        req_keys = list(c["input_schema"]["required"].keys())
        for p in c["source_parents"]:
            raw_text = _strip_sap_bundle((skills_dir / p / "SKILL.md").read_text(encoding="utf-8"))
            units.append({"parent": p, "heading": p, "text": raw_text, "code_blocks": c["action_templates"]})
            # Runtime inputs (SaP 3.5) are episode state and stay unbound placeholders. Only
            # index-time constants are bound. Every {placeholder} in a template must be declared.
            declared = set(req_keys) | set(c["input_schema"].get("optional", {}))
            undeclared = {
                m
                for t in c["action_templates"] + c.get("probes", []) + c.get("verify", [])
                for m in re.findall(r"\{([a-z_]+)\}", t)
                if m not in declared
            }
            if undeclared:
                raise RuntimeError(f"Undeclared template placeholders in {c['id']}: {sorted(undeclared)}")
            bindings_map[p] = {"skill_dir": f".agent/skills/{p}"}

        prof = verify_contract(units, c)
        if prof["tier"] != "auto_promote":
            raise RuntimeError(f"Verifier rejected contract {c['id']}: {prof}")

        c_out = dict(c)
        c_out["bindings"] = bindings_map
        c_out["verifier_stats"] = {
            "coverage": prof["coverage"],
            "binding": prof["binding"],
            "replacement": prof["replacement"],
            "risk": prof["risk"],
            "promotion_score": prof["promotion_score"],
            "tier": prof["tier"],
        }
        out_file = contracts_dir / f"{c['id']}.yaml"
        out_file.write_text(
            yaml.dump(c_out, default_flow_style=False, sort_keys=False, allow_unicode=True, width=100),
            encoding="utf-8",
        )

    # 2. Inject SaP bundles into the 13 Core Parent Skills
    parent_to_contract = {}
    for c in CONTRACTS_CATALOG:
        for p in c["source_parents"]:
            parent_to_contract[p] = c

    skill_dirs = sorted(d for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith("."))
    for sdir in skill_dirs:
        sname = sdir.name
        if sname not in parent_to_contract:
            raise RuntimeError(f"Unmapped skill {sname} in CONTRACTS_CATALOG")
        contract = parent_to_contract[sname]
        inject_skill_bundle(sdir / "SKILL.md", contract)
        ok, reasons = verify_rc_bundle((sdir / "SKILL.md").read_text(encoding="utf-8"), [contract["id"]])
        if not ok:
            raise RuntimeError(f"RC verification failed on {sname}: {reasons}")

    # 3. Upgrade all 15 canonical agents in .agent/agents/*.yaml
    for af in sorted(agents_dir.glob("*.yaml")):
        aname = af.stem
        if aname not in AGENT_CONTRACTS:
            raise RuntimeError(f"Unmapped agent {aname} in AGENT_CONTRACTS")
        upgrade_agent_yaml(af, AGENT_CONTRACTS[aname])

    print(
        f"SaP compilation complete: {len(CONTRACTS_CATALOG)} contracts promoted, "
        f"{len(skill_dirs)} core parent skills bundled, {len(AGENT_CONTRACTS)} agents upgraded."
    )


if __name__ == "__main__":
    main()
