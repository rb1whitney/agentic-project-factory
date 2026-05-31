import argparse
import json
import logging
import subprocess
import sys
import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def run_vault_command(cmd, input_data=None):
    try:
        if input_data:
            result = subprocess.run(cmd, input=input_data.encode('utf-8'), capture_output=True, check=True)
        else:
            result = subprocess.run(cmd, capture_output=True, check=True)
        return result.stdout.decode('utf-8')
    except subprocess.CalledProcessError as e:
        if "already in use" in e.stderr.decode('utf-8'):
            logging.info(f"Ignoring error: {e.stderr.decode('utf-8').strip()}")
            return ""
        logging.error(f"Vault command failed: {e.stderr.decode('utf-8')}")
        raise

def process_api_object(api_object):
    api_path = api_object.get("api_path")
    api_method = api_object.get("api_method")
    
    if not api_path or not api_method:
        logging.error("api_path and api_method are required")
        return

    # Handle wrapped token unwrapping
    if api_object.get("wrapped_token") == "true":
        wrapped_token_val = api_object.get("wrapped_token_val") # assuming this is passed somehow, original script was flawed here
        # Original: wrapped_token=$(echo "$api_object" | jq -r .wrapped_token) ... wait, if it's "true", the token value isn't there?
        # Actually original script said: wrapped_token=$(echo "$api_object" | jq 'has("wrapped_token")')
        # if true -> wrapped_token=$(echo "$api_object" | jq -r .wrapped_token)
        # So it checked if key exists, then used the key's value.
        wrapped_token_val = api_object.get("wrapped_token")
        out = run_vault_command(["vault", "unwrap", "-format=json", wrapped_token_val])
        api_payload = json.loads(out).get("data", {})
    else:
        api_payload = api_object.get("api_payload", {})

    # Handle Transit decryption
    if api_object.get("transit_engine") and api_object.get("transit_key"):
        transit_engine = api_object["transit_engine"]
        transit_key = api_object["transit_key"]
        for key, val in api_payload.items():
            if isinstance(val, str) and val.startswith("vault:"):
                # decrypt
                out = run_vault_command(["vault", "write", "-format=json", f"{transit_engine}/decrypt/{transit_key}", f"ciphertext={val}"])
                import base64
                plaintext_b64 = json.loads(out)["data"]["plaintext"]
                api_payload[key] = base64.b64decode(plaintext_b64).decode('utf-8')

    # Handle sys/policy differently
    if api_path.startswith("sys/policy"):
        api_payload = {"policy": json.dumps(api_payload)}

    logging.info(f"Perform {api_method} against API Path {api_path}")
    
    cmd_base = ["vault"]
    
    if api_method == "get":
        cmd_base.extend(["read", "-format=json", api_path])
        out = run_vault_command(cmd_base)
        logging.info(f"API Response: {out}")
    elif api_method in ["list", "delete"]:
        cmd_base.extend([api_method, "-format=json", api_path])
        out = run_vault_command(cmd_base)
        logging.info(f"API Response: {out}")
    elif api_method in ["post", "put"]:
        cmd_base.extend(["write", "-format=json", api_path, "-"])
        payload_str = json.dumps(api_payload)
        out = run_vault_command(cmd_base, input_data=payload_str)
        logging.info(f"API Response: {out}")
    else:
        logging.error(f"Unknown API method: {api_method}")

def process_file(filepath):
    logging.info(f"Processing file {filepath}")
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Namespace
    if data.get("vault_namespace") == "true" or "vault_namespace" in data:
        ns = data.get("vault_namespace")
        if isinstance(ns, bool) and ns:
            pass # Original script was weird here too
        elif isinstance(ns, str):
            os.environ["VAULT_NAMESPACE"] = ns
    
    for obj in data.get("api_objects", []):
        process_api_object(obj)
        
    if "VAULT_NAMESPACE" in os.environ:
        del os.environ["VAULT_NAMESPACE"]

def main():
    parser = argparse.ArgumentParser(description="Manage Vault via JSON files")
    parser.add_argument("-p", "--file-path", required=True, help="Path to json file or directory of json files")
    args = parser.parse_args()

    if not os.environ.get("VAULT_ADDR") or not os.environ.get("VAULT_TOKEN"):
        logging.error("Please set VAULT_ADDR and VAULT_TOKEN prior to running this script")
        sys.exit(1)

    path = args.file_path
    if os.path.isfile(path) and path.endswith(".json"):
        process_file(path)
    elif os.path.isdir(path):
        for f in sorted(os.listdir(path)):
            if f.endswith(".json"):
                process_file(os.path.join(path, f))
    else:
        logging.error(f"Invalid path: {path}")
        sys.exit(1)

if __name__ == "__main__":
    main()
