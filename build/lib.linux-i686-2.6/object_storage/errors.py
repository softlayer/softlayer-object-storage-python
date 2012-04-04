""" 
    Exceptions 

    See COPYING for license information
"""
class ObjectStorageError(StandardError):
    """ A general Object Storage error. """
    pass
    
class AuthenticationError(ObjectStorageError):
    """ Could not authenticate. """
    pass

class StorageURLNotFound(AuthenticationError):
    """ 
        Raised when the requested protocol/network-type not found in Authentication response.
    """
    pass
    
class ContainerExists(ObjectStorageError):
    """ Container already exists """
    pass
    
class ContainerNotEmpty(ObjectStorageError):
    """ Container is not empty """
    pass

class NotFound(ObjectStorageError):
    """ Resource not found """
   
class ObjectNotFound(NotFound):
    """ Object not found """
    pass
    
class ContainerNotFound(NotFound):
    """ Container not found """
    pass
    
class ResponseError(ObjectStorageError):
    """ Response error """
    def __init__(self, status, reason):
        self.status = status or 0
        self.reason = reason or 'Unknown'
        ObjectStorageError.__init__(self)

    def __str__(self):
        return '%d: %s' % (self.status, self.reason)

    def __repr__(self):
        return '%d: %s' % (self.status, self.reason)
    
