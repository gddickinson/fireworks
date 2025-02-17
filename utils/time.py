# utils/time_utils.py
from typing import Callable
import time
from functools import wraps

class TimeUtils:
    @staticmethod
    def debounce(wait_time: float):
        """Decorator to debounce a function"""
        def decorator(fn: Callable):
            last_called = 0

            @wraps(fn)
            def debounced(*args, **kwargs):
                nonlocal last_called
                current_time = time.time()

                if current_time - last_called >= wait_time:
                    last_called = current_time
                    return fn(*args, **kwargs)

            return debounced
        return decorator

    @staticmethod
    def throttle(wait_time: float):
        """Decorator to throttle a function"""
        def decorator(fn: Callable):
            last_called = 0

            @wraps(fn)
            def throttled(*args, **kwargs):
                nonlocal last_called
                current_time = time.time()

                if current_time - last_called >= wait_time:
                    result = fn(*args, **kwargs)
                    last_called = current_time
                    return result

            return throttled
        return decorator
