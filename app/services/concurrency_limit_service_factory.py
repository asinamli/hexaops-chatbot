import redis

from app.core.config import REDIS_URL
from app.services.concurrency_limit_service import ConcurrencyLimitService


def get_concurrency_limit_service():
    redis_client = redis.Redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_timeout=2,
        socket_connect_timeout=2
    )

    return ConcurrencyLimitService(redis_client)