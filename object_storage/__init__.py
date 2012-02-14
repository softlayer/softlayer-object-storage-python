"""
    SoftLayer Object Storage python client.
       
    See COPYING for license information
"""

from object_storage.client import Client
from object_storage.consts import __version__, SL_AUTH_URL

def get_client(*args, **kwargs):
    return get_httplib2_client(*args, **kwargs)

def get_httplib2_client(username, password, auth_url=SL_AUTH_URL):
    from object_storage.transport.httplib2conn import AuthenticatedConnection, Authentication

    auth = Authentication(username, password, auth_url=auth_url)
    conn = AuthenticatedConnection(auth)
    client = Client(username, password, auth_url=auth_url, connection=conn)
    return client

def get_requests_client(username, password, auth_url=SL_AUTH_URL):
    from object_storage.transport.connection import AuthenticatedConnection, Authentication

    auth = Authentication(username, password, auth_url=auth_url)
    conn = AuthenticatedConnection(auth)
    client = Client(username, password, auth_url=auth_url, connection=conn)
    return client

def get_twisted_client(username, password, auth_url=SL_AUTH_URL):
    from object_storage.transport.twist import AuthenticatedConnection, Authentication

    auth = Authentication(username, password, auth_url=auth_url)
    conn = AuthenticatedConnection(auth)
    client = Client(username, password, auth_url=auth_url, connection=conn)
    
    d = auth.authenticate().addBoth(lambda r: client)
    return d
