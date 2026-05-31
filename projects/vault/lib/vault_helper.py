import base64
import json
import logging
import os
import re

# Cleans a PGP Key so it is properly processed by Vault API
# :param pgp_key: String representation of PGP Key
# :return: Cleaned PGP Representation of a PGP Key
def convert_pgp_key(pgp_key):
    cleaned_pgp_key = re.sub('-----BEGIN PGP PUBLIC KEY BLOCK-----.*\n\n', '', pgp_key, flags=re.S)
    cleaned_pgp_key = re.sub('=.*\n-----END PGP PUBLIC KEY BLOCK-----', '', cleaned_pgp_key,re.S)
    return cleaned_pgp_key

# Setups a usable logger for Vault Client
# :param logger_name: Sets name of logger
# :param log_level: Sets desired level of the logger
# :return: Returns a basic logger
def get_logger(logger_name, log_level):
    # Setup Basic Logging for Vault Operation Scripts
    numeric_log_level = getattr(logging, log_level, None)
    logging_formatter = logging.Formatter(
        '%(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(logger_name)
    logger.setLevel(numeric_log_level)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging_formatter)
    logger.addHandler(stream_handler)
    return logger

# Retrieves Cluster Configuration and Server Endpoints
# Open Config to retrieve cluster information
# :param cluster_name: Name of cluster to reference in Operational Config
# :return: Desired settings for a specific Vault Cluster
def get_cluster_config(cluster_name):
    current_file_dir = os.path.dirname(__file__)
    ops_config_path = os.path.join(current_file_dir, '../../config/ops.json')
    ops_config = json.load(open(ops_config_path, 'r'))
    if cluster_name in ops_config['clusters']:
        cluster_config = ops_config['clusters'][cluster_name]
    else:
        raise NameError(
            'Unable to find cluster {0} in Configuration File'.format(
                cluster_name))
    # Collect Server Endpoints in case we need to perform actions against them all
    server_endpoints = []
    for server_name in cluster_config['servers']:
        server_endpoints.append('https://{0}:{1}'.format(
            server_name, cluster_config['api_port']))
    cluster_config['server_endpoints'] = server_endpoints
    cluster_config['api_endpoint'] = 'https://{0}:{1}'.format(
        cluster_config['api_url'], cluster_config['api_port'])
    cluster_config['dr_endpoint'] = 'https://{0}:{1}'.format(
        cluster_config['api_url'], '8201')
    return cluster_config

# Pulls PGP Keys based upon PGP Key Holder Names and then returns this list for initialization process
# :param keyholders: Names of keyholders
# :return: String representation of PGP keys
def gather_pgp_keys(key_holders):
    base64_pgp_keys = []
    current_file_dir = os.path.dirname(__file__)
    for key_holder in key_holders:
        pgp_key_path = os.path.join(current_file_dir, '../../config/pgp_keys/{0}.asc'.format(key_holder))
        pgp_key_content = open(pgp_key_path, 'r').read()
        base64_pgp_key = convert_pgp_key(pgp_key_content)
        base64_pgp_keys.append(base64_pgp_key)
    return base64_pgp_keys

# Gather Key Input and make this information generically available
def format_key_response(key_response, key_holders, key_encrypt):
    key_output = {}
    key_suffix = '_base64' if key_encrypt else ''
    for index, vault_key in enumerate(key_response['keys' + key_suffix]):
        key = 'Keyholder #{0}'.format(str(index + 1))
        value = {
            'key' + key_suffix: vault_key,
            'email_address': key_holders[index]
        }
        key_output[key] = value
    return key_output
