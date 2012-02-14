"""
    Transport Methods

    See COPYING for license information
"""

import httplib
from socket  import timeout
from urlparse import urlparse
from object_storage.errors import ResponseError, NotFound
from object_storage.utils import unicode_quote
from object_storage import consts

import urllib

class Response(object):
    def __init__(self):
        self.status_code = 0
        self.version = 0
        self.phrase = self.verb = None
        self.headers = {}
        self.content = None

    def raise_for_status(self):
        if self.status_code == 404:
            raise NotFound(self.status_code, "Not Found")
        if (self.status_code >= 300) and (self.status_code < 400):
            raise ResponseError(self.status_code, '%s Redirection' % self.status_code)
        elif (self.status_code >= 400) and (self.status_code < 500):
            raise ResponseError(self.status_code, '%s Client Error' % self.status_code)
        elif (self.status_code >= 500) and (self.status_code < 600):
            raise ResponseError(self.status_code, '%s Server Error' % self.status_code)

class BaseAuthenticatedConnection:
    def _authenticate(self):
        """ Do authentication and set token and storage_url """
        self.auth_headers = self.auth.auth_headers
        self.token = self.auth.auth_token
        self.storage_url = self.auth.storage_url

    def get_headers(self):
        """ Get default headers for this connection """
        return dict([('User-Agent', consts.USER_AGENT)] + self.auth_headers.items())

    def get_chunkable(self, url, headers=None):
        """ Returns new ChunkedConnection """
        return ChunkedConnection(self, url, headers)

class BaseAuthentication(object):
    """ 
        Base Authentication class. To be inherited if you want to create
        a new Authentication method. authenticate() should be overwritten.
    """
    def __init__(self, *args, **kwargs):
        self.storage_url = None
        self.auth_headers = {}
        self.auth_token = None

    def authenticate(self):
        """ 
            Called when the client wants to authenticate. self.storage_url and
            self.auth_token needs to be set.
        """
        self.storage_url = 'STORAGE_URL'
        self.auth_token = 'AUTH_TOKEN'
        self.auth_headers = {'X-Auth-Token': 'AUTH_TOKEN'}

class ChunkedConnection:
    """ 
        Chunked Connection class.
        setup() will initiate a HTTP connection.
        send_chunk() will send more data.
        finish() will end the request.
    """
    def __init__(self, conn, url, headers=None):
        self.conn = conn
        self.url = url
        self.req = None
        self.headers = headers

    def setup(self, size=None):
        """ 
            Sets up the connection. Will optionally accept a size or
            else will use a chunked Transfer-Encoding.
        """
        headers = self.conn.get_headers()
        headers.update(self.headers)
        if size is None:
            if 'Content-Length' in headers:
                del headers['Content-Length']
            headers['Transfer-Encoding'] = 'chunked'
        else:
            headers['Content-Length'] = str(size)

        if 'ETag' in headers:
            del headers['ETag']

        url_parts = urlparse(self.url)
        self.req = httplib.HTTPConnection(url_parts.hostname, url_parts.port)

        path = requote_path(url_parts.path)
        try:
            self.req.putrequest('PUT', path)
            for key, value in headers.iteritems():
                self.req.putheader(key, value)
            self.req.endheaders()
        except Exception, err:
            raise ResponseError(0, 'Disconnected')

    def send_chunk(self, chunk):
        """ Sends a chunk of data. """
        try:
            self.req.send("%X\r\n" % len(chunk))
            self.req.send(chunk)
            self.req.send("\r\n")
        except timeout, err:
            raise err
        except Exception, err:
            raise ResponseError(0, 'Disconnected')

    def finish(self):
        """ Finished the request out and receives a response. """
        try:
            self.req.send("0\r\n\r\n")
        except timeout, err:
            raise err

        response = self.req.getresponse()
        response.read()

        if (response.status < 200) or (response.status > 299):
           raise ResponseError(response.status, response.reason)

def requote_path(path):
    """Re-quote the given URL path component.

    This function passes the given path through an unquote/quote cycle to
    ensure that it is fully and consistently quoted.
    """
    parts = path.split("/")
    parts = (urllib.quote(urllib.unquote(part), safe="") for part in parts)
    return "/".join(parts)
