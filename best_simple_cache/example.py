import asyncio
import time
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from . import EntityCache
from .caching import CacheDecorator
from .entity_cache import CachingConfig


async def main():
    print(f"\n{' Example caching and TTL ':=^70}\n")

    # Some kind of pydantic classes of API response (strict hashable)
    class Group(BaseModel):
        group_id: int
        name: str
        scope: str

        model_config = {"frozen": True}

    # Set `Group` entity's cache

    # Primary key of group
    @dataclass(frozen=True, kw_only=True)
    class GroupPK:
        group_id: int

    # Overload necessary methods
    class GroupCache(EntityCache):
        def make_pk(self, group_id: int, **_kwargs: Any) -> GroupPK:
            # We need `_kwargs` for backward compatibility
            return GroupPK(
                group_id=group_id
            )

    groups_cache: CacheDecorator[Group, GroupPK] = CacheDecorator(
        entity_cache=GroupCache(
            entity_name="group",
            model=Group,
            config=CachingConfig(
                ttl=3
            )
        )
    )

    # Arbitrary API-contract (adding caching)
    @groups_cache.cache
    async def get_group_contract(*, group_id: int) -> Group:
        # Warning: function with `.cache` decorator must include the same kwargs, that was set in PK

        # Some API and requests thing
        ...

        await asyncio.sleep(1)

        # Got the result
        return Group(
            group_id=group_id,
            name="PMiK-16",
            scope="GLOBAL"
        )

    start: float = time.perf_counter()
    await get_group_contract(group_id=1)
    end: float = time.perf_counter()

    print(f"Before caching: {end - start:.6f}")

    start: float = time.perf_counter()
    await get_group_contract(group_id=1)
    end: float = time.perf_counter()

    print(f"After caching: {end - start:.6f}")

    await asyncio.sleep(3.1)

    start: float = time.perf_counter()
    await get_group_contract(group_id=1)
    end: float = time.perf_counter()

    print(f"After ttl expire: {end - start:.6f}")

    print(f"\n{' Invalidation hook example ':=^70}\n")

    # New model and contract (invalidation hook with auto-refresh)
    class GroupSettings(BaseModel):
        group_id: int
        new_members: bool

        model_config = {"frozen": True}

    class GroupSettingsPK(GroupPK):
        ...

    class GroupSettingsCache(EntityCache):
        def make_pk(self, group_id: int, **_kwargs: Any) -> GroupPK:
            return GroupSettingsPK(
                group_id=group_id
            )

    groups_settings_cache: CacheDecorator[GroupSettings, GroupSettingsPK] = CacheDecorator(
        entity_cache=GroupSettingsCache(
            entity_name="group_settings",
            model=GroupSettings
        )
    )

    @groups_settings_cache.cache
    async def get_group_settings(*, group_id: int) -> GroupSettings:
        # Some API and requests thing
        ...

        print("Got group's settings")
        # Got the result
        return GroupSettings(
            group_id=group_id,
            new_members=True
        )

    @groups_settings_cache.refresh_after_by(get_group_settings)
    async def update_group_settings(*, group_id: int) -> None:
        # Some API and requests thing
        ...

        print(f"Group settings ({group_id=}) updated")

    await get_group_settings(group_id=1)
    await update_group_settings(group_id=1)
