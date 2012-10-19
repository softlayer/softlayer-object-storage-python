"""
    StorageObject module

    See COPYING for license information
"""
from object_storage.utils import json, Model
import mimetypes
import os
try:
    import StringIO
except ImportError:
    from io import StringIO as StringIO
try:
    from hashlib import md5
except ImportError:
    from md5 import md5

from object_storage import errors
from object_storage.utils import get_path


class StorageObjectModel(Model):
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
    chunk_size = 10 * 1024

    def __init__(self, container, name, headers=None, client=None):
        """ constructor for StorageObject

        @param container: container name
        @param name: object name
        @param headers: init headers to use when initializing the object
        @param client: `object_storage.client` instance.
        """
        self.container = container
        self.name = name
        self.client = client
        self.model = None
        self.content_type = None
        if headers:
            self.model = StorageObjectModel(self, self.container, self.name, headers)

    def exists(self):
        """ Tries to load the object to check existance

        @raises ResponseError
        @return: boolean, true if exists else false
        """
        def _formatter(res):
            self.model = StorageObjectModel(self, self.container, self.name, res.headers)
            return True
        try:
            return self.make_request('HEAD', formatter=_formatter)
        except errors.NotFound:
            return False

    def load(self, cdn=True):
        """ load data for the object

        @param cdn: True if you want CDN information; default=True
        @return: object_storage.storage_object, self
        """
        headers = {}
        if cdn:
            headers.setdefault('X-Context', 'cdn')

        def _formatter(res):
            self.model = StorageObjectModel(self, self.container, self.name, res.headers)
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
        """ loads data if not already available and returns the raw headers for the object """
        if not self.model:
            self.load()
        return self.model.headers

    @property
    def meta(self):
        """ loads data if not already available and returns the metadata for the object """
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

    def list(self, limit=None, marker=None, base_only=False):
        """ Uses sudo-hierarchical structure to list the children objects.

        @param limit: limit of results to return.
        @param marker: start listing after this object name
        @raises ResponseError
        @return: list of StorageObject instances
        """
        params = {'format': 'json',
                  'prefix': self.name + self.client.delimiter}
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
                        objects[item['name']] = self.client.storage_object(self.container, item['name'], headers=item)
                    elif 'subdir' in item:
                        name = item['subdir'].rstrip('/')
                        item['name'] = name
                        item['content_type'] = 'application/directory'
                        objects[item['name']] = self.client.storage_object(self.container, item['name'], headers=item)
            return objects.values()
        return self.client.make_request('GET', [self.container], params=params, formatter=_formatter)

    def is_dir(self):
        """ returns True if content_type is 'text/directory' or 'application/directory' """
        return self.model.content_type in ['text/directory', 'application/directory']

    def set_metadata(self, meta):
        """ Sets metadata for the object

        @param meta: dict of metadata on the object
        @raises ResponseError
        """
        meta_headers = {}
        for k, v in meta.iteritems():
            meta_headers["X-Object-Meta-%s" % (k, )] = v
        return self.make_request('POST', headers=meta_headers)

    def create(self):
        """ Create object

        @raises ResponseError
        @return: StorageObject - self
        """
        content_type = self.content_type or mimetypes.guess_type(self.name)[0]
        if not content_type:
            content_type = 'application/octet-stream'
        headers = {'content-type': content_type, 'Content-Length': '0'}

        def _formatter(res):
            return self
        return self.make_request('PUT', headers=headers, formatter=_formatter)

    def delete(self, recursive=False):
        """ Delete object

        @raises ResponseError
        @return: True
        """
        return self.client.delete_object(self.container, self.name)

    def read(self, size=None, offset=None, headers=None):
        """ Reads object content

        @param size: number of bytes to read (0 reads all of the object data)
        @param offset: number of bytes to offset the read
        @raises ResponseError
        @return: str, data
        """
        headers = headers or {}
        if all([offset, size]):
            end = (offset + size) - 1
            headers['Range'] = 'bytes=%s-%s' % (offset, end)
        elif offset is None and size is not None and size < 0:
            headers['Range'] = 'bytes=%s' % (size,)
        elif offset is None and size:
            end = size - 1
            headers['Range'] = 'bytes=0-%s' % (end,)
        elif offset is not None and size is None:
            headers['Range'] = 'bytes=%s-' % (offset,)

        def _formatter(res):
            return res.content
        return self.make_request('GET', headers=headers, formatter=_formatter)

    def save_to_filename(self, filename):
        """ Reads object content into a file

        @param filename: filename
        @raises ResponseError
        """
        f = open(filename, 'wb')
        conn = self.chunk_download()
        try:
            for data in conn:
                f.write(data)
        finally:
            f.close()

    def chunk_download(self, chunk_size=None):
        """ Returns an iterator to read the object data.

        @param chunk_size: size of the chunks to read in.
            If not defined uses self.chunk_size
        @raises: ResponseError
        @return: iterable
        """
        chunk_size = chunk_size or self.chunk_size
        return self.client.chunk_download([self.container, self.name], chunk_size=chunk_size)
    iter_content = chunk_download
    __iter__ = chunk_download

    def chunk_upload(self, size=None, headers=None):
        """ Returns a chunkable upload instance.
            This is needed for transient data uploads

        @param headers: size in bytes, if known
        @param headers: extra headers to use to initialize the request
        @raises: ResponseError
        @return: object that responds to o.send('data') to send data
            and o.finish() to finish the upload.
        """
        chunkable = self.client.chunk_upload([self.container, self.name], size=size, headers=headers)
        return chunkable

    def send(self, data, check_md5=True):
        """ Uploads object data

        @param data: either a file-like object or a string.
        @raises: ResponseError
        @return: StorageObject, self
        """
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

        if isinstance(data, basestring):
            data = StringIO.StringIO(data)

        headers = {}
        content_type = self.content_type
        if not content_type:
            _type = None
            if hasattr(data, 'name'):
                _type = mimetypes.guess_type(data.name)[0]
            content_type = _type or mimetypes.guess_type(self.name)[0] or 'application/octet-stream'
        headers['Content-Type'] = content_type

        checksum = md5()
        transfered = 0
        conn = self.chunk_upload(size=size, headers=headers)
        buff = data.read(4096)
        while len(buff) > 0:
            conn.send(buff)
            if check_md5:
                checksum.update(buff)
            transfered += len(buff)
            buff = data.read(4096)
        res = conn.finish()

        if check_md5:
            assert checksum.hexdigest() == res.headers['etag'], 'md5 hashes do not match'
        res.headers['content-length'] = transfered
        self.model = StorageObjectModel(self, self.container, self.name, res.headers)
        headers['Content-Type'] = content_type
        return self

    write = send

    def upload_directory(self, directory):
        """ Uploads an entire directory

        @param directory: path of the directory to upload
        @raises: ResponseError
        """
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
        """ Uploads a file from the local filename

        @param filename: path of the directory to upload
        @raises: ResponseError, IOError
        """
        if os.path.isdir(filename):
            self.upload_directory(filename)
        else:
            try:
                _file = open(filename, 'rb')
            finally:
                return self.send(_file)

    def copy_from(self, old_obj, *args, **kwargs):
        """ Copies content from an existing object

        @param old_obj: StorageObject instance to copy data from
        @raises: ResponseError
        @return: StorageObject, self
        """
        headers = {}
        headers['X-Copy-From'] = old_obj.path
        headers['Content-Length'] = "0"
        if 'formatter' not in kwargs:
            kwargs['formatter'] = lambda r: self
        return self.make_request('PUT', headers=headers, *args, **kwargs)

    def copy_to(self, new_obj, *args, **kwargs):
        """ Copies content from an existing object

        @param new_obj: StorageObject instance to copy data to
        @raises: ResponseError
        @return: StorageObject, new_obj
        """
        headers = {}
        headers['Destination'] = new_obj.path
        headers['Content-Length'] = "0"
        if 'formatter' not in kwargs:
            kwargs['formatter'] = lambda r: new_obj
        return self.make_request('COPY', headers=headers, *args, **kwargs)

    def rename(self, new_obj, *args, **kwargs):
        """ Copies content to a new object existing object and deletes the current object

        @param new_obj: StorageObject instance to copy data to
        @raises: ResponseError
        """
        def _delete(res):
            return self.delete()

        def _copy_to(res):
            kwargs['formatter'] = _delete
            return new_obj.copy_from(self, *args, **kwargs)
        return new_obj.make_request('PUT', headers={'Content-Length': '0'}, formatter=_copy_to)

    def search(self, q, options=None, **kwargs):
        """ Search within path """
        options = options or {}
        options.update({'path': "%s/%s" % (self.container, self.name)})
        return self.client.search(q, options=options, **kwargs)

    def prime_cdn(self, *args, **kwargs):
        """ Prime the object for CDN usage """
        headers = {'X-Context': 'cdn', 'X-Cdn-Load': True}
        return self.make_request('POST', headers=headers, *args, **kwargs)

    def purge_cdn(self, *args, **kwargs):
        """ Purge the object for CDN usage """
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
        return 'StorageObject(%s, %s, %sB)' % (self.container.encode("utf-8"), self.name.encode("utf-8"), size)
    __repr__ = __str__

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass
