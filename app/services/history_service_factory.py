# hangi history servicenin kullanılacağına karar veriyor 
import redis

from app.core.config import REDIS_URL
from app.services.in_memory_history_service import InMemoryHistoryService
from app.services.redis_history_service import RedisHistoryService

def get_history_service():
    try:
        redis_client = redis.Redis.from_url( # redis client oluşturuyyoruz
            REDIS_URL,
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=2
        )

        # Redis clienti service sınıfına veriyoruz
        redis_service = RedisHistoryService(redis_client)

        if redis_service.is_available():
            print("History backend: Redis")
            return redis_service

    except Exception as e:
        print(f"Redis backend hatası: {e}")

    print("History backend: InMemory")
    return InMemoryHistoryService()