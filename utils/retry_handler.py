"""
Production-ready intelligent retry mechanism for ViMax platform.

This module provides a comprehensive retry handler with:
- Exponential backoff with jitter
- Sophisticated error classification
- Circuit breaker pattern
- Detailed structured logging
- Metrics collection
- Provider-specific retry policies
"""

import time
import asyncio
import logging
import random
import uuid
from typing import Callable, Any, Optional, Dict, Type, Union, List
from functools import wraps
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import threading


# ============================================================================
# Error Classification
# ============================================================================

class ErrorType(Enum):
    """Error type classification for retry decisions."""
    RETRIABLE = "retriable"                    # Temporary errors, safe to retry
    NON_RETRIABLE = "non_retriable"           # Permanent errors, don't retry
    RATE_LIMIT = "rate_limit"                 # API rate limiting
    INSUFFICIENT_BALANCE = "insufficient_balance"  # Quota/balance exhausted
    TIMEOUT = "timeout"                       # Network timeout
    SERVICE_UNAVAILABLE = "service_unavailable"  # Temporary service issues
    MODEL_ERROR = "model_error"               # Model-specific errors


class ErrorClassifier:
    """Classifies exceptions into retry categories."""
    
    # Error patterns for classification
    RETRIABLE_PATTERNS = [
        "timeout", "connection", "network", "temporary",
        "unavailable", "503", "502", "504", "429"
    ]
    
    NON_RETRIABLE_PATTERNS = [
        "invalid", "not found", "404", "400", "unauthorized",
        "forbidden", "403", "401", "bad request"
    ]
    
    RATE_LIMIT_PATTERNS = [
        "rate limit", "too many requests", "429", "quota exceeded"
    ]
    
    BALANCE_PATTERNS = [
        "insufficient", "balance", "quota", "credit", "limit exceeded"
    ]
    
    @classmethod
    def classify(cls, error: Exception) -> ErrorType:
        """
        Classify an exception into an error type.
        
        Args:
            error: The exception to classify
            
        Returns:
            ErrorType: The classified error type
        """
        error_msg = str(error).lower()
        error_type_name = type(error).__name__.lower()
        
        # Check for specific exception types first
        if "timeout" in error_type_name:
            return ErrorType.TIMEOUT
        
        # Check balance/quota issues
        if any(pattern in error_msg for pattern in cls.BALANCE_PATTERNS):
            return ErrorType.INSUFFICIENT_BALANCE
        
        # Check rate limiting
        if any(pattern in error_msg for pattern in cls.RATE_LIMIT_PATTERNS):
            return ErrorType.RATE_LIMIT
        
        # Check non-retriable errors
        if any(pattern in error_msg for pattern in cls.NON_RETRIABLE_PATTERNS):
            return ErrorType.NON_RETRIABLE
        
        # Check retriable errors
        if any(pattern in error_msg for pattern in cls.RETRIABLE_PATTERNS):
            return ErrorType.RETRIABLE
        
        # Default to retriable for unknown errors
        return ErrorType.RETRIABLE


# ============================================================================
# Retry Configuration
# ============================================================================

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    
    # Basic retry settings
    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: tuple[float, float] = (0.5, 1.5)
    
    # Timeout settings
    timeout: Optional[float] = None
    
    # Error-specific settings
    retry_on_timeout: bool = True
    retry_on_rate_limit: bool = True
    retry_on_service_unavailable: bool = True
    
    # Circuit breaker settings
    circuit_breaker_enabled: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0
    
    # Logging settings
    log_level: int = logging.INFO
    log_retries: bool = True
    log_success: bool = False


# Provider-specific configurations
PROVIDER_CONFIGS: Dict[str, RetryConfig] = {
    "openai": RetryConfig(
        max_retries=5,
        base_delay=1.0,
        max_delay=60.0,
        exponential_base=2.0,
        circuit_breaker_threshold=10
    ),
    "anthropic": RetryConfig(
        max_retries=5,
        base_delay=1.0,
        max_delay=60.0,
        exponential_base=2.0,
        circuit_breaker_threshold=10
    ),
    "minimax": RetryConfig(
        max_retries=5,
        base_delay=2.0,
        max_delay=120.0,
        exponential_base=2.0,
        circuit_breaker_threshold=8
    ),
    "runway": RetryConfig(
        max_retries=3,
        base_delay=5.0,
        max_delay=300.0,
        exponential_base=2.0,
        circuit_breaker_threshold=5
    ),
    "luma": RetryConfig(
        max_retries=3,
        base_delay=5.0,
        max_delay=300.0,
        exponential_base=2.0,
        circuit_breaker_threshold=5
    ),
    "kling": RetryConfig(
        max_retries=3,
        base_delay=5.0,
        max_delay=300.0,
        exponential_base=2.0,
        circuit_breaker_threshold=5
    ),
    "default": RetryConfig()
}


# ============================================================================
# Circuit Breaker
# ============================================================================

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.
    
    Implements the circuit breaker pattern to fail fast when
    a service is consistently failing.
    """
    
    threshold: int = 5
    timeout: float = 60.0
    
    # Internal state
    failure_count: int = field(default=0, init=False)
    last_failure_time: Optional[datetime] = field(default=None, init=False)
    state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    
    def record_success(self):
        """Record a successful call."""
        with self._lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED
    
    def record_failure(self):
        """Record a failed call."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.threshold:
                self.state = CircuitState.OPEN
    
    def can_attempt(self) -> bool:
        """Check if a call attempt is allowed."""
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            if self.state == CircuitState.OPEN:
                # Check if timeout has passed
                if self.last_failure_time:
                    elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                    if elapsed >= self.timeout:
                        self.state = CircuitState.HALF_OPEN
                        return True
                return False
            
            # HALF_OPEN state - allow one attempt
            return True
    
    def reset(self):
        """Reset the circuit breaker."""
        with self._lock:
            self.failure_count = 0
            self.last_failure_time = None
            self.state = CircuitState.CLOSED


# ============================================================================
# Metrics Collection
# ============================================================================

@dataclass
class RetryMetrics:
    """Metrics for monitoring retry behavior."""
    
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    retry_counts: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    error_types: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    total_latency: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    
    def record_attempt(self, success: bool, retries: int, latency: float, error_type: Optional[str] = None):
        """Record a retry attempt."""
        with self._lock:
            self.total_attempts += 1
            if success:
                self.successful_attempts += 1
            else:
                self.failed_attempts += 1
            
            self.retry_counts[retries] += 1
            self.total_latency += latency
            
            if error_type:
                self.error_types[error_type] += 1
    
    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_attempts == 0:
            return 0.0
        return self.successful_attempts / self.total_attempts
    
    def get_average_latency(self) -> float:
        """Calculate average latency."""
        if self.total_attempts == 0:
            return 0.0
        return self.total_latency / self.total_attempts
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        return {
            "total_attempts": self.total_attempts,
            "successful_attempts": self.successful_attempts,
            "failed_attempts": self.failed_attempts,
            "success_rate": self.get_success_rate(),
            "average_latency": self.get_average_latency(),
            "retry_distribution": dict(self.retry_counts),
            "error_distribution": dict(self.error_types)
        }


# ============================================================================
# Retry Handler
# ============================================================================

class RetryHandler:
    """
    Production-ready retry handler with comprehensive features.
    
    Features:
    - Exponential backoff with jitter
    - Error classification
    - Circuit breaker pattern
    - Metrics collection
    - Structured logging
    - Provider-specific policies
    - Thread-safe operations
    
    Example:
        >>> retry_handler = RetryHandler(provider="openai")
        >>> 
        >>> @retry_handler
        >>> async def call_api():
        >>>     return await some_api_call()
    """
    
    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        provider: str = "default",
        correlation_id: Optional[str] = None
    ):
        """
        Initialize retry handler.
        
        Args:
            config: Retry configuration (uses provider default if None)
            provider: API provider name for provider-specific config
            correlation_id: Correlation ID for request tracking
        """
        self.config = config or PROVIDER_CONFIGS.get(provider, PROVIDER_CONFIGS["default"])
        self.provider = provider
        self.correlation_id = correlation_id or str(uuid.uuid4())
        
        # Initialize components
        self.circuit_breaker = CircuitBreaker(
            threshold=self.config.circuit_breaker_threshold,
            timeout=self.config.circuit_breaker_timeout
        ) if self.config.circuit_breaker_enabled else None
        
        self.metrics = RetryMetrics()
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup structured logger."""
        logger = logging.getLogger(f"retry_handler.{self.provider}")
        logger.setLevel(self.config.log_level)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - '
                f'[{self.correlation_id}] - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay with exponential backoff and jitter.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            float: Delay in seconds
        """
        # Exponential backoff
        delay = min(
            self.config.base_delay * (self.config.exponential_base ** attempt),
            self.config.max_delay
        )
        
        # Add jitter to prevent thundering herd
        if self.config.jitter:
            jitter_min, jitter_max = self.config.jitter_range
            delay = delay * random.uniform(jitter_min, jitter_max)
        
        return delay
    
    def _should_retry(self, error: Exception, attempt: int) -> tuple[bool, ErrorType]:
        """
        Determine if an error should be retried.
        
        Args:
            error: The exception that occurred
            attempt: Current attempt number
            
        Returns:
            tuple: (should_retry, error_type)
        """
        # Classify error
        error_type = ErrorClassifier.classify(error)
        
        # Check if max retries exceeded
        if attempt >= self.config.max_retries:
            return False, error_type
        
        # Check circuit breaker
        if self.circuit_breaker and not self.circuit_breaker.can_attempt():
            self.logger.warning(
                f"Circuit breaker OPEN, rejecting retry attempt {attempt + 1}"
            )
            return False, error_type
        
        # Determine retry based on error type
        if error_type == ErrorType.NON_RETRIABLE:
            return False, error_type
        
        if error_type == ErrorType.INSUFFICIENT_BALANCE:
            return False, error_type
        
        if error_type == ErrorType.TIMEOUT and not self.config.retry_on_timeout:
            return False, error_type
        
        if error_type == ErrorType.RATE_LIMIT and not self.config.retry_on_rate_limit:
            return False, error_type
        
        if error_type == ErrorType.SERVICE_UNAVAILABLE and not self.config.retry_on_service_unavailable:
            return False, error_type
        
        return True, error_type
    
    def __call__(self, func: Callable) -> Callable:
        """
        Decorator to add retry logic to a function.
        
        Args:
            func: Function to wrap with retry logic
            
        Returns:
            Wrapped function with retry capability
        """
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            """Async wrapper with retry logic."""
            start_time = time.time()
            last_exception = None
            attempt = 0
            
            while attempt < self.config.max_retries:
                try:
                    # Check circuit breaker
                    if self.circuit_breaker and not self.circuit_breaker.can_attempt():
                        raise RuntimeError(
                            f"Circuit breaker OPEN for provider {self.provider}"
                        )
                    
                    # Apply timeout if configured
                    if self.config.timeout:
                        result = await asyncio.wait_for(
                            func(*args, **kwargs),
                            timeout=self.config.timeout
                        )
                    else:
                        result = await func(*args, **kwargs)
                    
                    # Success - record metrics and return
                    latency = time.time() - start_time
                    self.metrics.record_attempt(True, attempt, latency)
                    
                    if self.circuit_breaker:
                        self.circuit_breaker.record_success()
                    
                    if self.config.log_success:
                        self.logger.info(
                            f"Success after {attempt} retries, latency: {latency:.2f}s"
                        )
                    
                    return result
                
                except Exception as e:
                    last_exception = e
                    should_retry, error_type = self._should_retry(e, attempt)
                    
                    # Record circuit breaker failure
                    if self.circuit_breaker:
                        self.circuit_breaker.record_failure()
                    
                    # Log the error
                    if self.config.log_retries:
                        self.logger.warning(
                            f"Attempt {attempt + 1}/{self.config.max_retries} failed: "
                            f"{type(e).__name__}: {str(e)}\n"
                            f"Error type: {error_type.value}\n"
                            f"Will retry: {should_retry}"
                        )
                    
                    # Don't retry if not appropriate
                    if not should_retry:
                        latency = time.time() - start_time
                        self.metrics.record_attempt(False, attempt, latency, error_type.value)
                        raise
                    
                    # Calculate and apply delay
                    if attempt < self.config.max_retries - 1:
                        delay = self._calculate_delay(attempt)
                        self.logger.info(f"Waiting {delay:.2f}s before retry...")
                        await asyncio.sleep(delay)
                    
                    attempt += 1
            
            # All retries exhausted
            latency = time.time() - start_time
            self.metrics.record_attempt(False, attempt, latency, error_type.value)
            
            self.logger.error(
                f"All {self.config.max_retries} retry attempts exhausted. "
                f"Last error: {type(last_exception).__name__}: {str(last_exception)}"
            )
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            """Sync wrapper with retry logic."""
            start_time = time.time()
            last_exception = None
            attempt = 0
            
            while attempt < self.config.max_retries:
                try:
                    # Check circuit breaker
                    if self.circuit_breaker and not self.circuit_breaker.can_attempt():
                        raise RuntimeError(
                            f"Circuit breaker OPEN for provider {self.provider}"
                        )
                    
                    result = func(*args, **kwargs)
                    
                    # Success
                    latency = time.time() - start_time
                    self.metrics.record_attempt(True, attempt, latency)
                    
                    if self.circuit_breaker:
                        self.circuit_breaker.record_success()
                    
                    if self.config.log_success:
                        self.logger.info(
                            f"Success after {attempt} retries, latency: {latency:.2f}s"
                        )
                    
                    return result
                
                except Exception as e:
                    last_exception = e
                    should_retry, error_type = self._should_retry(e, attempt)
                    
                    if self.circuit_breaker:
                        self.circuit_breaker.record_failure()
                    
                    if self.config.log_retries:
                        self.logger.warning(
                            f"Attempt {attempt + 1}/{self.config.max_retries} failed: "
                            f"{type(e).__name__}: {str(e)}\n"
                            f"Error type: {error_type.value}\n"
                            f"Will retry: {should_retry}"
                        )
                    
                    if not should_retry:
                        latency = time.time() - start_time
                        self.metrics.record_attempt(False, attempt, latency, error_type.value)
                        raise
                    
                    if attempt < self.config.max_retries - 1:
                        delay = self._calculate_delay(attempt)
                        self.logger.info(f"Waiting {delay:.2f}s before retry...")
                        time.sleep(delay)
                    
                    attempt += 1
            
            # All retries exhausted
            latency = time.time() - start_time
            self.metrics.record_attempt(False, attempt, latency, error_type.value)
            
            self.logger.error(
                f"All {self.config.max_retries} retry attempts exhausted. "
                f"Last error: {type(last_exception).__name__}: {str(last_exception)}"
            )
            raise last_exception
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get retry metrics."""
        return self.metrics.get_stats()
    
    def reset_metrics(self):
        """Reset metrics collection."""
        self.metrics = RetryMetrics()
    
    def reset_circuit_breaker(self):
        """Reset circuit breaker state."""
        if self.circuit_breaker:
            self.circuit_breaker.reset()


# ============================================================================
# Context Manager for Resource Cleanup
# ============================================================================

class RetryContext:
    """
    Context manager for retry operations with automatic cleanup.
    
    Example:
        >>> async with RetryContext(provider="openai") as retry:
        >>>     result = await retry(api_call)()
    """
    
    def __init__(self, provider: str = "default", **kwargs):
        """Initialize retry context."""
        self.provider = provider
        self.kwargs = kwargs
        self.handler: Optional[RetryHandler] = None
    
    async def __aenter__(self) -> RetryHandler:
        """Enter async context."""
        self.handler = RetryHandler(provider=self.provider, **self.kwargs)
        return self.handler
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context with cleanup."""
        if self.handler:
            # Log final metrics
            metrics = self.handler.get_metrics()
            self.handler.logger.info(f"Final metrics: {metrics}")
        return False
    
    def __enter__(self) -> RetryHandler:
        """Enter sync context."""
        self.handler = RetryHandler(provider=self.provider, **self.kwargs)
        return self.handler
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit sync context with cleanup."""
        if self.handler:
            metrics = self.handler.get_metrics()
            self.handler.logger.info(f"Final metrics: {metrics}")
        return False


# ============================================================================
# Convenience Functions
# ============================================================================

def create_retry_handler(
    provider: str = "default",
    max_retries: int = 5,
    **kwargs
) -> RetryHandler:
    """
    Create a retry handler with custom configuration.
    
    Args:
        provider: API provider name
        max_retries: Maximum number of retry attempts
        **kwargs: Additional configuration parameters
        
    Returns:
        RetryHandler: Configured retry handler
    """
    config = PROVIDER_CONFIGS.get(provider, PROVIDER_CONFIGS["default"])
    config.max_retries = max_retries
    
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return RetryHandler(config=config, provider=provider)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    provider: str = "default"
):
    """
    Simple decorator for retry with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        provider: API provider name
        
    Returns:
        Decorator function
        
    Example:
        >>> @retry_with_backoff(max_retries=3, base_delay=1.0)
        >>> async def my_function():
        >>>     return await api_call()
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay
    )
    return RetryHandler(config=config, provider=provider)


# ============================================================================
# Export Public API
# ============================================================================

__all__ = [
    "RetryHandler",
    "RetryConfig",
    "RetryContext",
    "ErrorType",
    "ErrorClassifier",
    "CircuitBreaker",
    "CircuitState",
    "RetryMetrics",
    "PROVIDER_CONFIGS",
    "create_retry_handler",
    "retry_with_backoff"
]