"""
Error Handling Utilities
自定义异常类和错误处理机制
"""

from typing import Optional, Dict, Any, List
from enum import Enum
import traceback
from datetime import datetime


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"           # 可忽略的警告
    MEDIUM = "medium"     # 需要注意但不致命
    HIGH = "high"         # 严重错误，需要人工干预
    CRITICAL = "critical" # 致命错误，系统无法继续


class ErrorCategory(Enum):
    """错误类别"""
    VALIDATION = "validation"           # 输入验证错误
    API = "api"                        # 外部API调用错误
    GENERATION = "generation"          # AI生成错误
    RESOURCE = "resource"              # 资源不足错误
    TIMEOUT = "timeout"                # 超时错误
    NETWORK = "network"                # 网络错误
    FILE_SYSTEM = "file_system"        # 文件系统错误
    DATABASE = "database"              # 数据库错误
    CONFIGURATION = "configuration"    # 配置错误
    UNKNOWN = "unknown"                # 未知错误


class ViMaxError(Exception):
    """ViMax基础异常类"""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        retry_suggested: bool = False,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.recoverable = recoverable
        self.retry_suggested = retry_suggested
        self.original_exception = original_exception
        self.timestamp = datetime.utcnow().isoformat()
        self.stack_trace = traceback.format_exc() if original_exception else None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "recoverable": self.recoverable,
            "retry_suggested": self.retry_suggested,
            "timestamp": self.timestamp,
            "stack_trace": self.stack_trace
        }
    
    def __str__(self) -> str:
        return f"[{self.category.value.upper()}] {self.message}"


class ValidationError(ViMaxError):
    """输入验证错误"""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            details=details,
            recoverable=True,
            retry_suggested=False,
            **kwargs
        )


class APIError(ViMaxError):
    """外部API调用错误"""
    
    def __init__(
        self,
        message: str,
        api_name: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details["api_name"] = api_name
        if status_code:
            details["status_code"] = status_code
        if response_body:
            details["response_body"] = response_body[:500]  # Limit size
        
        super().__init__(
            message=message,
            category=ErrorCategory.API,
            severity=ErrorSeverity.HIGH,
            details=details,
            recoverable=True,
            retry_suggested=True,
            **kwargs
        )


class GenerationError(ViMaxError):
    """AI生成错误"""
    
    def __init__(
        self,
        message: str,
        generation_type: str,
        prompt: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details["generation_type"] = generation_type
        if prompt:
            details["prompt"] = prompt[:200]  # Limit size
        
        super().__init__(
            message=message,
            category=ErrorCategory.GENERATION,
            severity=ErrorSeverity.HIGH,
            details=details,
            recoverable=True,
            retry_suggested=True,
            **kwargs
        )


class ResourceError(ViMaxError):
    """资源不足错误"""
    
    def __init__(
        self,
        message: str,
        resource_type: str,
        required: Optional[Any] = None,
        available: Optional[Any] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details["resource_type"] = resource_type
        if required is not None:
            details["required"] = str(required)
        if available is not None:
            details["available"] = str(available)
        
        super().__init__(
            message=message,
            category=ErrorCategory.RESOURCE,
            severity=ErrorSeverity.CRITICAL,
            details=details,
            recoverable=False,
            retry_suggested=False,
            **kwargs
        )


class TimeoutError(ViMaxError):
    """超时错误"""
    
    def __init__(
        self,
        message: str,
        operation: str,
        timeout_seconds: Optional[float] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details["operation"] = operation
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        
        super().__init__(
            message=message,
            category=ErrorCategory.TIMEOUT,
            severity=ErrorSeverity.HIGH,
            details=details,
            recoverable=True,
            retry_suggested=True,
            **kwargs
        )


class NetworkError(ViMaxError):
    """网络错误"""
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if url:
            details["url"] = url
        
        super().__init__(
            message=message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH,
            details=details,
            recoverable=True,
            retry_suggested=True,
            **kwargs
        )


class FileSystemError(ViMaxError):
    """文件系统错误"""
    
    def __init__(
        self,
        message: str,
        path: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if path:
            details["path"] = path
        if operation:
            details["operation"] = operation
        
        super().__init__(
            message=message,
            category=ErrorCategory.FILE_SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            recoverable=True,
            retry_suggested=False,
            **kwargs
        )


class DatabaseError(ViMaxError):
    """数据库错误"""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if operation:
            details["operation"] = operation
        if table:
            details["table"] = table
        
        super().__init__(
            message=message,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            details=details,
            recoverable=True,
            retry_suggested=True,
            **kwargs
        )


class ConfigurationError(ViMaxError):
    """配置错误"""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if config_key:
            details["config_key"] = config_key
        if config_file:
            details["config_file"] = config_file
        
        super().__init__(
            message=message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.CRITICAL,
            details=details,
            recoverable=False,
            retry_suggested=False,
            **kwargs
        )


class ErrorContext:
    """错误上下文管理器"""
    
    def __init__(self):
        self.errors: List[ViMaxError] = []
        self.warnings: List[ViMaxError] = []
    
    def add_error(self, error: ViMaxError):
        """添加错误"""
        if error.severity in [ErrorSeverity.LOW, ErrorSeverity.MEDIUM]:
            self.warnings.append(error)
        else:
            self.errors.append(error)
    
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """是否有警告"""
        return len(self.warnings) > 0
    
    def get_critical_errors(self) -> List[ViMaxError]:
        """获取致命错误"""
        return [e for e in self.errors if e.severity == ErrorSeverity.CRITICAL]
    
    def get_recoverable_errors(self) -> List[ViMaxError]:
        """获取可恢复的错误"""
        return [e for e in self.errors if e.recoverable]
    
    def clear(self):
        """清空错误"""
        self.errors.clear()
        self.warnings.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "has_errors": self.has_errors(),
            "has_warnings": self.has_warnings(),
            "critical_count": len(self.get_critical_errors()),
            "recoverable_count": len(self.get_recoverable_errors())
        }


def wrap_exception(
    exception: Exception,
    message: Optional[str] = None,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    **kwargs
) -> ViMaxError:
    """
    将标准异常包装为ViMaxError
    
    Args:
        exception: 原始异常
        message: 自定义错误消息
        category: 错误类别
        **kwargs: 其他参数
    
    Returns:
        ViMaxError实例
    """
    error_message = message or str(exception)
    
    # 根据异常类型选择合适的ViMaxError子类
    if isinstance(exception, ValueError):
        return ValidationError(
            message=error_message,
            original_exception=exception,
            **kwargs
        )
    elif isinstance(exception, ConnectionError):
        return NetworkError(
            message=error_message,
            original_exception=exception,
            **kwargs
        )
    elif isinstance(exception, FileNotFoundError):
        return FileSystemError(
            message=error_message,
            operation="read",
            original_exception=exception,
            **kwargs
        )
    elif isinstance(exception, PermissionError):
        return FileSystemError(
            message=error_message,
            operation="permission",
            original_exception=exception,
            **kwargs
        )
    else:
        return ViMaxError(
            message=error_message,
            category=category,
            original_exception=exception,
            **kwargs
        )


def format_error_for_user(error: ViMaxError) -> str:
    """
    格式化错误消息供用户查看
    
    Args:
        error: ViMaxError实例
    
    Returns:
        格式化的错误消息
    """
    message = f"❌ {error.message}\n"
    
    if error.severity == ErrorSeverity.CRITICAL:
        message += "\n⚠️ This is a critical error that requires immediate attention.\n"
    
    if error.retry_suggested:
        message += "\n🔄 You may try again. The operation might succeed on retry.\n"
    
    if not error.recoverable:
        message += "\n⛔ This error cannot be automatically recovered. Manual intervention required.\n"
    
    if error.details:
        message += "\n📋 Details:\n"
        for key, value in error.details.items():
            message += f"  • {key}: {value}\n"
    
    return message


def format_error_for_log(error: ViMaxError) -> str:
    """
    格式化错误消息供日志记录
    
    Args:
        error: ViMaxError实例
    
    Returns:
        格式化的日志消息
    """
    log_message = f"[{error.category.value.upper()}] [{error.severity.value.upper()}] {error.message}\n"
    log_message += f"Timestamp: {error.timestamp}\n"
    log_message += f"Recoverable: {error.recoverable}\n"
    log_message += f"Retry Suggested: {error.retry_suggested}\n"
    
    if error.details:
        log_message += "Details:\n"
        for key, value in error.details.items():
            log_message += f"  {key}: {value}\n"
    
    if error.stack_trace:
        log_message += f"\nStack Trace:\n{error.stack_trace}\n"
    
    return log_message