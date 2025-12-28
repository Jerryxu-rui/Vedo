"""
Error Recovery Strategies
错误恢复策略和机制
"""

from typing import Optional, Callable, Any, Dict, List
from enum import Enum
import asyncio
import time
from functools import wraps
import logging

from utils.error_handling import (
    ViMaxError, ErrorCategory, ErrorSeverity,
    APIError, TimeoutError, NetworkError, GenerationError
)

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """恢复策略"""
    RETRY = "retry"                    # 重试
    FALLBACK = "fallback"              # 降级/备用方案
    SKIP = "skip"                      # 跳过
    ABORT = "abort"                    # 中止
    MANUAL = "manual"                  # 需要人工干预
    CIRCUIT_BREAKER = "circuit_breaker"  # 熔断器


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常状态
    OPEN = "open"          # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态


class CircuitBreaker:
    """
    熔断器模式实现
    防止对失败的服务进行过多的重试
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        """
        Args:
            failure_threshold: 失败次数阈值
            recovery_timeout: 恢复超时时间（秒）
            expected_exception: 预期的异常类型
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        通过熔断器调用函数
        
        Args:
            func: 要调用的函数
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            函数返回值
        
        Raises:
            Exception: 如果熔断器打开或函数调用失败
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception(
                    f"Circuit breaker is OPEN. "
                    f"Service unavailable. "
                    f"Will retry after {self.recovery_timeout}s"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """异步版本的call"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception(
                    f"Circuit breaker is OPEN. "
                    f"Service unavailable. "
                    f"Will retry after {self.recovery_timeout}s"
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """是否应该尝试重置"""
        return (
            self.last_failure_time is not None and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """成功时的处理"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        logger.info(f"Circuit breaker reset to CLOSED state")
    
    def _on_failure(self):
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )


class ErrorRecoveryManager:
    """错误恢复管理器"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.recovery_history: List[Dict[str, Any]] = []
    
    def get_circuit_breaker(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0
    ) -> CircuitBreaker:
        """
        获取或创建熔断器
        
        Args:
            service_name: 服务名称
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时
        
        Returns:
            CircuitBreaker实例
        """
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout
            )
        return self.circuit_breakers[service_name]
    
    def determine_strategy(self, error: ViMaxError) -> RecoveryStrategy:
        """
        根据错误类型确定恢复策略
        
        Args:
            error: ViMaxError实例
        
        Returns:
            RecoveryStrategy
        """
        # 致命错误 - 中止
        if error.severity == ErrorSeverity.CRITICAL:
            return RecoveryStrategy.ABORT
        
        # 不可恢复的错误 - 需要人工干预
        if not error.recoverable:
            return RecoveryStrategy.MANUAL
        
        # 建议重试的错误 - 重试
        if error.retry_suggested:
            return RecoveryStrategy.RETRY
        
        # API错误 - 使用熔断器
        if error.category == ErrorCategory.API:
            return RecoveryStrategy.CIRCUIT_BREAKER
        
        # 网络错误 - 重试
        if error.category == ErrorCategory.NETWORK:
            return RecoveryStrategy.RETRY
        
        # 超时错误 - 重试
        if error.category == ErrorCategory.TIMEOUT:
            return RecoveryStrategy.RETRY
        
        # 生成错误 - 降级
        if error.category == ErrorCategory.GENERATION:
            return RecoveryStrategy.FALLBACK
        
        # 默认 - 跳过
        return RecoveryStrategy.SKIP
    
    def record_recovery(
        self,
        error: ViMaxError,
        strategy: RecoveryStrategy,
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        记录恢复尝试
        
        Args:
            error: 错误实例
            strategy: 使用的策略
            success: 是否成功
            details: 额外详情
        """
        record = {
            "timestamp": time.time(),
            "error_type": error.__class__.__name__,
            "error_category": error.category.value,
            "strategy": strategy.value,
            "success": success,
            "details": details or {}
        }
        self.recovery_history.append(record)
        
        # 保留最近100条记录
        if len(self.recovery_history) > 100:
            self.recovery_history = self.recovery_history[-100:]
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """获取恢复统计信息"""
        if not self.recovery_history:
            return {
                "total_attempts": 0,
                "success_rate": 0.0,
                "by_strategy": {},
                "by_error_type": {}
            }
        
        total = len(self.recovery_history)
        successful = sum(1 for r in self.recovery_history if r["success"])
        
        by_strategy = {}
        by_error_type = {}
        
        for record in self.recovery_history:
            strategy = record["strategy"]
            error_type = record["error_type"]
            
            if strategy not in by_strategy:
                by_strategy[strategy] = {"total": 0, "successful": 0}
            by_strategy[strategy]["total"] += 1
            if record["success"]:
                by_strategy[strategy]["successful"] += 1
            
            if error_type not in by_error_type:
                by_error_type[error_type] = {"total": 0, "successful": 0}
            by_error_type[error_type]["total"] += 1
            if record["success"]:
                by_error_type[error_type]["successful"] += 1
        
        return {
            "total_attempts": total,
            "success_rate": successful / total if total > 0 else 0.0,
            "by_strategy": by_strategy,
            "by_error_type": by_error_type
        }


# 全局恢复管理器实例
recovery_manager = ErrorRecoveryManager()


def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    重试装饰器
    
    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟（秒）
        backoff_factor: 退避因子
        exceptions: 要捕获的异常类型
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed. Last error: {e}"
                        )
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed. Last error: {e}"
                        )
            
            raise last_exception
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def with_fallback(fallback_func: Callable):
    """
    降级装饰器 - 失败时使用备用函数
    
    Args:
        fallback_func: 备用函数
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"Primary function failed: {e}. Using fallback."
                )
                if asyncio.iscoroutinefunction(fallback_func):
                    return await fallback_func(*args, **kwargs)
                else:
                    return fallback_func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"Primary function failed: {e}. Using fallback."
                )
                return fallback_func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def with_circuit_breaker(
    service_name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0
):
    """
    熔断器装饰器
    
    Args:
        service_name: 服务名称
        failure_threshold: 失败阈值
        recovery_timeout: 恢复超时
    """
    def decorator(func):
        breaker = recovery_manager.get_circuit_breaker(
            service_name,
            failure_threshold,
            recovery_timeout
        )
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker.call_async(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


async def safe_execute(
    func: Callable,
    *args,
    max_retries: int = 3,
    fallback: Optional[Callable] = None,
    on_error: Optional[Callable[[ViMaxError], None]] = None,
    **kwargs
) -> tuple[bool, Any]:
    """
    安全执行函数，带有错误处理和恢复
    
    Args:
        func: 要执行的函数
        *args: 位置参数
        max_retries: 最大重试次数
        fallback: 降级函数
        on_error: 错误回调
        **kwargs: 关键字参数
    
    Returns:
        (success, result) 元组
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            return True, result
        except Exception as e:
            # 包装为ViMaxError
            if isinstance(e, ViMaxError):
                last_error = e
            else:
                from utils.error_handling import wrap_exception
                last_error = wrap_exception(e)
            
            # 调用错误回调
            if on_error:
                on_error(last_error)
            
            # 确定恢复策略
            strategy = recovery_manager.determine_strategy(last_error)
            
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed. "
                f"Strategy: {strategy.value}. Error: {last_error}"
            )
            
            # 如果不应该重试，跳出循环
            if strategy not in [RecoveryStrategy.RETRY, RecoveryStrategy.CIRCUIT_BREAKER]:
                break
            
            # 等待后重试
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # 指数退避
    
    # 所有重试都失败，尝试降级
    if fallback:
        try:
            logger.info("Attempting fallback function")
            if asyncio.iscoroutinefunction(fallback):
                result = await fallback(*args, **kwargs)
            else:
                result = fallback(*args, **kwargs)
            
            recovery_manager.record_recovery(
                last_error,
                RecoveryStrategy.FALLBACK,
                True
            )
            return True, result
        except Exception as e:
            logger.error(f"Fallback also failed: {e}")
            recovery_manager.record_recovery(
                last_error,
                RecoveryStrategy.FALLBACK,
                False
            )
    
    # 记录失败的恢复
    recovery_manager.record_recovery(
        last_error,
        RecoveryStrategy.RETRY,
        False
    )
    
    return False, last_error