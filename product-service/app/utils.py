import asyncio
import threading
from functools import wraps
from flask import jsonify

# Thread-local storage for event loops
_thread_local = threading.local()


def get_or_create_event_loop():
    """Get or create an event loop for the current thread"""
    try:
        # Try to get the existing event loop for this thread
        loop = getattr(_thread_local, 'loop', None)
        if loop is None or loop.is_closed():
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            _thread_local.loop = loop
        return loop
    except RuntimeError:
        # No event loop exists, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _thread_local.loop = loop
        return loop


def run_async(coro):
    """Run an async coroutine in the current thread's event loop"""
    loop = get_or_create_event_loop()
    # In Flask's synchronous context, the loop should never be running
    # If it is, that indicates a problem
    if loop.is_running():
        raise RuntimeError("Event loop is already running. This should not happen in Flask.")
    return loop.run_until_complete(coro)


def async_route(f):
    """Decorator to make Flask route async-compatible"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Check if result is already a response (from auth decorators)
        result = f(*args, **kwargs)
        
        # If it's a tuple (response, status_code) from jsonify, return it
        if isinstance(result, tuple) and len(result) == 2:
            return result
        
        # If it's a coroutine, run it
        if asyncio.iscoroutine(result):
            return run_async(result)
        
        return result
    
    return wrapper

