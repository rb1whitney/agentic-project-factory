import argparse
import json
import logging
import os
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

# Parse Arguments
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
                    default='ldap')
parser.add_argument('--namespace',
                    dest='namespace',
                    help='Namespace to deploy code',
                    default=None)
parser.add_argument('--wrapped-token',
                    dest='wrapped_token',
                    help='Wrapped token to deploy configuration to',
                    default=None,
                    required=True)
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
logger = vault_helper.get_logger('Manage Secret Data', args.log_level)
config = vault_helper.get_cluster_config(cluster_name)

# Log into Vault
vault_client = LocalVaultClient(config['api_endpoint'], logger)
vault_client.login(auth_method=args.auth_method, mount_point=args.mount_point)

# Retrieve wrapped token
unwrapped_response = vault_client.get('/v1/sys/wrapping/unwrap', { "token" : args.wrapped_token })
api_payload = unwrapped_response['data']

# Validate all JSON files prior to processing
validator = LocalVaultValidator('secret', api_payload)
validation_errors = validator.validate(cluster_name, json_payload=api_payload)
if len(validation_errors) > 0:
    raise ValueError('Error found in wrapped payload. Errors are:\n{0}'.format(
        '\n'.join(validation_errors)))

# Deploy either to a specific namespace or root namespace
if args.namespace != None and args.namespace != '':
    # Re-use current access token to access namespace
    namespace_client = LocalVaultClient(config['api_endpoint'], logger,
                                        args.namespace)
    if args.auth_namespace == 'True':
        namespace_client.login(auth_method=args.auth_method,
                               mount_point=args.mount_point)
    else:
        namespace_client.adapter.token = vault_client.adapter.token
    namespace_client.adapter.token = vault_client.adapter.token
    namespace_client.submit(api_payload)
    namespace_client.logout()
else:
    vault_client.submit(api_payload)

# Revoke our current access
vault_client.logout()
