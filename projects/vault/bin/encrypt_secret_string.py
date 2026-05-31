import argparse
import base64
import json
import logging
import os
import sys
import urllib3

# Don't write byte code for imported libraries
sys.dont_write_bytecode = True

# Import Custom Libraries
from lib import vault_helper
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
                    default='')
parser.add_argument('--string', dest='string',
                    required=True)
parser.add_argument('--encode-string', 
                    dest='encode_string',
                    default="True",
                    required=False)
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

# Limit Error Seen By User Unless in DEBUG MODE
if 'DEBUG' not in args.log_level:
    sys.tracebacklimit = 0

# Get Logger and Cluster Config
cluster_name = args.cluster_name
logger = vault_helper.get_logger('Encrypt Data', args.log_level)
config = vault_helper.get_cluster_config(cluster_name)

client = LocalVaultClient(
    config['api_endpoint'], logger, namespace=args.namespace)
client.login(auth_method=args.auth_method, mount_point=args.mount_point)

encrypt_payload = {}
encrypt_value = args.string
if 'True' == args.encode_string:
    client.logger.debug('Encoding string into base64 value')
    encrypt_value = str(base64.b64encode(encrypt_value.encode('UTF-8')), 'UTF-8')
encrypt_payload['plaintext'] = encrypt_value
if args.transit_context != '':
    encrypt_payload['transit_context'] = args.transit_context   

transit_payload = { 'batch_input' : [ encrypt_payload ] }
transit_api_path = "v1/{0}/encrypt/{1}".format(args.transit_engine, args.transit_key)
encrypted_payload = client.post(transit_api_path, transit_payload)
for index, batch_result in enumerate(encrypted_payload['data']['batch_results']):
    client.logger.info('Encrypted String is {0}'.format(batch_result['ciphertext']))
    
client.logout()
