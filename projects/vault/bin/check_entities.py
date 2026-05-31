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
args = parser.parse_args()

# Limit Error Seen By User Unless in DEBUG MODE
if 'DEBUG' not in args.log_level:
    sys.tracebacklimit = 0

# Get Logger and Cluster Config
cluster_name = args.cluster_name
logger = vault_helper.get_logger('Process Licenses', args.log_level)
config = vault_helper.get_cluster_config(cluster_name)

client = LocalVaultClient(config['api_endpoint'], logger)
client.login(auth_method=args.auth_method, mount_point=args.mount_point)

entity_info = {}
token_info = {}

entities = client.list('v1/identity/entity/id')['data']['keys']
alias_names = []
for entity in entities:
    entity_data = client.get('v1/identity/entity/id/{0}'.format(entity))
    alias_name = []
    for alias in entity_data['data']['aliases']:
        alias_name.append(alias['name'])
    alias_names.append(','.join(alias_name))
entity_info['root'] = alias_names
token_info['root'] = client.get('v1/sys/internal/counters/tokens')['data']['counters']


namespaces = client.list('v1/sys/namespaces')['data']['key_info'].keys()
for namespace in namespaces:
    target_namespace = namespace.replace('/', '')
    namespace_client = LocalVaultClient(config['api_endpoint'], logger, namespace=target_namespace)
    namespace_client.adapter.token = client.adapter.token
    alias_names = []
    entities = namespace_client.list('v1/identity/entity/id')['data']['keys']
    for entity in entities:
        entity_data = namespace_client.get('v1/identity/entity/id/{0}'.format(entity))
        alias_name = []
        for alias in entity_data['data']['aliases']:
            alias_to_use = alias['name']
            if alias['metadata']:
                alias_to_use = ", ".join("=".join((str(k),str(v))) for k,v in alias['metadata'].items())
            alias_name.append(alias_to_use)
        alias_names.append(','.join(alias_name))

    entity_info[target_namespace] = alias_names
    token_info[target_namespace] = namespace_client.get('v1/sys/internal/counters/tokens')['data']['counters']
    

client.logout()

total_aliases = []
for namespace, alias_names in entity_info.items():
    alias_names.sort()
    total_aliases.extend(alias_names)
    logger.info('Namespace {0} has {1} entities. They are\n\t{2}'.format(namespace, len(alias_names), ",\n\t".join(alias_names)))
for namespace, counter_info in token_info.items():
    logger.info('Namespace {0} has following tokens:\n\t{1}'.format(namespace, json.dumps(counter_info, sort_keys=True)))

total_aliases.sort()
unique_aliases = set(total_aliases)
logger.info('True number of entities are {1}:\n\t{0}'.format(",\n\t".join(unique_aliases), len(unique_aliases)))