import time
import logging
import functools
import random
import asyncio

logger = logging.getLogger('utils')

def retry(max_retries=3, delay=1, backoff=2, exceptions=(Exception,)):
    """
    Retry decorator with exponential backoff (synchronous).

    :param max_retries: Maximum number of retries
    :param delay: Initial delay in seconds
    :param backoff: Backoff multiplier
    :param exceptions: Tuple of exceptions to catch
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            for i in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if i == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                        raise

                    wait_time = current_delay + random.uniform(0, 0.1) # Add jitter
                    logger.warning(f"Function {func.__name__} failed: {e}. Retrying in {wait_time:.2f}s... ({i+1}/{max_retries})")
                    time.sleep(wait_time)
                    current_delay *= backoff
        return wrapper
    return decorator

def async_retry(max_retries=3, delay=1, backoff=2, exceptions=(Exception,)):
    """
    Retry decorator with exponential backoff (asynchronous).

    :param max_retries: Maximum number of retries
    :param delay: Initial delay in seconds
    :param backoff: Backoff multiplier
    :param exceptions: Tuple of exceptions to catch
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            for i in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if i == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                        raise

                    wait_time = current_delay + random.uniform(0, 0.1) # Add jitter
                    logger.warning(f"Function {func.__name__} failed: {e}. Retrying in {wait_time:.2f}s... ({i+1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    current_delay *= backoff
        return wrapper
    return decorator
