"""
    Client module. Contains the primary interface for the client.

    See COPYING for license information.
"""
try:
    import simplejson as json
except ImportError:
    import json

from object_storage.container import Container
from object_storage.storage_object import StorageObject
from object_storage.utils import get_path

from object_storage import errors

import logging
import UserDict
logger = logging.getLogger(__name__)

class AccountModel(UserDict.UserDict):
    def __init__(self, controller, headers={}):
        _headers = {}

        # Lowercase headers
        for key, value in headers.iteritems():
            _key = key.lower()
            _headers[_key] = value
        self.headers = _headers
        self._meta = None

        _properties = {}
        
        _properties['container_count'] = int(self.headers.get('x-account-container-count') or\
                                             self.headers.get('count') or 0)
        _properties['object_count'] = int(self.headers.get('x-account-object-count') or\
                                          self.headers.get('object_count') or 0)
        _properties['size'] = int(self.headers.get('x-account-bytes-used') or\
                                  self.headers.get('size') or 0)

        _properties['path'] = controller.path
        _properties['url'] = controller.url

        meta = {}
        for key, value in self.headers.iteritems():
            if key.startswith('meta_'):
                meta[key[5:]] = value
            elif key.startswith('x-account-meta-'):
                meta[key[15:]] = value
        self.meta = meta
        _properties['meta'] = self.meta

        self.properties = _properties
        self.data = self.properties

class Client(object):
    """
        Client class. Primary interface for the client.
    """
    def __init__(self, username=None, api_key=None, connection=None, **kwargs):
        self.username = username
        self.api_key = api_key
        self.delimiter = kwargs.get('delimiter', '/')
        self.container_class = kwargs.get('container_class', Container)
        self.object_class = kwargs.get('object_class', StorageObject)
        self.storage_url = None
        self.conn = connection

        self.model = None

    def load(self):
        def _formatter(res):
            self.model = AccountModel(self, res.headers)
            return self
        return self.make_request('HEAD', formatter=_formatter)

    def get_info(self):
        if not self.model:
            self.load()
        return self.model.properties

    @property
    def properties(self):
        return self.get_info()
    props = properties

    @property
    def headers(self):
        if not self.model:
            self.load()
        return self.model.headers

    @property
    def meta(self):
        if not self.model:
            self.load()
        return self.model.meta

    @property
    def path(self):
        """ Returns the file-path. Always returns an empty string. """
        return ''

    @property
    def url(self):
        """ Returns the url of the resource. """
        return self.get_url()

    def is_dir(self):
        """ Returns whether or not this is a directory. Always True. """
        return True

    def search(self, options={}):
        """
            Access the search interface.
        """
        default_params = {
                    'format': 'json',
                 }
        params = {}
        for key, val in options.iteritems():
            if key.startswith('q_'):
                params["q.%s" % key[2:]] = val
            else:
                params[key] = val
        params = dict(default_params.items() + params.items())
        headers = {'X-Context': 'search'}
        _path = None
        if options.has_key('container'):
            _path = [options['container']]
        if 'path' in options and type(options['path']) is not dict:
            _path = [options['path']]
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
                    objs.append(self.container(item['name'], headers=item))
                elif item['type'] == 'object':
                    obj = self.storage_object(item['container'],
                                      item['name'],
                                      headers=item)
                    objs.append(obj)
            count = int(headers.get('x-search-items-count', 0))
            total = int(headers.get('x-search-items-total', 0))
            return {'count': count, 'total': total, 'results': objs}
        return self.make_request('GET', _path, headers=headers, 
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

    def container(self, name, headers=None):
        """ Makes a container object. """
        return self.container_class(name, headers=headers, client=self)

    def get_container(self, name):
        """ 
            Makes a container object and calls load() on it. 
            Can raise ResponseError
        """
        return self.container(name).load()

    def set_metadata(self, meta):
        meta_headers = {}
        for k, v in meta.iteritems():
            meta_headers["x-account-meta-{0}".format(k)] = v
        self.make_request('POST', headers=meta_headers)
    
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
    
    def containers(self, marker=None, headers=None):
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

    def public_containers(self, *args, **kwargs):
        kwargs['headers'] = {'X-Context': 'cdn'}
        return self.containers(*args, **kwargs)

    def storage_object(self, container, name, headers=None):
        """ Creates a storage object... object. """
        return self.object_class(container, name, 
                                headers=headers, client=self)
        
    def get_object(self, container, name):
        """ Creates a storage object and calls load() on it """
        return self.storage_object(container, name).load()
    
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
            url = "%s/%s" % (url, get_path(path))
        return url

    def make_request(self, method, path=None, *args, **kwargs):
        """ Makes a request on a resource. """
        url = self.get_url(path)
        result = self.conn.make_request(method, url, *args, **kwargs)
        return result

    def chunk_download(self, path, chunk_size=10*1024, headers=None):
        url = self.get_url(path)
        return self.conn.chunk_download(url, chunk_size=chunk_size)

    def chunk_upload(self, path, headers=None):
        """ Returns a chunkable connection object at the given path. """
        url = self.get_url(path)
        return self.conn.chunk_upload('PUT', url, headers)

    def __getitem__(self, name):
        """ Returns a container object with the given name """
        return self.container(name)

    def __iter__(self):
        """ Returns an interator based on results of self.containers() """
        listing = self.containers()
        for obj in listing:
            yield obj
