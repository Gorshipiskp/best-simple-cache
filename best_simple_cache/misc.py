import inspect
from typing import TypeVar, Callable, Awaitable, Coroutine

T = TypeVar("T")


async def handle_maybe_async(func: Coroutine[..., ..., T] | Callable[..., T | Awaitable[T]] | T, *args, **kwargs) -> T:
    """
    Execute a value that may be synchronous, asynchronous, or already a result,
    and return its resolved value

    This utility normalizes mixed sync/async inputs into a single awaited result,
    simplifying code that needs to transparently handle both execution models

    Args:
        func: A coroutine function, coroutine object, callable returning a value or awaitable,
              or a direct value
        *args: Positional arguments passed to the callable, if applicable
        **kwargs: Keyword arguments passed to the callable, if applicable

    Returns:
        The resolved value of type `T` after executing or awaiting as necessary
    """

    if inspect.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    if inspect.iscoroutine(func):
        return await func
    if not inspect.isfunction(func):
        return func

    result: T = func(*args, **kwargs)

    if inspect.isawaitable(result):
        return await result

    return result
