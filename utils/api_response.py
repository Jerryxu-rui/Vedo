"""
Unified API Response Format
Provides standardized response structure across all API endpoints
"""

from typing import Any, Optional, Dict, List, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ResponseStatus(str, Enum):
    """Response status enum"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PARTIAL = "partial"


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class ErrorDetail(BaseModel):
    """Error detail structure"""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    field: Optional[str] = Field(None, description="Field that caused the error")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class StandardResponse(BaseModel):
    """
    Standard API response format
    
    All API endpoints should return responses in this format for consistency
    """
    status: ResponseStatus = Field(..., description="Response status")
    message: str = Field(..., description="Human-readable message")
    data: Optional[Any] = Field(None, description="Response data")
    
    # Metadata
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Response timestamp")
    request_id: Optional[str] = Field(None, description="Request tracking ID")
    
    # Pagination (for list endpoints)
    pagination: Optional[PaginationMeta] = Field(None, description="Pagination metadata")
    
    # Errors (for error responses)
    errors: Optional[List[ErrorDetail]] = Field(None, description="List of errors")
    
    # Deprecation warnings
    deprecated: Optional[bool] = Field(None, description="Whether this endpoint is deprecated")
    deprecation_message: Optional[str] = Field(None, description="Deprecation notice")
    migration_guide: Optional[str] = Field(None, description="Migration guide URL or text")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "data": {"id": "123", "name": "Example"},
                "timestamp": "2025-12-29T14:00:00Z",
                "request_id": "req_abc123"
            }
        }


class SuccessResponse(StandardResponse):
    """Success response helper"""
    status: ResponseStatus = ResponseStatus.SUCCESS


class ErrorResponse(StandardResponse):
    """Error response helper"""
    status: ResponseStatus = ResponseStatus.ERROR
    data: None = None


class WarningResponse(StandardResponse):
    """Warning response helper"""
    status: ResponseStatus = ResponseStatus.WARNING


# ============================================================================
# Response Builder Functions
# ============================================================================

def success_response(
    message: str,
    data: Any = None,
    request_id: Optional[str] = None,
    pagination: Optional[PaginationMeta] = None
) -> Dict[str, Any]:
    """
    Create a success response
    
    Args:
        message: Success message
        data: Response data
        request_id: Request tracking ID
        pagination: Pagination metadata
    
    Returns:
        Standardized success response dictionary
    
    Example:
        >>> success_response("User created", data={"id": "123", "name": "John"})
        {
            "status": "success",
            "message": "User created",
            "data": {"id": "123", "name": "John"},
            "timestamp": "2025-12-29T14:00:00Z"
        }
    """
    response = SuccessResponse(
        message=message,
        data=data,
        request_id=request_id,
        pagination=pagination
    )
    return response.model_dump(exclude_none=True)


def error_response(
    message: str,
    errors: Optional[List[ErrorDetail]] = None,
    error_code: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create an error response
    
    Args:
        message: Error message
        errors: List of error details
        error_code: Error code
        request_id: Request tracking ID
    
    Returns:
        Standardized error response dictionary
    
    Example:
        >>> error_response("Validation failed", errors=[
        ...     ErrorDetail(code="INVALID_EMAIL", message="Invalid email format", field="email")
        ... ])
    """
    if errors is None and error_code:
        errors = [ErrorDetail(code=error_code, message=message)]
    
    response = ErrorResponse(
        message=message,
        errors=errors,
        request_id=request_id
    )
    return response.model_dump(exclude_none=True)


def warning_response(
    message: str,
    data: Any = None,
    warnings: Optional[List[str]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a warning response
    
    Args:
        message: Warning message
        data: Response data
        warnings: List of warning messages
        request_id: Request tracking ID
    
    Returns:
        Standardized warning response dictionary
    """
    response = WarningResponse(
        message=message,
        data=data,
        request_id=request_id
    )
    result = response.model_dump(exclude_none=True)
    if warnings:
        result["warnings"] = warnings
    return result


def deprecated_response(
    message: str,
    data: Any = None,
    deprecation_message: str = "This endpoint is deprecated",
    migration_guide: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a deprecated endpoint response
    
    Args:
        message: Success message
        data: Response data
        deprecation_message: Deprecation notice
        migration_guide: Migration guide
        request_id: Request tracking ID
    
    Returns:
        Standardized response with deprecation warning
    
    Example:
        >>> deprecated_response(
        ...     "Job created",
        ...     data={"job_id": "123"},
        ...     deprecation_message="Use POST /api/v1/videos/generate instead",
        ...     migration_guide="https://docs.example.com/migration"
        ... )
    """
    response = SuccessResponse(
        message=message,
        data=data,
        request_id=request_id,
        deprecated=True,
        deprecation_message=deprecation_message,
        migration_guide=migration_guide
    )
    return response.model_dump(exclude_none=True)


def paginated_response(
    message: str,
    items: List[Any],
    total: int,
    page: int,
    page_size: int,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a paginated response
    
    Args:
        message: Success message
        items: List of items for current page
        total: Total number of items
        page: Current page number (1-indexed)
        page_size: Items per page
        request_id: Request tracking ID
    
    Returns:
        Standardized paginated response
    
    Example:
        >>> paginated_response(
        ...     "Users retrieved",
        ...     items=[{"id": "1"}, {"id": "2"}],
        ...     total=100,
        ...     page=1,
        ...     page_size=10
        ... )
    """
    total_pages = (total + page_size - 1) // page_size  # Ceiling division
    
    pagination = PaginationMeta(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )
    
    return success_response(
        message=message,
        data={"items": items},
        pagination=pagination,
        request_id=request_id
    )


# ============================================================================
# Exception Response Builders
# ============================================================================

def validation_error_response(
    errors: List[Dict[str, Any]],
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a validation error response from Pydantic validation errors
    
    Args:
        errors: List of validation errors from Pydantic
        request_id: Request tracking ID
    
    Returns:
        Standardized validation error response
    """
    error_details = [
        ErrorDetail(
            code="VALIDATION_ERROR",
            message=error.get("msg", "Validation failed"),
            field=".".join(str(loc) for loc in error.get("loc", [])),
            details={"type": error.get("type")}
        )
        for error in errors
    ]
    
    return error_response(
        message="Request validation failed",
        errors=error_details,
        request_id=request_id
    )


def not_found_response(
    resource: str,
    resource_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a not found error response
    
    Args:
        resource: Resource type (e.g., "User", "Job", "Episode")
        resource_id: Resource identifier
        request_id: Request tracking ID
    
    Returns:
        Standardized not found response
    """
    message = f"{resource} not found"
    if resource_id:
        message += f": {resource_id}"
    
    return error_response(
        message=message,
        error_code="NOT_FOUND",
        request_id=request_id
    )


def unauthorized_response(
    message: str = "Unauthorized access",
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create an unauthorized error response"""
    return error_response(
        message=message,
        error_code="UNAUTHORIZED",
        request_id=request_id
    )


def forbidden_response(
    message: str = "Access forbidden",
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a forbidden error response"""
    return error_response(
        message=message,
        error_code="FORBIDDEN",
        request_id=request_id
    )


def internal_error_response(
    message: str = "Internal server error",
    error_details: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create an internal server error response
    
    Args:
        message: Error message
        error_details: Detailed error information (for debugging)
        request_id: Request tracking ID
    
    Returns:
        Standardized internal error response
    """
    errors = [ErrorDetail(
        code="INTERNAL_ERROR",
        message=message,
        details={"error": error_details} if error_details else None
    )]
    
    return error_response(
        message=message,
        errors=errors,
        request_id=request_id
    )


# ============================================================================
# Response Middleware Helper
# ============================================================================

def wrap_response(data: Any, status_code: int = 200) -> Dict[str, Any]:
    """
    Automatically wrap any response data in standard format
    
    Args:
        data: Response data (can be dict, list, or any serializable type)
        status_code: HTTP status code
    
    Returns:
        Standardized response
    """
    # If already in standard format, return as-is
    if isinstance(data, dict) and "status" in data and "message" in data:
        return data
    
    # Determine message based on status code
    if status_code >= 200 and status_code < 300:
        message = "Operation successful"
        status = ResponseStatus.SUCCESS
    elif status_code >= 400 and status_code < 500:
        message = "Client error"
        status = ResponseStatus.ERROR
    elif status_code >= 500:
        message = "Server error"
        status = ResponseStatus.ERROR
    else:
        message = "Operation completed"
        status = ResponseStatus.SUCCESS
    
    return StandardResponse(
        status=status,
        message=message,
        data=data
    ).model_dump(exclude_none=True)


# ============================================================================
# Usage Examples
# ============================================================================

"""
Example Usage in FastAPI Endpoints:

from utils.api_response import success_response, error_response, paginated_response

@router.post("/users")
async def create_user(user: UserCreate):
    try:
        new_user = await user_service.create(user)
        return success_response(
            message="User created successfully",
            data=new_user.dict()
        )
    except ValidationError as e:
        return validation_error_response(e.errors())
    except Exception as e:
        return internal_error_response(str(e))

@router.get("/users")
async def list_users(page: int = 1, page_size: int = 10):
    users, total = await user_service.list(page, page_size)
    return paginated_response(
        message="Users retrieved successfully",
        items=[u.dict() for u in users],
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await user_service.get(user_id)
    if not user:
        return not_found_response("User", user_id)
    return success_response(
        message="User retrieved successfully",
        data=user.dict()
    )
"""