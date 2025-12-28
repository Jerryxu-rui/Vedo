"""
Comprehensive Error Reporting System
Provides structured error tracking, logging, and user-friendly error messages
"""

import traceback
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for classification"""
    VALIDATION = "validation"
    API_CALL = "api_call"
    DATABASE = "database"
    FILE_IO = "file_io"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class ErrorContext:
    """Context information for an error"""
    def __init__(
        self,
        operation: str,
        component: str,
        user_id: Optional[str] = None,
        episode_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        self.operation = operation
        self.component = component
        self.user_id = user_id
        self.episode_id = episode_id
        self.additional_data = additional_data or {}
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "operation": self.operation,
            "component": self.component,
            "user_id": self.user_id,
            "episode_id": self.episode_id,
            "additional_data": self.additional_data,
            "timestamp": self.timestamp
        }


class StructuredError:
    """Structured error with full context"""
    def __init__(
        self,
        error: Exception,
        context: ErrorContext,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        user_message: Optional[str] = None,
        recovery_suggestions: Optional[List[str]] = None
    ):
        self.error = error
        self.context = context
        self.severity = severity
        self.category = category
        self.user_message = user_message or self._generate_user_message()
        self.recovery_suggestions = recovery_suggestions or []
        self.traceback = traceback.format_exc()
        self.error_id = self._generate_error_id()
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID"""
        import hashlib
        content = f"{self.context.timestamp}{self.context.operation}{str(self.error)}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _generate_user_message(self) -> str:
        """Generate user-friendly error message"""
        error_str = str(self.error).lower()
        
        # API-related errors
        if "rate limit" in error_str or "saturated" in error_str:
            return "The service is currently experiencing high demand. Please try again in a few moments."
        elif "timeout" in error_str:
            return "The operation took too long to complete. Please try again."
        elif "connection" in error_str or "network" in error_str:
            return "Unable to connect to the service. Please check your internet connection."
        elif "authentication" in error_str or "unauthorized" in error_str:
            return "Authentication failed. Please check your credentials."
        
        # Validation errors
        elif "validation" in error_str or "invalid" in error_str:
            return f"Invalid input: {str(self.error)}"
        
        # Resource errors
        elif "not found" in error_str:
            return "The requested resource was not found."
        elif "permission" in error_str or "forbidden" in error_str:
            return "You don't have permission to perform this operation."
        
        # Generic error
        else:
            return f"An error occurred: {str(self.error)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "error_id": self.error_id,
            "severity": self.severity,
            "category": self.category,
            "message": self.user_message,
            "technical_details": str(self.error),
            "recovery_suggestions": self.recovery_suggestions,
            "context": self.context.to_dict(),
            "timestamp": self.context.timestamp
        }
    
    def to_log_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging (includes traceback)"""
        return {
            **self.to_dict(),
            "traceback": self.traceback
        }
    
    def log(self):
        """Log the error with appropriate level"""
        log_data = self.to_log_dict()
        log_message = (
            f"[{self.error_id}] {self.category.upper()} in {self.context.component}.{self.context.operation}: "
            f"{str(self.error)}"
        )
        
        if self.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra=log_data)
        elif self.severity == ErrorSeverity.ERROR:
            logger.error(log_message, extra=log_data)
        elif self.severity == ErrorSeverity.WARNING:
            logger.warning(log_message, extra=log_data)
        else:
            logger.info(log_message, extra=log_data)


class ErrorReporter:
    """Central error reporting system"""
    def __init__(self):
        self.errors: List[StructuredError] = []
        self.max_stored_errors = 1000
    
    def report(
        self,
        error: Exception,
        context: ErrorContext,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        user_message: Optional[str] = None,
        recovery_suggestions: Optional[List[str]] = None
    ) -> StructuredError:
        """Report an error with full context"""
        structured_error = StructuredError(
            error=error,
            context=context,
            severity=severity,
            category=category,
            user_message=user_message,
            recovery_suggestions=recovery_suggestions
        )
        
        # Log the error
        structured_error.log()
        
        # Store for retrieval
        self.errors.append(structured_error)
        if len(self.errors) > self.max_stored_errors:
            self.errors.pop(0)
        
        return structured_error
    
    def get_recent_errors(
        self,
        limit: int = 10,
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
        episode_id: Optional[str] = None
    ) -> List[StructuredError]:
        """Get recent errors with optional filtering"""
        filtered = self.errors
        
        if severity:
            filtered = [e for e in filtered if e.severity == severity]
        if category:
            filtered = [e for e in filtered if e.category == category]
        if episode_id:
            filtered = [e for e in filtered if e.context.episode_id == episode_id]
        
        return filtered[-limit:]
    
    def get_error_by_id(self, error_id: str) -> Optional[StructuredError]:
        """Get error by ID"""
        for error in self.errors:
            if error.error_id == error_id:
                return error
        return None
    
    def clear_errors(self, episode_id: Optional[str] = None):
        """Clear errors, optionally filtered by episode"""
        if episode_id:
            self.errors = [e for e in self.errors if e.context.episode_id != episode_id]
        else:
            self.errors.clear()


# Global error reporter instance
error_reporter = ErrorReporter()


def categorize_error(error: Exception) -> ErrorCategory:
    """Automatically categorize an error"""
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()
    
    if "validation" in error_str or "pydantic" in error_type:
        return ErrorCategory.VALIDATION
    elif "rate" in error_str or "saturated" in error_str:
        return ErrorCategory.RATE_LIMIT
    elif "timeout" in error_str or "timeout" in error_type:
        return ErrorCategory.TIMEOUT
    elif "connection" in error_str or "network" in error_str:
        return ErrorCategory.NETWORK
    elif "auth" in error_str or "unauthorized" in error_str:
        return ErrorCategory.AUTHENTICATION
    elif "database" in error_str or "sql" in error_str:
        return ErrorCategory.DATABASE
    elif "file" in error_str or "io" in error_str:
        return ErrorCategory.FILE_IO
    elif "api" in error_str or "request" in error_str:
        return ErrorCategory.API_CALL
    elif "memory" in error_str or "resource" in error_str:
        return ErrorCategory.RESOURCE
    elif "config" in error_str:
        return ErrorCategory.CONFIGURATION
    else:
        return ErrorCategory.UNKNOWN


def get_recovery_suggestions(category: ErrorCategory) -> List[str]:
    """Get recovery suggestions based on error category"""
    suggestions = {
        ErrorCategory.RATE_LIMIT: [
            "Wait a few moments before retrying",
            "Reduce the frequency of requests",
            "Consider upgrading your API plan"
        ],
        ErrorCategory.TIMEOUT: [
            "Try again with a simpler request",
            "Check your internet connection",
            "The service may be experiencing high load"
        ],
        ErrorCategory.NETWORK: [
            "Check your internet connection",
            "Verify the service is accessible",
            "Try again in a few moments"
        ],
        ErrorCategory.AUTHENTICATION: [
            "Verify your API credentials",
            "Check if your API key is still valid",
            "Ensure you have the necessary permissions"
        ],
        ErrorCategory.VALIDATION: [
            "Check your input data format",
            "Ensure all required fields are provided",
            "Verify data types match requirements"
        ],
        ErrorCategory.DATABASE: [
            "Check database connection",
            "Verify database credentials",
            "Ensure database is running"
        ],
        ErrorCategory.FILE_IO: [
            "Check file permissions",
            "Verify file path exists",
            "Ensure sufficient disk space"
        ],
        ErrorCategory.RESOURCE: [
            "Free up system resources",
            "Reduce concurrent operations",
            "Consider upgrading system resources"
        ]
    }
    
    return suggestions.get(category, ["Try again later", "Contact support if the issue persists"])


# Convenience function for quick error reporting
def report_error(
    error: Exception,
    operation: str,
    component: str,
    episode_id: Optional[str] = None,
    user_message: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> StructuredError:
    """Quick error reporting with automatic categorization"""
    category = categorize_error(error)
    suggestions = get_recovery_suggestions(category)
    
    context = ErrorContext(
        operation=operation,
        component=component,
        episode_id=episode_id,
        additional_data=additional_data
    )
    
    return error_reporter.report(
        error=error,
        context=context,
        category=category,
        user_message=user_message,
        recovery_suggestions=suggestions
    )


# Example usage:
"""
try:
    # Some operation that might fail
    result = await generate_image(prompt)
except Exception as e:
    structured_error = report_error(
        error=e,
        operation="generate_image",
        component="image_generator",
        episode_id="episode_123",
        additional_data={"prompt": prompt}
    )
    
    # Return user-friendly error to API
    return {
        "error": structured_error.to_dict()
    }
"""