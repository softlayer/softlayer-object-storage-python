"""
    Container module

    See COPYING for license information
"""
import os
from object_storage.utils import json, Model
from object_storage import errors
from object_storage.storage_object import StorageObject
from object_storage.utils import get_path


class ContainerModel(Model):
    def __init__(self, controller, name, headers={}):
        self.name = name
        _headers = {}

        # Lowercase headers
        for key, value in headers.iteritems():
            _key = key.lower()
            _headers[_key] = value
        self.headers = _headers
        self._meta = None

        _properties = {'name': self.name}

        _properties['count'] = int(self.headers.get('x-container-object-count') or\
                                   self.headers.get('count') or 0)
        _properties['object_count'] = _properties['count']
        _properties['size'] = int(self.headers.get('x-container-bytes-used') or\
                                  self.headers.get('size') or 0)
        _properties['read'] = self.headers.get('x-container-read') or\
                              self.headers.get('read')
        _properties['write'] = self.headers.get('x-container-read') or\
                               self.headers.get('read')
        _properties['ttl'] = int(self.headers.get('x-cdn-ttl') or 0)
        _properties['date'] = self.headers.get('date')
        _properties['cdn_url'] = self.headers.get('x-cdn-url')
        _properties['cdn_ssl_url'] = self.headers.get('x-cdn-ssl-url')

        _properties['path'] = controller.path
        _properties['url'] = controller.url

        meta = {}

        for key, value in self.headers.iteritems():
            if key.startswith('meta_'):
                meta[key[5:]] = value
            elif key.startswith('x-container-meta-'):
                meta[key[17:]] = value
        self.meta = meta
        _properties['meta'] = self.meta

        self.properties = _properties
        self.data = self.properties


class Container:
    """ Container class. Encapsulates Storage containers. """
    def __init__(self, name, headers=None, client=None):
        """ constructor for Container

        @param name: container name
        @param headers: init headers to use when initializing the container
        @param client: `object_storage.client` instance.
        """
        self.name = name
        self.client = client
        self.model = None
        if headers:
            self.model = ContainerModel(self, self.name, headers)

    def exists(self):
        """ Tries to load the container to check existance

        @raises ResponseError
        @return: boolean, true if exists else false
        """
        def _formatter(res):
            self.model = ContainerModel(self, self.name, res.headers)
            return True
        try:
            return self.make_request('HEAD', formatter=_formatter)
        except errors.NotFound:
            return False

    def load(self, cdn=True):
        """ load data for the container

        @param cdn: True if you want CDN information; default=True
        @return: object_storage.container, self
        """
        headers = {}
        if cdn:
            headers.setdefault('X-Context', 'cdn')

        def _formatter(res):
            self.model = ContainerModel(self, self.name, res.headers)
            return self
        return self.make_request('HEAD', headers=headers, formatter=_formatter)

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
        """ loads data if not already available and returns the raw headers for the container """
        if not self.model:
            self.load()
        return self.model.headers

    @property
    def meta(self):
        """ loads data if not already available and returns the metadata for the container """
        if not self.model:
            self.load()
        return self.model.meta

    @property
    def path(self):
        """ returns path of the container """
        path = [self.name]
        return get_path(path)

    @property
    def url(self):
        """ Returns the url of the container """
        path = [self.name]
        return self.client.get_url(path)

    def is_dir(self):
        """ Returns if the container is a directory (always True) """
        return True

    def set_metadata(self, meta):
        """ Sets metadata for the container

        @param meta: dict of metadata on the container
        @raises ResponseError
        """
        meta_headers = {}
        for k, v in meta.iteritems():
            meta_headers["x-container-meta-%s" % (k, )] = v
        return self.make_request('POST', headers=meta_headers)

    def create(self):
        """ Create container

        @raises ResponseError
        @return: Containert - self
        """
        def _formatter(res):
            return self
        return self.make_request('PUT', formatter=_formatter, headers={'Content-Length': '0'})

    def delete(self, recursive=False):
        """ Delete container

        @param recursive: true if you want to delete all of the
            objects in the container as well.
        @raises ResponseError
        @return: True
        """
        return self.client.delete_container(self.name, recursive=recursive)

    def delete_all_objects(self):
        """ Deletes all objects in the container

        @raises ResponseError
        """
        resps = []
        for item in self.objects():
            resps.append(item.delete())
        return resps

    def delete_object(self, obj):
        """ Deletes an object in the container

        @param obj: object name to delete
        @raises ResponseError
        """
        if isinstance(obj, StorageObject):
            obj = obj.name
        return self.client.delete_object(self.name, obj)

    def rename(self, new_container):
        """ Rename container. Will not work if container is not empty.

        @param new_container: new container name
        @raises ResponseError
        """
        self.delete()
        new_container.create()

    def objects(self, limit=None, marker=None, base_only=False, headers=None):
        """ Lists objects in the container.

        @param limit: limit of results to return.
        @param marker: start listing after this object name
        @param base_only: only return the base objects.
            container/object not container/dir/object
        @param headers: extra headers to use in the request
        @raises ResponseError
        @return: list of StorageObject instances
        """
        params = {'format': 'json'}
        if base_only:
            params['delimiter'] = self.client.delimiter
        if limit:
            params['limit'] = limit
        if marker:
            params['marker'] = marker

        def _formatter(res):
            objects = {}
            if res.content:
                items = json.loads(res.content)
                for item in items:
                    if 'name' in item:
                        objects[item['name']] = self.storage_object(item['name'], item)
                    elif 'subdir' in item:
                        item['name'] = item['subdir'].rstrip('/')
                        item['content_type'] = 'application/directory'
                        objects[item['name']] = self.storage_object(item['name'], item)
            return objects.values()
        return self.make_request('GET', params=params, headers=headers, formatter=_formatter)

    def set_ttl(self, ttl):
        """ Set time to live for CDN

        @param ttl: time in seconds to set as the TTL
        @raises ResponseError
        """
        if not ttl:
            ttl = ' '
        headers = {'x-cdn-ttl': str(ttl)}
        return self.make_request('POST', headers=headers)

    def set_read_acl(self, acl):
        """ Set read ACL

        @param acl: ACL to set for the container
        @raises ResponseError
        """
        headers = {'x-container-read': acl}
        return self.make_request('POST', headers=headers)

    def set_write_acl(self, acl):
        """ Set write ACL

        @param acl: ACL to set for the container
        @raises ResponseError
        """
        headers = {'x-container-write': acl}
        return self.make_request('POST', headers=headers)

    def make_public(self, ttl=1440):
        """ Make container public

        @param ttl: time in seconds to set as the TTL
        @raises ResponseError
        """
        headers = {'x-container-read': '.r:*', 'x-cdn-ttl': str(ttl)}
        return self.make_request('POST', headers=headers)
    enable_cdn = make_public

    def make_private(self):
        """ Make container private (empty ACL)

        @raises ResponseError
        """
        headers = {'x-container-read': ' '}
        return self.make_request('POST', headers=headers)
    disable_cdn = make_private

    def search(self, q, options=None, **kwargs):
        """ Search within container. """
        options = options or {}
        options.update({'path': self.name})
        return self.client.search(q, options=options, **kwargs)

    def get_object(self, name):
        """ Calls get_object() on the client. """
        return self.client.get_object(self.name, name)

    def storage_object(self, name, headers=None):
        """ Creates a new instance of Object """
        return self.client.storage_object(self.name, name, headers=headers)

    def load_from_filename(self, filename):
        """ Creates an object from a file. Uses the basename of the file path as the object name. """
        name = os.path.basename(filename)
        return self.storage_object(name).load_from_filename(filename)

    def make_request(self, method, path=None, *args, **kwargs):
        """ Makes a request on the resource. """
        path = [self.name]
        return self.client.make_request(method, path, *args, **kwargs)

    def __getitem__(self, name):
        """ Returns object corresponding to the given name """
        return self.storage_object(name)

    def __str__(self):
        return self.name

    def __repr__(self):
        return 'Container(%s)' % (self.name.encode("utf-8"), )

    def __iter__(self):
        """ Returns an interator based on results of self.objects() """
        listing = self.objects()
        for obj in listing:
            yield obj
