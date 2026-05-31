import argparse
import base64
import json
import os
import sys
import urllib3
import glob

# Don't write byte code for imported libraries
sys.dont_write_bytecode = True

# Import Custom Libraries
from lib import vault_helper
from lib.vault_client import LocalVaultClient
from lib.vault_client_error import VaultClientError
from lib import secure_cmd
from lib.validators import validate_cluster_name, validate_namespace, validate_path

# Surpress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def list_secrets_func(client, mount_name, mount_path):
    mount_secrets = []
    mount_path = mount_path.replace('//','')    
    if mount_path.endswith('/'):
        api_path = "/v1/{0}/{1}".format(mount_name, mount_path)
        secret_paths = client.list(api_path)['data']['keys']
        for secret_path in secret_paths:
            if '/' in secret_path:
                new_mount_path = "{0}{1}".format(mount_path, secret_path)
                results = list_secrets_func(client, mount_name, new_mount_path)
                mount_secrets.extend(results)
            else:
                path_suffix = mount_path if mount_path.startswith('/') else "/{0}".format(mount_path)
                mount_secrets.append("{0}{1}".format(path_suffix, secret_path))
    else:
        mount_secrets.append(mount_path)
    return mount_secrets

def encrypt_api_payload(client, payload, older_json_payload, transit_encrypt_api_path, transit_decrypt_api_path, api_path, enable_plaintext_secrets, decrypt_password, decrypt_cmd_path):
    encrypted_payload = {}
    for key, value in list(payload.items()):
        if isinstance(value, dict):
            older_value = older_json_payload[key] if older_json_payload and key in older_json_payload else {}
            encrypted_payload[key] = encrypt_api_payload(
                client, value, older_value, transit_encrypt_api_path, 
                transit_decrypt_api_path, api_path, enable_plaintext_secrets, decrypt_password, decrypt_cmd_path)
        else:
            value_list = [value]
            if isinstance(value, list):
                value_list = value
                encrypted_payload[key] = []
            for index, current_value in enumerate(value_list):
                older_value = ''
                older_encrypted_value = ''
                if older_json_payload and key in older_json_payload:
                    older_json_payload_value = older_json_payload[key]
                    older_json_payload_value_list = older_json_payload_value if isinstance(older_json_payload_value, list) else [older_json_payload_value]
                    older_encrypted_value = older_json_payload_value_list[index] if index < len(older_json_payload_value_list) else ''
                    
                    if older_encrypted_value:
                        decrypt_payload = { 'ciphertext': older_encrypted_value }
                        try:
                            decrypted_payload =  client.post(transit_decrypt_api_path, decrypt_payload)
                            try:
                                older_value = str(base64.b64decode(decrypted_payload['data']['plaintext']), 'UTF-8')
                            except ValueError:
                                older_value = str(base64.b64decode(decrypted_payload['data']['plaintext']))
                        except:
                            older_value = ''

                encrypted_payload_value = None
                if(older_value != current_value):
                    base64_value = str(base64.b64encode(str(current_value).encode('UTF-8')), 'UTF-8')
                    transit_payload = {'plaintext': base64_value}
                    encrypted_data = client.post(transit_encrypt_api_path, transit_payload)
                    if 'error' in encrypted_data:
                        client.logger.error("Vault unable to parse {0} at api_path: {2} with error: {1}".format(
                            key, encrypted_data['error'], api_path))
                        sys.exit(1)
                    
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
                
                if(enable_plaintext_secrets == 'True' and "ENC(" in str(older_value)) and not current_value == 'changeme':
                    cleaned_jasypt_value = str(older_value).replace('ENC(','').replace(')','')
                    os.environ["encrypt_password"] = decrypt_password
                    os.environ["encrypt_secret"] = cleaned_jasypt_value
                    decrypted_secret = secure_cmd.run(['sh', 'decrypt_env.sh'], cwd=decrypt_cmd_path).stdout
                    base64_value = str(base64.b64encode(decrypted_secret.encode('UTF-8')), 'UTF-8')
                    transit_payload = {'plaintext': base64_value}
                    encrypted_data = client.post(transit_encrypt_api_path, transit_payload)
                    plaintext_key = "{}_plaintext".format(key)
                    encrypted_payload[plaintext_key] = encrypted_data['data']['ciphertext']

    return encrypted_payload

def get_transit_encoded_keys(value, key_path = ''):
    transit_encoded_keys = []
    for k, v in value.items():
        if isinstance(v, dict):
            nested_keys = get_transit_encoded_keys(v, '{}/{}'.format(key_path, k))
            transit_encoded_keys.extend(nested_keys)
        else:
            transit_encoded_keys.append('{}/{}'.format(key_path,k)[1:])
    return transit_encoded_keys

def handle_sync(args, config, logger):
    auth_namespace = args.source_namespace if args.auth_namespace == 'False' else None
    auth_client = LocalVaultClient(config['api_endpoint'], logger, namespace=auth_namespace)
    auth_client.login(auth_method=args.auth_method, mount_point=args.mount_point)

    client = LocalVaultClient(config['api_endpoint'], logger, namespace=args.source_namespace)
    client.adapter.token = auth_client.adapter.token

    secret_paths = list_secrets_func(client, args.source_kv, args.source_path)
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

        older_json_payload = {}
        if os.path.exists(json_file):
            try:
                older_json_payload = json.load(open(json_file, 'r'))["api_paths"][0]['api_payload']
            except:
                pass
                
        try:
            api_object['api_payload'] = encrypt_api_payload(
                client, api_payload, older_json_payload, 
                transit_encrypt_api_path, transit_decrypt_api_path, api_object['api_path'], args.enable_plaintext, args.encrypt_password, args.decrypt_cmd_path)
        except Exception as e:
            logger.error("Unable to process object {0}: {1}".format(api_object['api_path'], e))
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

def handle_list(args, config, logger):
    auth_namespace = args.source_namespace if args.auth_namespace == 'False' else None
    auth_client = LocalVaultClient(config['api_endpoint'], logger, namespace=auth_namespace)
    auth_client.login(auth_method=args.auth_method, mount_point=args.mount_point)

    client = LocalVaultClient(config['api_endpoint'], logger, namespace=args.source_namespace)
    client.adapter.token = auth_client.adapter.token

    print("Finding all secrets at target path...")
    secret_paths = list_secrets_func(client, args.source_kv, args.source_path)
    secret_paths.sort()
    for secret_path in secret_paths:
        print(secret_path)

    client.logout()

def is_valid_json(file_path):
    try:
        with open(file_path, 'r') as f:
            json.load(f)
        return True
    except json.JSONDecodeError:
        return False

def handle_validate(args):
    invalid_files = []
    
    for file in glob.iglob(f"./{args.directory}/{args.allow_file_regex}", recursive=True, include_hidden=True):
        if os.path.isdir(file):
            continue
        else:
            if not is_valid_json(file):
                invalid_files.append(file)
    if invalid_files:
        print(f"The following JSON files are invalid:")
        for filename in invalid_files:
            print(f"  - {filename}")
    else:
        print("All JSON files in the directory are valid.")

def main():
    parser = argparse.ArgumentParser(description='Local Secrets Manager')
    subparsers = parser.add_subparsers(dest='command', required=True, help='Action to perform')

    # Vault global arguments
    vault_parser = argparse.ArgumentParser(add_help=False)
    vault_parser.add_argument('--name', dest='cluster_name', type=validate_cluster_name, help='Vault Cluster Name', required=True)
    vault_parser.add_argument('--log-level', dest='log_level', help='<<WARN|DEBUG|INFO>>', default='INFO')
    vault_parser.add_argument('--auth-method', dest='auth_method', help='<<ldap|token|tls>>', default='ldap')
    vault_parser.add_argument('--mount-path', dest='mount_point', type=validate_path, help='../config', default='ldap')
    vault_parser.add_argument('--source-namespace', dest='source_namespace', type=validate_namespace, default='')
    vault_parser.add_argument('--source-kv', dest='source_kv', type=validate_path, default='')
    vault_parser.add_argument('--source-path', dest='source_path', type=validate_path, default='/')
    vault_parser.add_argument('--auth-namespace', dest='auth_namespace', help='../config', default='False')

    # sync command
    parser_sync = subparsers.add_parser('sync', parents=[vault_parser], help='Sync local secrets')
    parser_sync.add_argument('--source-transit-engine', dest='source_transit_engine', default='namespace-encryption')
    parser_sync.add_argument('--file-path', dest='source_namespace_filepath', default='')
    parser_sync.add_argument('--enable-plaintext', dest='enable_plaintext', default='False')
    parser_sync.add_argument('--encrypt-password', dest='encrypt_password', default='')
    parser_sync.add_argument('--decrypt-command-path', dest='decrypt_cmd_path', default='/Users/richard.whitney/Documents/Programming/bin/enc/')

    # list command
    parser_list = subparsers.add_parser('list', parents=[vault_parser], help='List secrets at target path')

    # validate command
    parser_validate = subparsers.add_parser('validate', help='Check if JSON files in a directory are valid')
    parser_validate.add_argument('-d','--directory', help='The directory containing the JSON files.', default="./config/json_workspaces")
    parser_validate.add_argument('-w', '--allow_file_regex', help='What files to include', default="**/*.json")

    args = parser.parse_args()

    if args.command == 'validate':
        handle_validate(args)
    else:
        if 'DEBUG' not in args.log_level:
            sys.tracebacklimit = 0

        cluster_name = args.cluster_name
        logger = vault_helper.get_logger('Local Secrets', args.log_level)
        config = vault_helper.get_cluster_config(cluster_name)

        if args.command == 'sync':
            handle_sync(args, config, logger)
        elif args.command == 'list':
            handle_list(args, config, logger)

if __name__ == '__main__':
    main()
