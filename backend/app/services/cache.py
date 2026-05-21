from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

_redis = redis.from_url(settings.redis_url, decode_responses=True)


async def cache_get_json(key: str) -> Any | None:
    raw = await _redis.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def cache_set_json(key: str, value: Any, ttl_seconds: int) -> None:
    await _redis.set(key, json.dumps(value), ex=ttl_seconds)

