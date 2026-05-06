#servis oluşturma
# history factorye benzer ama burda fallback koymuyurz ilk adımda önce redis tabanlı düzgünn rate limitingi ayağa kaldırmak istiorm 
# bu dosya sadece Redis client oluşturur , RateLimitService döndürür
import redis

from app.core.config import REDIS_URL
from app.services.rate_limit_service import RateLimitService


def get_rate_limit_service():
    redis_client = redis.Redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_timeout=2,
        socket_connect_timeout=2
    )

    return RateLimitService(redis_client)