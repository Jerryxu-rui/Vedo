"""
API Resilience Utilities
Provides retry mechanisms, rate limiting, and circuit breaker patterns for external API calls
"""

import asyncio
import time
from typing import Callable, Any, Optional, TypeVar, Dict
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior"""
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection"""
        if self.state == "open":
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = "half_open"
                logger.info(f"Circuit breaker entering half-open state")
            else:
                raise Exception(f"Circuit breaker is OPEN. Service unavailable.")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0
                logger.info(f"Circuit breaker closed after successful call")
            return result
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(f"Circuit breaker OPENED after {self.failure_count} failures")
            
            raise e
    
    async def call_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute async function with circuit breaker protection"""
        if self.state == "open":
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = "half_open"
                logger.info(f"Circuit breaker entering half-open state")
            else:
                raise Exception(f"Circuit breaker is OPEN. Service unavailable.")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0
                logger.info(f"Circuit breaker closed after successful call")
            return result
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(f"Circuit breaker OPENED after {self.failure_count} failures")
            
            raise e


def calculate_backoff_delay(
    attempt: int,
    config: RetryConfig
) -> float:
    """Calculate exponential backoff delay with jitter"""
    delay = min(
        config.initial_delay * (config.exponential_base ** attempt),
        config.max_delay
    )
    
    if config.jitter:
        import random
        delay = delay * (0.5 + random.random() * 0.5)
    
    return delay


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None
):
    """
    Decorator for synchronous functions with exponential backoff retry
    
    Args:
        config: Retry configuration
        on_retry: Optional callback called on each retry attempt
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < config.max_attempts - 1:
                        delay = calculate_backoff_delay(attempt, config)
                        logger.warning(
                            f"Attempt {attempt + 1}/{config.max_attempts} failed: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        
                        if on_retry:
                            on_retry(attempt + 1, e)
                        
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {config.max_attempts} attempts failed. Last error: {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


def async_retry_with_backoff(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None
):
    """
    Decorator for async functions with exponential backoff retry
    
    Args:
        config: Retry configuration
        on_retry: Optional callback called on each retry attempt
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < config.max_attempts - 1:
                        delay = calculate_backoff_delay(attempt, config)
                        logger.warning(
                            f"Attempt {attempt + 1}/{config.max_attempts} failed: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        
                        if on_retry:
                            on_retry(attempt + 1, e)
                        
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {config.max_attempts} attempts failed. Last error: {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


class RequestQueue:
    """Queue for managing rate-limited API requests"""
    def __init__(self, max_concurrent: int = 3, rate_limit_per_second: float = 1.0):
        self.max_concurrent = max_concurrent
        self.rate_limit_per_second = rate_limit_per_second
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.last_request_time = 0.0
        self.lock = asyncio.Lock()
    
    async def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with rate limiting and concurrency control"""
        async with self.semaphore:
            async with self.lock:
                # Enforce rate limit
                current_time = time.time()
                time_since_last = current_time - self.last_request_time
                min_interval = 1.0 / self.rate_limit_per_second
                
                if time_since_last < min_interval:
                    wait_time = min_interval - time_since_last
                    logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                
                self.last_request_time = time.time()
            
            # Execute the function
            return await func(*args, **kwargs)


# Global circuit breakers for different services
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(service_name: str) -> CircuitBreaker:
    """Get or create a circuit breaker for a service"""
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0
        )
    return _circuit_breakers[service_name]


# Example usage:
"""
# Synchronous function with retry
@retry_with_backoff(config=RetryConfig(max_attempts=3))
def fetch_data():
    # API call that might fail
    pass

# Async function with retry
@async_retry_with_backoff(config=RetryConfig(max_attempts=5, initial_delay=2.0))
async def generate_image(prompt: str):
    # API call that might fail
    pass

# Using request queue
queue = RequestQueue(max_concurrent=3, rate_limit_per_second=1.0)
result = await queue.execute(generate_image, "a beautiful landscape")

# Using circuit breaker
breaker = get_circuit_breaker("image_api")
result = await breaker.call_async(generate_image, "a beautiful landscape")
"""