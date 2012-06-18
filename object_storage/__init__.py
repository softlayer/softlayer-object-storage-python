"""
    SoftLayer Object Storage python client.

    See COPYING for license information
"""
import object_storage.consts

__version__ = object_storage.consts.__version__


def get_client(*args, **kwargs):
    """ Returns an Object Storage client (using httplib2)

    @param username: username for Object Storage
    @param password: password or api key for Object Storage
    @param auth_url: Auth URL for Object Storage
    @param auth_token: If provided, bypasses authentication and uses the given auth_token
    @return: `object_storage.client.Client`
    """
    return get_httplib2_client(*args, **kwargs)


def get_httplib2_client(username, password, auth_url=None, auth_token=None, **kwargs):
    """ Returns an Object Storage client (using httplib2)

    @param username: username for Object Storage
    @param password: password or api key for Object Storage
    @param auth_url: Auth URL for Object Storage
    @param auth_token: If provided, bypasses authentication and uses the given auth_token
    @return: `object_storage.client.Client`
    """
    from object_storage.client import Client
    from object_storage.transport.httplib2conn import AuthenticatedConnection, Authentication

    auth = Authentication(username, password, auth_url=auth_url, auth_token=auth_token, **kwargs)
    conn = AuthenticatedConnection(auth)
    client = Client(username, password, connection=conn)
    return client


def get_requests_client(username, password, auth_url=None, auth_token=None, **kwargs):
    """ Returns an Object Storage client (using Requests) """
    from object_storage.client import Client
    from object_storage.transport.requestsconn import AuthenticatedConnection, Authentication

    auth = Authentication(username, password, auth_url=auth_url, auth_token=auth_token, **kwargs)
    conn = AuthenticatedConnection(auth)
    client = Client(username, password, connection=conn)
    return client


def get_twisted_client(username, password, auth_url=None, auth_token=None, **kwargs):
    """ Returns an Object Storage client (using Twisted) """
    from object_storage.client import Client
    from object_storage.transport.twist import AuthenticatedConnection, Authentication

    auth = Authentication(username, password, auth_url=auth_url, auth_token=auth_token, **kwargs)
    conn = AuthenticatedConnection(auth)
    client = Client(username, password, connection=conn)

    d = conn.authenticate().addCallback(lambda r: client)
    return d

__all__ = ['get_client', 'get_httplib2_client', 'get_requests_client', 'get_twisted_client']
