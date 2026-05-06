# LOCAL STORE ram tabanlı implementasyon

# Dictionary tabanlı in-memory state yani python sözlükleri ile state tutuyor
# Key composition productionda state i ayırmak için önemli olabilir. Şimdilik basit tutuyoruz ama ileride user_id ekleyebiliriz.
# Encapsulation state e doğrudan dışardan erişmiyoruz set_topic, get_topic gibi metotlarla erişiyoruz


from typing import Dict, List, Optional

from app.services.base_history_service import BaseHistoryService

"""
history ile lgili işlemler :
meseaj eklemek 
geçmişi almak 
geçmişi silmek 
"""
#history yönetimi için ayrı bir service sınıfı açıyotuz
class InMemoryHistoryService(BaseHistoryService):
    def __init__(self):
        self.store: Dict[str, List[dict]] = {}
        self.topic_store: Dict[str, str] = {}
        self.weather_city_store: Dict[str, str] = {}
        self.math_result_store: Dict[str, float] = {}
        self.company_detail_store: Dict[str, str] = {}
# self.store geçici history belleğimiz 
# mesaj listesi -->  List[dict]


    # user ve conv izolasyonu için key oluşturma
    def _build_key(self, conversation_id: str, user_id: Optional[str] = None) -> str:
        if user_id:
            return f"{user_id}:{conversation_id}"
        return conversation_id

    # bu metodun görevi belirli bi konuşmaya yeni bir mesaj eklemek 
    """
    conversation_id: hangi konuşma
    role: mesajı kim söylüyor (user veya assistant)
    content: mesajın metni
    """
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None
    ) -> None:
        key = self._build_key(conversation_id, user_id)

        if key not in self.store:
            self.store[key] = []
        
        # burda mesajı ilgili konuşmanın listesine ekliyoruz 
        self.store[key].append(
            {
                "role": role,
                "content": content
            }
        )
    
    #belirli bir konuşmanın geçmişini döndürmek
    def get_history(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> List[Dict]:
        key = self._build_key(conversation_id, user_id)
        return self.store.get(key, []).copy()

    def clear_history(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> None:
        key = self._build_key(conversation_id, user_id)

        if key in self.store:
            del self.store[key]

        if key in self.topic_store:
            del self.topic_store[key]

        if key in self.weather_city_store:
            del self.weather_city_store[key]

        if key in self.math_result_store:
            del self.math_result_store[key]

        if key in self.company_detail_store:
            del self.company_detail_store[key]

    def set_topic(
        self,
        conversation_id: str,
        topic: str,
        user_id: Optional[str] = None
    ) -> None:
        key = self._build_key(conversation_id, user_id)
        self.topic_store[key] = topic

    def get_topic(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> Optional[str]:
        key = self._build_key(conversation_id, user_id)
        return self.topic_store.get(key)

    def set_weather_city(
        self,
        conversation_id: str,
        city: str,
        user_id: Optional[str] = None
    ) -> None:
        key = self._build_key(conversation_id, user_id)
        self.weather_city_store[key] = city

    def get_weather_city(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> Optional[str]:
        key = self._build_key(conversation_id, user_id)
        return self.weather_city_store.get(key)

    def set_math_result(
        self,
        conversation_id: str,
        result: float,
        user_id: Optional[str] = None
    ) -> None:
        key = self._build_key(conversation_id, user_id)
        self.math_result_store[key] = result

    def get_math_result(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> Optional[float]:
        key = self._build_key(conversation_id, user_id)
        return self.math_result_store.get(key)

    def set_company_detail(
        self,
        conversation_id: str,
        detail: str,
        user_id: Optional[str] = None
    ) -> None:
        key = self._build_key(conversation_id, user_id)
        self.company_detail_store[key] = detail

    def get_company_detail(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> Optional[str]:
        key = self._build_key(conversation_id, user_id)
        return self.company_detail_store.get(key)


"""
add_message("conv_1", "user", "selam")

çağrılırsa store şöyle olur 

{
    "conv_1": [
        {"role": "user", "content": "selam"}
    ]
}
"""