import json
import os
from unittest.mock import patch

import pytest


class TestRemediationSafety:

    @pytest.fixture
    def dummy_tf_file(self, tmp_path):
        """Create a dummy Terraform file for testing"""
        tf_content = """
resource "aws_ebs_volume" "ghost_vol" {
  availability_zone = "us-east-1a"
  size              = 40
  tags = {
    Name = "GhostVolume"
  }
}

resource "google_compute_disk" "ghost_disk" {
  name  = "ghost-disk"
  type  = "pd-ssd"
  zone  = "us-central1-a"
  size  = 50
}
"""
        tf_file = tmp_path / "main.tf"
        tf_file.write_text(tf_content)
        return tf_file

    @patch("bin.finops_oracle.FinOpsOracle.get_ghosts")
    def test_dry_run_produces_json_no_mod(self, mock_get_ghosts, dummy_tf_file):
        """Verify Dry Run mode produces remediation_plan.json but does not touch .tf files"""
        from bin.finops_oracle import FinOpsOracle

        mock_get_ghosts.return_value = [
            {
                "id": "vol-0123456789abcdef0",
                "provider": "aws",
                "signature_id": "AWS-EBS-001",
                "risk_level": "LOW"
            }
        ]

        original_content = dummy_tf_file.read_text()
        oracle = FinOpsOracle()

        # Run remediation in dry-run mode
        plan_path = "remediation_plan.json"
        oracle.remediate(dry_run=True, target_dir=str(dummy_tf_file.parent))

        # Assertions
        assert os.path.exists(plan_path)
        with open(plan_path, "r") as f:
            plan = json.load(f)
            assert len(plan["actions"]) == 1
            assert plan["actions"][0]["resource_id"] == "vol-0123456789abcdef0"
            assert plan["dry_run"] is True

        assert dummy_tf_file.read_text() == original_content

        # Cleanup
        if os.path.exists(plan_path):
            os.remove(plan_path)

    @patch("bin.finops_oracle.GitHubAgent")
    def test_pr_generation_logic(self, mock_gh_agent, dummy_tf_file):
        """Verify that PR generation logic correctly identifies resources in HCL"""
        from bin.finops_oracle import FinOpsOracle

        oracle = FinOpsOracle()
        ghosts = [
            {
                "id": "ghost-disk", # Matching the name in dummy_tf_file
                "provider": "gcp",
                "signature_id": "GCP-GCE-001",
                "risk_level": "LOW"
            }
        ]

        oracle.generate_remediation_pr(ghosts, target_dir=str(dummy_tf_file.parent))

        # Verify GitHubAgent was called with correct branch and message
        mock_gh_agent_instance = mock_gh_agent.return_value
        mock_gh_agent_instance.create_branch.assert_called()
        args, _ = mock_gh_agent_instance.create_pull_request.call_args
        assert "FinOps: Remediate Ghost Resources" in args[0]
        assert "GCP-GCE-001" in args[1] # PR body should contain signature
