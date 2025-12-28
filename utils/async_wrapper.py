"""
Async Wrapper Utilities
Provides utilities for wrapping synchronous functions and enabling progress callbacks
"""

import asyncio
import functools
from typing import Callable, Any, Optional, TypeVar, Coroutine
from concurrent.futures import ThreadPoolExecutor
import logging

T = TypeVar('T')


# Global thread pool for CPU-bound tasks
_thread_pool: Optional[ThreadPoolExecutor] = None


def get_thread_pool(max_workers: int = 4) -> ThreadPoolExecutor:
    """
    Get or create the global thread pool
    
    Args:
        max_workers: Maximum number of worker threads
    
    Returns:
        ThreadPoolExecutor instance
    """
    global _thread_pool
    if _thread_pool is None:
        _thread_pool = ThreadPoolExecutor(max_workers=max_workers)
    return _thread_pool


def run_in_thread(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
    """
    Decorator to run a synchronous function in a thread pool
    
    Usage:
        @run_in_thread
        def sync_function(arg1, arg2):
            # CPU-bound or blocking operation
            return result
        
        # Can now be awaited
        result = await sync_function(arg1, arg2)
    
    Args:
        func: Synchronous function to wrap
    
    Returns:
        Async function that runs the original in a thread pool
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        loop = asyncio.get_event_loop()
        thread_pool = get_thread_pool()
        
        # Run the synchronous function in the thread pool
        result = await loop.run_in_executor(
            thread_pool,
            functools.partial(func, *args, **kwargs)
        )
        return result
    
    return wrapper


async def run_sync_in_thread(func: Callable[..., T], *args, **kwargs) -> T:
    """
    Run a synchronous function in a thread pool without decorator
    
    Usage:
        result = await run_sync_in_thread(sync_function, arg1, arg2, kwarg1=value1)
    
    Args:
        func: Synchronous function to run
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
    
    Returns:
        Result from the function
    """
    loop = asyncio.get_event_loop()
    thread_pool = get_thread_pool()
    
    result = await loop.run_in_executor(
        thread_pool,
        functools.partial(func, *args, **kwargs)
    )
    return result


class ProgressCallback:
    """
    Progress callback handler for long-running operations
    
    Usage:
        progress = ProgressCallback()
        
        async def long_operation():
            await progress.update(0.0, "Starting...")
            # Do work
            await progress.update(0.5, "Halfway done...")
            # More work
            await progress.update(1.0, "Complete!")
        
        # Subscribe to progress updates
        async def on_progress(percentage, message):
            print(f"{percentage*100}%: {message}")
        
        progress.subscribe(on_progress)
        await long_operation()
    """
    
    def __init__(self):
        self.callbacks: list[Callable[[float, str], Coroutine]] = []
        self.current_progress: float = 0.0
        self.current_message: str = ""
    
    def subscribe(self, callback: Callable[[float, str], Coroutine]):
        """
        Subscribe to progress updates
        
        Args:
            callback: Async function that receives (percentage, message)
        """
        self.callbacks.append(callback)
    
    def unsubscribe(self, callback: Callable[[float, str], Coroutine]):
        """
        Unsubscribe from progress updates
        
        Args:
            callback: Callback to remove
        """
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    async def update(self, percentage: float, message: str = ""):
        """
        Update progress and notify all subscribers
        
        Args:
            percentage: Progress percentage (0.0 to 1.0)
            message: Progress message
        """
        self.current_progress = max(0.0, min(1.0, percentage))
        self.current_message = message
        
        # Notify all subscribers
        for callback in self.callbacks:
            try:
                await callback(self.current_progress, self.current_message)
            except Exception as e:
                logging.error(f"Error in progress callback: {e}")
    
    def get_current(self) -> tuple[float, str]:
        """
        Get current progress state
        
        Returns:
            Tuple of (percentage, message)
        """
        return (self.current_progress, self.current_message)


class AsyncBatchProcessor:
    """
    Process items in batches with concurrency control
    
    Usage:
        processor = AsyncBatchProcessor(max_concurrent=3)
        
        async def process_item(item):
            # Process single item
            return result
        
        results = await processor.process_batch(items, process_item)
    """
    
    def __init__(self, max_concurrent: int = 5):
        """
        Initialize batch processor
        
        Args:
            max_concurrent: Maximum number of concurrent operations
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_batch(
        self,
        items: list[T],
        processor: Callable[[T], Coroutine[Any, Any, Any]],
        progress_callback: Optional[ProgressCallback] = None
    ) -> list[Any]:
        """
        Process a batch of items with concurrency control
        
        Args:
            items: List of items to process
            processor: Async function to process each item
            progress_callback: Optional progress callback
        
        Returns:
            List of results in the same order as input items
        """
        async def process_with_semaphore(index: int, item: T) -> tuple[int, Any]:
            async with self.semaphore:
                result = await processor(item)
                
                if progress_callback:
                    progress = (index + 1) / len(items)
                    await progress_callback.update(
                        progress,
                        f"Processed {index + 1}/{len(items)} items"
                    )
                
                return (index, result)
        
        # Process all items concurrently with semaphore control
        tasks = [
            process_with_semaphore(i, item)
            for i, item in enumerate(items)
        ]
        
        results_with_indices = await asyncio.gather(*tasks)
        
        # Sort by original index to maintain order
        results_with_indices.sort(key=lambda x: x[0])
        results = [result for _, result in results_with_indices]
        
        return results


def with_progress(
    total_steps: int,
    step_messages: Optional[list[str]] = None
) -> Callable:
    """
    Decorator to add automatic progress tracking to async functions
    
    Usage:
        @with_progress(total_steps=3, step_messages=["Step 1", "Step 2", "Step 3"])
        async def my_function(progress: ProgressCallback):
            await progress.update(0.33, "Step 1")
            # Do work
            await progress.update(0.66, "Step 2")
            # More work
            await progress.update(1.0, "Step 3")
            return result
    
    Args:
        total_steps: Total number of steps
        step_messages: Optional list of messages for each step
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, progress: Optional[ProgressCallback] = None, **kwargs):
            if progress is None:
                progress = ProgressCallback()
            
            # Inject progress into kwargs if function accepts it
            if 'progress' in func.__code__.co_varnames:
                kwargs['progress'] = progress
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


async def retry_with_backoff(
    func: Callable[..., Coroutine[Any, Any, T]],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    *args,
    **kwargs
) -> T:
    """
    Retry an async function with exponential backoff
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        *args: Arguments for the function
        **kwargs: Keyword arguments for the function
    
    Returns:
        Result from the function
    
    Raises:
        Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            
            if attempt < max_retries:
                logging.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
                delay *= backoff_factor
            else:
                logging.error(f"All {max_retries + 1} attempts failed")
    
    raise last_exception


def cleanup_thread_pool():
    """
    Cleanup the global thread pool
    Should be called on application shutdown
    """
    global _thread_pool
    if _thread_pool is not None:
        _thread_pool.shutdown(wait=True)
        _thread_pool = None