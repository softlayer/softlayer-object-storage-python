""" 
    Commonly used constants 

    See COPYING for license information
"""
__version__ = "0.3"

USER_AGENT = "sl-object-storage-python: %s" % __version__
SL_DAL_HTTPS_AUTH_URL = 'https://dal05.objectstorage.softlayer.net/auth/v1.0'
SL_DAL_HTTP_AUTH_URL = "http://dal05.objectstorage.softlayer.net/auth/v1.0"
SL_DAL_PRIV_HTTPS_AUTH_URL = 'http://dal05.objectstorage.service.networklayer.com/auth/v1.0'
SL_DAL_PRIV_HTTP_AUTH_URL = "http://dal05.objectstorage.service.networklayer.com/auth/v1.0"
SL_AUTH_URL = SL_DAL_HTTPS_AUTH_URL
