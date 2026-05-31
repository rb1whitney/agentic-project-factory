#!/usr/bin/env python3
import hvac
import os
import json
import sys
import base64
import urllib3
from projects.vault.lib.logger import get_logger

logger = get_logger("decode_secret_data")
urllib3.disable_warnings()

class VaultException(Exception):
    def __init__(self, msg):
        self.msg = msg
        super().__init__(msg)

class VaultClient:

    '''
        Class Vault
    '''

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def login(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        # Set the Request CA Bundle to ensure. Must handle logic when run either from vault
        ca_path = os.getcwd() + "/vault/config/certs/ca-bundle.crt"
        if os.getcwd().endswith('/vault'):
             ca_path = os.getcwd() + "/config/certs/ca-bundle.crt"
        os.environ["REQUESTS_CA_BUNDLE"] = ca_path
        self.client = hvac.Client(
            url = self.url,
            namespace = self.namespace,
            verify = True
        )
        try:
            self.client.auth.ldap.login(
                username = self.username,
                password = self.password,
                mount_point = self.mount_point
            )
        except hvac.exceptions.InvalidRequest as exp:
            raise VaultException(exp)

        if not self.client.is_authenticated:
            raise VaultException("Could not authenticate")

        self.client.secrets.kv.default_kv_version = 1

    def read(self, path):
        try:
            return self.client.read(path)
        except hvac.exceptions.Forbidden as exp:
            raise VaultException(exp)


def sanitize_path(config):
    path = os.path.expanduser(config)
    path = os.path.expandvars(path)
    path = os.path.abspath(path)
    return path


def main(path):
    path = sanitize_path(path)
    if not os.path.isfile(path):
        logger.error("Could not find {0}".format(path))
        sys.exit(1)

    vc = VaultClient(
        username=os.environ.get("LDAP_USERNAME"), 
        password=os.environ.get("LDAP_PASSWORD"), 
        mount_point="prod-ldap", 
        namespace=os.environ.get("VAULT_NAMESPACE", "puppet"),  
        url=os.environ.get("VAULT_ADDR", "https://vault-usprod01.corp.clover.com")
    )
    vc.login()
    client = vc.client

    with open(path) as secret_text:
        d = json.loads(secret_text.read())
        
    try:
        cipher_text = d.get('api_paths')[0].get('api_payload').get('key')
    except:
        logger.error("Invalid Format {0}".format(path))
        sys.exit(1)

    try:
        decrypted = client.write('transit/decrypt/namespace-encryption', ciphertext=cipher_text)
    except:
        logger.error("Can not Decrypt {0}".format(path))
        sys.exit(1)
    
    return base64.b64decode(decrypted.get('data').get('plaintext')).decode('utf-8')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Decode Secret Data")
    parser.add_argument("--path", required=True, help="Path to secret file")
    args = parser.parse_args()
    print(main(args.path))