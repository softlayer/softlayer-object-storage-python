""" 
    Misc Utils

    See COPYING for license information
"""

import urllib

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
