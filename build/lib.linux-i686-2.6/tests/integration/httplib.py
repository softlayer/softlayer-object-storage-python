import unittest
import time
import os
from object_storage import get_httplib2_client, get_requests_client
import ConfigParser

class ClientTest(unittest.TestCase):
    container_name = 'python_test_container'
    object_name = 'python_test_object'

    def setUp(self):
        config = ConfigParser.ConfigParser()
        config.read(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'user.conf'))
        account = dict(config.items('account'))
        username = account.get('username')
        api_key = account.get('api_key')
        auth_url = account.get('auth_url')
        datacenter = account.get('datacenter')
        network = account.get('network')
        protocol = account.get('protocol')
        self.client = get_httplib2_client(username, api_key, 
                                                    auth_url=auth_url, 
                                                    protocol=protocol, 
                                                    datacenter=datacenter, 
                                                    network=network)

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
        self.assert_(container.props['name'] == self.container_name, "Container name matches")
        self.assert_(container.props['count'] == 0, "Container count is 0")
        self.assert_(container.props['size'] == 0.0, "Container size is 0")

    def test_create_object(self):
        container = self.client[self.container_name].create()
        obj = container[self.object_name]
        obj.content_type = "text/html"
        obj.create()
        obj.send("<html></html>")
        obj = container[self.object_name].load()
        self.assert_(obj.props['hash'] == 'c83301425b2ad1d496473a5ff3d9ecca', "Hash matches")
        self.assert_(obj.props['content_type'] == "text/html", "Content-type matches")
        self.assert_(obj.props['size'] == 13.0, "Size matches")
        self.assert_(obj.read() == "<html></html>", "Object body matches")

    def test_enable_cdn(self):
        container = self.client[self.container_name].create()
        lst = self.client.public_containers()
        container.enable_cdn()
        time.sleep(2)
        lst = self.client.public_containers()
        
        result_list = self.filter_by_name(lst)
        self.assert_(len(result_list) == 1)
        self.assert_(result_list.pop().name == self.container_name, "The container has CDN enabled")
        self.assert_(container.props['read'] == ".r:*", "The container has read property set")
        container.delete()
        time.sleep(2)
        lst = self.client.public_containers()
        result_list = self.filter_by_name(lst)
        self.assert_(len(result_list) == 0)

    def test_set_ttl(self):
        container = self.client[self.container_name].create()
        container.set_ttl(1000)
        self.assert_(self.client[self.container_name].load().props['ttl'] == 1000, "TTL is set correctly")

        container.set_ttl(None)
        self.assert_(self.client[self.container_name].load().props['ttl'] == 0, "TTL is cleared correctly")

    def test_search_container(self):
        time.sleep(2)
        results = self.client.search({'q': '*'})
        result_list = self.filter_by_name(results['results'])
        self.assert_(len(result_list) == 0, "Search returns no results")

        container = self.client[self.container_name].create()
        time.sleep(2)
        results = self.client.search({'q': '*test*', 'type': 'container'})
        result_list = self.filter_by_name(results['results'])
        self.assert_(len(result_list) == 1, "Correct amount of search results")
        self.assert_(result_list.pop().name == self.container_name, "Correct search result name")

        container.delete()
        time.sleep(2)
        results = self.client.search({'q': '*test*', 'type': 'container'})
        result_list = self.filter_by_name(results['results'])
        self.assert_(len(result_list) == 0, "Search returns no results")

    def test_search_object(self):
        time.sleep(2)
        results = self.client.search({'q': '*test*'})
        result_list = self.filter_by_name(results['results'])
        self.assert_(len(result_list) == 0, "Search returns no results")

        container = self.client[self.container_name].create()
        obj = container[self.object_name]
        obj.content_type = 'application/text'
        obj.create()
        time.sleep(3)
        
        results = self.client.search({'q': '*test*', 'type': 'object'})
        result_list = self.filter_by_name(results['results'])
        self.assert_(len(result_list) == 1, "Correct amount of search results")
        self.assert_(result_list.pop().name == self.object_name, "Correct search result name")

        results = self.client.search({'q': '*test*', 'type': 'object', 'content_type': 'application/text'})
        result_list = self.filter_by_name(results['results'])
        self.assert_(len(result_list) == 1, "Correct amount of search results")
        self.assert_(result_list.pop().name == self.object_name, "Correct search result name")
        
        obj.delete()
        time.sleep(2)
        results = self.client.search({'q': '*test*', 'type': 'object'})
        result_list = self.filter_by_name(results['results'])
        self.assert_(len(result_list) == 0, "Search returns no results")
        
