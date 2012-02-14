import unittest
import time
import os
from object_storage import get_httplib2_client
import ConfigParser

class ClientTest(unittest.TestCase):
    container_name = 'python_test_container'
    object_name = 'python_test_object'

    def setUp(self):
        config = ConfigParser.ConfigParser()
        config.read(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'user.conf'))
        username = config.get('account', 'username')
        api_key = config.get('account', 'api_key')
        auth_url = config.get('account', 'auth_url')
        self.client = get_httplib2_client(username, api_key, auth_url=auth_url)

    def tearDown(self):
        for container in self.client:
            if container.name.startswith('python_test'):
                for obj in container:
                    if obj.name.startswith('python_test'):
                        obj.delete()
                container.delete()

    def filter_by_name(self, lst):
        new_list = []
        for item in lst:
            if item.name.startswith('python_test'):
                new_list.append(item)
        return new_list

    def test_auth_setup(self):
        self.client.conn.auth.authenticate()

    def test_create_container(self):
        container = self.client[self.container_name].create()
        container = self.client[self.container_name].load()
        self.assert_(container.name == self.container_name, "Container name matches")
        self.assert_(container.count == '0', "Container count is 0")
        self.assert_(container.size == '0', "Container size is 0")

    def test_create_object(self):
        container = self.client[self.container_name].create()
        obj = container[self.object_name]
        obj.content_type = "text/html"
        obj.create()
        obj.send("<html></html>")
        obj = container[self.object_name].load()
        self.assert_(obj.hash == 'c83301425b2ad1d496473a5ff3d9ecca', "Hash matches")
        self.assert_(obj.content_type == "text/html", "Content-type matches")
        self.assert_(obj.size == '13', "Size matches")
        self.assert_(obj.read() == "<html></html>", "Object body matches")

    def test_enable_cdn(self):
        container = self.client[self.container_name].create()
        lst = self.client.list_cdn()
        container.enable_cdn()
        time.sleep(2)
        lst = self.client.list_cdn()
        
        result_list = self.filter_by_name(lst)
        self.assert_(len(result_list) == 1)
        self.assert_(result_list.pop().name == self.container_name, "The container has CDN enabled")
        self.assert_(container.read == ".r:*", "The container has read property set")
        container.delete()
        time.sleep(2)
        lst = self.client.list_cdn()
        result_list = self.filter_by_name(lst)
        self.assert_(len(result_list) == 0)

    def test_set_ttl(self):
        container = self.client[self.container_name].create()
        container.ttl = 1000
        container.save_headers()
        self.assert_(self.client[self.container_name].load().ttl == '1000', "TTL is set correctly")

        container.ttl = ' '
        container.save_headers()
        self.assert_(self.client[self.container_name].load().ttl == None, "TTL is cleared correctly")

    def test_search_container(self):
        time.sleep(2)
        results = self.client.search('*')
        result_list = self.filter_by_name(results['results'])
        self.assert_(len(result_list) == 0, "Search returns no results")

        container = self.client[self.container_name].create()
        time.sleep(2)
        results = self.client.search('*test*', type='container')
        result_list = self.filter_by_name(results['results'])
        self.assert_(len(result_list) == 1, "Correct amount of search results")
        self.assert_(result_list.pop().name == self.container_name, "Correct search result name")

        container.delete()
        time.sleep(2)
        results = self.client.search('*test*', type='container')
        result_list = self.filter_by_name(results['results'])
        self.assert_(len(result_list) == 0, "Search returns no results")

    def test_search_object(self):
        time.sleep(2)
        results = self.client.search('*test*')
        result_list = self.filter_by_name(results['results'])
        self.assert_(len(result_list) == 0, "Search returns no results")

        container = self.client[self.container_name].create()
        obj = container[self.object_name]
        obj.content_type = 'application/text'
        obj.create()
        time.sleep(3)
        
        results = self.client.search('*test*', type='object')
        result_list = self.filter_by_name(results['results'])
        self.assert_(len(result_list) == 1, "Correct amount of search results")
        self.assert_(result_list.pop().name == self.object_name, "Correct search result name")

        results = self.client.search('*test*', type='object', content_type='application/text')
        result_list = self.filter_by_name(results['results'])
        self.assert_(len(result_list) == 1, "Correct amount of search results")
        self.assert_(result_list.pop().name == self.object_name, "Correct search result name")
        
        obj.delete()
        time.sleep(2)
        results = self.client.search('*test*', type='object')
        result_list = self.filter_by_name(results['results'])
        self.assert_(len(result_list) == 0, "Search returns no results")
        
