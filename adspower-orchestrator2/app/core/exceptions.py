# app/core/exceptions.py
from fastapi import HTTPException, status

class AdsPowerException(Exception):
    """Base exception for AdsPower related errors"""
    pass

class AdsPowerConnectionError(AdsPowerException):
    """AdsPower connection error"""
    pass

class AdsPowerAPIError(AdsPowerException):
    """AdsPower API error"""
    pass

class ProxyException(Exception):
    """Base exception for Proxy related errors"""
    pass

class ProxyTestFailed(ProxyException):
    """Proxy test failed"""
    pass

class ProfileException(Exception):
    """Base exception for Profile related errors"""
    pass

class ProfileNotFound(ProfileException):
    """Profile not found"""
    pass

class ComputerException(Exception):
    """Base exception for Computer related errors"""
    pass

class ComputerNotAvailable(ComputerException):
    """Computer not available"""
    pass

# HTTP Exceptions
def not_found_exception(detail: str = "Resource not found"):
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

def bad_request_exception(detail: str = "Bad request"):
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

def unauthorized_exception(detail: str = "Unauthorized"):
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

def forbidden_exception(detail: str = "Forbidden"):
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

def internal_server_exception(detail: str = "Internal server error"):
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)