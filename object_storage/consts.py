"""
    Commonly used constants

    See COPYING for license information
"""

__version__ = "0.5.1"

USER_AGENT = "sl-object-storage-python/%s" % __version__


def _dc_endpoints(dc):
    return {
        'public': {
            'http': 'http://%s.%s/auth/v1.0' % (dc, PUBLIC_SUFFIX),
            'https': 'https://%s.%s/auth/v1.0' % (dc, PUBLIC_SUFFIX),
        },
        'private': {
            'http': 'http://%s.%s/auth/v1.0' % (dc, PRIVATE_SUFFIX),
            'https': 'https://%s.%s/auth/v1.0' % (dc, PRIVATE_SUFFIX),
        }
    }

DATACENTERS = ['dal05',  # US - Texas - Dallas
               'ams01',  # NL - North Holland - Amsterdam
               'sng01',  # SG - Singapore
               'sjc01',  # US - California - San Jose
               'hkg02',  # HK - Hong Kong
               'lon02',  # GB - London
               'tor01',  # CA - Ontario - Toronto
               'mel01',  # AU - Victoria - Melbourne
               'par01']  # FR - Paris

PUBLIC_SUFFIX = 'objectstorage.softlayer.net'
PRIVATE_SUFFIX = 'objectstorage.service.networklayer.com'

# Normally this could be a dict comprehension, but we're maintaining
# compatibility with Python 2.6, so the slower dict() is necessary.
ENDPOINTS = dict((dc, _dc_endpoints(dc)) for dc in DATACENTERS)
