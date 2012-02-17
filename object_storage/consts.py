""" 
    Commonly used constants 

    See COPYING for license information
"""
__version__ = "0.4"

USER_AGENT = "sl-object-storage-python: %s" % __version__
ENDPOINTS = {
      'dal05': {
        'public': {
          'http': "http://dal05.objectstorage.softlayer.net/auth/v1.0",
          'https': "https://dal05.objectstorage.softlayer.net/auth/v1.0"
        },
        'private': {
          'http': "http://dal05.objectstorage.service.networklayer.com/auth/v1.0",
          'https': "https://dal05.objectstorage.service.networklayer.com/auth/v1.0"
        }
      }
    }
