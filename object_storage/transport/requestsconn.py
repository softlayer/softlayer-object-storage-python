"""
    Connection Module

    See COPYING for license information
"""
import requests
import httplib
from socket  import timeout
from urlparse import urlparse
from object_storage import consts
from object_storage.transport import BaseAuthentication, BaseAuthenticatedConnection
from object_storage import errors

try:
    import simplejson as json
except ImportError:
    import json

import logging
logger = logging.getLogger(__name__)

class AuthenticatedConnection(BaseAuthenticatedConnection):
    """ 
        Connection that will authenticate if it isn't already 
        and retry once if an auth error is returned.
    """
    def __init__(self, auth, **kwargs):
        self.token = None
        self.storage_url = None
        self.auth = auth
        self.auth.authenticate()
        self._authenticate()
        
    def make_request(self, method, url=None, *args, **kwargs):
        """ Makes a request """
        _headers = kwargs.get('headers', {})
        headers = self.get_headers()
        if _headers:
            headers.update(_headers)
        kwargs['headers'] = headers
        
        if 'verify' not in kwargs:
            kwargs['verify'] = False

        formatter = None
        if 'formatter' in kwargs:
            formatter = kwargs.get('formatter')
            del kwargs['formatter']

        res = requests.request(method, url, *args, **kwargs)
        if kwargs.get('return_response', True):
            res = self._check_success(res)
            if res.status_code == 404:
                raise NotFound('Not found')
            if res.error:
                try:
                    raise res.raise_for_status()
                except Exception, ex:
                    raise errors.ResponseError(res.status_code, str(ex))

        if formatter:
            return formatter(res)
        return res
    
    def _check_success(self, res):
        """ 
            Checks for request success. If a 401 is returned, it will 
            authenticate again and retry the request.
        """
        if res.status_code == 401:

            # Authenticate and try again with a (hopefully) new token
            self._authenticate()
            res.request.headers.update(self.auth_headers)
            res.request.send(anyway=True)
            res = res.request.response
        return res

class Authentication(BaseAuthentication):
    """
        Authentication class.
    """
    def __init__(self, username, api_key, *args, **kwargs):
        super(Authentication, self).__init__(*args, **kwargs)
        self.username = username
        self.api_key = api_key

    def authenticate(self):
        """ Does authentication """
        headers = {'X-Storage-User': self.username,
                   'X-Storage-Pass': self.api_key,
                   'Content-Length': '0'}
        response = requests.get(self.auth_url, headers=headers, verify=False)

        if response.status_code == 401:
            raise errors.AuthenticationError('Invalid Credentials')

        response.raise_for_status()
        
        try:
            storage_options = json.loads(response.content)['storage']
        except ValueError:
            raise errors.StorageURLNotFound("Could not parse services JSON.")

        self.auth_token = response.headers['x-auth-token']
        self.storage_url = self.get_storage_url(storage_options)
        self.auth_headers = {'X-Auth-Token': self.auth_token}
        if not self.storage_url:
            self.storage_url = response.headers['x-storage-url']
            raise errors.StorageURLNotFound("Could not find defined storage URL. Using default.")
        if not self.auth_token or not self.storage_url:
            raise errors.AuthenticationError('Invalid Authentication Response')
