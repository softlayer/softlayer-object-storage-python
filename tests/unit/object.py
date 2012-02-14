import unittest
from mock import Mock
from object_storage.object import Object

class ClientTest(unittest.TestCase):
    def test_instance_setup(self):
        self.assert_(self.client == self.obj.client, "client is set")
        self.assert_(self.obj.container == 'CONTAINER', "container is set")
        self.assert_(self.obj.name == 'NAME', "name is set")
        self.assert_(self.obj.content_type == None, "content_type is None")
        self.assert_(self.obj.last_modified == None, "last_modified is None")
        self.assert_(self.obj.size == None, "size is None")
        self.assert_(self.obj.hash == None, "hash is None")
        self.assert_(self.obj.manifest == None, "manifest is None")
        self.assert_(self.obj.content_encoding == None, "content_encoding is None")
        self.assert_(self.obj.meta == {}, "meta is {}")

    def test_is_dir(self):
        result = self.obj.is_dir()
        self.assert_(result == False, "Object isn't a directory")

    def test_is_dir_yes(self):
        self.obj.content_type = 'text/directory'
        result =self.obj.is_dir()
        self.assert_(result == True, "Object is a directory")

    def test_create(self):
        # no content_type and no ext
        _headers = Mock()
        _make_request = Mock()
        self.obj._headers = _headers
        self.obj.make_request = _make_request
        result = self.obj.create()
        self.assert_(self.obj.content_type == 'text/plain', "Content type set through side-effect")

        self.obj._headers.called_once_with()
        self.obj.make_request.called_once_with('PUT', headers=_headers)
        
        # with .py file ext
        self.obj.content_type = None
        self.obj.name = "FILENAME.py"
        result = self.obj.create()
        self.assert_(self.obj.content_type == 'text/x-python', "Content type set through side-effect")

        # with content type set
        self.obj.content_type = 'CONTENT_TYPE'
        result = self.obj.create()
        self.assert_(self.obj.content_type == 'CONTENT_TYPE', "Content type set through side-effect")

    def test_delete(self):
        result = self.client.delete()
        self.client.delete_object.called_once_with(self.obj.container, self.obj.name)

    def test_read(self):#, size=0, offset=0):
        _result = Mock()
        self.obj.make_request = Mock(return_value=_result)
        result = self.obj.read()
        
        result = self.obj.read(1111, 2222)
        self.obj.make_request.called_once_with('GET', headers={'Range': 'bytes=1111-3332'})

    def test_copy_to(self):
        _make_request = Mock()
        self.obj._make_request = _make_request
        self.obj._headers = Mock(return_value={})

        other_obj = Mock()
        self.obj.copy_to(other_obj, 1, 2, a1=1, a2=2)

        self.obj._headers.called_once_with()
        _make_request.called_once_with('COPY', 1, 2,
                                headers={'Destination': other_obj.path, 'Content-Length': 0}, 
                                data='', a1=1, a2=2)

    def test_rename(self):#, new_obj, *args, **kwargs):
        self.obj.copy_to = Mock()
        self.obj.delete = Mock()

        _new_obj = Mock()
        self.obj.rename(_new_obj, 1, 2, a1=1, a2=2)
        self.obj.copy_to.called_once_with(_new_obj, 1, 2, a1=1, a2=2)
        self.obj.delete.called_once_with()

    def save_headers(self):
        """ POSTS the header content """
        headers = self._headers()
        headers['Content-Length'] = "0"
        self.make_request('POST', headers=headers, data='')
        return True

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

        for key in self.meta:
            headers['X-Object-Meta-' + key] = self.meta[key]
        return headers

    @property
    def url(self):
        """ Get the URL of the object """
        path = [self.container, self.name]
        return self.client.get_url(path)

    def setUp(self):
        self.client = Mock()
        self.obj = Object('CONTAINER', 'NAME', client=self.client)
