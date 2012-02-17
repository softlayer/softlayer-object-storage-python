"""
    SoftLayer Object Storage python client.
       
    See COPYING for license information
"""
from object_storage.client import Client
from object_storage.consts import __version__

def get_client(*args, **kwargs):
    """ Returns an Object Storage client """
    return get_httplib2_client(*args, **kwargs)

def get_httplib2_client(username, password, auth_url=None, **kwargs):
    """ Returns an Object Storage client (using httplib2) """
    from object_storage.transport.httplib2conn import AuthenticatedConnection, Authentication

    auth = Authentication(username, password, auth_url=auth_url, **kwargs)
    conn = AuthenticatedConnection(auth)
    client = Client(username, password, connection=conn)
    return client

def get_requests_client(username, password, auth_url=None, **kwargs):
    """ Returns an Object Storage client (using Requests) """
    from object_storage.transport.requestsconn import AuthenticatedConnection, Authentication

    auth = Authentication(username, password, auth_url=auth_url, **kwargs)
    conn = AuthenticatedConnection(auth)
    client = Client(username, password, connection=conn)
    return client

def get_twisted_client(username, password, auth_url=None, **kwargs):
    """ Returns an Object Storage client (using Twisted) """
    from object_storage.transport.twist import AuthenticatedConnection, Authentication

    auth = Authentication(username, password, auth_url=auth_url, **kwargs)
    conn = AuthenticatedConnection(auth)
    client = Client(username, password, connection=conn)
    
    d = auth.authenticate().addBoth(lambda r: client)
    return d
