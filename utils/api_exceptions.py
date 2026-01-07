"""
Unified API Exception Framework
Provides standardized exception handling across all API endpoints
"""

from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import traceback
import logging

from utils.api_response import (
    error_response,
    validation_error_response,
    not_found_response,
    unauthorized_response,
    forbidden_response,
    internal_error_response,
    ErrorDetail
)

# Setup logger
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exception Classes
# ============================================================================

class APIException(Exception):
    """Base exception for all API errors"""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "API_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(APIException):
    """Validation error exception"""
    
    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details or {}
        )
        self.field = field


class NotFoundException(APIException):
    """Resource not found exception"""
    
    def __init__(
        self,
        resource: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        message = f"{resource} not found"
        if resource_id:
            message += f": {resource_id}"
        
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details=details or {}
        )
        self.resource = resource
        self.resource_id = resource_id


class UnauthorizedException(APIException):
    """Unauthorized access exception"""
    
    def __init__(
        self,
        message: str = "Unauthorized access",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
            details=details or {}
        )


class ForbiddenException(APIException):
    """Forbidden access exception"""
    
    def __init__(
        self,
        message: str = "Access forbidden",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
            details=details or {}
        )


class ConflictException(APIException):
    """Resource conflict exception"""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
            details=details or {}
        )


class RateLimitException(APIException):
    """Rate limit exceeded exception"""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details or {}
        )
        self.retry_after = retry_after


class ServiceUnavailableException(APIException):
    """Service unavailable exception"""
    
    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE",
            details=details or {}
        )
        self.retry_after = retry_after


class DatabaseException(APIException):
    """Database operation exception"""
    
    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            details=details or {}
        )
        self.operation = operation


class ExternalServiceException(APIException):
    """External service error exception"""
    
    def __init__(
        self,
        service: str,
        message: str = "External service error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{service}: {message}",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=details or {}
        )
        self.service = service


# ============================================================================
# Exception Handlers
# ============================================================================

async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """
    Handle custom API exceptions
    
    Args:
        request: FastAPI request object
        exc: API exception
    
    Returns:
        JSON response with standardized error format
    """
    logger.error(
        f"API Exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details
        }
    )
    
    errors = [ErrorDetail(
        code=exc.error_code,
        message=exc.message,
        details=exc.details if exc.details else None
    )]
    
    response_data = error_response(
        message=exc.message,
        errors=errors,
        request_id=request.headers.get("X-Request-ID")
    )
    
    # Add retry-after header if applicable
    headers = {}
    if hasattr(exc, 'retry_after') and exc.retry_after:
        headers["Retry-After"] = str(exc.retry_after)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data,
        headers=headers
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors
    
    Args:
        request: FastAPI request object
        exc: Validation error
    
    Returns:
        JSON response with validation error details
    """
    logger.warning(
        f"Validation Error: {request.url.path}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors()
        }
    )
    
    response_data = validation_error_response(
        errors=exc.errors(),
        request_id=request.headers.get("X-Request-ID")
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response_data
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle FastAPI HTTP exceptions
    
    Args:
        request: FastAPI request object
        exc: HTTP exception
    
    Returns:
        JSON response with error details
    """
    logger.error(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    # Map status codes to error codes
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT"
    }
    
    error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")
    
    response_data = error_response(
        message=str(exc.detail),
        error_code=error_code,
        request_id=request.headers.get("X-Request-ID")
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions
    
    Args:
        request: FastAPI request object
        exc: Exception
    
    Returns:
        JSON response with generic error message
    """
    # Log full traceback for debugging
    logger.error(
        f"Unhandled Exception: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc()
        },
        exc_info=True
    )
    
    # Don't expose internal error details in production
    error_details = None
    if logger.level == logging.DEBUG:
        error_details = traceback.format_exc()
    
    response_data = internal_error_response(
        message="An unexpected error occurred",
        error_details=error_details,
        request_id=request.headers.get("X-Request-ID")
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_data
    )


# ============================================================================
# Exception Handler Registration
# ============================================================================

def register_exception_handlers(app):
    """
    Register all exception handlers with FastAPI app
    
    Args:
        app: FastAPI application instance
    
    Example:
        >>> from fastapi import FastAPI
        >>> from utils.api_exceptions import register_exception_handlers
        >>> 
        >>> app = FastAPI()
        >>> register_exception_handlers(app)
    """
    # Custom API exceptions
    app.add_exception_handler(APIException, api_exception_handler)
    
    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    
    # HTTP exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)
    
    # Catch-all for unexpected errors
    app.add_exception_handler(Exception, general_exception_handler)


# ============================================================================
# Utility Functions
# ============================================================================

def raise_not_found(resource: str, resource_id: Optional[str] = None):
    """
    Raise a not found exception
    
    Args:
        resource: Resource type
        resource_id: Resource identifier
    
    Raises:
        NotFoundException
    
    Example:
        >>> raise_not_found("User", "user_123")
    """
    raise NotFoundException(resource, resource_id)


def raise_validation_error(message: str, field: Optional[str] = None):
    """
    Raise a validation exception
    
    Args:
        message: Error message
        field: Field that failed validation
    
    Raises:
        ValidationException
    
    Example:
        >>> raise_validation_error("Invalid email format", field="email")
    """
    raise ValidationException(message, field)


def raise_unauthorized(message: str = "Unauthorized access"):
    """
    Raise an unauthorized exception
    
    Args:
        message: Error message
    
    Raises:
        UnauthorizedException
    """
    raise UnauthorizedException(message)


def raise_forbidden(message: str = "Access forbidden"):
    """
    Raise a forbidden exception
    
    Args:
        message: Error message
    
    Raises:
        ForbiddenException
    """
    raise ForbiddenException(message)


# ============================================================================
# Usage Examples
# ============================================================================

"""
Example Usage in FastAPI Endpoints:

from utils.api_exceptions import (
    NotFoundException,
    ValidationException,
    raise_not_found,
    raise_validation_error
)

@router.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await user_service.get(user_id)
    if not user:
        raise_not_found("User", user_id)
    return success_response("User retrieved", data=user.dict())

@router.post("/users")
async def create_user(user: UserCreate):
    if not is_valid_email(user.email):
        raise_validation_error("Invalid email format", field="email")
    
    try:
        new_user = await user_service.create(user)
        return success_response("User created", data=new_user.dict())
    except DatabaseException as e:
        logger.error(f"Database error: {e}")
        raise

# In main app file (api_server.py):
from utils.api_exceptions import register_exception_handlers

app = FastAPI()
register_exception_handlers(app)
"""