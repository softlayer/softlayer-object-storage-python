"""
    Object module

    See COPYING for license information
"""
import json
import mimetypes
import os
import StringIO

from object_storage.node import Node

class Object(Node):
    """ 
        Representation of a Object Storage object.
    """
    type = 'object'
    property_names = ['container', 'name', 'content_type', 
                      'last_modified', 'size', 'hash', 
                      'manifest', 'content_encoding']
    meta_prefixes = ['meta_', 'x-object-meta-']
    property_mappings = {
            'content_type': 'content_type',
            'content-type': 'content_type',
            'last_modified': 'last_modified',
            'last-modified': 'last_modified',
            'content-length': 'size',
            'size': 'size',
            'bytes': 'size',
            'hash': 'hash',
            'etag': 'hash',
            'date': 'date',
            'x-object-manifest': 'manifest',
            'content-encoding': 'content_encoding',
            'content_encoding': 'content_encoding',
            'Cache-Control': 'cache_control',
        }

    def __init__(self, container, name, properties=None, client=None):
        self.container = container
        self.name = name
        self.content_type = None
        self.last_modified = None
        self.size = None
        self.hash = None
        self.manifest = None
        self.content_encoding = None
        self.cache_control = None
        self.meta = {}
        
        self._cdn_url = None
        self._cdn_ssl_url = None

        if properties:
            self._process_props(properties)
        self.client = client
        super(Object, self).__init__()
    
    def list(self, limit=None, marker=None):
        """ Get list
            Uses sudo-hierarchical structure to list the children objects.

            return list(object, object, ...)
        """
        params = {'format': 'json', 
                  'path': self.name}
        if limit:
            params['limit'] = limit
        if marker:
            params['marker'] = marker
        def _formatter(res):
            objects = []
            if res.content:
                items = json.loads(res.content)
                for item in items:
                    obj = self.client.object(self.container,
                                             item['name'],
                                             properties=item)
                    objects.append(obj)
            return objects
        return self.client.make_request('GET', [self.container], params=params, formatter=_formatter)
    
    def is_dir(self):
        """ returns True if content_type is 'text/directory' """
        return self.content_type == 'text/directory'

    def create(self):
        """ Creates the object. This WILL overrite the current data if any. """
        if not self.content_type:
            self.content_type = mimetypes.guess_type(self.name)[0]
        if not self.content_type:
            self.content_type = 'text/plain'
        headers = self._headers()
        def _formatter(res):
            return self
        return self.make_request('PUT', headers=headers, formatter=_formatter)
        
    def delete(self, recursive=False):
        """ Deletes the object """
        return self.client.delete_object(self.container, self.name)
        
    def read(self, size=0, offset=0):
        """ Reads object content """
        headers = {}
        if size > 0:
            _range = 'bytes=%d-%d' % (offset, (offset + size) - 1)
            headers['Range'] = _range
        def _formatter(res):
            return res.content
        return self.make_request('GET', headers=headers, formatter=_formatter)
        
    def iter_content(self, chunk_size=10 * 1024):
        """ Returns an iterator to read the object data. """
        req = self.make_request('GET', return_response=False)
        req.send()
        res = req.response
        return res.iter_content(chunk_size=chunk_size)
        
    def send(self, data):
        """ Sends data for an object. Takes a string or an open file object. """
        if isinstance(data, file):
            try:
                data.flush()
            except IOError:
                pass
            self.size = int(os.fstat(data.fileno())[6])
        else:
            #data = StringIO.StringIO(data)
            self.size = len(data)
        
        headers = self._headers()
        
        if not self.content_type:
            _type = None
            if hasattr(data, 'name'):
                _type = mimetypes.guess_type(data.name)[0]
            self.content_type = _type or 'application/octet-stream'
        if self.size is None:
            del headers['Content-Length']
            headers['Transfer-Encoding'] = 'chunked'
        def _formatter(res):
            return True
        return self.make_request('PUT', data=data, headers=headers, formatter=_formatter)
    write = send
   
    def upload_directory(self, directory):
        """ Uploads an entire local directory. """
        directories = []
        files = []
        for root, dirnames, filenames in os.walk(directory):
            for _dir in dirnames:
                directories.append(os.path.relpath(os.path.join(root, _dir)))
            for _file in filenames:
                files.append(os.path.relpath(os.path.join(root, _file)))
                
        for _dir in directories:
            # Create a list of 'create' request objects and execute them
            obj = self.__class__(self.container, _dir, client=self.client)
            obj.content_type = 'application/directory'
            obj.create()
        
        for _file in files:
            # I expect to get a list of 'write' request objects
            obj = self.__class__(self.container, file, client=self.client)
            obj.load_from_filename(_file)
            
    def load_from_filename(self, filename):
        """ Uploads data for an object using the file contents of the file 
            corresponding to the given filename"""
        if os.path.isdir(filename):
            self.upload_directory(filename)
        else:
            with open(filename, 'rb') as _file:
                return self.send(_file)

    def copy_from(self, old_obj, *args, **kwargs):
        headers = old_obj._headers()
        headers['X-Copy-From'] = old_obj.path
        headers['Content-Length'] = "0"
        return self.make_request('PUT', headers=headers, *args, **kwargs)

    def copy_to(self, new_obj, *args, **kwargs):
        """ Issues a copy-to command """
        headers = self._headers()
        headers['Destination'] = new_obj.path
        headers['Content-Length'] = "0"
        return self.make_request('COPY', headers=headers, *args, **kwargs)

    def rename(self, new_obj, *args, **kwargs):
        """ Copies one object to a new name and deletes the old version """
        def _delete(res):
            return self.delete()
        def _copy_to(res):
            return new_obj.copy_from(self, *args, formatter=_delete, **kwargs)
        return new_obj.make_request('PUT', headers=self._headers(), formatter=_copy_to)

    def search(self, *args, **kwargs):
        """ Search within path """
        return self.client.search(*args, path=[self.container, self.name], **kwargs)

    def prime_cdn(self):
        headers = {'X-Context': 'cdn', 'X-Cdn-Load': True}
        return self.make_request('POST', headers=headers, *args, **kwargs)

    def purge_cdn(self):
        headers = {'X-Context': 'cdn', 'X-Cdn-Purge': True}
        return self.make_request('POST', headers=headers, *args, **kwargs)

    def _headers(self):
        """ Returns a dict of all of the known header values for an object. """
        headers = {}
        length = self.size or 0
        headers['Content-Length'] = str(length)
        if self.hash:
            headers['ETag'] = self.hash

        if self.content_type:
            headers['Content-Type'] = self.content_type
        else:
            headers['Content-Type'] = 'application/octet-stream'

        if self.manifest:
            headers['X-Object-Manifest'] = self.manifest
            
        if self.content_encoding:
            headers['Content-Encoding'] = self.content_encoding

        if self.cache_control:
            headers['Cache-Control'] = self.cache_control
        
        for key in self.meta:
            headers['X-Object-Meta-' + key] = self.meta[key]
        return headers

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
        """ Get the URL of the object """
        path = [self.container, self.name]
        return self.client.get_url(path)

    @property
    def path(self):
        """ Get the path of the object """
        path = [self.container, self.name]
        return self.client.get_path(path)

    def get_chunkable(self):
        """ Returns a 'chunkable' connection. This is used for chunked 
            uploading of files. This is needed for transient data uploads """
        chunkable = self.client.get_chunkable([self.container, self.name], 
                                              headers=self._headers())
        return chunkable

    def make_request(self, method, path=None, *args, **kwargs):
        """ returns a request object """
        path = [self.container, self.name]
        return self.client.make_request(method, path, *args, **kwargs)
    
    def __getitem__(self, name):
        new_name = self.client.delimiter.join([self.name, name])
        return self.client.object(self.container, new_name)
        
    def __str__(self):
        return 'Object({0}, {1})'.format(self.container.encode("utf-8"), self.name.encode("utf-8"))
    __repr__ = __str__

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass
