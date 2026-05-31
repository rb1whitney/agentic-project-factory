''' Modify json files (& handle base64 encoding & encryption) to prep for vault repo check-in.'''

import argparse
import base64
import json
import os
import sys
import urllib3
from lib import vault_helper
from lib.vault_client import LocalVaultClient

# Surpress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Parse arguments
parser = argparse.ArgumentParser(description='Manage Secret Data')
parser.add_argument('--name',
                    dest='cluster_name',
                    help='Vault Cluster Name',
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
                    default='prod-ldap')
parser.add_argument('--namespace',
                    dest='namespace',
                    default='')
parser.add_argument('--path', dest='path',
                    help='../config',
                    required=True)
parser.add_argument('--transit-engine',
                    dest='transit_engine',
                    help='../config',
                    default='transit')
parser.add_argument('--transit-key',
                    dest='transit_key',
                    default='namespace-encryption')
parser.add_argument('--transit-context',
                    dest='transit_context',
                    default='')

args = parser.parse_args()

# Limit error seen by user unless in DEBUG mode
if 'DEBUG' not in args.log_level:
    sys.tracebacklimit = 0

# Get logger and cluster config
cluster_name = args.cluster_name
logger = vault_helper.get_logger('Encrypt Data', args.log_level)
config = vault_helper.get_cluster_config(cluster_name)

client = LocalVaultClient(
    config['api_endpoint'], logger, namespace=args.namespace)
client.login(auth_method=args.auth_method, mount_point=args.mount_point)

# Find all json files provided or process single json file if provided instead
json_files = []
if os.path.isdir(args.path):
    for root, dirs, files in os.walk(args.path):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
else:
    json_files.append(args.path)
json_files.sort()

def validate_batch_result(batch_result, key, path):
    if 'error' in batch_result:
        client.logger.error("Vault unable to parse "
                            "{0} at api_path: {1} with error: {2}".format(
            key, path, batch_result['error']))
        sys.exit(1)

# Process all json files against Vault API
for json_file in json_files:
    client.logger.debug('Processing {0}'.format(json_file))
    json_payload = json.load(open(json_file, 'r'))

    for api_object in json_payload['api_paths']:
        # Decrypt existing values first and then re-encrypt as desired
        if 'transit_encoded_keys' in api_object:
            transit_secret_engine = api_object.get('transit_secret_engine', 'transit')
            transit_key = api_object.get('transit_key', 'namespace-encryption')
            transit_api_path = "v1/{0}/decrypt/{1}".format(transit_secret_engine, transit_key)
            for key_name in api_object['transit_encoded_keys']:
                transit_payload = { 'ciphertext' : api_object['api_payload'][key_name] }
                if 'transit_context' in api_object:
                    transit_payload['context'] = api_object['transit_context']
                decrypted_payload = client.post(transit_api_path, transit_payload)
                base64_string = decrypted_payload['data']['plaintext']
                api_object['api_payload'][key_name] = str(base64.b64decode(base64_string), 'UTF-8')
        # Retrieve object information
        api_payload = api_object['api_payload']
        base64_encoded_keys = api_object.get('decode_base64_keys', [])

        # clear transit encoded keys
        api_object['transit_encoded_keys'] = list()

    client.logger.info('Writing {0} to {1}'.format(json_payload, json_file))

    # Now write output to the same file
    output_file = open(json_file, "w")
    output_file.write(json.dumps(json_payload, indent=4, sort_keys=True))
    output_file.close()

client.logout()
