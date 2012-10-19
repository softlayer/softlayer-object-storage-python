"""
    Misc Utils

    See COPYING for license information
"""

import urllib
import sys

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        try:
            import django.utils.simplejson as json
        except ImportError:
            ImportError("Requires a json parsing library")

try:
    from UserDict import DictMixin
except ImportError:
    from collections import MutableMapping as DictMixin


class Model(DictMixin):
    def __getitem__(self, key):
        return self.properties[key]

    def __setitem__(self, key, item):
        self.properties[key] = item

    def __delitem__(self, key):
        del self.properties[key]

    def keys(self):
        return self.properties.keys()

if sys.version_info >= (3,):
    def unicode_quote(s):
        from urllib.parse import quote
        return quote(s)
else:
    def unicode_quote(s):
        """ Solves an issue with url-quoting unicode strings"""
        if isinstance(s, unicode):
            return urllib.quote(s.encode("utf-8"))
        else:
            return urllib.quote(str(s))


def get_path(parts=None):
    """
        Returns the path to a resource. Parts can be a list of strings or
        a string.
    """
    path = parts
    if parts:
        if isinstance(parts, list):
            path = '/'.join(map(unicode_quote, parts))
        else:
            path = '/'.join(map(unicode_quote, path.split('/')))
    return path
