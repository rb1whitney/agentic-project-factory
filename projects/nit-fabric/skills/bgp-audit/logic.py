# Skill: BGP Path Auditor (Hardened Industrial Middleware)
import asyncio
import logging
import argparse
import sys
from typing import Dict

# 1. Industrial Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("BGP-Auditor")

async def audit_session_async(remote_asn: int, local_asn: int, session_state: str, bfd_status: str = "UNKNOWN", prefix_count: int = 0) -> Dict:
    """Industrial-grade Async diagnostic loop for BGP peering sessions."""
    logger.info(f"Initiating BGP Audit for Remote ASN: {remote_asn}")
    try:
        await asyncio.sleep(0.1) 
        
        # 1. State Verification
        if session_state != "ESTABLISHED":
            logger.error(f"Audit Failed: Session is in {session_state} state.")
            return {"status": "FAIL", "reason": f"Session state is {session_state}"}
        
        # 2. Identity Verification (EBGP Mandatory)
        if remote_asn == local_asn:
            logger.error(f"Audit Failed: IBGP collision detected (ASN: {local_asn}).")
            return {"status": "FAIL", "reason": "IBGP detected. EBGP required for cross-cloud hub."}
        
        # 3. Liveness Depth (BFD)
        if bfd_status != "UP":
            logger.warning(f"Performance Alert: BFD is {bfd_status}. Sub-second failover IS NOT ACTIVE.")
            return {"status": "WARNING", "reason": f"BFD is {bfd_status}"}
        
        # 4. Route Telemetry
        if prefix_count == 0:
            logger.error("Audit Failed: Zero prefixes received.")
            return {"status": "FAIL", "reason": "Zero prefixes received."}
            
        logger.info(f"Audit Pass: Established EBGP ({remote_asn}) with {prefix_count} active routes.")
        return {"status": "PASS"}
        
    except Exception as e:
        logger.critical(f"Diagnostic Engine Failure: {str(e)}")
        return {"status": "ERROR", "reason": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Industrial BGP Path Auditor CLI")
    parser.add_argument("--remote-asn", type=int, required=True, help="Remote peer ASN")
    parser.add_argument("--local-asn", type=int, required=True, help="Local hub ASN")
    parser.add_argument("--session-state", type=str, default="ESTABLISHED", help="Current BGP state")
    parser.add_argument("--bfd-status", type=str, default="UP", help="Current BFD state")
    parser.add_argument("--prefix-count", type=int, default=1, help="Received prefix count")
    
    args = parser.parse_args()
    
    asyncio.run(audit_session_async(
        args.remote_asn, 
        args.local_asn, 
        args.session_state, 
        args.bfd_status, 
        args.prefix_count
    ))

if __name__ == "__main__":
    main()
