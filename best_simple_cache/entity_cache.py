import time
from abc import ABC, abstractmethod
from asyncio import Lock
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, Hashable

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
PK = TypeVar("PK", bound=Hashable)


@dataclass(frozen=True, kw_only=True)
class CacheInfo(Generic[T]):
    entity: T
    created_at: float


class CachingConfig:
    def __init__(
            self,
            ttl: float | None = None,
            max_size: int = 0,
            disabled: bool = False,
    ):
        self.ttl: float | None = ttl
        self.max_size: int = max_size
        self.disabled: bool = disabled

    def __repr__(self):
        return f"CachingConfig(ttl={self.ttl}; max_size={self.max_size}; disabled={self.disabled})"


class EntityCache(ABC, Generic[T, PK]):
    def __init__(
            self,
            entity_name: str,
            model: type[T],
            config: CachingConfig | None = None,
    ):
        self.entity_name: str = entity_name
        self.model: type[T] = model

        self._config: CachingConfig = config or CachingConfig()
        self._pool: OrderedDict[PK, CacheInfo[T]] = OrderedDict()
        self._pool_locks: dict[PK, Lock] = {}

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(name=\"{self.entity_name}\"; "
                f"pool_len={len(self._pool)}; config={self._config})")

    async def set(self, entity: T, **kwargs: Any) -> None:
        if self._config.disabled:
            return

        entity_pk: PK = self.make_pk(**kwargs)

        async with self._pool_locks.setdefault(entity_pk, Lock()):
            now: float = time.monotonic()

            self._pool[entity_pk] = CacheInfo(entity=entity, created_at=now)

            self._pool.move_to_end(entity_pk)

            self._evict_if_needed()

    async def get_by_pk(self, pk: PK) -> T | None:
        return await self._get(pk)

    async def get(self, **kwargs: Any) -> T | None:
        return await self._get(
            self.make_pk(**kwargs)
        )

    async def _get(self, entity_pk: PK) -> T | None:
        if self._config.disabled:
            return None

        async with self._pool_locks.setdefault(entity_pk, Lock()):
            info: CacheInfo[T] = self._pool.get(entity_pk)

            if info is None:
                return None

            if self._is_expired(info):
                self._pool.pop(entity_pk, None)
                self._pool_locks.pop(entity_pk, None)
                return None

            self._pool.move_to_end(entity_pk)

            return info.entity

    async def invalidate(self, entity_pk: PK | None = None, **kwargs: Any) -> None:
        if entity_pk is None:
            entity_pk = self.make_pk(**kwargs)

        async with self._pool_locks.setdefault(entity_pk, Lock()):
            self._pool.pop(entity_pk, None)
            self._pool_locks.pop(entity_pk, None)

    def _evict_if_needed(self) -> None:
        max_size: int = self._config.max_size

        if max_size <= 0:
            return

        while len(self._pool) > max_size:
            entity_pk: PK = self._pool.popitem(last=False)
            self._pool_locks.pop(entity_pk, None)

    def _is_expired(self, info: CacheInfo[T]) -> bool:
        ttl: float | None = self._config.ttl

        if ttl is None:
            return False

        return (time.monotonic() - info.created_at) > ttl

    @abstractmethod
    def make_pk(self, **kwargs: Any) -> PK:
        ...
