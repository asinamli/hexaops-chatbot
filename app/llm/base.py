# soyut temel sınıf yapıları için kullanılan modülü import edelim

from abc import ABC, abstractmethod # ABC bir sınıfı soyut temel sınıf olacağını belirtir

# BaseLLMProvider sınıfı, tüm LLM sağlayıcılarının ortak bir arayüzü olarak hizmet verecek
# yani yarın başka llm koyduğumuzda hepsinde get_response() fonku olmak zorunda
class BaseLLMProvider(ABC):
    @abstractmethod
    def get_response(self, message: str) -> str:
        pass