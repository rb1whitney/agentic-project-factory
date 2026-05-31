import argparse
import json
import os
import sys
import time
import urllib3

# Don't write byte code for imported libraries
sys.dont_write_bytecode = True

# Import Custom Libraries
from lib.vault_client import LocalVaultClient
from lib import vault_helper

# Rekeys a cluster given input keys
# :param client: Client performs API actions
# :param keys: Keys to rekey vault
# :param secret_threshold: Specifies the number of shares required to reconstruct the master key
# :param pgp_keys: Specifies an array of PGP public keys used to encrypt the output unseal keys
# :param backup: If true, vault will make a backup of vault keys on its API
# :param recovery_key: If true, send requests to "rekey-recovery-key" instead of "rekey" api path.
# :return: The response of the request
def rekey(client, keys, secret_threshold, pgp_keys=None, backup=True, auto_unseal=False):
    api_payload = {
        'secret_shares': len(keys),
        'secret_threshold': secret_threshold,
    }

    if pgp_keys:
        api_payload['pgp_keys'] = pgp_keys
        api_payload['backup'] = backup

    api_path = 'v1/sys/rekey-recovery-key/init' if auto_unseal else 'v1/sys/rekey/init'
    init_response = client.put(api_path, api_payload)

    for key in keys:
        api_payload = {'key': key, 'nonce': init_response['nonce']}
        api_path = 'v1/sys/rekey-recovery-key/update' if auto_unseal else 'v1/sys/rekey/update'
        rekey_response = client.put(api_path, api_payload)
        if "complete" in rekey_response and rekey_response['complete']:
            break

    return rekey_response

# Initialize a new Vault with desired keys
# :param secret_shares: The number of shares to shard the master key
# :param secret_threshold: Specifies the number of shares required to reconstruct the master key
# :param auto_unseal_enabled: Will enable auto-recovery shares if auto-unseal is desired
# :return: Returns unseal keys and root token
def initialize(client, secret_shares=5, secret_threshold=3, auto_unseal_enabled=False):
    api_payload = {'secret_shares': secret_shares, 'secret_threshold': secret_threshold} if not auto_unseal_enabled else {}
    if auto_unseal_enabled:
        api_payload['recovery_shares'] = secret_shares
        api_payload['stored_shares'] = secret_shares
        api_payload['recovery_threshold'] = secret_threshold

    response = client.put('v1/sys/init', api_payload)
    return response

# Unseals a target host
# :param: logger: Logger to attach to local host client
# :param: host: List of Host Endpoints to unseal
# :param: keys: Keys to unseal all instances with
def unseal_host(logger, host, keys):
    unseal_client = LocalVaultClient(host, logger)
    for key in keys:
        api_payload = {'key': key}
        unseal_response = unseal_client.put('v1/sys/unseal', api_payload)
        if not unseal_response['sealed']:
            break

# Initialize the cluster and rekey if needed
def init_cluster(cluster_name,
                 server_endpoints,
                 logger,
                 key_holders,
                 key_shares=3,
                 key_threshold=2,
                 rekey_cluster=True,
                 auto_unseal_enabled=False):

    # Target First Server to Initialize
    client = LocalVaultClient(server_endpoints[0], logger)
    init_response = initialize(
        client,
        secret_shares=key_shares,
        secret_threshold=key_threshold,
        auto_unseal_enabled=auto_unseal_enabled)
    root_token = init_response['root_token']
    keys = init_response['recovery_keys'] if auto_unseal_enabled else init_response['keys']

    logger.info('Initialized {0} Vault Cluster at: {1}'.format(
        cluster_name, server_endpoints[0]))

    # Try to unseal clustered instances if auto-unseal is not enabled
    if not auto_unseal_enabled:
        for server_endpoint in server_endpoints:
            unseal_host(logger, server_endpoint, keys)

    if rekey_cluster:
        time.sleep(10)
        # Gather Key Holder Information
        base64_pgp_keys = vault_helper.gather_pgp_keys(key_holders)
        # Rekey Servers
        init_response = rekey(client, keys, key_threshold, pgp_keys=base64_pgp_keys, auto_unseal=auto_unseal_enabled)

    # Make final Key/Rekey information available to logger
    key_output = vault_helper.format_key_response(init_response, key_holders, rekey_cluster)
    logger.info('{0} Vault Cluster Keys:\n{1}'.format(cluster_name, json.dumps(key_output, indent=4)))

    return root_token


# Surpress InsecureRequestWarning
def main():
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Parse Arguments
    parser = argparse.ArgumentParser(description='Vault Cluster Init Script')
    parser.add_argument('--name',
                        dest='cluster_name',
                        help='Vault Cluster Name',
                        required=True)
    parser.add_argument('--log-level',
                        dest='log_level',
                        default='INFO',
                        help='Script Logging Level: WARN, DEBUG, INFO')
    args = parser.parse_args()

    # Limit Error Seen By User Unless in DEBUG MODE
    if 'DEBUG' not in args.log_level:
        sys.tracebacklimit = 0

    # Get Logger and Cluster Config
    cluster_name = args.cluster_name
    config = vault_helper.get_cluster_config(cluster_name)
    logger = vault_helper.get_logger('Vault Init', args.log_level)

    # Initialize Cluster
    root_token = init_cluster(
        cluster_name=cluster_name,
        key_shares=len(config['key_holders']),
        key_threshold=config['key_threshold'],
        key_holders=config['key_holders'],
        logger=logger,
        server_endpoints=config['server_endpoints'],
        rekey_cluster=config['key_encrypt'],
        auto_unseal_enabled=config['recovery_key'])

    # Apply Admin Configuration as Root Token
    vault_client = LocalVaultClient(config['server_endpoints'][0], logger)
    vault_client.adapter.token = root_token

    # Search for all JSON files and then process them
    admin_json_path = '{0}/../config/json_workspaces/{1}/admin/'.format(
        os.path.dirname(__file__), config['config_env'])
    json_files = []
    for root, dirs, files in os.walk(admin_json_path):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    json_files.sort()

    for json_file in json_files:
        json_payload = json.load(open(json_file, 'r'))
        if '_namespace' in json_payload:
            # Re-use current access token to access namespace
            namespace_client = LocalVaultClient(
                config['api_endpoint'],
                logger,
                namespace=json_payload['_namespace'])
            namespace_client.adapter.token = vault_client.adapter.token
            namespace_client.submit(json_payload)
        else:
            vault_client.submit(json_payload)

    # Revoke Root Token
    vault_client.logout()

if __name__ == '__main__':
    main()
