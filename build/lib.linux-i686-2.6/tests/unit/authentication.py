import unittest
from object_storage.transport import BaseAuthentication

class BaseAuthenticationTest(unittest.TestCase):

    def test_instance_setup(self):
        self.assert_(self.auth.storage_url == None, "Storage url is set correctly")
        self.assert_(self.auth.auth_headers == {}, "auth headers set correctly")
        self.assert_(self.auth.auth_token == None, "auth_token set correctly")
        
    def test_authenticate(self):
        self.auth.authenticate()
        self.assert_(self.auth.storage_url == 'STORAGE_URL', "storage_url set correctly")
        self.assert_(self.auth.auth_token == 'AUTH_TOKEN', "auth_token set correctly")

    def setUp(self):
        self.auth = BaseAuthentication(auth_url='auth_url')
