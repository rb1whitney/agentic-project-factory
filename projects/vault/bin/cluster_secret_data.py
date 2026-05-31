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
parser.add_argument('--name',
                    dest='cluster_name',
                    help='Vault Cluster Name',
                    required=True)
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--path', dest='path', help='Path to config files')
group.add_argument('--wrapped-token', dest='wrapped_token', help='Wrapped token to deploy configuration to')

parser.add_argument('--namespace',
                    dest='namespace',
                    help='Namespace to deploy code (wrapped token only)',
                    default=None)

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
                    default='ldap')
parser.add_argument('--auth-namespace',
                    dest='auth_namespace',
                    help='../config',
                    default='False')
args = parser.parse_args()

# Limit Error Seen By User Unless in DEBUG MODE
if 'DEBUG' not in args.log_level:
    sys.tracebacklimit = 0

# Get Logger and Cluster Config
cluster_name = args.cluster_name
logger = vault_helper.get_logger('Manage Data', args.log_level)
config = vault_helper.get_cluster_config(cluster_name)

# Log into root namespace
vault_client = LocalVaultClient(config['api_endpoint'], logger)
if args.auth_namespace == 'False':
    vault_client.login(auth_method=args.auth_method, mount_point=args.mount_point)

if args.wrapped_token:
    # Handle wrapped data deployment
    unwrapped_response = vault_client.get('/v1/sys/wrapping/unwrap', { "token" : args.wrapped_token })
    api_payload = unwrapped_response['data']

    validator = LocalVaultValidator('secret', api_payload)
    validation_errors = validator.validate(cluster_name, json_payload=api_payload)
    if len(validation_errors) > 0:
        raise ValueError('Error found in wrapped payload. Errors are:\n{0}'.format(
            '\n'.join(validation_errors)))

    if args.namespace != None and args.namespace != '':
        namespace_client = LocalVaultClient(config['api_endpoint'], logger, args.namespace)
        if args.auth_namespace == 'True':
            namespace_client.login(auth_method=args.auth_method, mount_point=args.mount_point)
        else:
            namespace_client.adapter.token = vault_client.adapter.token
        namespace_client.submit(api_payload)
        if args.auth_namespace == 'True':
            namespace_client.logout()
    else:
        vault_client.submit(api_payload)

else:
    # Find All json files provided or process single json file if provided instead
    json_files = []
    if os.path.isdir(args.path):
        for root, dirs, files in os.walk(args.path):
            for file in files:
                if file.endswith('.json'):
                    json_files.append(os.path.join(root, file))
    else:
        json_files.append(args.path)
    json_files.sort()

    # Validate all JSON files prior to processing
    validateInput(cluster_name, 'namespaces', '.*/namespaces/.*', json_files, logger)
    validateInput(cluster_name, 'admin', '.*/admin/.*', json_files, logger)

    # Process all json files against Vault API
    for json_file in json_files:
        vault_client.logger.info('Processing {0}'.format(json_file))
        json_payload = json.load(open(json_file, 'r'))
        if '_namespace' in json_payload:
            namespace_client = LocalVaultClient(config['api_endpoint'], logger, namespace=json_payload['_namespace'])
            if args.auth_namespace == 'True':
                namespace_client.login(auth_method=args.auth_method, mount_point=args.mount_point)
            else:
                namespace_client.adapter.token = vault_client.adapter.token
            namespace_client.submit(json_payload)

            if args.auth_namespace == 'True':
                namespace_client.logout()
        else:
            vault_client.submit(json_payload)

# Revoke our current access
vault_client.logout()
