import argparse
import base64
import json
import os
import sys
import urllib3

# Don't write byte code for imported libraries
sys.dont_write_bytecode = True

# Import Custom Libraries
from lib import vault_helper
from lib.vault_client import LocalVaultClient
from lib.vault_client_error import VaultClientError
from lib import secure_cmd
from lib.validators import validate_cluster_name, validate_namespace, validate_path
from os import path

# Surpress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# List all k/v secrets under a target path, so 
# they can be bettered targeted by maintenance actions. 
# Folders themselves are managed by vault itself
def list_secrets(client, mount_name, mount_path):
    mount_secrets = []
    mount_path = mount_path.replace('//','')    
    if mount_path.endswith('/'):
        api_path = "/v1/{0}/{1}".format(mount_name, mount_path)
        secret_paths = client.list(api_path)['data']['keys']
        for secret_path in secret_paths:
            if '/' in secret_path:
                new_mount_path = "{0}{1}".format(mount_path, secret_path)
                results = list_secrets(client, mount_name, new_mount_path)
                mount_secrets.extend(results)
            else:
                path_suffix = mount_path if mount_path.startswith('/') else "/{0}".format(mount_path)
                mount_secrets.append("{0}{1}".format(path_suffix, secret_path))
    else:
        mount_secrets.append(mount_path)
    return mount_secrets

# Iterates over api payload and encrypts values
def encrypt_api_payload(client, payload, older_json_payload, transit_encrypt_api_path, transit_decrypt_api_path, api_path, enable_plaintext_secrets, decrypt_password, decrypt_cmd_path):
    encrypted_payload = {}
    for key, value in list(payload.items()):
        if isinstance(value, dict):
            older_value = older_json_payload[key] if older_json_payload else {}
            encrypted_payload[key] = encrypt_api_payload(
                client, value, older_value, transit_encrypt_api_path, 
                transit_decrypt_api_path, api_path)
        else:
            value_list = [value]
            if isinstance(value, list):
                value_list = value
                encrypted_payload[key] = []
            for index, current_value in enumerate(value_list):
                older_value = ''
                older_encrypted_value = ''
                # Decrypt older json value to check if value is same if passed
                if older_json_payload and key in older_json_payload:
                    older_json_payload_value = older_json_payload[key]
                    older_json_payload_value_list = older_json_payload_value if isinstance(older_json_payload_value, list) else [older_json_payload_value]
                    older_encrypted_value = older_json_payload_value_list[index]
                    decrypt_payload = { 'ciphertext': older_encrypted_value }
                    decrypted_payload =  client.post(transit_decrypt_api_path, decrypt_payload)
                    if 'transit_base64_keys' in api_object and key in api_object['transit_base64_keys']:
                        older_value = decrypted_payload['data']['plaintext']
                    else:
                        try:
                            older_value = str(base64.b64decode(decrypted_payload['data']['plaintext']), 'UTF-8')
                        except ValueError:
                            # Sometimes values are not able to be converted to UTF-8
                            older_value = str(base64.b64decode(decrypted_payload['data']['plaintext']))
                # Perform Transit Encryption if older value doesn't match existing value
                encrypted_payload_value = None
                if(older_value != current_value):
                    base64_value = str(base64.b64encode(current_value.encode('UTF-8')), 'UTF-8')
                    transit_payload = {'plaintext': base64_value}
                    encrypted_data = client.post(transit_encrypt_api_path, transit_payload)
                    if 'error' in encrypted_data:
                        client.logger.error("Vault unable to parse {0} at api_path: {2} with error: {1}".format(
                            key, encrypted_data['error'], api_path))
                        exit(1)
                    
                    if(current_value == "changeme"):
                        encrypted_payload_value = current_value
                    else:
                        encrypted_payload_value = encrypted_data['data']['ciphertext']
                else:
                    encrypted_payload_value = older_encrypted_value
                if isinstance(value, list):
                    encrypted_payload[key].append(encrypted_payload_value)
                else:
                    encrypted_payload[key] = encrypted_payload_value
                
                if(enable_plaintext_secrets == 'True' and "ENC(" in older_value) and not current_value == 'changeme':
                    # Pass the suggested password... a bit hacky... and decrypt the value
                    os.chdir(decrypt_cmd_path)
                    cleaned_jasypt_value = older_value.replace('ENC(','').replace(')','')
                    os.environ["encrypt_password"] = decrypt_password
                    os.environ["encrypt_secret"] = cleaned_jasypt_value
                    decrypted_secret = secure_cmd.run(['sh', 'decrypt_env.sh'], cwd=decrypt_cmd_path).stdout
                    # Pass value back into vault to re-encrypt with transit engine
                    base64_value = str(base64.b64encode(decrypted_secret.encode('UTF-8')), 'UTF-8')
                    transit_payload = {'plaintext': base64_value}
                    encrypted_data = client.post(transit_encrypt_api_path, transit_payload)
                    # Store Secret at Key value with plaintext after to ensure we don't run into collisions
                    plaintext_key = "{}_plaintext".format(key)
                    encrypted_payload[plaintext_key] = encrypted_data['data']['ciphertext']

    return encrypted_payload

# extracts keys from api_payload json
def get_transit_encoded_keys(value, key_path = ''):
    transit_encoded_keys = []
    for k, v in value.items():
        if isinstance(v, dict):
            nested_keys = get_transit_encoded_keys(v, '{}/{}'.format(key_path, k))
            transit_encoded_keys.extend(nested_keys)
        else:
            transit_encoded_keys.append('{}/{}'.format(key_path,k)[1:])
    return transit_encoded_keys

# Parse Arguments
parser = argparse.ArgumentParser(description='Manage Secret Data')
parser.add_argument('--name',
                    dest='cluster_name',
                    help='Vault Cluster Name',
                    type=validate_cluster_name,
                    required=True)
parser.add_argument('--log-level',
                    dest='log_level',
                    help='<<WARN|DEBUG|INFO>>',
                    default='INFO')
parser.add_argument('--auth-method',
                    dest='auth_method',
                    help='<<ldap|token|tls>>',
                    default='ldap')
parser.add_argument('--mount-path',
                    dest='mount_point',
                    help='../config',
                    type=validate_path,
                    default='ldap')
parser.add_argument('--source-namespace',
                    dest='source_namespace',
                    type=validate_namespace,
                    default='')
parser.add_argument('--source-kv',
                    dest='source_kv',
                    type=validate_path,
                    default='')
parser.add_argument('--source-path',
                    dest='source_path',
                    type=validate_path,
                    default='/')
parser.add_argument('--source-transit-engine',
                    dest='source_transit_engine',
                    default='namespace-encryption')
parser.add_argument('--file-path',
                    dest='source_namespace_filepath',
                    default='')
parser.add_argument('--auth-namespace',
                    dest='auth_namespace',
                    help='../config',
                    default='False')
parser.add_argument('--enable-plaintext',
                    dest='enable_plaintext',
                    default='False')
parser.add_argument('--encrypt-password',
                    dest='encrypt_password',
                    default='')
parser.add_argument('--decrypt-command-path',
                    dest='decrypt_cmd_path',
                    default='/Users/richard.whitney/Documents/Programming/bin/enc/')
args = parser.parse_args()

# Limit Error Seen By User Unless in DEBUG MODE
if 'DEBUG' not in args.log_level:
    sys.tracebacklimit = 0

# Get Logger and Cluster Config
cluster_name = args.cluster_name
logger = vault_helper.get_logger('Syncing Data from KV', args.log_level)
config = vault_helper.get_cluster_config(cluster_name)

# Setup Connections to auth namespace (allows root namespace)
auth_namespace = args.source_namespace if args.auth_namespace == 'False' else None
auth_client = LocalVaultClient(config['api_endpoint'], logger, namespace=auth_namespace)
auth_client.login(auth_method=args.auth_method, mount_point=args.mount_point)

client = LocalVaultClient(config['api_endpoint'], logger, namespace=args.source_namespace)
client.adapter.token = auth_client.adapter.token

# Find all secrets and then read them out
secret_paths = list_secrets(client, args.source_kv, args.source_path)
for secret_path in secret_paths:
    api_object = {}
    api_path = "v1/{0}{1}".format(args.source_kv, secret_path)
    api_payload = client.get(api_path)['data']

    api_object['api_action'] = 'post'
    api_object['api_path'] = "v1/{0}{1}".format(args.source_kv, secret_path)
    api_object['transit_encoded_keys'] = get_transit_encoded_keys(api_payload)
    api_object['transit_key'] = args.source_transit_engine
    api_object['transit_secret_engine'] = 'transit'

    transit_encrypt_api_path = "v1/{0}/encrypt/{1}".format(
        api_object['transit_secret_engine'], api_object['transit_key'])
    transit_decrypt_api_path = "v1/{0}/decrypt/{1}".format(
        api_object['transit_secret_engine'], api_object['transit_key'])
    json_file = "{0}/secrets/{1}{2}.json".format(
        args.source_namespace_filepath, args.source_kv, secret_path)

    older_json_payload =  json.load(open(json_file, 'r'))["api_paths"][0]['api_payload'] if path.exists(json_file) else {}
    try:
        api_object['api_payload'] = encrypt_api_payload(
            client, api_payload, older_json_payload, 
            transit_encrypt_api_path, transit_decrypt_api_path, api_object['api_path'], args.enable_plaintext, args.encrypt_password, args.decrypt_cmd_path)
    except: # Eating errors and doing best effort now
        logger.error("Unable to process object {0}".format(api_object['api_path']))
        continue

    json_payload = {
        '_namespace': args.source_namespace,
        'api_paths': [api_object]
    }
    logger.info('Writing to {0}'.format(json_file))

    parent_path = os.path.abspath(os.path.join(json_file, os.pardir))
    if not os.path.exists(parent_path):
        os.makedirs(parent_path)
    
    output_file = open(json_file, "w")
    output_file.write(json.dumps(json_payload, indent=2, sort_keys=True))
    output_file.close()

client.logout()
