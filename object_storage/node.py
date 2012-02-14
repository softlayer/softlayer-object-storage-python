"""
    Node module.

    See COPYING for license information
"""
class Node(object):
    """ 
        Node Class. This is intended to be inherited from. This represents
        a standard interface for a 'node' which encapsulates common concepts
        between containers, objects, and the base directory, which you can
        imagine as an account object.
    """
    type = 'node'
    property_names = ['size', 'count']
    meta_prefixes = ['meta_']
    property_mappings = {
            'count': 'count',
            'size': 'size',
        }

    @property
    def url(self):
        """ returns url of the resource. To be overridden """
        pass

    @property
    def path(self):
        """ returns path of the resource. To be overridden """
        pass

    def is_dir(self):
        """ returns if the resource is a directory. To be overridden """
        return True

    def create(self):
        """ creates resource. To be overridden """
        pass

    def delete(self, recursive=False):
        """ deletes resource. To be overridden """
        pass

    def list(self):
        """ lists sub-items of the resource. To be overridden """
        pass

    def make_request(self, method, path=None, *args, **kwargs):
        """ makes a request on the resource. To be overridden """
        pass

    def _headers(self):
        """ returns the headers for the resource. To be overridden """
        return {}
    
    def save_headers(self):
        """ POSTS the header content """
        headers = self._headers()
        headers.update({'x-context': 'cdn'})
        return self.make_request('POST', headers=headers)

    @property
    def properties(self):
        """ Returns a dict of the properties of the resource. """
        properties = {}
        for prop in self.property_names:
            val = getattr(self, prop, None)
            if val:
                properties[prop] = val
        for key, meta in self.meta.iteritems():
            properties['meta_'+key] = meta
        return properties
    props = properties

    def load_meta(self):
        """ 
            Loads meta for the resource. Will call _process_props with
            the given headers.
        """
        def _formatter(res):
            self._process_props(res.headers)
            return self
        return self.make_request('HEAD', formatter=_formatter)
    load = load_meta

    def _process_props(self, properties):
        """
            Populates object with the given properties.
            Uses property_mappings and meta_prefixes to determine
            how the attributes are populated
        """
        meta = {}
        headers = {}
        for key, val in properties.items():
            key = key.lower()
            if key in self.property_mappings:
                setattr(self, self.property_mappings[key], val)
            for prefix in self.meta_prefixes:
                if key.startswith(prefix):
                    meta[key[len(prefix):]] = val
            if key.startswith('x-'):
                headers[key[2:].replace('-', '_')] = val
            if key.startswith('header_'):
                headers[key[7:]] = val
        self.meta = meta
        self.headers = headers

    def __iter__(self):
        """ Returns an interator based on results of self.list() """
        listing = self.list()
        for obj in listing:
            yield obj
