# bu dosyanın gelen emsajı okuyup karar vermesi gerekiyor o yüzden toolları burda kullanmamız lazım 
# yani kullanıcının yazdığı mesaja bakmalı ve hangi fonksiyonla alakalı ise onu çağırmalı 
# Python resmi regex HOWTO ve re dokümantasyonunda re.fullmatch() fonksiyonunu kullanarak bir string'in belirli bir regex desenine tam olarak uyup uymadığını kontrol edebilirsiniz. re.fullmatch() fonksiyonu, verilen desene tam olarak uyan bir string döndürür veya eşleşme olmazsa None döndürür bu anlatılıyor

import re
from typing import Optional

# bu aşamada artık funtion-calling mantığına geçtik
from app.llm.ollama_provider import OllamaProvider
from app.services.history_service_factory import get_history_service
from app.services.weather_service import (
    get_current_weather,
    get_tomorrow_weather,
    get_weekly_weather
)
from app.services.company_info_service import get_company_info
from app.tools.math_tools import (
    add_numbers,
    subtract_numbers,
    multiply_numbers,
    divide_numbers
)


provider = OllamaProvider()
history_service = get_history_service()


def is_weather_related(text: str) -> bool:
    weather_keywords = [
        "hava durumu",
        "hava nasıl",
        "kaç derece",
        "sıcaklık",
        "sicaklik",
        "rüzgar",
        "ruzgar",
        "yağmur",
        "yagmur",
        "hava"
    ]
    return any(keyword in text for keyword in weather_keywords)


def is_company_related(text: str) -> bool:
    return "mesai" in text or "adres" in text or "telefon" in text


def extract_math_expression(message: str):
    match = re.search(r"(-?\d+)\s*([\+\-\*/])\s*(-?\d+)", message)
    if not match:
        return None

    a = int(match.group(1))
    operator = match.group(2)
    b = int(match.group(3))

    return a, operator, b


def is_math_related(text: str) -> bool:
    if extract_math_expression(text):
        return True

    math_follow_up_keywords = [
        "ekle",
        "çıkar",
        "cikar",
        "çarp",
        "carp",
        "böl",
        "bol",
        "topla",
        "sonuca",
        "sonucu",
        "sonuçtan",
        "sonuctan",
        "ona"
    ]

    return any(keyword in text for keyword in math_follow_up_keywords)


def needs_tool(message: str) -> bool:
    text = message.lower().strip()

    if is_company_related(text):
        return True

    if is_math_related(text):
        return True

    return False


def looks_like_follow_up(message: str) -> bool:
    text = message.lower().strip()

    follow_up_keywords = [
        "peki",
        "tamam da",
        "biraz daha",
        "daha açık",
        "daha acik",
        "orada",
        "yarın",
        "yarin",
        "bugün",
        "bugun",
        "şimdi",
        "simdi",
        "nasıl olur",
        "anlat",
        "detaylı",
        "detayli",
        "önceki",
        "onceki",
        "ona",
        "sonuca",
        "sonucu"
    ]

    return any(keyword in text for keyword in follow_up_keywords)

def is_project_info_question(message: str) -> bool:
    text = message.lower().strip()

    keywords = [
        "bu proje ne yapıyor",
        "bu proje ne işe yarıyor",
        "bu sistem ne yapıyor",
        "bu sistem ne işe yarıyor",
        "bu chatbot ne yapıyor",
        "bu chatbot ne işe yarıyor",
        "proje ne yapıyor",
        "proje ne işe yarıyor",
        "sistem ne yapıyor",
        "sistem ne işe yarıyor",
        "chatbot ne yapıyor",
        "chatbot ne işe yarıyor",
        "kendini tanıt",
        "bu proje nedir",
        "bu sistem nedir"
    ]

    return any(keyword in text for keyword in keywords)


def get_project_info_answer() -> str:
    return (
        "Bu proje, FastAPI backend ve Gradio arayüzü ile geliştirilen yapay zekâ destekli "
        "bir sohbet ve doküman asistanı prototipidir. Normal sohbetlerde açık kaynak LLM "
        "kullanılır; hava durumu, matematik ve şirket bilgisi gibi işlemler backend tarafındaki "
        "tool fonksiyonlarıyla çalışır. Redis ile konuşma geçmişi, takip soruları ve state bilgisi "
        "tutulur. Ayrıca rate limit ve LLM concurrency kontrolü ile çoklu isteklerde sistemin daha "
        "kontrollü çalışması sağlanır. RAG tarafında ise kullanıcı doküman yükleyebilir; sistem "
        "dokümanı parçalara ayırır, embedding üretir, Qdrant’a kaydeder ve dokümana dayalı cevap üretir."
    )

def get_recent_history(
    conversation_id: str,
    user_id: Optional[str] = None,
    limit: int = 6
) -> list[dict]:
    history = history_service.get_history(conversation_id, user_id=user_id)
    return history[-limit:]


def save_conversation_turn(
    conversation_id: Optional[str],
    user_message: str,
    assistant_message: str,
    user_id: Optional[str] = None
) -> None:
    if not conversation_id:
        return

    history_service.add_message(
        conversation_id=conversation_id,
        role="user",
        content=user_message,
        user_id=user_id
    )

    history_service.add_message(
        conversation_id=conversation_id,
        role="assistant",
        content=assistant_message,
        user_id=user_id
    )

def requires_llm_processing(
    message: str,
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> bool:
    """
    Mesajın gerçekten LLM çağrısına ihtiyaç duyup duymadığını belirler.

    Amaç:
    - weather/math/company gibi hızlı akışları concurrency limit dışında tutmak
    - sadece normal sohbet gibi LLM gerektiren akışları sınırlandırmak
    - follow-up mantığını bozmamak
    """

    text = message.lower().strip()

    # Açıkça hızlı/tool tabanlı akışlar LLM concurrency sınırına girmesin.
    if is_weather_related(text):
        return False

    if is_company_related(text):
        return False

    if is_math_related(text):
        return False

    last_topic = None
    previous_history = []

    if conversation_id:
        last_topic = history_service.get_topic(conversation_id, user_id=user_id)
        previous_history = get_recent_history(conversation_id, user_id=user_id)

    # Weather/company/math devam soruları da LLM'e gitmeden mevcut kurallarla cevaplanıyor.
    if looks_like_follow_up(message) and last_topic in ["weather", "company", "math"]:
        return False

    # Ortada geçmiş yoksa process_message zaten açıklama isteyen kısa cevap döndürüyor.
    # Bu durumda LLM çağırmaya gerek yok.
    if looks_like_follow_up(message) and not previous_history:
        return False

    # Geriye kalan normal sohbet / genel mesajlar LLM gerektirir.
    return True

def normalize_city_text(text: str) -> str:
    text = text.lower().strip()

    text = text.replace("?", " ")
    text = text.replace(",", " ")
    text = text.replace(".", " ")
    text = text.replace("'", "")
    text = text.replace("’", "")

    phrases_to_remove = [
        "hava durumu",
        "hava nasıl",
        "hava",
        "kaç derece",
        "sıcaklık",
        "sicaklik",
        "rüzgar",
        "ruzgar",
        "yağmur",
        "yagmur",
        "haftalık",
        "haftalik",
        "1 haftalık",
        "1 haftalik",
        "bir haftalık",
        "bir haftalik",
        "1 hafta boyunca",
        "bir hafta boyunca",
        "hafta boyunca",
        "bir hafta",
        "1 hafta",
        "7 günlük",
        "7 gunluk",
        "bu hafta",
        "önümüzdeki günler",
        "onumuzdeki gunler",
        "yarın",
        "yarin",
        "bugün",
        "bugun",
        "şimdi",
        "simdi",
        "nasıl olur",
        "nasil olur",
        "nasıl",
        "nasil",
        "için",
        "icin",
        "ver",
        "göster",
        "goster",
        "ne",
        "nedir"
    ]

    for phrase in phrases_to_remove:
        text = text.replace(phrase, " ")

    words = text.split()
    cleaned_words = []

    ignored_words = {
        "peki",
        "biraz",
        "daha",
        "detaylı",
        "detayli",
        "açıkla",
        "acikla",
        "anlat",
        "olur",
        "bir",
        "1",
        "boyunca"
    }

    for word in words:
        if word in ignored_words:
            continue

        if word == "de" or word == "da":
            continue

        if word.endswith("de") and len(word) > 4:
            root = word[:-2]
            if len(root) >= 3:
                word = root

        if word.endswith("da") and len(word) > 4:
            root = word[:-2]
            if len(root) >= 3:
                word = root

        cleaned_words.append(word)

    return " ".join(cleaned_words).strip()


def extract_city_from_message(message: str) -> Optional[str]:
    text = normalize_city_text(message)

    if not text:
        return None

    invalid_city_tokens = {
        "nasıl",
        "nasil",
        "yarın",
        "yarin",
        "bugün",
        "bugun",
        "şimdi",
        "simdi",
        "peki",
        "olur",
        "anlat",
        "bir",
        "boyunca",
        "hafta",
        "haftalık",
        "haftalik",
        "hava"
    }

    if text in invalid_city_tokens:
        return None

    return text


def is_weekly_weather_request(message: str) -> bool:
    text = message.lower().strip()

    weekly_keywords = [
        "haftalık",
        "haftalik",
        "7 günlük",
        "7 gunluk",
        "bu hafta",
        "önümüzdeki günler",
        "onumuzdeki gunler",
        "1 haftalık",
        "1 haftalik",
        "bir haftalık",
        "bir haftalik",
        "1 hafta boyunca",
        "bir hafta boyunca",
        "bir hafta",
        "1 hafta"
    ]

    return any(keyword in text for keyword in weekly_keywords)


def is_tomorrow_weather_request(message: str) -> bool:
    text = message.lower().strip()
    return "yarın" in text or "yarin" in text


def process_weather_message(
    message: str,
    conversation_id: Optional[str],
    user_id: Optional[str] = None
) -> str:
    city = extract_city_from_message(message)
    text = message.lower().strip()

    last_city = None
    if conversation_id:
        last_city = history_service.get_weather_city(conversation_id, user_id=user_id)

    explicit_city_like_request = any(
        phrase in text for phrase in [
            " için ",
            "icin ",
            "mersin",
            "trabzon",
            "ankara",
            "izmir",
            "istanbul",
            "kayseri",
            "osmaniye",
            "kahramanmaraş",
            "kahramanmaras"
        ]
    )

    follow_up_only = looks_like_follow_up(message) and not explicit_city_like_request

    if follow_up_only and last_city:
        city = last_city

    if not city and last_city:
        city = last_city

    if not city:
        return "Hangi şehir için sorduğunu biraz daha net yazabilir misin?"

    if conversation_id:
        history_service.set_weather_city(conversation_id, city, user_id=user_id)
        history_service.set_topic(conversation_id, "weather", user_id=user_id)

    if is_weekly_weather_request(message):
        return get_weekly_weather(city)

    if is_tomorrow_weather_request(message):
        return get_tomorrow_weather(city)

    return get_current_weather(city)


def process_company_message(
    message: str,
    conversation_id: Optional[str],
    user_id: Optional[str] = None
) -> str:
    text = message.lower().strip()

    if conversation_id:
        history_service.set_topic(conversation_id, "company", user_id=user_id)

    if "mesai" in text:
        if conversation_id:
            history_service.set_company_detail(conversation_id, "mesai", user_id=user_id)
        return "Mesai saatleri 09.00 ile 18.00 arasındadır."

    if "adres" in text:
        if conversation_id:
            history_service.set_company_detail(conversation_id, "adres", user_id=user_id)
        return get_company_info("adres")

    if "telefon" in text:
        if conversation_id:
            history_service.set_company_detail(conversation_id, "telefon", user_id=user_id)
        return get_company_info("telefon")

    return "İstersen mesai, adres veya telefon bilgisinden hangisini istediğini daha açık yazabilirsin."


def process_company_follow_up(
    message: str,
    conversation_id: Optional[str],
    user_id: Optional[str] = None
) -> str:
    text = message.lower().strip()
    detail = history_service.get_company_detail(conversation_id, user_id=user_id) if conversation_id else None

    if detail == "mesai":
        time_match = re.search(r"(\d{1,2})[.:](\d{2})", text)

        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))

            if hour < 9:
                return "09.00'dan önce gelirsen mesai başlamadan gelmiş olursun."
            if hour < 18 or (hour == 18 and minute == 0):
                return "09.00 ile 18.00 arasında gelirsen mesai saatleri içinde gelmiş olursun."
            return "18.00 sonrasında gelirsen mesai saatleri dışına çıkmış olursun."

        return "Mesai saatleri 09.00 ile 18.00 arasındadır. İstersen belirli bir saat yazarak tekrar sorabilirsin."

    if detail == "adres":
        return "Adres bilgisiyle ilgili daha net neyi öğrenmek istediğini yazabilir misin?"

    if detail == "telefon":
        return "Telefon bilgisiyle ilgili daha net neyi öğrenmek istediğini yazabilir misin?"

    return "İstersen mesai, adres veya telefon bilgisinden hangisini daha detaylı istediğini daha açık yazabilirsin."


def process_math_message(
    message: str,
    conversation_id: Optional[str],
    user_id: Optional[str] = None
) -> str:
    parsed = extract_math_expression(message)

    if parsed:
        a, operator, b = parsed

        if operator == "+":
            result = add_numbers(a, b)
        elif operator == "-":
            result = subtract_numbers(a, b)
        elif operator == "*":
            result = multiply_numbers(a, b)
        elif operator == "/":
            try:
                result = divide_numbers(a, b)
            except ValueError as e:
                return str(e)
        else:
            return "Desteklenmeyen işlem."

        if conversation_id:
            history_service.set_topic(conversation_id, "math", user_id=user_id)
            history_service.set_math_result(conversation_id, result, user_id=user_id)

        return f"Sonuç {result}."

    text = message.lower().strip()
    last_result = history_service.get_math_result(conversation_id, user_id=user_id) if conversation_id else None

    if last_result is None:
        return "İşlemi daha açık şekilde yazabilir misin?"

    add_patterns = [
        r"sonuca\s*\+?\s*(\d+)\s*(daha\s*)?ekle",
        r"sonucu\s*\+?\s*(\d+)\s*(daha\s*)?ekle",
        r"ona\s*\+?\s*(\d+)\s*(daha\s*)?ekle",
        r"bu sonuca\s*\+?\s*(\d+)\s*(daha\s*)?ekle",
        r"bu sonucu\s*\+?\s*(\d+)\s*(daha\s*)?ekle",
        r"önceki sonuca\s*\+?\s*(\d+)\s*(daha\s*)?ekle",
        r"onceki sonuca\s*\+?\s*(\d+)\s*(daha\s*)?ekle",
        r"\+?\s*(\d+)\s*(daha\s*)?ekle"
    ]

    for pattern in add_patterns:
        match = re.search(pattern, text)
        if match:
            extra = int(match.group(1))
            result = last_result + extra

            if conversation_id:
                history_service.set_topic(conversation_id, "math", user_id=user_id)
                history_service.set_math_result(conversation_id, result, user_id=user_id)

            return f"Önceki sonuç {last_result} idi, {extra} ekleyince sonuç {result} oldu."

    subtract_patterns = [
        r"sonuçtan\s*(\d+)\s*(daha\s*)?(çıkar|cikar)",
        r"sonuctan\s*(\d+)\s*(daha\s*)?(çıkar|cikar)",
        r"sonucu\s*(\d+)\s*(daha\s*)?(çıkar|cikar)",
        r"sonuca\s*(\d+)\s*(daha\s*)?(çıkar|cikar)",
        r"ondan\s*(\d+)\s*(daha\s*)?(çıkar|cikar)",
        r"(\d+)\s*(daha\s*)?(çıkar|cikar)"
    ]

    for pattern in subtract_patterns:
        match = re.search(pattern, text)
        if match:
            extra = int(match.group(1))
            result = last_result - extra

            if conversation_id:
                history_service.set_topic(conversation_id, "math", user_id=user_id)
                history_service.set_math_result(conversation_id, result, user_id=user_id)

            return f"Önceki sonuç {last_result} idi, {extra} çıkarınca sonuç {result} oldu."

    multiply_patterns = [
        r"sonucu\s*(\d+)\s*ile\s*(çarp|carp)",
        r"sonuca\s*(\d+)\s*ile\s*(çarp|carp)",
        r"onu\s*(\d+)\s*ile\s*(çarp|carp)",
        r"(\d+)\s*ile\s*(çarp|carp)"
    ]

    for pattern in multiply_patterns:
        match = re.search(pattern, text)
        if match:
            extra = int(match.group(1))
            result = last_result * extra

            if conversation_id:
                history_service.set_topic(conversation_id, "math", user_id=user_id)
                history_service.set_math_result(conversation_id, result, user_id=user_id)

            return f"Önceki sonuç {last_result} idi, {extra} ile çarpınca sonuç {result} oldu."

    divide_patterns = [
        r"sonucu\s*(\d+)\s*e\s*(böl|bol)",
        r"sonucu\s*(\d+)\s*ya\s*(böl|bol)",
        r"sonuca\s*(\d+)\s*e\s*(böl|bol)",
        r"sonuca\s*(\d+)\s*ya\s*(böl|bol)",
        r"onu\s*(\d+)\s*e\s*(böl|bol)",
        r"onu\s*(\d+)\s*ya\s*(böl|bol)",
        r"(\d+)\s*e\s*(böl|bol)",
        r"(\d+)\s*ya\s*(böl|bol)"
    ]

    for pattern in divide_patterns:
        match = re.search(pattern, text)
        if match:
            extra = int(match.group(1))
            try:
                result = divide_numbers(last_result, extra)
            except ValueError as e:
                return str(e)

            if conversation_id:
                history_service.set_topic(conversation_id, "math", user_id=user_id)
                history_service.set_math_result(conversation_id, result, user_id=user_id)

            return f"Önceki sonuç {last_result} idi, {extra}'e bölünce sonuç {result} oldu."

    if "sonuca" in text or "sonucu" in text or "sonuçtan" in text or "sonuctan" in text or "ona" in text:
        return "Önceki sonuca ne yapmak istediğini biraz daha açık yazabilir misin? Örneğin: sonuca 2 ekle, sonuçtan 3 çıkar, sonucu 4e böl."

    return "İşlemi daha açık şekilde yazabilir misin?"


def process_message(
        message: str,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None
        # akışa dahil ettik ama bir sonraki adımda kullanıyor olucaz
        ) -> str:
    try:
        text = message.lower().strip()
        previous_history = []
        last_topic = None

        if conversation_id:
            previous_history = get_recent_history(conversation_id, user_id=user_id)
            last_topic = history_service.get_topic(conversation_id, user_id=user_id)

        if is_weather_related(text):
            answer = process_weather_message(message, conversation_id, user_id=user_id)
            save_conversation_turn(conversation_id, message, answer, user_id=user_id)
            return answer

        if is_company_related(text):
            answer = process_company_message(message, conversation_id, user_id=user_id)
            save_conversation_turn(conversation_id, message, answer, user_id=user_id)
            return answer

        if is_math_related(text):
            answer = process_math_message(message, conversation_id, user_id=user_id)
            save_conversation_turn(conversation_id, message, answer, user_id=user_id)
            return answer

        if looks_like_follow_up(message) and last_topic == "weather":
            answer = process_weather_message(message, conversation_id, user_id=user_id)
            save_conversation_turn(conversation_id, message, answer, user_id=user_id)
            return answer

        if looks_like_follow_up(message) and last_topic == "company":
            answer = process_company_follow_up(message, conversation_id, user_id=user_id)
            save_conversation_turn(conversation_id, message, answer, user_id=user_id)
            return answer

        if looks_like_follow_up(message) and last_topic == "math":
            answer = process_math_message(message, conversation_id, user_id=user_id)
            save_conversation_turn(conversation_id, message, answer, user_id=user_id)
            return answer

        if looks_like_follow_up(message) and not previous_history:
            answer = "Hangi konunun devamı olduğunu biraz daha net yazabilir misin?"
            save_conversation_turn(conversation_id, message, answer, user_id=user_id)
            return answer
        
        if is_project_info_question(message):
            answer = get_project_info_answer()

            if conversation_id:
                history_service.set_topic(conversation_id, "chat", user_id=user_id)

            save_conversation_turn(conversation_id, message, answer, user_id=user_id)
            return answer

        if conversation_id:
            history_service.set_topic(conversation_id, "chat", user_id=user_id)

        answer = provider.get_normal_chat_response(message)
        save_conversation_turn(conversation_id, message, answer, user_id=user_id)
        return answer

    except Exception as e:
        print(f"Agent service beklenmeyen hata: {type(e).__name__} - {e}")
        return "Şu anda isteğini işlerken beklenmedik bir sorun oluştu. Lütfen tekrar dene."