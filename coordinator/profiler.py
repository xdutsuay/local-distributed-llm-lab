import time
import functools
import logging

logger = logging.getLogger("llmlab.profiler")

def profile(func):
    """Decorator to measure execution time of async or sync functions"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        func_name = func.__name__
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            logger.info(f"⏱️ [PROFILE] {func_name}: {duration:.4f}s")
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        func_name = func.__name__
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            logger.info(f"⏱️ [PROFILE] {func_name}: {duration:.4f}s")

    import asyncio
    if asyncio.iscoroutinefunction(func):
        return wrapper
    else:
        return sync_wrapper
