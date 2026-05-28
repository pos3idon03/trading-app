import json
from typing import Any

import redis.asyncio as aioredis

from config import get_settings
from utils.logging import get_logger

logger = get_logger(__name__)

CHANNEL = "execution:activity"
_redis: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis | None:
    global _redis
    try:
        if _redis is None:
            _redis = aioredis.from_url(get_settings().redis_url, decode_responses=True)
        await _redis.ping()
        return _redis
    except Exception as exc:
        logger.warning("execution_redis_unavailable", error=str(exc))
        return None


async def publish_activity_event(payload: dict[str, Any]) -> None:
    client = await _get_redis()
    if client is None:
        return
    try:
        await client.publish(CHANNEL, json.dumps(payload, default=str))
    except Exception as exc:
        logger.warning("execution_publish_failed", error=str(exc))


async def subscribe_activity_events():
    client = await _get_redis()
    if client is None:
        return None
    pubsub = client.pubsub()
    await pubsub.subscribe(CHANNEL)
    return pubsub


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
