# Skill: IPAM Expert (Hardened Radix Trie Middleware)
import ipaddress
import threading
import logging
import argparse
import sys
from typing import List, Optional

# Industrial Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("IPAM-Expert")

class RadixNode:
    def __init__(self):
        self.children = {}
        self.is_leaf = False

class RadixTrie:
    """Industrial-grade Radix Trie for O(k) CIDR disjointness proving."""
    def __init__(self):
        self.root = RadixNode()
        self._lock = threading.Lock()

    def insert(self, cidr: str):
        with self._lock:
            logger.debug(f"Inserting CIDR into Trie: {cidr}")
            network = ipaddress.ip_network(cidr)
            binary = self._to_binary_string(network)
            node = self.root
            for bit in binary[:network.prefixlen]:
                if bit not in node.children:
                    node.children[bit] = RadixNode()
                node = node.children[bit]
            node.is_leaf = True

    def check_overlap(self, cidr: str) -> bool:
        with self._lock:
            logger.info(f"Performing O(k) Overlap Check for: {cidr}")
            network = ipaddress.ip_network(cidr)
            binary = self._to_binary_string(network)
            node = self.root
            for bit in binary[:network.prefixlen]:
                if node.is_leaf: 
                    logger.warning(f"Collision Detected: Supernet overlap at bit depth {binary[:network.prefixlen].find(bit)}")
                    return True
                if bit not in node.children: 
                    return False
                node = node.children[bit]
            return True

    def next_available(self, parent: str, prefix_len: int) -> Optional[str]:
        """Proactively finds the next non-overlapping CIDR within a parent range."""
        logger.info(f"Seeking next available /{prefix_len} in parent {parent}")
        parent_net = ipaddress.ip_network(parent)
        
        for subnet in parent_net.subnets(new_prefix=prefix_len):
            if not self.check_overlap(str(subnet)):
                logger.info(f"Found available CIDR: {subnet}")
                return str(subnet)
        
        logger.error(f"IPAM DEPLETION: No available /{prefix_len} in {parent}")
        return None

    def _to_binary_string(self, network) -> str:
        return ''.join([f"{int(b):08b}" for b in network.network_address.packed])

def main():
    parser = argparse.ArgumentParser(description="Industrial IPAM Prover CLI")
    parser.add_argument("--proposal", type=str, required=True, help="Proposed CIDR range")
    parser.add_argument("--existing", nargs="+", help="Existing CIDR ranges to check against")
    
    args = parser.parse_args()
    
    trie = RadixTrie()
    if args.existing:
        for ex in args.existing:
            trie.insert(ex)
    
    if trie.check_overlap(args.proposal):
        logger.error(f"IPAM VERDICT: REJECTED - Overlap Detected for {args.proposal}")
        sys.exit(1)
    else:
        logger.info(f"IPAM VERDICT: APPROVED - {args.proposal} is Sovereign")
        sys.exit(0)

if __name__ == "__main__":
    main()
