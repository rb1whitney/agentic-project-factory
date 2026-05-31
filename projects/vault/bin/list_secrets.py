#!/usr/bin/env python3
import argparse
import sys
import urllib3

# Don't write byte code for imported libraries
sys.dont_write_bytecode = True

# Import Custom Libraries
from lib import vault_helper
from lib.vault_client import LocalVaultClient
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

if __name__ == '__main__':
    # Parse Arguments
    parser = argparse.ArgumentParser(description='Manage Secret Data')
    parser.add_argument('--name',
                        dest='cluster_name',
                        help='Vault Cluster Name',
                        required=True)
    parser.add_argument('--log-level',
                        dest='log_level',
                        help='<<WARN|DEBUG|INFO>>',
                        default='WARN')
    parser.add_argument('--auth-method',
                        dest='auth_method',
                        help='<<ldap|token|tls>>',
                        default='ldap')
    parser.add_argument('--mount-path',
                        dest='mount_point',
                        help='../config',
                        default='ldap')
    parser.add_argument('--source-namespace',
                        dest='source_namespace',
                        default='puppet')
    parser.add_argument('--source-kv',
                        dest='source_kv',
                        default='puppet')
    parser.add_argument('--source-path',
                        dest='source_path',
                        default='/')
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
    logger = vault_helper.get_logger('List Secrets', args.log_level)
    config = vault_helper.get_cluster_config(cluster_name)

    # Setup Connections to auth namespace (allows root namespace)
    auth_namespace = args.source_namespace if args.auth_namespace == 'False' else None
    auth_client = LocalVaultClient(config['api_endpoint'], logger, namespace=auth_namespace)
    auth_client.login(auth_method=args.auth_method, mount_point=args.mount_point)

    client = LocalVaultClient(config['api_endpoint'], logger, namespace=args.source_namespace)
    client.adapter.token = auth_client.adapter.token


    # Find all secrets and then read them out
    print ("Finding all secrets at target path...")
    secret_paths = list_secrets(client, args.source_kv, args.source_path)
    secret_paths.sort()
    for secret_path in secret_paths:
        print(secret_path)

    client.logout()
