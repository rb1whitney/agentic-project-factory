#!/usr/bin/env python3
import argparse
import json
import logging
import os
import subprocess
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def run_cmd(cmd, check=True):
    logging.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        logging.error(f"Command failed: {result.stderr}")
        sys.exit(result.returncode)
    return result

def login(vault_cluster, vault_ldap, vault_namespace):
    os.environ["VAULT_ADDR"] = f"https://vault-{vault_cluster}01.corp.clover.com:8200"
    os.environ["VAULT_NAMESPACE"] = vault_namespace
    ldap_user = os.environ.get("LDAP_USERNAME")
    if not ldap_user:
        logging.error("LDAP_USERNAME environment variable must be set")
        sys.exit(1)
    
    cmd = ["vault", "login", "-method=ldap", f"-path={vault_ldap}", f"username={ldap_user}"]
    run_cmd(cmd)

def backup(vault_path, vault_cluster):
    basename = os.path.basename(vault_path)
    bkup_marker = f"backup-{basename}-{vault_cluster}.bkup"
    json_out = f"{basename}-{vault_cluster}.json"
    
    with open(bkup_marker, 'w') as f:
        pass
    
    cmd = ["vault", "read", "-format=json", vault_path]
    result = run_cmd(cmd)
    
    data = json.loads(result.stdout).get("data", {})
    with open(json_out, 'w') as f:
        json.dump(data, f, indent=2)
    logging.info(f"Backup saved to {json_out}")

def restore(vault_path, vault_cluster):
    basename = os.path.basename(vault_path)
    bkup_marker = f"backup-{basename}-{vault_cluster}.bkup"
    json_in = f"{basename}-{vault_cluster}.json"
    
    if not os.path.exists(bkup_marker):
        logging.error(f"Backup marker {bkup_marker} not found. Aborting.")
        sys.exit(1)
        
    cmd = ["vault", "write", vault_path, f"@{json_in}"]
    run_cmd(cmd)
    
    os.remove(bkup_marker)
    logging.info(f"Restored from {json_in} and removed marker {bkup_marker}")

def main():
    parser = argparse.ArgumentParser(description="Vault backup/restore utility")
    parser.add_argument("mode", choices=["backup", "restore"])
    parser.add_argument("vault_path")
    parser.add_argument("vault_cluster")
    parser.add_argument("vault_ldap", nargs="?", default="ldap")
    parser.add_argument("vault_namespace", nargs="?", default="puppet")
    args = parser.parse_args()
    
    login(args.vault_cluster, args.vault_ldap, args.vault_namespace)
    
    if args.mode == "backup":
        backup(args.vault_path, args.vault_cluster)
    elif args.mode == "restore":
        restore(args.vault_path, args.vault_cluster)

if __name__ == "__main__":
    main()
