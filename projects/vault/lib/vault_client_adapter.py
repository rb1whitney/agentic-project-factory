import requests
import requests.exceptions
from lib.vault_client_error import VaultClientError

# Vault Client Adapter
# This code was ported from HVAC plugin: https://github.com/hvac/hvac/blob/master/hvac/adapters.py
class VaultClientAdapter:    
    def __init__(self, base_uri, token=None, cert=None, verify=True, timeout=30,
                 allow_redirects=True, namespace=None, ignore_exceptions=False):
        """Create a new request adapter instance.

        :param base_uri: Base URL for the Vault instance being addressed.
        :param token: Authentication token to include in requests sent to Vault.
        :param cert: Certificates for use in requests sent to the Vault instance. This should be a tuple with the
            certificate and then key.
        :param verify: Either a boolean to indicate whether TLS verification should be performed when sending requests to Vault,
            or a string pointing at the CA bundle to use for verification. See http://docs.python-requests.org/en/master/user/advanced/#ssl-cert-verification.
        :param timeout: The timeout value for requests sent to Vault.
        :param proxies: Proxies to use when preforming requests.
            See: http://docs.python-requests.org/en/master/user/advanced/#proxies
        :param allow_redirects: Whether to follow redirects when sending requests to Vault.
        :param namespace: Optional Vault Namespace.
        :param ignore_exceptions: If True, _always_ return the response object for a given request. I.e., don't raise an exception
            based on response status code, etc.
        """
        session = requests.Session()

        self.base_uri = base_uri
        self.token = token
        self.namespace = namespace
        self.session = session
        self.allow_redirects = allow_redirects
        self.ignore_exceptions = ignore_exceptions

        self._kwargs = {
            'cert': cert,
            'verify': verify,   #while working locally if any error comes try with None, False options
            'timeout': timeout,
        }

    # Closes the underlying Requests session.
    def close(self):
        self.session.close()

    # Cleans and constructs a vault url
    # :param base_uri: Base Cluster URI
    # :param api_url: API to append to base URI
    # :return: Full URL combining all provided arguments
    def construct_url(self, base_uri, api_url):
        #If testing in local without https override this base_uri="http://vault-raft-nonprod0101.dev.pdx10.clover.network:8200/"
        while '//' in api_url:
            # Vault CLI treats a double forward slash ('//') as a single forward slash for a given path.
            api_url = api_url.replace('//', '/')
        url = '/'.join([base_uri.strip('/'), api_url.strip('/')])
        return url

    # Handles sending request using request
    # :param method: HTTP method to use with the request: create, read, put, post, delete, head
    # :param url: Partial URL path to send the request to. This will be joined to the end of the instance's base_uri
    # :param headers: Additional headers to include with the request
    # :param kwargs: Additional keyword arguments to include in the requests call
    # :return: The response of the request
    def request(self, method, url, headers=None, raise_exception=True, **kwargs):
        url = self.construct_url(self.base_uri, url)

        if not headers:
            headers = {}

        if self.token:
            headers['X-Vault-Token'] = self.token

        if self.namespace:
            headers['X-Vault-Namespace'] = self.namespace

        _kwargs = self._kwargs.copy()
        _kwargs.update(kwargs)

        response = self.session.request(
            method=method,
            url=url,
            headers=headers,
            allow_redirects=self.allow_redirects,
            **_kwargs
        )

        # Try to determine failure and return error response
        if not response.ok:
            error = None
            if response.headers.get('Content-Type') == 'application/json':
                try:
                    error = response.json().get('errors')
                except Exception:
                    pass
            if error is None:
                error = response.text
            raise VaultClientError(response.status_code, error, method, url)
        return response
