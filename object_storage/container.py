"""
    Container module

    See COPYING for license information
"""
import json
import os
from object_storage.object import Object
from object_storage.node import Node

class Container(Node):
    """ Container class. Encapsulates Storage containers. """
    type = 'container'
    property_names = ['name', 'size', 'count']
    meta_prefixes = ['meta_', 'x-container-meta-']
    property_mappings = {
            'x-container-object-count': 'count',
            'x-container-bytes-used': 'size',
            'x-container-read': 'read',
            'x-container-write': 'write',
            'count': 'count',
            'size': 'size',
            'date': 'date',
            'x-cdn-ttl': 'ttl',
        }

    def __init__(self, name, properties=None, client=None): 
        self.name = name
        self.size = self.count = self.read = self.write = None
        self.meta = {}

        if properties:
            self._process_props(properties)

        self.client = client

        self._cdn_url = None
        self._cdn_ssl_url = None

        self.ttl = None

        super(Container, self).__init__()

    def create(self):
        """ Creates container """
        def _formatter(res):
            return self
        return self.make_request('PUT', formatter=_formatter)

    def _headers(self):
        """ Returns a dict of all of the known header values for an object. """
        headers = {}
        for key, value in self.meta.iteritems():
            headers['X-Container-Meta-' + key] = value
        if self.read:
            headers['X-Container-Read'] = self.read
        if self.write:
            headers['X-Container-Write'] = self.write
        if self.ttl:
            headers['X-Cdn-Ttl'] = str(self.ttl)

        return headers
        
    def delete(self, recursive=False):
        """ Delete container """
        #if recursive:
        #    self.delete_all_objects()
        return self.client.delete_container(self.name, recursive=recursive)
        
    def delete_all_objects(self):
        """ Delete all objects in container """
        resps = []
        for item in self.list():
            resps.append(item.delete())
        return resps
        
    def delete_object(self, obj):
        """ Delete object in the container """
        if isinstance(obj, Object):
            obj = obj.name
        return self.client.delete_object(self.name, obj)

    def rename(self, new_container):
        """ Rename container. Will not work if container is not empty. """
        self.delete()
        new_container.create()

    def list(self, limit=None, marker=None, base_only=False, headers=None):
        """ Lists objects in the container.  """
        params = {'format': 'json'}
        if base_only:
            params['delimiter'] = '/'
        if limit:
            params['limit'] = limit
        if marker:
            params['marker'] = marker

        def _formatter(res):
            objects = []
            if res.content:
                items = json.loads(res.content)
                for item in items:
                    if 'name' in item:
                        objects.append(self.object(item['name'], item))
            return objects

        return self.make_request('GET', params=params, headers=headers, formatter=_formatter)

    def enable_cdn(self, ttl=1440):
        self.read = '.r:*'
        self.ttl = ttl
        return self.save_headers()

    def disable_cdn(self):
        self.read = ' '
        self.ttl = None
        return self.save_headers()

    def search(self, *args, **kwargs):
        """ Search within container. """
        return self.client.search(*args, path=self.name, **kwargs)

    def get_object(self, name):
        """ Calls get_object() on the client. """
        return self.client.get_object(self.name, name)

    def object(self, name, properties=None):
        """ Creates a new instance of Object """
        return self.client.object(self.name, name, properties=properties)
        
    def load_from_filename(self, filename):
        """ Creates an object from a file. Uses the basename of the file path as the object name. """
        name = os.path.basename(filename)
        return self.object(name).load_from_filename(filename)

    @property
    def path(self):
        """ returns path of the container """
        path = [self.name]
        return self.client.get_path(path)


    def _get_cdn_urls(self, callback=None):
        def _formatter(res):
            self._cdn_url = res.headers.get('x-cdn-url', None)
            self._cdn_ssl_url = res.headers.get('x-cdn-ssl-url', None)
            if callback:
                return callback()
        return self.make_request('HEAD', headers={'X-Context': 'cdn'}, formatter=_formatter)

    @property
    def cdn_url(self):
        if self._cdn_url is None:
            def cb():
                return self._cdn_url
            self._get_cdn_urls(callback=cb)
        return self._cdn_url

    @property
    def cdn_ssl_url(self):
        if self._cdn_ssl_url is None:
            def cb():
                return self._cdn_ssl_url
            self._get_cdn_urls(callback=cb)
        return self._cdn_ssl_url

    @property
    def url(self):
        """ Returns the url of the container """
        path = [self.name]
        return self.client.get_url(path)

    def is_dir(self):
        """ Returns if the container is a directory (always True) """
        return True

    def make_request(self, method, path=None, *args, **kwargs):
        """ Makes a request on the resource. """
        path = [self.name]
        return self.client.make_request(method, path, *args, **kwargs)
    
    def __getitem__(self, name):
        """ Returns object corresponding to the given name """
        return self.object(name)
        
    def __str__(self):
        return self.name
        
    def __repr__(self):
        return 'Container({0})'.format(self.name.encode("utf-8"))
