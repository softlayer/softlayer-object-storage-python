"""
    Connection Module

    See COPYING for license information
"""
from urlparse import urlparse
import urllib
from object_storage import consts
from object_storage import errors
from object_storage.transport import BaseAuthentication, BaseAuthenticatedConnection, Response
import httplib2

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
    def __init__(self, auth, debug=False, **kwargs):
        if debug:
            httplib2.debuglevel=4
        self.token = None
        self.storage_url = None
        self.http = httplib2.Http(disable_ssl_certificate_validation=True)
        self.auth = auth
        self.auth.authenticate()
        self._authenticate()
        
    def make_request(self, method, url=None, headers=None, formatter=None, params=None, data=None, *args, **kwargs):
        """ Makes a request """
        headers = headers or {}
        headers.update(self.get_headers())

        if params:
            url = "%s?%s" % (url, urllib.urlencode(params))
        
        def _make_request(headers):
            res, content = self.http.request(url, method, headers=headers, body=data)
            response = Response()
            response.headers = res
            response.status_code = int(res.status)
            response.content = content
            return response

        response = _make_request(headers)

        if response.status_code == 401:
            self._authenticate()
            headers.update(self.auth_headers)
            response = _make_request(headers)
        
        response.raise_for_status()
        
        if formatter:
            return formatter(response)
        return response
    
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
        http = httplib2.Http(disable_ssl_certificate_validation=True)
        res, content = http.request(self.auth_url, 'GET', headers=headers)
        response = Response()
        response.headers = res
        response.status_code = int(res.status)
        response.content = content

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
