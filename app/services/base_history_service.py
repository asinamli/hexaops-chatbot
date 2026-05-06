from abc import ABC, abstractmethod
from typing import Dict, List, Optional

# burda kullanılan teknik @abstractmethod yani soyut sınıf mantığı 
# bu kodun amacı implementasyonları zorunlu hale getirmek
# Yani InMemoryHistoryService ya da RedisHistoryService bu metodları yazmak zorunda.

# yarın history backend değiştirmek istediğimde örneğin database history yazmak istediğimde bu dosyaya bakıcam ve yazacağım sınıfın hangi işleri yapmak zorunda olacağını biliycem


class BaseHistoryService(ABC):
    # mesaj eklemek için add_message metodu tanımlıyoruz
    @abstractmethod
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None
    ) -> None:
        pass

    #geçmişi almak için get_history metodu tanımlıyoruz
    @abstractmethod
    def get_history(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> List[Dict]:
        pass

    #geçmşi silmek için clear_history metodu tanımlıyoruz
    @abstractmethod
    def clear_history(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> None:
        pass

    # konu başlığını ayarlamak için set_topic metodu tanımlıyoruz
    @abstractmethod
    def set_topic(
        self,
        conversation_id: str,
        topic: str,
        user_id: Optional[str] = None
    ) -> None:
        pass

    @abstractmethod
    def get_topic(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> Optional[str]:
        pass

    # hava durumunu ayarlamak için set_weather_city metodu tanımlıyoruz
    @abstractmethod
    def set_weather_city(
        self,
        conversation_id: str,
        city: str,
        user_id: Optional[str] = None
    ) -> None:
        pass

    @abstractmethod
    def get_weather_city(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> Optional[str]:
        pass

    @abstractmethod
    def set_math_result(
        self,
        conversation_id: str,
        result: float,
        user_id: Optional[str] = None
    ) -> None:
        pass

    @abstractmethod
    def get_math_result(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> Optional[float]:
        pass

    @abstractmethod
    def set_company_detail(
        self,
        conversation_id: str,
        detail: str,
        user_id: Optional[str] = None
    ) -> None:
        pass

    @abstractmethod
    def get_company_detail(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> Optional[str]:
        pass