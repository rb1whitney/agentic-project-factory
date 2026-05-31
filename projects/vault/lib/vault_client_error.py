# Exposes a specialized Python Exception error
class VaultError(Exception):
    # Setup a Basic Vault Client Error
    # :param status_code: error code from Vault API
    # :param message: Possible error message from Vault API
    # :param method: API action undertaken against Vault API
    # :param url: URL posted action against
    def __init__(self, status_code="", message="", method="", url=""):
        self.status_code = status_code
        self.message = message
        self.method = method
        self.url = url
        err_msg = ""
        if message:
            err_msg = " Error is: {0}".format(message)
        
        exception_err = "Vault Client received a {0} status code after making a {1} to {2}.{3}".format(self.status_code, self.method, self.url, err_msg)
        super(VaultError, self).__init__(exception_err)

class VaultClientError(VaultError):
    pass