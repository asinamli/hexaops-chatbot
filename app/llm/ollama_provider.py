import requests  # http isteği atmak için

from app.core.config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_REQUEST_TIMEOUT_SECONDS,
)
from app.llm.base import BaseLLMProvider
from app.schemas.llm import LLMResponse
from app.schemas.tools import ToolCall
from app.tools.tool_definitions import TOOLS


# sınıfın içine koyuyoruz
# ollama ile local API den konşuyoruz
class OllamaProvider(BaseLLMProvider):
    def __init__(self, model: str = OLLAMA_MODEL, base_url: str = OLLAMA_BASE_URL):
        self.model = model
        self.base_url = base_url

# BU METODU HATALARI YAKALAMASI İÇİN YAZDIM 
# ŞU HATALAR: TİMEOUT, CONNECTİON ERROR(500 HATASI ALMIŞTIM), REQUEST ERROR, JSON PARSE ERROR 
    def _post_chat_request(self, payload: dict) -> dict | None:
        url = f"{self.base_url}/api/chat"

        try:
            response = requests.post(
            url,
            json=payload,
            timeout=OLLAMA_REQUEST_TIMEOUT_SECONDS
)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            print("Ollama timeout hatası oluştu.")
            return None

        except requests.exceptions.ConnectionError:
            print("Ollama bağlantı hatası oluştu.")
            return None

        except requests.exceptions.RequestException as e:
            print(f"Ollama request hatası oluştu: {e}")
            return None

        except ValueError:
            print("Ollama JSON parse hatası oluştu.")
            return None

    def get_response(self, message: str) -> LLMResponse:
        system_prompt = """
Sen Türkçe konuşan yardımcı bir asistansın.

Kurallar:
- Normal selamlaşma, hal hatır sorma ve genel sohbet mesajlarında tool çağırma.
- Bu tür mesajlara doğrudan kısa ve doğal Türkçe cevap ver.
- Sadece gerçekten gerekli olduğunda tool kullan.

Tool kullanman gereken durumlar:
- hava durumu soruları -> weather_tool
- şirket bilgileri (mesai, adres, telefon) -> company_info_tool
- açık matematik işlemleri -> add_numbers, subtract_numbers, multiply_numbers, divide_numbers

Örnek:
- "selam naber" -> normal sohbet cevabı ver, tool çağırma
- "ankara hava durumu nasıl" -> weather_tool çağır
- "5 + 3 kaç eder" -> uygun matematik tool'unu çağır
- "mesai saatleriniz" -> company_info_tool çağır
"""

        # ne gönderiyoruz ollamaya
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": message
                }
            ],
            "tools": TOOLS,
            "stream": False
        }

        data = self._post_chat_request(payload)

        if not data:
            return LLMResponse(
                content="Şu anda yanıt üretme servisinde geçici bir sorun var. Lütfen tekrar dene."
            )

        message_data = data.get("message", {})
        tool_calls = message_data.get("tool_calls")

        # eğer model tool çağrısı döndürdüyse onu alıyoruz
        if tool_calls:
            try:
                first_tool_call = tool_calls[0]
                tool_name = first_tool_call["function"]["name"]
                arguments = first_tool_call["function"]["arguments"]

                tool_call = ToolCall(
                    name=tool_name,
                    arguments=arguments
                )

                return LLMResponse(tool_call=tool_call)

            except (KeyError, TypeError, IndexError):
                return LLMResponse(
                    content="Şu anda yanıt üretme servisinde geçici bir sorun var. Lütfen tekrar dene."
                )

        # tool çağrısı yoksa normal cevabı alıyoruz
        content = message_data.get("content", "")
        return LLMResponse(content=content)

    def get_response_with_history(self, history: list[dict]) -> LLMResponse:
        system_prompt = """
Sen Türkçe konuşan yardımcı bir asistansın.
Kurallar:
- Normal selamlaşma, hal hatır sorma ve genel sohbet mesajlarında tool çağırma.
- Bu tür mesajlara doğrudan kısa ve doğal Türkçe cevap ver.
- Sadece gerçekten gerekli olduğunda tool kullan.

Tool kullanman gereken durumlar:
- hava durumu soruları -> weather_tool
- şirket bilgileri (mesai, adres, telefon) -> company_info_tool
- açık matematik işlemleri -> add_numbers, subtract_numbers, multiply_numbers, divide_numbers

Ek kurallar:
- Eğer kullanıcı kısa bir devam mesajı yazdıysa önceki konuşma bağlamını dikkate al.
- Önceki konuşma bir tool akışıyla ilgiliyse, devam mesajını da buna göre yorumla.
"""

        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ] + history

        payload = {
            "model": self.model,
            "messages": messages,
            "tools": TOOLS,
            "stream": False
        }

        data = self._post_chat_request(payload)

        if not data:
            return LLMResponse(
                content="Şu anda yanıt üretme servisinde geçici bir sorun var. Lütfen tekrar dene."
            )

        message_data = data.get("message", {})
        tool_calls = message_data.get("tool_calls")

        if tool_calls:
            try:
                first_tool_call = tool_calls[0]
                tool_name = first_tool_call["function"]["name"]
                arguments = first_tool_call["function"]["arguments"]

                tool_call = ToolCall(
                    name=tool_name,
                    arguments=arguments
                )

                return LLMResponse(tool_call=tool_call)

            except (KeyError, TypeError, IndexError):
                return LLMResponse(
                    content="Şu anda yanıt üretme servisinde geçici bir sorun var. Lütfen tekrar dene."
                )

        content = message_data.get("content", "")
        return LLMResponse(content=content)

    def get_normal_chat_response(self, message: str) -> str:
        system_prompt = """
Sen Türkçe konuşan yardımcı bir asistansın.
Normal günlük sohbette kısa, doğal ve arkadaşça cevap ver.

Kurallar:
- JSON yazma.
- Tool, fonksiyon, parametre gibi teknik ifadeler kullanma.
- Kısa ve doğal cevap ver.
- Türkçe yaz.
"""

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": message
                }
            ],
            "stream": False
        }

        data = self._post_chat_request(payload)

        if not data:
            return "Şu anda yanıt üretme servisinde geçici bir sorun var. Lütfen tekrar dene."

        message_data = data.get("message", {})
        return message_data.get("content", "").strip() or \
            "Şu anda yanıt üretme servisinde geçici bir sorun var. Lütfen tekrar dene."

    def get_normal_chat_response_with_history(self, history: list[dict]) -> str:
        system_prompt = """
Sen türkçe konuşan bir yardımcı asistansın,
Normal günlük sohbette kısa, doğal ve arkadaşça cevap ver.
Kurallar:
- JSON yazma.
- Tool, fonksiyon, parametre gibi teknik ifadeler kullanma.
- Kısa ve doğal cevap ver.
- Türkçe yaz.
- Önceki konuşma bağlamını dikkate al.
- Eğer kullanıcı kısa bir devam mesajı yazdıysa önceki konuşmayla bağlantıyı koru.
"""

        messages = [
            {
                "role": "system",
                "content": system_prompt
            }

        ] + history

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }

        data = self._post_chat_request(payload)

        if not data:
            return "Şu anda yanıt üretme servisinde geçici bir sorun var. Lütfen tekrar dene."

        message_data = data.get("message", {})
        return message_data.get("content", "").strip() or \
            "Şu anda yanıt üretme servisinde geçici bir sorun var. Lütfen tekrar dene()"

    def get_final_response(self, user_message: str, tool_output: str) -> str:
        system_prompt = """
Sen Türkçe konuşan yardımcı bir asistansın.
Görevin, verilen bilgiyi kısa, doğal ve düzgün bir Türkçe cevap haline getirmektir.

Kurallar:
- Sadece son cevabı yaz.
- "Kullanıcı sorusu", "Tool sonucu", "Cevap" gibi ifadeleri asla yazma.
- Soru cümlesi kurma.
- Gereksiz açıklama yapma.
- Ek bilgi uydurma.
- Türkçe yaz.
- Matematikte çok kısa cevap ver.
- Şirket bilgisi ve hava durumunda doğal ama kısa cevap ver.

Örnekler:
Veri: Mesai saatleri 09:00 - 18:00 arasındadır.
Cevap: Mesai saatleri 09:00 ile 18:00 arasındadır.

Veri: Sonuç: 8
Cevap: Sonuç 8.

Veri: Osmaniye için güncel hava durumu: Sıcaklık 21.5°C, Rüzgar Hızı 10.8 km/s
Cevap: Osmaniye’de sıcaklık 21.5°C, rüzgar hızı ise 10.8 km/s seviyesindedir.
"""

        user_prompt = f"""
Veri:
{tool_output}
"""

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "stream": False
        }

        data = self._post_chat_request(payload)

        if not data:
            return "Şu anda yanıt üretme servisinde geçici bir sorun var. Lütfen tekrar dene."

        message_data = data.get("message", {})
        return message_data.get("content", "").strip() or \
            "Şu anda yanıt üretme servisinde geçici bir sorun var. Lütfen tekrar dene."