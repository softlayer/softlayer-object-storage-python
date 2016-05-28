"""
    Commonly used constants

    See COPYING for license information
"""


__version__ = "0.5.4"

USER_AGENT = "sl-object-storage-python/%s" % __version__

DATACENTERS = [
    'ams01',  # NL - North Holland - Amsterdam
    'che01',  # IN - Tamil Nadu - Chennai
    'dal05',  # US - Texas - Dallas
    'fra02',  # DE - Hesse - Frankfurt
    'hkg02',  # HK - Hong Kong
    'lon02',  # GB - London
    'mel01',  # AU - Victoria - Melbourne
    'mex01',  # MX - Mexico City
    'mil01',  # IT - Lombardy - Milan
    'mon01',  # CA - Quebec - Montreal
    'par01',  # FR - Paris
    'sao01',  # BR - SP - Sao Paulo
    'sjc01',  # US - California - San Jose
    'sng01',  # SG - Singapore
    'syd01',  # AU - New South Wales - Sydney
    'tor01',  # CA - Ontario - Toronto
    'tok02',  # JP - Tokyo
    'wdc',    # US - DC - District of Columbia
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
