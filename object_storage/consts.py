"""
    Commonly used constants

    See COPYING for license information
"""


__version__ = "0.5.4"

USER_AGENT = "sl-object-storage-python/%s" % __version__

DATACENTERS = [
    'dal05',  # US - Texas - Dallas
    'ams01',  # NL - North Holland - Amsterdam
    'sng01',  # SG - Singapore
    'sjc01',  # US - California - San Jose
    'hkg02',  # HK - Hong Kong
    'lon02',  # GB - London
    'tor01',  # CA - Ontario - Toronto
    'mel01',  # AU - Victoria - Melbourne
    'par01',  # FR - Paris
    'mex01',  # MX - Mexico City
    'tok02',  # JP - Tokyo
    'fra02',  # DE - Hesse - Frankfurt
    'syd01',  # AU - New South Wales - Sydney
    'mon01',  # CA - Quebec - Montreal
]

PUBLIC_SUFFIX = 'objectstorage.softlayer.net'
PRIVATE_SUFFIX = 'objectstorage.service.networklayer.com'


def dc_endpoints(dc):
    dc = dc.lower()
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

# Normally this could be a dict comprehension, but we're maintaining
# compatibility with Python 2.6, so the slower dict() is necessary.
ENDPOINTS = dict((dc, dc_endpoints(dc)) for dc in DATACENTERS)
