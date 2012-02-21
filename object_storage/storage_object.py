"""
    StorageObject module

    See COPYING for license information
"""
import json
import mimetypes
import os
import StringIO
import UserDict

from object_storage import errors
from object_storage.utils import get_path

class StorageObjectModel(UserDict.UserDict):
    def __init__(self, controller, container, name, headers={}):
        self.container = container
        self.name = name
        _headers = {}

        # Lowercase headers
        for key, value in headers.iteritems():
            _key = key.lower()
            _headers[_key] = value
        self.headers = _headers
        self._meta = None
        
        _properties = {'container': self.container, 'name': self.name}

        _properties['size'] = int(self.headers.get('content-length') or\
                                  self.headers.get('bytes') or\
                                  self.headers.get('size') or 0)
        _properties['content_type'] = self.headers.get('content_type') or\
                                      self.headers.get('content-type')
        _properties['last_modified'] = self.headers.get('last_modified') or\
                                       self.headers.get('last-modified')
        _properties['hash'] = self.headers.get('etag') or\
                              self.headers.get('hash')
        _properties['manifest'] = self.headers.get('manifest')
        _properties['content_encoding'] = self.headers.get('content_encoding') or\
                                          self.headers.get('content-encoding')
        _properties['cache_control'] = self.headers.get('cache-control')
        _properties['cdn_url'] = self.headers.get('x-cdn-url')
        _properties['cdn_ssl_url'] = self.headers.get('x-cdn-ssl-url')

        _properties['path'] = controller.path
        _properties['url'] = controller.url

        meta = {}
        for key, value in self.headers.iteritems():
            if key.startswith('meta_'):
                meta[key[5:]] = value
            elif key.startswith('x-object-meta-'):
                meta[key[14:]] = value
        self.meta = meta
        _properties['meta'] = self.meta

        self.properties = _properties
        self.data = self.properties

class StorageObject:
    """ 
        Representation of a Object Storage object.
    """
    chunk_size=10*1024
    def __init__(self, container, name, headers=None, client=None):
        self.container = container
        self.name = name
        self.client = client
        self.model = None
        self.content_type = None
        if headers:
            self.model = StorageObjectModel(self, self.container, self.name, headers)

    def exists(self):
        def _formatter(res):
            self.model = StorageObjectModel(self, self.container, self.name, res.headers)
            return True
        try:
            return self.make_request('HEAD', headers={'X-Context': 'cdn'}, formatter=_formatter)
        except errors.NotFound:
            return False

    def load(self):
        def _formatter(res):
            self.model = StorageObjectModel(self, self.container, self.name, res.headers)
            return self
        return self.make_request('HEAD', headers={'X-Context': 'cdn'}, formatter=_formatter)

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
    def url(self):
        """ Get the URL of the object """
        path = [self.container, self.name]
        return self.client.get_url(path)

    @property
    def path(self):
        """ Get the path of the object """
        path = [self.container, self.name]
        return get_path(path)
    
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
                    obj = self.client.storage_object(self.container,
                                             item['name'],
                                             headers=item)
                    objects.append(obj)
            return objects
        return self.client.make_request('GET', [self.container], params=params, formatter=_formatter)
    
    def is_dir(self):
        """ returns True if content_type is 'text/directory' """
        return self.model.content_type == 'text/directory'

    def set_metadata(self, meta):
        meta_headers = {}
        for k, v in meta.iteritems():
            meta_headers["X-Object-Meta-{0}".format(k)] = v
        return self.make_request('POST', headers=meta_headers)

    def create(self):
        """ Creates the object. This WILL overrite the current data if any. """
        content_type = self.content_type or mimetypes.guess_type(self.name)[0]
        if not content_type:
            content_type = 'application/octet-stream'
        headers = {'content-type': content_type, 'Content-Length': '0'}
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

    def save_to_filename(self, filename):
       f = open(filename, 'wb')
       conn = self.chunk_download()
       try:
           for data in conn:
               f.write(data)
       finally:
           f.close()
        
    def chunk_download(self, chunk_size=None):
        """ Returns an iterator to read the object data. """
        chunk_size = chunk_size or self.chunk_size
        return self.client.chunk_download([self.container, self.name], chunk_size=chunk_size)
    iter_content = chunk_download
    __iter__ = chunk_download
    
    def chunk_upload(self):
        """ Returns a 'chunkable' connection. This is used for chunked 
            uploading of files. This is needed for transient data uploads """
        chunkable = self.client.chunk_upload([self.container, self.name])
        return chunkable
        
    def send(self, data):
        """ Sends data for an object. Takes a string or an open file object. """
        size = None
        if isinstance(data, file):
            try:
                data.flush()
            except IOError:
                pass
            size = int(os.fstat(data.fileno())[6])
        else:
            if hasattr(data, '__len__'):
                size = len(data)

        headers = {}
        content_type = self.content_type
        if not content_type:
            _type = None
            if hasattr(data, 'name'):
                _type = mimetypes.guess_type(data.name)[0]
            content_type = _type or mimetypes.guess_type(self.name)[0] or 'application/octet-stream'
        headers['Content-Type'] = content_type

        if size or size == 0:
            headers['Content-Length'] = str(size)
        else:
            headers['Transfer-Encoding'] = 'chunked'

        return self.make_request('PUT', data=data, headers=headers, formatter=lambda r: self)
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
            obj = self.__class__(self.container, _dir, client=self.client)
            obj.content_type = 'application/directory'
            obj.create()
        
        for _file in files:
            obj = self.__class__(self.container, _file, client=self.client)
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
        headers = {}
        headers['X-Copy-From'] = old_obj.path
        headers['Content-Length'] = "0"
        return self.make_request('PUT', headers=headers, *args, **kwargs)

    def copy_to(self, new_obj, *args, **kwargs):
        """ Issues a copy-to command """
        headers = {}
        headers['Destination'] = new_obj.path
        headers['Content-Length'] = "0"
        return self.make_request('COPY', headers=headers, *args, **kwargs)

    def rename(self, new_obj, *args, **kwargs):
        """ Copies one object to a new name and deletes the old version """
        def _delete(res):
            return self.delete()
        def _copy_to(res):
            return new_obj.copy_from(self, *args, formatter=_delete, **kwargs)
        return new_obj.make_request('PUT', formatter=_copy_to)

    def search(self, *args, **kwargs):
        """ Search within path """
        return self.client.search(*args, path=[self.container, self.name], **kwargs)

    def prime_cdn(self):
        headers = {'X-Context': 'cdn', 'X-Cdn-Load': True}
        return self.make_request('POST', headers=headers, *args, **kwargs)

    def purge_cdn(self):
        headers = {'X-Context': 'cdn', 'X-Cdn-Purge': True}
        return self.make_request('POST', headers=headers, *args, **kwargs)

    def make_request(self, method, path=None, *args, **kwargs):
        """ returns a request object """
        path = [self.container, self.name]
        return self.client.make_request(method, path, *args, **kwargs)

    def fileno(self):
        return 1
    
    def __len__(self):
        if not self.model:
            self.load()
        return int(self.model['size'])

    def __getitem__(self, name):
        new_name = self.client.delimiter.join([self.name, name])
        return self.client.storage_object(self.container, new_name)
        
    def __str__(self):
        size = 'Unknown'
        if self.model:
            size = self.model.get('size', 0)
        return 'StorageObject({0}, {1}, {2}B)'.format(self.container.encode("utf-8"), self.name.encode("utf-8"), size)
    __repr__ = __str__

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass
