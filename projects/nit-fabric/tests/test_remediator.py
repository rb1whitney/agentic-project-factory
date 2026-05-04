import pytest
from bin.remediator import AIRemediator

@pytest.fixture
def remediator():
    return AIRemediator()

def test_analyze_failure_bgp_mismatch(remediator):
    """
    Ensures that the engine correctly identifies a BGP ASN mismatch
    and generates the appropriate removal/injection HCL patch.
    """
    scenario = {
        "id": "bgp-asn-mismatch",
        "symptom": "BGP Session Down",
        "truth_report": {
            "aws_tgw_asn": 64512,
            "gcp_router_asn": 64600
        }
    }
    
    investigation, patch = remediator.analyze_failure(scenario)
    
    assert "Finding: AWS ASN (64512) does not match GCP ASN (64600)" in investigation
    assert "- bgp { asn = 64600 }" in patch
    assert "+ bgp { asn = 64512 }" in patch

def test_analyze_failure_malformed_input(remediator):
    """
    Verifies that the engine handles malformed truth reports without crashing.
    """
    scenario = {"id": "invalid-scenario"} # Missing truth_report
    
    investigation, patch = remediator.analyze_failure(scenario)
    
    assert investigation == "ERR_MALFORMED_INPUT"
    assert patch == ""

def test_analyze_failure_unknown_mode(remediator):
    """
    Verifies that unrecognized failure modes are logged and returned as unknown.
    """
    scenario = {
        "id": "unknown-problem",
        "truth_report": {"some": "data"}
    }
    
    investigation, patch = remediator.analyze_failure(scenario)
    
    assert investigation == "Unknown failure mode."
    assert patch == ""
