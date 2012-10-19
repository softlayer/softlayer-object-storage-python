"""
    Client module. Contains the primary interface for the client.

    See COPYING for license information.
"""
from object_storage.utils import json, Model

from object_storage.container import Container
from object_storage.storage_object import StorageObject
from object_storage.utils import get_path

from object_storage import errors

import logging
logger = logging.getLogger(__name__)


class AccountModel(Model):
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
    def __init__(self, username=None,
                       api_key=None,
                       connection=None,
                       delimiter='/',
                       **kwargs):
        """ constructor for Client object

        @param username: the username
        @param api_key: api_key for Object Storage
        @param connection: `object_storage.transport.AuthenticatedConnection`
            instance.
        @param delimiter: the symbol to use to divid up hiearchical divisions
            for objects.
        @param container_class: factory or class for Container constructing
        @param object_class: factory or class for StorageObject constructing
        """
        self.username = username
        self.api_key = api_key
        self.delimiter = delimiter
        self.container_class = kwargs.get('container_class', Container)
        self.object_class = kwargs.get('object_class', StorageObject)
        self.storage_url = None
        self.conn = connection

        self.model = None

    def load(self, cdn=True):
        """ load data for the account

        @return: object_storage.client, self
        """
        def _formatter(res):
            self.model = AccountModel(self, res.headers)
            return self
        return self.make_request('HEAD', formatter=_formatter)

    def get_info(self):
        """ loads data if not already available and returns the properties """
        if not self.model:
            self.load()
        return self.model.properties

    @property
    def properties(self):
        """ loads data if not already available and returns the properties """
        return self.get_info()
    props = properties

    @property
    def headers(self):
        """ loads data if not already available and returns the raw headers for the account """
        if not self.model:
            self.load()
        return self.model.headers

    @property
    def meta(self):
        """ loads data if not already available and returns the metadata for the account """
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

    def search(self, q, options=None, **kwargs):
        """ Access the search interface.
        @param q: the search query. This can be None.
        @param options: options for the search API. Valid options:
            q.[fieldname] -> define search query for a specific field.
            field         -> field name (when using q)
            type          -> 'object' or 'container'; default shows both.
            recursive     -> whether to search recursively or to limit to
                             one level; default=true
        @param **kwargs: to be merged into the options param.
            Provides a nicer interface for the same thing.

        More information on options:
            http://sldn.softlayer.com/article/API-Operations-Search-Services
        """
        default_params = {
                    'format': 'json',
                    'q': q
                 }
        params = {}
        options = options or {}
        options.update(kwargs)
        for key, val in options.iteritems():
            if key.startswith('q_'):
                params["q.%s" % key[2:]] = val
            else:
                params[key] = val
        params = dict(default_params.items() + params.items())
        headers = {'X-Context': 'search'}
        _path = None
        if 'container' in options:
            _path = [options['container']]
        if 'path' in options and type(options['path']) is not dict:
            _path = [options['path']]

        def _formatter(response):
            """ Formats search results. """
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
        """ Sets the delimiter for pseudo hierarchical directory structure.
        @param delimiter: delimiter to use
        """
        self.delimiter = delimiter

    def set_storage_url(self, url):
        """ Sets the storage URL. After authentication, the URL is automatically
        populated, but the default value can be overwritten.

        @param url: url to use to call the Object Storage API.
        """
        self.storage_url = url

    def container(self, name, headers=None):
        """ Initializes container object.

        @param name: name of the container
        @param headers: initial headers to use to initialize the object
        """
        return self.container_class(name, headers=headers, client=self)

    def get_container(self, name):
        """ Makes a container object and calls load() on it.
        @param name: container name
        @raises ResponseError
        """
        return self.container(name).load()

    def set_metadata(self, meta, headers={}):
        """ Sets metadata for the account

        @param meta: dict of metadata on the account
        @raises ResponseError
        """
        meta_headers = {}
        for k, v in headers.iteritems():
            meta_headers[k] = v
        for k, v in meta.iteritems():
            meta_headers["x-account-meta-%s" % (k, )] = v
        self.make_request('POST', headers=meta_headers)

    def create_container(self, name):
        """ Creates a new container

        @param name: container name
        @raises ResponseError
        """
        return self.container(name).create()

    def delete_container(self, name, recursive=False):
        """ Deletes a container.

        @param name: container name
        @raises ResponseError
        @raises ContainerNotEmpty if container is not empty
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
        """ Lists containers

        @param marker: start listing after this container name
        @param headers: extra headers to use when making the listing call
        @raises ResponseError
        """
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
        """ Lists public containers. Same interface as self.containers()

        @raises ResponseError
        """
        kwargs['headers'] = {'X-Context': 'cdn'}
        return self.containers(*args, **kwargs)

    def storage_object(self, container, name, headers=None):
        """ Initialize a StorageObject instance

        @param container: container name
        @param name: object name
        @param headers: initial headers to use to initialize the object
        """
        return self.object_class(container, name,
                                headers=headers, client=self)

    def get_object(self, container, name):
        """ Load an object from swift

        @param container: container name
        @param name: object name
        @raises ResponseError
        """
        return self.storage_object(container, name).load()

    def delete_object(self, container, name):
        """ Delete an object from swift

        @param container: container name
        @param name: object name
        @raises ResponseError
        """
        return self.make_request('DELETE', [container, name], formatter=lambda r: True)

    def get_url(self, path=None):
        """ Returns the url of the resource

        @param path: path to append to the end of the URL
        """
        url = self.storage_url
        if not url:
            self.storage_url = self.conn.storage_url
            url = self.storage_url
        if path:
            url = "%s/%s" % (url, get_path(path))
        return url

    def make_request(self, method, path=None, *args, **kwargs):
        """ Make an HTTP request

        @param method: HTTP method (GET, HEAD, POST, PUT, ...)
        @param path: path
        @raises ResponseError
        """
        url = self.get_url(path)
        result = self.conn.make_request(method, url, *args, **kwargs)
        return result

    def chunk_download(self, path, chunk_size=10 * 1024, headers=None):
        """ Returns a chunk download generator

        @param path: path
        @param chunk_size: the max size in bytes to return on each yield
        @param headers: extra headers to use with this request
        @raises ResponseError
        """
        url = self.get_url(path)
        return self.conn.chunk_download(url, chunk_size=chunk_size)

    def chunk_upload(self, path, size=None, headers=None):
        """ Returns a chunkable connection object at the given path

        @param path: path
        @param headers: extra headers to use with this request
        @raises ResponseError
        """
        url = self.get_url(path)
        return self.conn.chunk_upload('PUT', url, size=size, headers=headers)

    def __getitem__(self, name):
        """ Returns a container object with the given name """
        return self.container(name)

    def __iter__(self):
        """ Returns an interator based on results of self.containers() """
        listing = self.containers()
        for obj in listing:
            yield obj
