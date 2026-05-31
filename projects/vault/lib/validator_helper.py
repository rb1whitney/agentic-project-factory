import json
import logging
import os.path
import re

class LocalVaultValidator:
    def __init__(self, validation_scheme, logger):
        self.validation_scheme = validation_scheme
        self.logger = logger

    def validate(self, cluster_name, json_files=None, json_payload=None):
        results = []
        if self.validation_scheme == 'namespaces':
            validators = [
                'validate_namespace',
                #'prohibit_sudo_policy',
                'prohibit_read_write_policy',
                #'prohibit_plain_text_secrets',
                'prohibit_long_lived_tokens'
            ]
            for validator_name in validators:
                result = getattr(self, validator_name)(json_files,
                                                       cluster_name)
                results.append(result)
        elif self.validation_scheme == 'admin':
            validators = [
                #'prohibit_plain_text_secrets', 
                #'prohibit_long_lived_tokens'
            ]
            for validator_name in validators:
                result = getattr(self, validator_name)(json_files,
                                                       cluster_name)
                results.append(result)
        elif self.validation_scheme == 'secret':
            validators = ['prohibit_configurations']
            for validator_name in validators:
                result = getattr(self, validator_name)(json_payload,
                                                       cluster_name)
                results.append(result)
        else:
            raise AssertionError(
                'Unable to find rules for target validation scheme {0}'.format(
                    self.validation_scheme))
        return [item for sublist in results for item in sublist]

    def validate_namespace(self, json_files, cluster_name):
        # Ensure namespace is valid
        errors = []
        for json_file in json_files:
            json_payload = json.load(open(json_file, 'r'))
            namespace_name = os.path.abspath(json_file).split('namespaces/')[-1].split('/')[0]
            if '_namespace' not in json_payload:
                errors.append(
                    'Namespace not detected in file: {0}'.format(json_file))
                continue
            if json_payload['_namespace'] != namespace_name:
                errors.append('Must use {1} namespace in files {0}'.format(
                    json_file, namespace_name))
            if json_payload['_namespace'] == 'root':
                errors.append('Namespace may not be root')
        return errors

    def prohibit_sudo_policy(self, json_files, cluster_name):
        # Do not allow sudo in policy for the majority of policies
        errors = []
        for json_file in json_files:
            json_payload = json.load(open(json_file, 'r'))
            for api_object in json_payload['api_paths']:
                if re.match('v1/sys/policy/.*',
                            api_object['api_path']) != None:
                    sudo_acls = 0
                    for policy_acl in list(api_object['api_payload']['path'].values(
                    )):
                        if 'sudo' in policy_acl['capabilities']:
                            sudo_acls = +1
                    if sudo_acls != 0:
                        errors.append(
                            'Error with policy {1} giving sudo access in {0}. Namespace policies may not give sudo access'
                            .format(json_file, api_object['api_path']))
        return errors

    def prohibit_read_write_policy(self, json_files, cluster_name):
        # Do not allow normal users to combine read and write access
        errors = []
        for json_file in json_files:
            json_payload = json.load(open(json_file, 'r'))
            for api_object in json_payload['api_paths']:
                if re.match('v1/sys/policy/.*',
                            api_object['api_path']) != None and api_object['api_action'] == 'post':
                    read_acls = 0
                    write_acls = 0
                    for policy_acl in list(api_object['api_payload']['path'].values(
                    )):
                        if 'read' in policy_acl[
                                'capabilities'] or 'list' in policy_acl[
                                    'capabilities']:
                            read_acls = +1
                        if 'create' in policy_acl[
                                'capabilities'] or 'update' in policy_acl[
                                    'capabilities'] or 'delete' in policy_acl[
                                        'capabilities']:
                            write_acls = +1
                    if read_acls != 0 and write_acls != 0:
                        errors.append(
                            'Error with policy {1} giving read and write access in {0}. Please separate access'
                            .format(json_file, api_object['api_path']))
        return errors

    def prohibit_plain_text_secrets(self, json_files, cluster_name):
        # Ensures we don't write plain text secrets
        errors = []
        secret_engines = []

        # Find all secret engines in json files
        for json_file in json_files:
            json_payload = json.load(open(json_file, 'r'))
            for api_object in json_payload['api_paths']:
                if re.match('^v1/sys/mounts/.*',
                            api_object['api_path']) != None:
                    secret_engine_name = api_object['api_path'].split('/')[3]
                    secret_engines.append(secret_engine_name)

        # Dedupe the list
        secret_engines = list(set(secret_engines))

        # Verify no secrets are written to these endpoints
        for json_file in json_files:
            json_payload = json.load(open(json_file, 'r'))
            for api_object in json_payload['api_paths']:
                if re.match(
                        '^v1/({0})/.*'.format(
                            '|'.join(secret_engines)), api_object['api_path']
                ) != None and 'not_plain_secret' not in api_object and 'transit_encoded_keys' not in api_object and 'wrapped_token' not in api_object:
                    errors.append(
                        'Error with api_object {1} in {0}. Targeting a change in a known secret engine. Teams may not store secrets in open configuration. Bypassing this check improperly may be grounds for dismissal if secrets are leaked. Mark in api object not_plain_secret: false or use wrapped_token to seed secret in secret engine'
                        .format(json_file, api_object['api_path']))
        return errors

    def prohibit_configurations(self, json_payload, cluster_name):
        # Ensures we do not secretly rewrite policies, print secrets, or delete values
        errors = []
        for api_object in json_payload['api_paths']:
            if re.match('v1/sys/policy/*', api_object['api_path']) != None:
                errors.append(
                    'Error with api_object {0} in wrapped token. May not modify policy'
                    .format(api_object['api_path']))
            if api_object['api_action'] in ['delete', 'get', 'list'
                                            ] != None:
                errors.append(
                    'Error with api_object {0} in wrapped token. May not delete, get, or list objects'
                    .format(api_object['api_path']))
        return errors

    def prohibit_long_lived_tokens(self, json_files, cluster_name):
        # Ensures no vault secret engine exceeds defined standards
        errors = []
        for json_file in json_files:
            json_payload = json.load(open(json_file, 'r'))
            for api_object in json_payload['api_paths']:
                if re.match('^v1/sys/mounts/*',
                            api_object['api_path']) != None:
                    if 'config' in api_object['api_payload']:
                        if 'default_lease_ttl' in api_object['api_payload'][
                                'config']:
                            default_lease_ttl = self.normalize_time(
                                api_object['api_payload']['config']
                                ['default_lease_ttl'])
                            max_default_lease_ttl = '60m' if api_object[
                                'api_payload']['type'] != 'pki' else '17520h'
                            if default_lease_ttl == -1 or default_lease_ttl > self.normalize_time(
                                    max_default_lease_ttl):
                                errors.append(
                                    'Error with api_object {1} in {0}. Default Lease TTL may not be more than 60 minutes'
                                    .format(json_file, api_object['api_path']))
                        if 'max_lease_ttl' in api_object['api_payload'][
                                'config']:
                            max_lease_ttl = self.normalize_time(
                                api_object['api_payload']['config']
                                ['max_lease_ttl'])
                            max_lease_ttl_limit = '30d' if api_object[
                                'api_payload']['type'] != 'pki' else '87600h'
                            if max_lease_ttl == -1 or max_lease_ttl > self.normalize_time(
                                    max_lease_ttl_limit):
                                errors.append(
                                    'Error with api_object {1} in {0}. Max Lease TTL may not be more than {2} days'
                                    .format(json_file, api_object['api_path'],
                                            max_lease_ttl_limit[:-1]))
        return errors

    def normalize_time(self, time_string):
        # Normalize current times to seconds for standard way
        base_time = time_string[:-1]
        time_unit = time_string[-1:]
        if time_unit == 's':
            return int(base_time)
        elif time_unit == 'm':
            return int(base_time) * 60
        elif time_unit == 'h':
            return int(base_time) * 60 * 60
        elif time_unit == 'd':
            return int(base_time) * 60 * 60 * 24
        else:
            return -1
