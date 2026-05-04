import ipaddress
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from schemas import UnifiedSecurityRule, BoundaryViolation

logger = logging.getLogger("nit-fabric.policies")

class Policy:
    """Base class for all deterministic policies."""
    def __init__(self, name: str, description: str, severity: str = "CRITICAL", params: Dict[str, Any] = None):
        self.name = name
        self.description = description
        self.severity = severity
        self.params = params or {}
        self.advice = self.params.get("remediation_advice", "")

    def evaluate(self, context: Dict[str, Any]) -> List[BoundaryViolation]:
        raise NotImplementedError

class CIDROverlapPolicy(Policy):
    """Network Expert Rule: Detects CIDR overlaps across all cloud and on-prem pools."""
    def evaluate(self, context: Dict[str, Any]) -> List[BoundaryViolation]:
        violations = []
        
        # 1. Gather all CIDR pools
        pools = {
            "AWS": context.get("aws_cidrs", []),
            "GCP": context.get("gcp_cidrs", []),
            "ON_PREM": self.params.get("protected_ranges", [])
        }
        
        # Flatten all networks into a list of (CIDR, Source)
        all_nets = []
        for source, cidrs in pools.items():
            for cidr in cidrs:
                try:
                    all_nets.append((ipaddress.ip_network(cidr), source, cidr))
                except ValueError:
                    logger.error(f"Invalid CIDR detected in pool {source}: {cidr}")

        # 2. Perform O(n^2) overlap check (safe for typical VPC counts)
        for i in range(len(all_nets)):
            net_a, source_a, cidr_a = all_nets[i]
            for j in range(i + 1, len(all_nets)):
                net_b, source_b, cidr_b = all_nets[j]
                
                if net_a.overlaps(net_b):
                    overlap_type = "CROSS-CLOUD" if source_a != source_b else "INTRA-CLOUD"
                    if source_a == "ON_PREM" or source_b == "ON_PREM":
                        overlap_type = "ON-PREM-CONFLICT"
                    
                    violations.append(BoundaryViolation(
                        rule=UnifiedSecurityRule(
                            rule_id=f"cidr-overlap-{cidr_a}-{cidr_b}",
                            platform="MULTI",
                            direction="BOTH",
                            action="DENY",
                            source_cidr=[cidr_a],
                            destination_cidr=[cidr_b]
                        ),
                        violation_type=f"{self.name} ({overlap_type})",
                        remediation_proposal=f"Conflict between {source_a} ({cidr_a}) and {source_b} ({cidr_b}). Re-address one network.",
                        advice=self.advice,
                        severity=self.severity,
                        metadata={"net_a": cidr_a, "source_a": source_a, "net_b": cidr_b, "source_b": source_b}
                    ))
        return violations

class PublicIngressPolicy(Policy):
    def evaluate(self, context: Dict[str, Any]) -> List[BoundaryViolation]:
        violations = []
        sensitive_ports = self.params.get("sensitive_ports", [])
        rules = context.get("rules", [])
        for rule in rules:
            if rule.direction == "INGRESS" and rule.action == "ALLOW":
                if "0.0.0.0/0" in rule.source_cidr:
                    if rule.port_range in sensitive_ports or not rule.port_range:
                        violations.append(BoundaryViolation(
                            rule=rule,
                            violation_type=self.name,
                            remediation_proposal="Restrict source CIDR to internal ranges.",
                            advice=self.advice,
                            severity=self.severity
                        ))
        return violations

class AWSPublicS3Policy(Policy):
    def evaluate(self, context: Dict[str, Any]) -> List[BoundaryViolation]:
        violations = []
        buckets = context.get("aws_s3_buckets", [])
        for bucket in buckets:
            if bucket.get("public_access", False):
                violations.append(BoundaryViolation(
                    rule=UnifiedSecurityRule(
                        rule_id=f"s3-public-{bucket['name']}",
                        platform="AWS",
                        direction="INGRESS",
                        action="ALLOW",
                        source_cidr=["0.0.0.0/0"]
                    ),
                    violation_type=self.name,
                    remediation_proposal=f"Enable 'Block Public Access' for {bucket['name']}.",
                    advice=self.advice,
                    severity=self.severity,
                    metadata={"bucket_name": bucket['name']}
                ))
        return violations

class GCPExternalIPPolicy(Policy):
    def evaluate(self, context: Dict[str, Any]) -> List[BoundaryViolation]:
        violations = []
        instances = context.get("gcp_instances", [])
        for instance in instances:
            if instance.get("has_external_ip", False):
                violations.append(BoundaryViolation(
                    rule=UnifiedSecurityRule(
                        rule_id=f"gcp-ext-ip-{instance['name']}",
                        platform="GCP",
                        direction="BOTH",
                        action="ALLOW",
                        source_cidr=["0.0.0.0/0"]
                    ),
                    violation_type=self.name,
                    remediation_proposal=f"Remove external IP from {instance['name']}.",
                    advice=self.advice,
                    severity=self.severity,
                    metadata={"instance_name": instance['name'], "zone": instance.get("zone", "us-central1-a")}
                ))
        return violations

class VPCEndpointPolicy(Policy):
    """AWS Expert Rule: Ensures services are accessed via VPC Endpoints."""
    def evaluate(self, context: Dict[str, Any]) -> List[BoundaryViolation]:
        violations = []
        vpcs = context.get("vpcs", [])
        for vpc in vpcs:
            endpoints = vpc.get("endpoints", [])
            required_services = ["s3", "kms", "dynamodb"]
            for svc in required_services:
                # Expert Note: Now checking service name in the high-res endpoint dict
                found = False
                for ep in endpoints:
                    service_name = ep.get("Service", "") if isinstance(ep, dict) else str(ep)
                    if svc in service_name.lower():
                        found = True
                        break
                
                if not found:
                    violations.append(BoundaryViolation(
                        rule=UnifiedSecurityRule(
                            rule_id=f"missing-endpoint-{svc}",
                            platform="AWS",
                            direction="EGRESS",
                            action="DENY"
                        ),
                        violation_type=self.name,
                        remediation_proposal=f"Create a VPC Endpoint for {svc} in VPC {vpc['id']}.",
                        advice=self.advice,
                        severity=self.severity
                    ))
        return violations

class GKEWorkloadIdentityPolicy(Policy):
    """GCP Expert Rule: Ensures GKE clusters use Workload Identity."""
    def evaluate(self, context: Dict[str, Any]) -> List[BoundaryViolation]:
        violations = []
        clusters = context.get("gke_clusters", [])
        for cluster in clusters:
            if not cluster.get("workload_identity_enabled", False):
                violations.append(BoundaryViolation(
                    rule=UnifiedSecurityRule(
                        rule_id=f"gke-no-wi-{cluster['name']}",
                        platform="GCP",
                        direction="BOTH",
                        action="DENY"
                    ),
                    violation_type=self.name,
                    remediation_proposal=f"Enable Workload Identity on cluster {cluster['name']}.",
                    advice=self.advice,
                    severity=self.severity,
                    metadata={
                        "cluster_name": cluster['name'], 
                        "location": cluster.get("location", "us-central1"),
                        "node_pools": cluster.get("node_pools", []),
                        "project_id": context.get("project_id", "project-placeholder")
                    }
                ))
        return violations

class BinaryAuthorizationPolicy(Policy):
    """GCP Expert Rule: Ensures Binary Authorization is ENFORCED."""
    def evaluate(self, context: Dict[str, Any]) -> List[BoundaryViolation]:
        violations = []
        clusters = context.get("gke_clusters", [])
        for cluster in clusters:
            if cluster.get("binary_authorization", "DISABLED") != "ENFORCED":
                violations.append(BoundaryViolation(
                    rule=UnifiedSecurityRule(
                        rule_id=f"gke-binauth-{cluster['name']}",
                        platform="GCP",
                        direction="INGRESS",
                        action="DENY"
                    ),
                    violation_type=self.name,
                    remediation_proposal=f"Set Binary Authorization to 'ENFORCED' for {cluster['name']}.",
                    advice=self.advice,
                    severity=self.severity
                ))
        return violations

class IAMAccessAnalyzerPolicy(Policy):
    """AWS Expert Rule: Checks for IAM Access Analyzer findings."""
    def evaluate(self, context: Dict[str, Any]) -> List[BoundaryViolation]:
        violations = []
        findings = context.get("iam_findings", [])
        for finding in findings:
            if finding.get("is_public", False):
                violations.append(BoundaryViolation(
                    rule=UnifiedSecurityRule(
                        rule_id=f"iam-finding-{finding['id']}",
                        platform="AWS",
                        direction="BOTH",
                        action="DENY"
                    ),
                    violation_type=self.name,
                    remediation_proposal=f"Review and remediate IAM finding: {finding['description']}",
                    severity=self.severity
                ))
        return violations

class SharedVPCPolicy(Policy):
    """GCP Expert Rule: Validates Shared VPC hierarchy."""
    def evaluate(self, context: Dict[str, Any]) -> List[BoundaryViolation]:
        violations = []
        networks = context.get("gcp_networks", [])
        for net in networks:
            if net.get("is_shared_vpc_service_project", False) and not net.get("host_project_id"):
                violations.append(BoundaryViolation(
                    rule=UnifiedSecurityRule(
                        rule_id=f"shared-vpc-orphan-{net['name']}",
                        platform="GCP",
                        direction="BOTH",
                        action="DENY"
                    ),
                    violation_type=self.name,
                    remediation_proposal=f"Associate service project network {net['name']} with a Host Project.",
                    severity=self.severity
                ))
        return violations

class PrivateAccessPolicy(Policy):
    """Security Specialist Rule: Ensures private access to cloud services is enabled."""
    def evaluate(self, context: Dict[str, Any]) -> List[BoundaryViolation]:
        violations = []
        # GCP Subnets
        subnets = context.get("gcp_subnets", [])
        for subnet in subnets:
            if not subnet.get("private_google_access", False):
                violations.append(BoundaryViolation(
                    rule=UnifiedSecurityRule(
                        rule_id=f"gcp-no-pga-{subnet['name']}",
                        platform="GCP",
                        direction="EGRESS",
                        action="DENY"
                    ),
                    violation_type=self.name,
                    remediation_proposal=f"Enable Private Google Access on subnet {subnet['name']}.",
                    severity=self.severity,
                    metadata={"subnet_name": subnet['name'], "region": subnet['region']}
                ))
        
        # AWS Endpoints
        vpcs = context.get("vpcs", [])
        for vpc in vpcs:
            for ep in vpc.get("endpoints", []):
                if isinstance(ep, dict) and ep.get("Type") == "Interface" and not ep.get("DnsEnabled", False):
                    violations.append(BoundaryViolation(
                        rule=UnifiedSecurityRule(
                            rule_id=f"aws-ep-dns-disabled-{ep['Service']}",
                            platform="AWS",
                            direction="BOTH",
                            action="DENY"
                        ),
                        violation_type=self.name,
                        remediation_proposal=f"Enable Private DNS for endpoint {ep['Service']} in VPC {vpc['id']}.",
                        severity=self.severity,
                        metadata={"vpc_id": vpc['id'], "service": ep['Service']}
                    ))
        return violations

class InspectionVPCPolicy(Policy):
    """Security Specialist Rule: Ensures cross-cloud transit passes through an inspection hub."""
    def evaluate(self, context: Dict[str, Any]) -> List[BoundaryViolation]:
        violations = []
        # Simplified: Check if an 'inspection' VPC exists in the context
        vpcs = context.get("vpcs", [])
        has_inspection = any("inspection" in vpc['id'].lower() for vpc in vpcs)
        if not has_inspection:
            violations.append(BoundaryViolation(
                rule=UnifiedSecurityRule(
                    rule_id="missing-inspection-hub",
                    platform="MULTI",
                    direction="BOTH",
                    action="DENY"
                ),
                violation_type=self.name,
                remediation_proposal="Deploy a centralized Inspection VPC to audit east-west transit traffic.",
                severity="HIGH"
            ))
        return violations

class ResourceAttributePolicy(Policy):
    """Generic policy to check if a resource attribute matches a required state."""
    def evaluate(self, context: Dict[str, Any]) -> List[BoundaryViolation]:
        violations = []
        resource_type = self.params.get("resource_type")
        attribute = self.params.get("attribute")
        expected_value = self.params.get("expected_value")
        
        resources = context.get(resource_type, [])
        for res in resources:
            if res.get(attribute) != expected_value:
                violations.append(BoundaryViolation(
                    rule=UnifiedSecurityRule(
                        rule_id=f"attr-mismatch-{res.get('name', 'unknown')}",
                        platform="MULTI",
                        direction="BOTH",
                        action="DENY"
                    ),
                    violation_type=self.name,
                    remediation_proposal=f"Set {attribute} to {expected_value} for {res.get('name')}.",
                    advice=self.advice,
                    severity=self.severity,
                    metadata={"resource": res.get("name"), "attr": attribute, "val": expected_value}
                ))
        return violations

class ResourceExistencePolicy(Policy):
    """Generic policy to check if a required resource exists."""
    def evaluate(self, context: Dict[str, Any]) -> List[BoundaryViolation]:
        violations = []
        resource_type = self.params.get("resource_type")
        if not context.get(resource_type):
            violations.append(BoundaryViolation(
                rule=UnifiedSecurityRule(
                    rule_id=f"missing-{resource_type}",
                    platform="MULTI",
                    direction="BOTH",
                    action="DENY"
                ),
                violation_type=self.name,
                remediation_proposal=f"Deploy required resource type: {resource_type}.",
                advice=self.advice,
                severity=self.severity
            ))
        return violations

class PolicyLoader:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.registry = {
            "CIDROverlapPolicy": CIDROverlapPolicy,
            "PublicIngressPolicy": PublicIngressPolicy,
            "AWSPublicS3Policy": AWSPublicS3Policy,
            "GCPExternalIPPolicy": GCPExternalIPPolicy,
            "VPCEndpointPolicy": VPCEndpointPolicy,
            "GKEWorkloadIdentityPolicy": GKEWorkloadIdentityPolicy,
            "BinaryAuthorizationPolicy": BinaryAuthorizationPolicy,
            "IAMAccessAnalyzerPolicy": IAMAccessAnalyzerPolicy,
            "SharedVPCPolicy": SharedVPCPolicy,
            "PrivateAccessPolicy": PrivateAccessPolicy,
            "InspectionVPCPolicy": InspectionVPCPolicy,
            "ResourceAttributePolicy": ResourceAttributePolicy,
            "ResourceExistencePolicy": ResourceExistencePolicy
        }

    def load(self) -> List[Policy]:
        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)
        
        policies = []
        for p_cfg in config.get("policies", []):
            p_class = self.registry.get(p_cfg["class"])
            if p_class:
                policies.append(p_class(
                    name=p_cfg["name"],
                    description=p_cfg["description"],
                    severity=p_cfg["severity"],
                    params=p_cfg.get("params", {})
                ))
        return policies

class PolicyEngine:
    def __init__(self, config_path: str = None):
        if not config_path:
            config_path = str(Path(__file__).parent / "policies.yaml")
        self.loader = PolicyLoader(config_path)
        self.policies = self.loader.load()

    def run_all(self, context: Dict[str, Any]) -> List[BoundaryViolation]:
        all_violations = []
        for policy in self.policies:
            all_violations.extend(policy.evaluate(context))
        return all_violations
