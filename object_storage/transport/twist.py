"""
    Twisted connection type.

    See COPYING for license information
"""
from zope import interface

from object_storage.transport import requote_path
from object_storage.errors import NotFound
from object_storage.transport import Response, BaseAuthenticatedConnection, BaseAuthentication
from object_storage import errors

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol
from twisted.internet.ssl import ClientContextFactory
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer, UNKNOWN_LENGTH

import urlparse
import urllib

from object_storage.utils import json


def complete_request(resp, callback=None, load_body=True):
    r = Response()
    r.status_code = resp.code
    r.version = resp.version
    r.phrase = resp.phrase

    for k, v in resp.headers.getAllRawHeaders():
        r.headers[k.lower()] = v.pop()

    if r.status_code == 404:
        raise NotFound('Not found')
    r.raise_for_status()

    if not load_body:
        if callback:
            return callback(r)
        return r

    def build_response(body):
        r.content = body
        if callback:
            return callback(r)
        return r

    finished = Deferred()
    resp.deliverBody(FullBodyReader(finished))

    finished.addCallback(build_response)
    return finished


def print_error(failure):
    from twisted.web import _newclient
    if failure.check(_newclient.RequestGenerationFailed):
        for f in failure.value.reasons:
            print f.getTraceback()
    return failure


class AuthenticatedConnection(BaseAuthenticatedConnection):
    def __init__(self, auth, **kwargs):
        self.token = None
        self.storage_url = None
        self.auth = auth

    def authenticate(self):
        d = self.auth.authenticate()
        d.addCallback(lambda r: self._authenticate())
        return d

    def make_request(self, method, url=None, headers=None, *args, **kwargs):
        headers = headers or {}
        headers.update(self.get_headers())
        return make_request(method, url=url, headers=headers, *args, **kwargs)


def make_request(method, url=None, headers=None, *args, **kwargs):
    """ Makes a request """
    headers = Headers(dict([(k, [v]) for k, v in headers.items()]))

    formatter = None
    if 'formatter' in kwargs:
        formatter = kwargs.get('formatter')
        del kwargs['formatter']

    if not formatter:
        def _nothing(result):
            return result
        formatter = _nothing

    params = kwargs.get('params', None)

    if params:
        params = urllib.urlencode(params)

    url = _full_url(url, params)
    body = kwargs.get('data')

    #print method, url, headers, body

    contextFactory = WebClientContextFactory()
    agent = Agent(reactor, contextFactory)
    d = agent.request(
        method,
        url,
        headers,
        body)

    load_body = True
    if method.upper() in ['HEAD', 'DELETE']:
        load_body = False

    d.addCallback(complete_request, formatter, load_body=load_body)
    d.addErrback(print_error)
    return d


def _full_url(url, _params={}):
    """Build the actual URL to use."""

    # Support for unicode domain names and paths.
    scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)

    if not scheme:
        raise ValueError("Invalid URL %r: No schema supplied" % url)

    netloc = netloc.encode('idna')

    if isinstance(path, unicode):
        path = path.encode('utf-8')

    path = requote_path(path)

    url = str(urlparse.urlunparse([scheme, netloc, path, params, query, fragment]))

    if _params:
        if urlparse.urlparse(url).query:
            return '%s&%s' % (url, _params)
        else:
            return '%s?%s' % (url, _params)
    else:
        return url


class Authentication(BaseAuthentication):
    """
        Authentication class.
    """
    def __init__(self, username, api_key, auth_token=None, *args, **kwargs):
        super(Authentication, self).__init__(*args, **kwargs)
        self.username = username
        self.api_key = api_key
        self.auth_token = auth_token
        if self.auth_token:
            self.authenticated = True

    @property
    def auth_headers(self):
        return {'X-Auth-Token': self.auth_token}

    def _authenticate(self, response):
        if response.status_code == 401:
            raise errors.AuthenticationError('Invalid Credentials')

        response.raise_for_status()

        try:
            storage_options = json.loads(response.content)['storage']
        except ValueError:
            raise errors.StorageURLNotFound("Could not parse services JSON.")

        self.auth_token = response.headers.get('x-auth-token', 'huh?')
        self.storage_url = self.get_storage_url(storage_options)
        if not self.storage_url:
            self.storage_url = response.headers['x-storage-url']
            raise errors.StorageURLNotFound("Could not find defined storage URL. Using default.")
        if not self.auth_token or not self.storage_url:
            raise errors.AuthenticationError('Invalid Authentication Response')

    def authenticate(self):
        """ Does authentication """
        headers = {'X-Storage-User': self.username,
                   'X-Storage-Pass': self.api_key,
                   'Content-Length': '0'}
        d = make_request('GET', self.auth_url, headers=headers)
        d.addCallback(self._authenticate)
        return d


class WebClientContextFactory(ClientContextFactory):
    def getContext(self, hostname, port):
        return ClientContextFactory.getContext(self)


class FullBodyReader(Protocol):
    def __init__(self, finished):
        self.finished = finished
        self.body = ''

    def dataReceived(self, data):
        self.body += data

    def connectionLost(self, reason):
        self.finished.callback(self.body)


class ChunkedConnection:
    """
        Chunked Connection class.
        setup() will initiate a HTTP connection.
        send_chunk() will send more data.
        finish() will end the request.
    """
    def __init__(self, conn, url, headers=None, size=None):
        self.conn = conn
        self.url = url
        self.req = None
        self.headers = headers
        self.started = Deferred()
        self.size = size
        self.body = ChunkedStreamProducer(self.started, self.size)

    def setup(self, size=None):
        """
            Sets up the connection. Will optionally accept a size or
            else will use a chunked Transfer-Encoding.
        """
        if size:
            self.size = size
        if not self.size:
            self.size = UNKNOWN_LENGTH
        self.body.length = self.size
        req = self.conn.make_request('PUT', self.url, headers=self.headers, data=self.body)
        self.req = req
        print "ChunkedTwistedConnection: STARTED REQUEST"

    def send_chunk(self, chunk):
        """ Sends a chunk of data. """
        print "ChunkedTwistedConnection: send chunk"
        return self.body.send(chunk)

    def finish(self):
        """ Finished the request out and receives a response. """
        self.body.finish()


class ChunkedStreamProducer(object):
    interface.implements(IBodyProducer)

    def __init__(self, started, length=UNKNOWN_LENGTH):
        self.length = length
        self.consumer = None
        self.started = Deferred()
        self.finished = Deferred()

    def startProducing(self, consumer):
        print "ChunkedStreamProducer: START PRODUCING"
        self.consumer = consumer
        self.started.callback(None)
        return self.finished

    def _send(self, result, data):
        print "ChunkedStreamProducer: _SEND"
        return self.consumer.write(data)

    def send(self, data):
        print "ChunkedStreamProducer: SEND"
        d = Deferred()
        self.started.chainDeferred(d)
        d.addCallback(self._send, data)
        return d

    def finish(self):
        def _finish(result):
            self.finished.callback(None)
            return None
        d = Deferred()
        self.started.chainDeferred(d)
        d.addCallback(_finish)
        return d

    def pauseProducing(self):
        print "pause"
        pass

    def stopProducing(self):
        print "STOP"
        pass
