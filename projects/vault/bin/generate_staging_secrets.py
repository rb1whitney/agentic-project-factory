import argparse
import json
import os
import re
import sys
import urllib3

# Don't write byte code for imported libraries
sys.dont_write_bytecode = True

# Import Custom Libraries
from lib import vault_helper
from lib.validator_helper import LocalVaultValidator
from lib.vault_client import LocalVaultClient

# Surpress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Will check each file against Local Validator to determine
# if file(s) conforms to best standards
def validateInput(cluster_name, validation_type, file_filter, json_files,
                  logger):
    validator = LocalVaultValidator(validation_type, logger)
    files_to_check = list(filter(re.compile(file_filter).match, json_files))
    if len(files_to_check) > 0:
        validation_errors = validator.validate(cluster_name,
                                               json_files=files_to_check)
        if len(validation_errors) > 0:
            raise ValueError(
                'Error found in {1} json files. Errors are:\n{0}'.format(
                    '\n'.join(validation_errors), validation_type))


# Parse Arguments
parser = argparse.ArgumentParser(description='Manage Data')
parser.add_argument('--path', dest='path', help='../config', required=True)
args = parser.parse_args()

# Find All json files in target file to migrate
json_files = []
if os.path.isdir(args.path):
    for root, dirs, files in os.walk(args.path):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
else:
    json_files.append(args.path)
json_files.sort()

# Process all json files against Vault API
for json_file in json_files:
    print('Processing {0}'.format(json_file))
    prod_path = json_file
    non_prod_path = json_file.replace('/prod/', '/nonprod/').replace('/usprod/', '/dev/')
    nastaging_path = non_prod_path.replace('dev', 'nastaging')
    
    prod_json_payload = json.load(open(prod_path, 'r'))
    prod_secret = prod_json_payload['api_paths'][0]
    prod_keys = prod_secret['api_payload'].keys()

    non_prod_json_payload = {}
    try:
        non_prod_json_payload = json.load(open(non_prod_path, 'r'))
    except:
        non_prod_json_payload = {
            '_namespace' : 'puppet',
            'api_paths' : [ { 'api_payload': {} } ]
            }
    
    os.makedirs(os.path.dirname(nastaging_path), exist_ok=True)
    output_file = open(nastaging_path, 'w')
  
    nonprod_values = non_prod_json_payload['api_paths'][0]['api_payload']

    
    nastaging_json_payload = non_prod_json_payload
    nastaging_api_path = {}
    nastaging_keys = []
    for key in prod_keys:
        if key in nonprod_values:
            nastaging_api_path[key] = nonprod_values[key]
            nastaging_keys.append(key)
        else:
            nastaging_api_path[key] = 'changeme'

    nastaging_json_payload['api_paths'][0] = {}
    nastaging_json_payload['api_paths'][0]['api_action'] = 'post'
    nastaging_json_payload['api_paths'][0]['api_path'] = prod_secret['api_path'].replace('/usprod/', '/nastaging/')
    nastaging_json_payload['api_paths'][0]['api_payload'] = nastaging_api_path
    nastaging_json_payload['api_paths'][0]['transit_encoded_keys'] = nastaging_keys
    nastaging_json_payload['api_paths'][0]['transit_key'] = 'namespace-encryption'
    nastaging_json_payload['api_paths'][0]['transit_secret_engine'] = 'transit'
    
    output_file.write(json.dumps(nastaging_json_payload, indent=2, sort_keys=True))
    output_file.close()
