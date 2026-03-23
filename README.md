### Short Description

A lightweight, asynchronous caching library for Python with per‑key locking, TTL, LRU eviction, and convenient decorators. Built with `asyncio` and Pydantic.

---

# Best Simple Cache

**Best Simple Cache** is an asynchronous caching library designed for modern Python applications that use `asyncio` and Pydantic models. It provides:

- **Per‑key locking** for thread‑safe concurrent access.
- **Time‑to‑live (TTL)** and **LRU eviction**.
- **Decorator‑based integration** – add caching to any async/sync function with minimal boilerplate.
- **Invalidation hooks** and **automatic cache refresh**.
- **Flexible primary key generation** – define your own key structure.

## Features

- ✅ **Async‑first** – built on `asyncio` with per‑key locks to avoid race conditions.
- ✅ **TTL & LRU** – automatically evict stale or least‑recently used entries.
- ✅ **Decoupled storage** – implement your own cache backend by subclassing `EntityCache`.
- ✅ **Decorator suite** – `@cache`, `@invalidate_after`, and `@refresh_after_by` for common patterns.
- ✅ **Mixed sync/async support** – works with both synchronous and asynchronous functions.
- ✅ **Type hints** – fully typed for better IDE support.

## Installation

```bash
pip install best_simple_caching
```

**Requirements:** Python 3.10+, Pydantic (v2).

## Quick Start

```python
import asyncio
from pydantic import BaseModel
from best_simple_cache import EntityCache, CacheDecorator, CachingConfig

# 1. Define your Pydantic model
class User(BaseModel):
    id: int
    name: str

# 2. Define the primary key (must be hashable)
class UserPK:
    def __init__(self, user_id: int):
        self.user_id = user_id

    def __hash__(self):
        return hash(self.user_id)

    def __eq__(self, other):
        return isinstance(other, UserPK) and self.user_id == other.user_id

# 3. Implement your cache class
class UserCache(EntityCache[User, UserPK]):
    def make_pk(self, user_id: int, **_kwargs) -> UserPK:
        return UserPK(user_id)

# 4. Create a decorator instance
user_cache = CacheDecorator(
    entity_cache=UserCache(
        entity_name="user",
        model=User,
        config=CachingConfig(ttl=60, max_size=1000)
    )
)

# 5. Decorate your function
@user_cache.cache
async def get_user(*, user_id: int) -> User:
    # Simulate an expensive API call
    await asyncio.sleep(1)
    return User(id=user_id, name="Alice")

async def main():
    # First call – runs the function, stores result
    user = await get_user(user_id=42)
    print(user)

    # Second call – returns from cache
    user = await get_user(user_id=42)
    print(user)  # Instant

asyncio.run(main())
```

## Advanced Usage

### Invalidation

```python
@user_cache.invalidate_after
async def update_user(*, user_id: int) -> User:
    # This function updates the user and then invalidates the cache
    updated_user = ...  # some update logic
    return updated_user
```

### Refresh After Write

```python
@user_cache.refresh_after_by(get_user)  # get_user is a cached function
async def update_user(*, user_id: int) -> None:
    # Perform update, then the cache will be invalidated and refreshed
    ...
```

### Custom Key Generation

The `make_pk` method receives the same keyword arguments as the decorated function. Use it to build a hashable key.

```python
class MyCache(EntityCache[MyModel, MyPK]):
    def make_pk(self, id: int, region: str = "default", **_kwargs) -> MyPK:
        return MyPK(id, region)
```

## API Reference

### `EntityCache(ABC, Generic[T, PK])`

Abstract base class for a cache backend.

- `__init__(entity_name: str, model: type[T], config: CachingConfig | None)`
- `async set(entity: T, **kwargs) -> None` – store an entity.
- `async get(**kwargs) -> T | None` – retrieve an entity by keyword arguments.
- `async get_by_pk(pk: PK) -> T | None` – retrieve directly by primary key.
- `async invalidate(entity_pk: PK | None = None, **kwargs) -> None` – remove an entry.
- `abstractmethod make_pk(**kwargs) -> PK` – build a primary key from arguments.

### `CacheDecorator(Generic[T, PK])`

Creates decorators bound to a specific `EntityCache`.

- `cache` – decorator that caches the function result.
- `invalidate_after` – decorator that invalidates the cache after the function runs.
- `refresh_after_by(refresh_func)` – decorator that invalidates and then calls `refresh_func` to repopulate the cache.

### `CachingConfig`

Configuration for a cache.

- `ttl: float | None` – seconds after which an entry is considered stale (default `None` = never expires).
- `max_size: int` – maximum number of entries; `0` means unlimited (default `0`).
- `disabled: bool` – if `True`, caching is disabled (default `False`).

## Limitations

- **Keyword arguments only** – the decorated function must use only keyword arguments (or at least those used in `make_pk` must be named). Positional arguments are not supported.
- **Pydantic models** – the library assumes cached entities are subclasses of `BaseModel`. You can extend it to work with other types by overriding type checks.
- **In‑memory only** – the default implementation stores data in an `OrderedDict`. For distributed caching, implement your own backend.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

MIT