import argparse
import datetime
import json
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

# Enter a single recovery key share to progress the rekey of the Vault
# :param client: Client performs API actions
# :param key: Specifies a single recovery share key.
# :param nonce: Specifies the nonce of the rekey operation.
# :param recovery_key: If true, send requests to "rekey-recovery-key" instead of "rekey" api path.
# :return: The response of the request
def rekey(client, key, nonce=None, recovery_key=False):
    api_payload = { 'key': key }
    
    if nonce != None:
        api_payload['nonce'] = nonce

    api_path = 'v1/sys/rekey/update'
    if recovery_key:
        api_path = 'v1/sys/rekey-recovery-key/update'
    return client.put(api_path, api_payload)

# Initializes a new rekey attempt
# :param client: Client performs API actions
# :param secret_shares: Specifies the number of shares to split the master key into
# :param secret_threshold: Specifies the number of shares required to reconstruct the master key
# :param pgp_keys: Specifies an array of PGP public keys used to encrypt the output unseal keys
# :param backup: If true, vault will make a backup of vault keys on its API
# :param recovery_key: If true, send requests to "rekey-recovery-key" instead of "rekey" api path.
# :return: The response of the request
def start_rekey(client, secret_shares, secret_threshold, pgp_keys=None, backup=True, recovery_key=False):
    api_payload = {
        'secret_shares': secret_shares,
        'secret_threshold': secret_threshold,
    }

    if pgp_keys:
        api_payload['pgp_keys'] = pgp_keys
        api_payload['backup'] = backup

    api_path = 'v1/sys/rekey/init'
    if recovery_key:
        api_path = 'v1/sys/rekey-recovery-key/init'
    return client.put(api_path, api_payload)

# Cancel any in-progress rekey
# :param client: Client performs API actions
# :return: The response of the request
def cancel_rekey(client, recovery_key=False):
    api_path = 'v1/sys/rekey/init'
    if recovery_key:
        api_path = 'v1/sys/rekey-recovery-key/init'
    return client.delete(api_path)

# Parse Arguments
parser = argparse.ArgumentParser(description='Vault Cluster Manage Data')
parser.add_argument('--name',
                    dest='cluster_name',
                    help='Vault Cluster Name',
                    required=True)
parser.add_argument('--auth-method',
                    dest='auth_method',
                    help='<<ldap|token|tls>>',
                    default='ldap')
parser.add_argument('--log-level',
                    dest='log_level',
                    help='<<WARN|DEBUG|INFO>>',
                    default='INFO')
parser.add_argument('--mount-path',
                    dest='mount_point',
                    help='../config',
                    default='ldap')
parser.add_argument('--event',
                    dest='event',
                    help='<<init|generate>>',
                    default='rekey')
args = parser.parse_args()

# Limit Error Seen By User Unless in DEBUG MODE
if 'DEBUG' not in args.log_level:
    sys.tracebacklimit = 0

# Get Logger and Cluster Config
cluster_name = args.cluster_name
config = vault_helper.get_cluster_config(cluster_name)
logger = vault_helper.get_logger('Manage Data', args.log_level)

# Get Key Holder Information
key_encrypt = config['key_encrypt']
key_holders = config['key_holders']
key_shares = len(config['key_holders'])
key_threshold = config['key_threshold']

# Log into Vault
vault_client = LocalVaultClient(config['api_endpoint'], logger)
vault_client.login(auth_method=args.auth_method, mount_point=args.mount_point)

# Perform either rekey init or rekey-single-user input action
if args.event == 'init':
    # Initializes a rekey attempt and returns nonce value for each keyholder
    base64_pgp_keys = vault_helper.gather_pgp_keys(key_holders)
    # Reset and then start Rekey Process
    cancel_rekey(vault_client, recovery_key=config['recovery_key'])
    start_rekey_response = start_rekey(
        vault_client,
        secret_shares=key_shares,
        secret_threshold=key_threshold,
        pgp_keys=base64_pgp_keys,
        backup=True,
        recovery_key=config['recovery_key'])
    logger.info(
        'Rekey event has started for cluster {0}. Nonce value for keyholders is: {1}'
        .format(cluster_name, start_rekey_response['nonce']))
else:
    if vault_client.valid_env_variables(['VAULT_KEY', 'NONCE']):
        rekey_response = rekey(vault_client, key=os.environ['VAULT_KEY'], nonce=os.environ['NONCE'], recovery_key=config['recovery_key'])
        logger.info('Results from rekeying effort: {0}'.format(rekey_response))
        if 'keys' in rekey_response:
            # Make final Key/Rekey information available to output
            key_output = vault_helper.format_key_response(rekey_response, key_holders, key_encrypt)
            logger.info('{0} Vault Cluster Keys:\n{1}'.format(
                cluster_name, json.dumps(key_output, indent=4)))

vault_client.logout()
