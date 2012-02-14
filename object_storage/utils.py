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
