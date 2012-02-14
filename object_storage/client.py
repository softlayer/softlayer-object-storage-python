"""
    Client module. Contains the primary interface for the client.

    See COPYING for license information.
"""
try:
    import simplejson as json
except ImportError:
    import json

try:
    from object_storage.transport.httplib2conn import AuthenticatedConnection, Authentication
except ImportError:
    try:
        from object_storage.transport.requestsconn import AuthenticatedConnection, Authentication
    except ImportError:
        from object_storage.transport.twist import AuthenticatedConnection, Authentication

from object_storage.container import Container
from object_storage.object import Object
from object_storage.node import Node
from object_storage.utils import unicode_quote

from object_storage import consts
from object_storage import errors

import logging
logger = logging.getLogger(__name__)

class Client(Node):
    """
        Client class. Primary interface for the client.
    """
    type = 'account'
    property_names = ['size', 'count']
    meta_prefixes = ['meta_']
    property_mappings = {
            'x-account-object-count': 'object_count',
            'x-account-container-count': 'count',
            'x-account-bytes-used': 'size',
            'count': 'count',
            'size': 'size',
        }
    
    def __init__(self, username=None, api_key=None, **kwargs):
        self.size = None
        self.count = None
        self.object_count = None
        self.username = username
        self.api_key = api_key
        self.delimiter = kwargs.get('delimiter', '/')

        self.container_class = kwargs.get('container_class', Container)
        self.object_class = kwargs.get('object_class', Object)
        
        self.storage_url = None
        auth_url = kwargs.get('auth_url', consts.SL_AUTH_URL)
        
        self.conn = kwargs.get('connection', None)
        if not self.conn:
            auth = kwargs.get('auth', Authentication(username, api_key, auth_url=auth_url))
            self.conn = AuthenticatedConnection(auth)

        super(Client, self).__init__()

    def search(self, query=None, **kwargs):
        """
            Access the search interface.
        """
        default_params = {
                    'q': query,
                    'format': 'json',
                 }
        params = {}
        for key, val in kwargs.iteritems():
            if key.startswith('q_'):
                params["q.%s" % key[2:]] = val
            else:
                params[key] = val
        params = dict(default_params.items() + params.items())
        headers = {'X-Context': 'search'}
        path = None
        if kwargs.has_key('container'):
            path = [kwargs['container']]
        if kwargs.has_key('path'):
            path = kwargs['path']
        def _formatter(response):
            """
                Formats search results.
            """
            headers = response.headers
            content = response.content
            items = json.loads(content)
            objs = []
            for item in items:
                if 'type' not in item or item['type'] == 'container':
                    objs.append(self.container(item['name'], properties=item))
                elif item['type'] == 'object':
                    obj = self.object(item['container'],
                                      item['name'],
                                      properties=item)
                    objs.append(obj)
            count = int(headers.get('x-search-items-count', 0))
            total = int(headers.get('x-search-items-total', 0))
            return {'count': count, 'total': total, 'results': objs}
        return self.make_request('GET', path, headers=headers, 
                                             params=params,
                                             formatter=_formatter)

    def set_delimiter(self, delimiter):
        """
            Sets the delimiter for pseudo hierarchical directory structure. 
        """
        self.delimiter = delimiter

    def set_storage_url(self, url):
        """
            Sets the storage URL. After authentication, the URL is automatically 
            populated, but the default value can be overwritten.
        """
        self.storage_url = url

    def container(self, name, properties=None):
        """ Makes a container object. """
        return self.container_class(name, properties=properties, client=self)

    def get_container(self, name):
        """ 
            Makes a container object and calls load() on it. 
            Can raise ResponseError
        """
        return self.container(name).load()
    
    def create_container(self, name):
        """ 
            Makes a container object and calls create() on it. CAn raise ResponseError
        """
        return self.container(name).create()
    
    def delete_container(self, name, recursive=False):
        """ 
            Deletes a container. 
            will raise ContainerNotEmpty if the container isn't empty 
        """
        params = {}
        if recursive:
            params['recursive'] = True
        def _formatter(res):
            if res.status_code is 409:
                raise errors.ContainerNotEmpty(name)
            return True

        return self.make_request('DELETE', [name], params=params, formatter=_formatter)
    
    def list_containers(self, marker=None, headers=None):
        """ Will list all containers in the account """
        params = {'format': 'json'}
        if marker:
            params['marker'] = marker
        def _formatter(res):
            containers = []
            if res.content:
                items = json.loads(res.content)
                for item in items:
                    name = item.get('name', None)
                    containers.append(self.container(name, item))
            return containers
        return self.make_request('GET', params=params, headers=headers, formatter=_formatter)
    list = list_containers

    def list_cdn_containers(self, *args, **kwargs):
        kwargs['headers'] = {'X-Context': 'cdn'}
        return self.list_containers(*args, **kwargs)
    list_cdn = list_cdn_containers
    
    def is_dir(self):
        """ Returns whether or not this is a directory. Always True. """
        return True

    @property
    def path(self):
        """ Returns the file-path. Always returns an empty string. """
        return ''
    
    @property
    def url(self):
        """ Returns the url of the resource. """
        return self.get_url()

    def object(self, container, name, properties=None):
        """ Creates a storage object... object. """
        return self.object_class(container, name, 
                                properties=properties, client=self)
        
    def get_object(self, container, name):
        """ Creates a storage object and calls load() on it """
        return self.object(container, name).load()
    
    def delete_object(self, container, obj):
        """ Deletes object """
        return self.make_request('DELETE', [container, obj], formatter=lambda r: True)

    def get_url(self, path=None):
        """ 
            Returns the url to a resource at the given path. The path can be a list
            of strings or a string.
        """
        url = self.storage_url
        if not url:
            self.storage_url = self.conn.storage_url
            url = self.storage_url
        if path:
            if isinstance(path, list):
                path = "/".join(map(unicode_quote, path))
            url = "%s/%s" % (url, path)
        return url

    @classmethod
    def get_path(cls, parts=None):
        """ 
            Returns the path to a resource. Parts can be a list of strings or 
            a string.
        """
        path = parts
        if parts:
            if isinstance(parts, list):
                path = "/".join(map(unicode_quote, parts))
        return path

    def make_request(self, method, path=None, *args, **kwargs):
        """ Makes a request on a resource. """
        url = self.get_url(path)
        result = self.conn.make_request(method, url, *args, **kwargs)
        return result

    def get_chunkable(self, path, headers=None):
        """ Returns a chunkable connection object at the given path. """
        url = self.get_url(path)
        return self.conn.get_chunkable(url, headers)

    def __getitem__(self, name):
        """ Returns a container object with the given name """
        return self.container(name)
