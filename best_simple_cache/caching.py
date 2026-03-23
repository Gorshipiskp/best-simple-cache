import functools
from typing import Generic, Any, Callable, Awaitable, Coroutine, ParamSpec

from . import EntityCache
from .entity_cache import PK, T
from .misc import handle_maybe_async

P = ParamSpec("P")


class CacheDecorator(Generic[T, PK]):
    def __init__(self, entity_cache: EntityCache[T, PK]) -> None:
        self._entity_cache: EntityCache[T, PK] = entity_cache

        self.cache = self.__cache()
        self.invalidate_after = self.__invalidate_after()

    def __cache(self) -> Callable[
        [Callable[P, T | Awaitable[T] | Coroutine[Any, Any, T]]],
        Callable[P, Coroutine[Any, Any, T]]
    ]:
        def decorator(
                func: Callable[P, T | Awaitable[T] | Coroutine[Any, Any, T]]
        ) -> Callable[P, Coroutine[Any, Any, T]]:
            func.is_cached = True

            @functools.wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                from_cache: T | None = await self._entity_cache.get(**kwargs)

                if from_cache is not None:
                    return from_cache

                result: T = await handle_maybe_async(func, *args, **kwargs)

                await self._entity_cache.set(entity=result, **kwargs)

                return result

            return wrapper

        return decorator

    def __invalidate_after(self):
        def decorator(
                func: Callable[P, T | Awaitable[T] | Coroutine[Any, Any, T]]
        ) -> Callable[P, Coroutine[Any, Any, T]]:
            @functools.wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                result: T = await handle_maybe_async(func, *args, **kwargs)

                await self._entity_cache.invalidate(**kwargs)

                return result

            return wrapper

        return decorator

    def refresh_after_by(
            self,
            refresh_func: Callable[..., T | Awaitable[T] | Coroutine[Any, Any, T]]
    ) -> Callable[[Callable[P, T | Awaitable[T]]], Callable[P, Coroutine[Any, Any, T]]]:
        def decorator(func: Callable[P, T | Awaitable[T]]) -> Callable[P, Coroutine[Any, Any, T]]:
            @functools.wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                result: T = await handle_maybe_async(func, *args, **kwargs)

                await self._entity_cache.invalidate(**kwargs)

                refresh_res: T = await handle_maybe_async(refresh_func, *args, **kwargs)
                if getattr(func, "is_cached", False):
                    await self._entity_cache.set(entity=refresh_res, **kwargs)

                return result

            return wrapper

        return decorator
