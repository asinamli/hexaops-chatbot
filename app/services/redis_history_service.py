# REDİS STORE bu dosyanın amacı ortak store sağlamak ve esneklik sağlamak 

# mantık başta yazdığım in-memory ile aynı sadece storage değişiyor 
# redis key-value store olduğu için user:123:conversation:abc:topic gibi keyler oluşturuyoruz 
# mesaj geçmişi liste old için string redise yazılmıyor json formatında yazılıyor ve okunurken json olarak parse ediliyor

import json
from typing import Dict, List, Optional

from app.services.base_history_service import BaseHistoryService


class RedisHistoryService(BaseHistoryService):
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.ttl_seconds = 86400

    # redis erişilebilir mi diye ping atıyoruz yani sağlık kontrolü
    def is_available(self) -> bool:
        try:
            result = self.redis_client.ping()
            print(f"Redis ping sonucu: {result}")
            return bool(result)
        except Exception as e:
            print(f"Redis ping hatası: {e}")
            return False

    def _build_key(self, conversation_id: str, user_id: Optional[str] = None) -> str:
        if user_id:
            return f"user:{user_id}:conversation:{conversation_id}"
        return f"conversation:{conversation_id}"

    def _set_ttl(self, *keys) -> None:
        for key in keys:
            self.redis_client.expire(key, self.ttl_seconds)

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None
    ) -> None:
        base_key = self._build_key(conversation_id, user_id)
        messages_key = f"{base_key}:messages"

        message_data = {
            "role": role,
            "content": content
        }
        # REDİS LİSTESİNE MESAJ EKLEMEK İÇİN RPUSH KULLANIYORUZ VE MESAJI JSON FORMATINDA YAZIYORUZ
        self.redis_client.rpush(messages_key, json.dumps(message_data))
        self._set_ttl(messages_key)

    def get_history(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> List[Dict]:
        base_key = self._build_key(conversation_id, user_id)
        messages_key = f"{base_key}:messages"

        raw_values = self.redis_client.lrange(messages_key, 0, -1)
        if not raw_values:
            return []

        return [json.loads(item) for item in raw_values]

    def clear_history(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> None:
        base_key = self._build_key(conversation_id, user_id)

        keys = [
            f"{base_key}:messages",
            f"{base_key}:topic",
            f"{base_key}:weather_city",
            f"{base_key}:math_result",
            f"{base_key}:company_detail",
        ]

        self.redis_client.delete(*keys)

    def set_topic(
        self,
        conversation_id: str,
        topic: str,
        user_id: Optional[str] = None
    ) -> None:
        base_key = self._build_key(conversation_id, user_id)
        topic_key = f"{base_key}:topic"
        self.redis_client.set(topic_key, topic)
        self._set_ttl(topic_key)


    def get_topic(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> Optional[str]:
        base_key = self._build_key(conversation_id, user_id)
        value = self.redis_client.get(f"{base_key}:topic")
        return value if value else None

    def set_weather_city(
        self,
        conversation_id: str,
        city: str,
        user_id: Optional[str] = None
    ) -> None:
        base_key = self._build_key(conversation_id, user_id)
        city_key = f"{base_key}:weather_city"
        self.redis_client.set(city_key, city)
        self._set_ttl(city_key)

    def get_weather_city(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> Optional[str]:
        base_key = self._build_key(conversation_id, user_id)
        value = self.redis_client.get(f"{base_key}:weather_city")
        return value if value else None

    def set_math_result(
        self,
        conversation_id: str,
        result: float,
        user_id: Optional[str] = None
    ) -> None:
        base_key = self._build_key(conversation_id, user_id)
        result_key = f"{base_key}:math_result"
        self.redis_client.set(result_key, result)
        self._set_ttl(result_key)


    def get_math_result(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> Optional[float]:
        base_key = self._build_key(conversation_id, user_id)
        value = self.redis_client.get(f"{base_key}:math_result")
        return float(value) if value else None

    def set_company_detail(
        self,
        conversation_id: str,
        detail: str,
        user_id: Optional[str] = None
    ) -> None:
        base_key = self._build_key(conversation_id, user_id)
        detail_key = f"{base_key}:company_detail"
        self.redis_client.set(detail_key, detail)
        self._set_ttl(detail_key)
        
    def get_company_detail(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> Optional[str]:
        base_key = self._build_key(conversation_id, user_id)
        value = self.redis_client.get(f"{base_key}:company_detail")
        return value if value else None