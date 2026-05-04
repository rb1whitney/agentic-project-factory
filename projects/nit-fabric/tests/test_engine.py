import unittest
import ipaddress
import sys
import os

# Add bin to path
sys.path.append(os.path.join(os.getcwd(), "projects/nit-fabric/bin"))

from policies import CIDROverlapPolicy, PublicIngressPolicy, PolicyEngine
from schemas import UnifiedSecurityRule

class TestConnectivityEngine(unittest.TestCase):

    def test_cidr_overlap_logic(self):
        # Test Intra-cloud overlap
        params = {"protected_ranges": ["192.168.0.0/16"]}
        policy = CIDROverlapPolicy(name="CIDR_TEST", description="Test", params=params)
        
        context = {
            "aws_cidrs": ["10.0.0.0/16", "10.0.1.0/24"],
            "gcp_cidrs": ["192.168.1.0/24"] # This overlaps with protected_ranges
        }
        
        violations = policy.evaluate(context)
        
        # Should have 2 violations: 
        # 1. AWS 10.0.0.0/16 vs 10.0.1.0/24
        # 2. GCP 192.168.1.0/24 vs ON_PREM 192.168.0.0/16
        self.assertEqual(len(violations), 2)
        v_types = [v.violation_type for v in violations]
        self.assertTrue(any("INTRA-CLOUD" in vt for vt in v_types))
        self.assertTrue(any("ON-PREM-CONFLICT" in vt for vt in v_types))

    def test_public_ingress_policy(self):
        policy = PublicIngressPolicy(name="INGRESS_TEST", description="Test", params={"sensitive_ports": ["22"]})
        
        rule = UnifiedSecurityRule(
            rule_id="bad-ssh",
            platform="AWS",
            direction="INGRESS",
            action="ALLOW",
            port_range="22",
            source_cidr=["0.0.0.0/0"]
        )
        
        context = {"rules": [rule]}
        violations = policy.evaluate(context)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule.rule_id, "bad-ssh")

    def test_policy_engine_loading(self):
        # Verify the engine can load the 40+ policies from YAML
        engine = PolicyEngine()
        self.assertGreater(len(engine.policies), 10)
        
        # Check if specific expert policies are loaded
        policy_names = [p.name for p in engine.policies]
        self.assertIn("MULTI_CLOUD_CIDR_OVERLAP", policy_names)
        self.assertIn("AWS_S3_VERSIONING", policy_names)
        self.assertIn("GCP_SQL_PUBLIC_IP", policy_names)

    def test_resource_attribute_policy(self):
        from policies import ResourceAttributePolicy
        params = {
            "resource_type": "aws_s3_buckets",
            "attribute": "versioning",
            "expected_value": "Enabled"
        }
        policy = ResourceAttributePolicy(name="S3_VER", description="Test", params=params)
        
        context = {
            "aws_s3_buckets": [
                {"name": "good-bucket", "versioning": "Enabled"},
                {"name": "bad-bucket", "versioning": "Disabled"}
            ]
        }
        
        violations = policy.evaluate(context)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].metadata["resource"], "bad-bucket")

    def test_inspection_vpc_policy(self):
        from policies import InspectionVPCPolicy
        policy = InspectionVPCPolicy(name="INSPEC_TEST", description="Test")
        
        # Scenario 1: Missing inspection VPC
        context = {"vpcs": [{"id": "prod-vpc"}]}
        violations = policy.evaluate(context)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule.rule_id, "missing-inspection-hub")
        
        # Scenario 2: Inspection VPC present
        context = {"vpcs": [{"id": "security-inspection-vpc"}]}
        violations = policy.evaluate(context)
        self.assertEqual(len(violations), 0)

if __name__ == "__main__":
    unittest.main()
