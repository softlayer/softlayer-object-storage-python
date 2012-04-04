import unittest
from mock import Mock, MagicMock
from object_storage.container import Container
from object_storage.storage_object import StorageObject

class ContainerTest(unittest.TestCase):
    def test_instance_setup(self):
        self.assert_(self.client == self.container.client, "client is set")
        self.assert_(self.container.name == 'CONTAINER', "name is set")

    def test_create(self):
        self.container.make_request = Mock()
        result = self.container.create()
        self.container.make_request.called_once_with('PUT')

    def test_delete(self):
        result = self.container.delete()
        self.client.delete_container.called_once_with(self.container.name)

    def test_delete_recursive(self):
        self.container.delete_all_objects = Mock()
        result = self.container.delete(recursive=True)
        self.container.delete_all_objects.called_once_with()
        self.client.delete_container.called_once_with(self.container.name)

    def test_delete_all_objects(self):
        _item1 = Mock()
        _item2 = Mock()
        self.container.list = Mock(return_value=[_item1, _item2])
        self.container.delete_all_objects()
        self.container.list.called_once_with()
        _item1.delete.assert_called_once_with()
        _item2.delete.assert_called_once_with()

    def test_delete_object(self):
        self.container.delete_object('OBJECT')
        self.client.delete_object.called_once_with(self.container, 'OBJECT')

    def test_delete_object_with_object(self):
        _object = Mock(spec=StorageObject)
        _object.name = 'OBJECT'
        self.container.delete_object(_object)
        self.client.delete_object.called_once_with(self.container, 'OBJECT')

    def test_list(self):
        pass

    def test_search(self, *args, **kwargs):
        options = {'q': 'query'}
        self.container.search(options)
        self.client.search.called_once_with({'q': 'query', 'path': self.container.name})

    def test_get_object(self):
        _name = Mock()
        self.container.get_object(_name)
        self.client.get_object.called_once_with(self.container.name, _name)

    def test_object(self):
        _name = Mock()
        _props = Mock()
        self.container.storage_object(_name, _props)
        self.container.client.storage_object.called_once_with(self.container.name, _name, properties=_props)

    def test_load_from_filename(self):
        _obj = Mock()
        self.container.storage_object = Mock(return_value=_obj)

        self.container.load_from_filename('/dir/to/filename')
        self.container.storage_object.called_once_with('filename')
        _obj.load_from_filename.called_once_with('/dir/to/filename')

    def test_path(self):
        path = self.container.path
        self.client.get_path.called_once_with([self.container.name])

    def test_url(self):
        path = self.container.url
        self.client.get_url.called_once_with([self.container.name])

    def test_is_dir(self):
        result = self.container.is_dir()
        self.assert_(result == True)

    def test_make_request(self):#, method, *args, **kwargs):
        self.container.make_request('METHOD', 1, 2, a1=1, a2=2)
        self.client.make_request.called_once_with('METHOD', [self.container.name], 1, 2, a1=1, a2=2)

    def test_getitem(self):
        _obj = Mock()
        self.container.storage_object = Mock(return_value=_obj)
        obj = self.container['OBJECT']
        self.assert_(obj == _obj, "Object returns from container.object()")
        self.container.storage_object.assert_called_once_with('OBJECT')

    def setUp(self):
        self.client = Mock()
        self.container = Container('CONTAINER', client=self.client)
