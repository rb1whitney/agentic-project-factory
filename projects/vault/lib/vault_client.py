import base64
import json
import os
import getpass
import pathlib
from lib.vault_client_adapter import VaultClientAdapter
from lib.vault_client_error import VaultClientError

# Exposes a usable Vault Client that makes API request based upon target payload
class LocalVaultClient:
    def __init__(self,
                 api_endpoint,
                 logger,
                 api_verify=True,
                 namespace=None,
                 allow_api_redirect=True,
                 api_timeout=15):
        self.logger = logger
        cert = (os.environ['CERT_PATH'],
                os.environ['KEY_PATH']) if 'CERT_PATH' in os.environ and 'KEY_PATH' in os.environ else None
        
        # Set the Request CA Bundle to ensure. Must handle logic when run either from vault
        ca_path = str(pathlib.Path(__file__).parent.resolve()) + "/../../config/certs/ca-bundle.crt"
        os.environ["REQUESTS_CA_BUNDLE"] = ca_path
        
        self.adapter = VaultClientAdapter(api_endpoint,
                                             verify=api_verify,
                                             namespace=namespace,
                                             allow_redirects=allow_api_redirect,
                                             timeout=api_timeout,
                                             cert=cert)
        self.namespace = namespace

    def valid_ldap(self):
        ldap_username = os.environ.get("LDAP_USERNAME", None)
        ldap_password = os.environ.get("LDAP_PASSWORD", None)
        if ldap_username is None:
            try:
                ldap_username = input("Enter LDAP Username: ")
                ldap_username = ldap_username if ldap_username else None
                if ldap_username is None:
                    return False
                os.environ["LDAP_USERNAME"] = ldap_username
            except Exception as error:
                self.logger.error('ERROR', error)
                return False

        if ldap_password is None:
            try:
                ldap_password = getpass.getpass()
                ldap_password = ldap_password if ldap_password else None
                if ldap_password is None:
                    return False
                os.environ["LDAP_PASSWORD"] = ldap_password
            except Exception as error:
                self.logger.error('ERROR', error)
                return False
        return True

    # Checks if environment variables are set
    # :param logger: Will send error output to logger before aborting
    # :param env_list: Will check if environment variables are set for sensitive values
    # :return: True if environment variables are all set, else will abort application run
    def valid_env_variables(self, env_list):
        invalid_env_variables = []
        for env_var_name in env_list:
            if env_var_name not in os.environ or not os.environ[env_var_name]:
                invalid_env_variables.append(env_var_name)
        if len(invalid_env_variables):
            self.logger.error('Please set the following environment variables prior to application run: {0}'.format(
                invalid_env_variables))
            exit(1)
        else:
            return True

    # Checks for required sensitive input based upon auth_method and creates auth method api path
    # :param auth_method: Auth Method to match for sensitive setting
    # :return : Returns the Auth Method API Path and API Payload
    def validate_sensitive_input(self, auth_method, mount_point):
        if auth_method == 'cert' and self.valid_env_variables(
                ['CERT_PATH', 'KEY_PATH', 'ROLE_NAME']):
            api_payload = {'name': os.environ['ROLE_NAME']}
        elif auth_method == 'ldap' and self.valid_ldap():
            api_path = 'v1/auth/{0}/login/{1}'.format(
                mount_point, os.environ['LDAP_USERNAME'])
            api_payload = {
                'username': os.environ['LDAP_USERNAME'],
                'password': os.environ['LDAP_PASSWORD']
            }
        elif auth_method == 'app_role' and self.valid_env_variables(
                ['APP_ROLE_ID', 'SECRET_ID']):
            api_payload = {
                'role_id': os.environ['APP_ROLE_ID'],
                'secret_id': os.environ['SECRET_ID']
            }
        elif auth_method == 'k8s' and self.valid_env_variables(
                ['JWT_TOKEN', 'ROLE_NAME']):
            api_payload = {
                'role': os.environ['ROLE_NAME'],
                'jwt': os.environ['JWT_TOKEN']
            }
        elif auth_method == 'token' and self.valid_env_variables(
                ['VAULT_TOKEN']):
            self.adapter.token = os.environ['VAULT_TOKEN']
        else:
            self.logger.error(
                'Auth method {0} is not supported. Please provide valid type: <<cert|ldap|app_role|k8s|token>>'
                .format(auth_method))
            exit(1)
        return api_path, api_payload

    def login(self, auth_method='ldap', mount_point='ldap'):
        # Provides Common Framework for logging into vault to make changes
        api_path = '/v1/auth/{0}/login'.format(mount_point)
        api_payload = None

        # Blows up if auth method input is not setup properly
        api_path, api_payload = self.validate_sensitive_input(auth_method, mount_point)
        # Perform a login if client doesn't already have a token
        if api_payload:
            self.logger.debug('Authenticating against {1}/{0} with payload:\n{2}'.format(api_path, self.adapter.base_uri, api_payload))
            response = self.adapter.request('post', api_path, json=api_payload)
            self.adapter.token = response.json()['auth']['client_token']

        if self.adapter.token:
            acl_policies = self.get('/v1/auth/token/lookup-self')['data']['policies']
            self.logger.info('Authorization is successful against {0}/{1}'.format(self.adapter.base_uri, api_path))
            self.logger.debug("Access is granted to ACL Policies: {0}".format(acl_policies))

    # Check if payload needs to be retrieve from Vault and replaces in-line
    # :param api_object : Object to modify as needed
    def inline_unwrap_operation(self, api_object):
        if 'wrapped_token' in api_object:
            self.logger.info('Retrieving wrapped token\'s payload: {0}'.format(api_object['wrapped_token']))
            api_payload = { "token" : api_object['wrapped_token'] }
            response = self.post('/v1/sys/wrapping/unwrap', api_payload)
            api_object['api_payload'] = response['data']
            self.logger.debug('Replaced API Object with wrapped token. New content:\n{0}'.format(api_object))
    
    # Finds target value in a nested dictionary by traversing the given keys
    # :param dict_values dictionary to check
    # :param keys to traverse
    def get_nested_key_value(self, dict_values, keys):
        for target_key in keys:
            try:
                dict_values = dict_values[target_key]
            except KeyError:
                self.logger.error("Unable to find key {0} in {1}".format(target_key, dict_values))
        return dict_values
    
    # 
    # Assigns target value in a nested dictionary by traversing the given keys, 
    # then stops to *second* last key
    # :param dict_values dictionary to check
    # :param keys to traverse
    # :param value target value to set given nested keys
    # :param encrypted_value target value to replace if array
    def set_nested_key_value(self, dict_values, keys, value, encrypted_value):
        lastkey = keys[-1]
        for k in keys[:-1]:  
            dict_values = dict_values[k]
        if isinstance(dict_values[lastkey], list):
            dict_values[lastkey] = [value if x == encrypted_value else x for x in dict_values[lastkey]]
        else:
            dict_values[lastkey] = value
        
    # Allows us to decrypt value before loading into Vault
    # :param api_object : Object to modify as needed
    def inline_transit_operation(self, api_object):
        if 'transit_encoded_keys' in api_object:
            transit_secret_engine = api_object['transit_secret_engine'] if 'transit_secret_engine' in api_object else 'transit'
            transit_key = api_object['transit_key'] if 'transit_key' in api_object else 'namespace-encryption'
            transit_api_path = "v1/{0}/decrypt/{1}".format(transit_secret_engine, transit_key)
            for transit_encoded_key in api_object['transit_encoded_keys']:
                key_path = transit_encoded_key.split('/')
                encrypted_value = self.get_nested_key_value(api_object['api_payload'], key_path)
                encrypted_value_list = encrypted_value if isinstance(encrypted_value, list) else [encrypted_value]
                for encrypted_value_item in encrypted_value_list:
                    transit_payload = { 'ciphertext': encrypted_value_item }
                    if 'transit_context' in api_object:
                        transit_payload['context'] = api_object['transit_context']
                    decrypted_payload = self.post(transit_api_path, transit_payload)
                    base64_value = decrypted_payload['data']['plaintext']
                    # Any value in transit_base64_keys means that the value should not be base64 decoded
                    if 'transit_base64_keys' in api_object and transit_encoded_key in api_object['transit_base64_keys']:
                        string_value = base64_value
                    else: 
                        key_value = base64.b64decode(base64_value)
                        try:
                            string_value = str(key_value, 'UTF-8')
                        except ValueError:
                            # Sometimes values are not able to be converted to UTF-8
                            string_value = str(key_value)
                    self.set_nested_key_value(api_object['api_payload'], key_path, string_value, encrypted_value_item)

    # Check if any payload elements need to be base64 decoded or encoded
    # :param api_object : Object to modify as needed
    def inline_base64_operations(self, api_object):
        if 'decode_base64_keys' in api_object:
            for key_name in api_object['decode_base64_keys']:
                key_path = key_name.split('/')
                value = self.get_nested_key_value(api_object['api_payload'], key_path)
                value_list = value if isinstance(value, list) else [value]
                for value_item in value_list:
                    string_value = str(base64.b64decode(value_item), 'UTF-8')
                    self.set_nested_key_value(api_object['api_payload'], key_path, string_value, value_item)
        if 'encode_base64_keys' in api_object:
            for key_name in api_object['encode_base64_keys']:
                key_path = key_name.split('/')
                value = self.get_nested_key_value(api_object['api_payload'], key_path)
                value_list = value if isinstance(value, list) else [value]
                for value_item in value_list:
                    string_value = str(base64.b64encode(value_item.encode('UTF-8')), 'UTF-8')
                    self.set_nested_key_value(api_object['api_payload'], key_path, string_value, value_item)

    # Policy API Calls are not handled well so we are allowing
    # Policy Files to be JSON like everything and function like
    # the vault policy write command does
    # :param api_object : Object to modify as needed
    def inline_transform_operation(self, api_object):
        if 'sys/policy' in api_object['api_path'] and api_object['api_action'] == 'post':
            api_object['api_payload'] = { 'policy': json.dumps(api_object['api_payload'])}
            if '/roleset/' in api_object['api_path'] and api_object['api_action'] == 'post':
                api_object['api_payload']['bindings'] = json.dumps(
                    api_object['api_payload']['bindings'])

    # Used by manage data to allow us to quickly make changes to the API
    # :param json_payload: JSON payload of multiple actions that can be taken against Vault
    # :return : List of responses for each action
    def submit(self, json_payload):
        ignore_api_matches = ['already in use', 'already exists']
        api_responses = []
        for api_object in json_payload['api_paths']:
            # Pre-Process every request to allow customization of individual payloads
            self.inline_unwrap_operation(api_object)
            self.inline_transit_operation(api_object)
            self.inline_base64_operations(api_object)
            self.inline_transform_operation(api_object)

            api_path = api_object['api_path']
            api_action = api_object['api_action']
            api_response = None

            namespace_message = ' and namespace {}'.format(self.namespace) if self.namespace else ''
            self.logger.info('Performing {0} action against API Path{3}: {1}/{2}'.format(api_action, self.adapter.base_uri, api_path, namespace_message))

            try:
                api_payload = None
                if 'api_payload' in api_object:
                    api_payload = api_object['api_payload']
                    self.logger.debug('API Payload is: {0}'.format(json.dumps(api_payload, indent=4)))
                api_response = self.adapter.request(api_action, api_path, json=api_payload, timeout=30)
            except VaultClientError as err:
                raise_error = True
                error_message = str(err)
                # We ignore any error messages that state the object already exists
                for ignore_api_match in ignore_api_matches:
                        if ignore_api_match in error_message:
                            raise_error = False
                if raise_error:
                    raise err

            if api_response != None and api_response.content != "" and api_response.status_code != 204:
                self.logger.debug('API Response is:\n{0}'.format(
                    json.dumps(api_response.json(), indent=4)))
                api_responses.append(api_response.json())
            else:
                api_responses.append({})
        return api_responses

    # Creates a generic API Payload for all REST API actions
    # :param :api_action: Set a valid API action
    # :param :api_path: This is URL to post action against
    # :param :api_payload: Optional payload for post or put action
    def create_json_payload(self, api_action, api_path, api_payload=None):
        json_payload = {
            'api_paths': [{
                'api_path': api_path,
                'api_action': api_action,
            }]
        }
        if api_payload:
            json_payload['api_paths'][0]['api_payload'] = api_payload
        return json_payload

    # Wrapper for Post API Calls
    # :param api_path: API Path to perform post action
    # :return: Vault API Response
    def post(self, api_path, api_payload):
        json_payload = self.create_json_payload('post', api_path, api_payload)
        api_responses = self.submit(json_payload)
        return api_responses[0]

    # Wrapper for Put API Calls
    # :param api_path: API Path to perform put action
    # :return: Vault API Response
    def put(self, api_path, api_payload):
        json_payload = self.create_json_payload('put', api_path, api_payload)
        api_responses = self.submit(json_payload)
        return api_responses[0]

    # Wrapper for Get API Calls
    # :param api_path: API Path to perform get action
    # :return: Vault API Response
    def get(self, api_path):
        json_payload = self.create_json_payload('get', api_path)
        api_responses = self.submit(json_payload)
        return api_responses[0]

    # Wrapper for List API Calls
    # :param api_path: API Path to perform list action
    # :return: Vault API Response
    def list(self, api_path):
        json_payload = self.create_json_payload('list', api_path)
        api_responses = self.submit(json_payload)
        return api_responses[0]

    # Wrapper for Delete API Calls
    # :param api_path: API Path to perform delete action
    # :return: Vault API Response
    def delete(self, api_path):
        json_payload = self.create_json_payload('delete', api_path)
        api_responses = self.submit(json_payload)
        return api_responses[0]

    # Wrapper for HEAD API Calls
    # :param api_path: API Path to perform head action
    # :return: Vault API Response
    def head(self, api_path):
        json_payload = self.create_json_payload('head', api_path)
        api_responses = self.submit(json_payload)
        return api_responses[0]

    # Revokes token that client is currently using
    def logout(self):
        if self.adapter.token:
            self.put('v1/auth/token/revoke-self', None)
            self.adapter.token = None

