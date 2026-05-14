#  chunkları prompt içine koyar ve Ollama’ya gönderir

import re
import requests


from app.core.config import OLLAMA_BASE_URL

try:
    from app.core.rag_config import OLLAMA_REQUEST_TIMEOUT_SECONDS
except ImportError:
    OLLAMA_REQUEST_TIMEOUT_SECONDS = 45


from app.core.rag_config import (
    RAG_MAX_CONTEXT_CHARS,
    RAG_MIN_SCORE,
    RAG_TOP_K,
    RAG_LLM_MODEL,
)

from app.services.rag.embedding_service import EmbeddingService
from app.services.rag.qdrant_service import QdrantService

NO_ANSWER_MESSAGE = "Bu bilgi yüklenen dokümanda bulunamadı."


class RagService:
    """
    rag cevap üretiminden sorumlu servis

    bu servis:
    -kullanıcı sorusunu embedinge çevirir
    -qdrant üzerinden ilgili chunkları getirir
    -chunkları llm promptuna context olarak ekler
    -ollama ile dokümana dayalı cevap üretir 
    -cevapla birlikte kaynak bilgisi döndürür
    """

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.qdrant_service = QdrantService()

    def _deduplicate_results(self, results: list[dict]) -> list[dict]:
        # aynı metin birden fazla kez gelirse context içinde tekrar oluşmasını engeller

        unique_results = []
        seen_text = set()

        for result in results:
            text = result.get("text") or ""
            normalized_text = " ".join(text.split()).lower()

            if normalized_text in seen_text:
                continue

            seen_text.add(normalized_text)
            unique_results.append(result)

        return unique_results

    def _filter_result_by_score(self, results: list[dict]) -> list[dict]:
        # çok düşük skorlu sonuçları eleyerek alakasız context gönderimini azaltır
        filtered_results = []

        for result in results:
            score = result.get("score", 0)

            if score >= RAG_MIN_SCORE:
                filtered_results.append(result)

        return filtered_results

    def _build_context(self, results: list[dict]) -> str:
        # qdranttan gelen chunkları llme verilecek context metnine dönüştürür
        # cevap içinde teknik kaynak ifadeleri görünmesin diye dosya/chunk/parça başlığı vermiyoruz
        # kaynak bilgileri _build_sources fonksiyonunda ayrıca hazırlanıyor

        context_parts = []
        current_length = 0

        for result in results:
            text = result.get("text") or ""
            context_item = text.strip()

            if current_length + len(context_item) > RAG_MAX_CONTEXT_CHARS:
                break

            context_parts.append(context_item)
            current_length += len(context_item)

        return "\n\n---\n\n".join(context_parts)

    def _build_sources(self, results: list[dict]) -> list[dict]:
        # kullanıcıya gösterilecek kaynak bilgisini üretir

        sources = []

        for index, result in enumerate(results, start=1):
            metadata = result.get("metadata") or {}

            sources.append(
                {
                    "source_no": index,
                    "file_name": metadata.get("file_name"),
                    "chunk_index": metadata.get("chunk_index"),
                    "document_id": metadata.get("document_id"),
                    "score": result.get("score"),
                }
            )

        return sources

    def _build_prompt(self, question: str, context: str) -> str:
        # llm e gönderilecek rag promptunu oluşturur
        # amaç cevabı sadece verilen kaynak metinlere dayandırmak
        # farklı doküman türlerinde sade ve anlaşılır cevap üretmesini sağlamak

        return f"""
Sen dokümana dayalı cevap veren bir asistansın.

Görevin:
Kullanıcının sorusunu yalnızca aşağıdaki kaynak metinlere göre cevaplamak.

Kurallar:
- Kaynak metinlerde sorunun cevabı varsa mutlaka cevap ver.
- Kaynak metinlerde cevap yoksa sadece şunu yaz: "Bu bilgi yüklenen dokümanda bulunamadı."
- Kaynaklarda olmayan bilgiyi ekleme.
- Tahmin yapma ve dış bilgi kullanma.
- Kullanıcının sorusunu cevap içinde tekrar etme.
- Cevabı sade, doğal ve anlaşılır Türkçe ile yaz.
- İngilizce kelime kullanma.
- Aynı cümleyi tekrar etme.
- Cevap içinde kaynak, parça, chunk, dosya veya skor bilgisi yazma.

Cevap biçimi:
- Soru "neden" diye soruyorsa sebep-sonuç ilişkisiyle açıkla.
- Soru koşul, şart, başvuru, gereklilik veya adım soruyorsa madde madde cevap ver.
- Soru özet istiyorsa kısa paragraf halinde özetle.
- Sayı, tarih, oran, süre, belge adı, not ortalaması ve başvuru yeri gibi kritik bilgileri atlama.

Kaynak metinler:
{context}

Kullanıcı sorusu:
{question}

Cevap:
""".strip()

    def _build_retry_prompt(self, question: str, context: str) -> str:
        # İlk cevap kalitesiz olursa daha kısa ve daha net ikinci prompt ile cevap üretir.

        return f"""
Aşağıdaki metne göre kullanıcı sorusuna cevap ver.

Kurallar:
- Sadece verilen metindeki bilgileri kullan.
- Cevabı sade ve anlaşılır Türkçe ile yaz.
- Kullanıcı sorusunu tekrar etme.
- İngilizce kelime kullanma.
- Aynı cümleyi tekrar etme.
- Eğer metinde cevap yoksa sadece "Bu bilgi yüklenen dokümanda bulunamadı." yaz.

Metin:
{context}

Soru:
{question}

Kısa ve net cevap:
""".strip()

    def _clean_answer(self, answer: str) -> str:
        # model bazen cevap içine kaynak/parça bilgisi veya bulunamadı cümlesini yanlış yerde ekleyebiliyor
        # kaynaklar zaten sistem tarafından ayrıca gösterildiği için bu satırları temizliyoruz

        if not answer:
            return "Cevap üretilemedi."

        cleaned_lines = []

        for line in answer.splitlines():
            stripped_line = line.strip()
            lowered_line = stripped_line.lower()

            if not stripped_line:
                continue

            if lowered_line.startswith("kaynak"):
                continue

            if lowered_line.startswith("parça"):
                continue

            if lowered_line.startswith("- parça"):
                continue

            if lowered_line.startswith("chunk"):
                continue

            if lowered_line.startswith("dosya"):
                continue

            if lowered_line.startswith("skor"):
                continue

            cleaned_lines.append(stripped_line)

        cleaned_answer = " ".join(cleaned_lines).strip()

        cleaned_answer = cleaned_answer.replace("process", "süreç")
        cleaned_answer = cleaned_answer.replace("Process", "Süreç")
        cleaned_answer = cleaned_answer.replace("first", "önce")
        cleaned_answer = cleaned_answer.replace("First", "Önce")

        # Cevap sadece bulunamadı mesajıysa bunu standart hale getir.
        if cleaned_answer.strip().lower() == NO_ANSWER_MESSAGE.lower():
            return NO_ANSWER_MESSAGE

        # Model doğru cevabın sonuna yanlışlıkla bulunamadı mesajı eklediyse onu temizle.
        if NO_ANSWER_MESSAGE in cleaned_answer:
            without_no_answer = cleaned_answer.replace(NO_ANSWER_MESSAGE, "").strip()

            if without_no_answer:
                return without_no_answer

            return NO_ANSWER_MESSAGE

        if not cleaned_answer:
            return "Cevap üretilemedi."

        return cleaned_answer

    def _is_weak_answer(self, answer: str, question: str) -> bool:
        # LLM bazen boş, sadece tırnak, soruyu tekrar eden veya kalitesiz cevap döndürebiliyor.
        # Bu durumda aynı context ile daha net ikinci bir cevap denemesi yapacağız.

        if not answer:
            return True

        normalized_answer = answer.strip()
        normalized_question = question.strip().lower()

        if normalized_answer in ['""', "''", "“”", "‘’"]:
            return True

        if len(normalized_answer) < 20:
            return True

        if normalized_answer.lower().startswith(normalized_question):
            return True

        lowered_answer = normalized_answer.lower()

        if "own " in lowered_answer or " users" in lowered_answer or " process" in lowered_answer:
            return True

        sentences = re.split(r"[.!?]+", normalized_answer)
        cleaned_sentences = [
            sentence.strip().lower()
            for sentence in sentences
            if sentence.strip()
        ]

        if len(cleaned_sentences) != len(set(cleaned_sentences)):
            return True

        return False

    def _ask_ollama(self, prompt: str) -> str:
        #oluşturulan rag promptunu ollamaya gönderir

        url = f"{OLLAMA_BASE_URL}/api/chat"

        payload = {
            "model": RAG_LLM_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Sen dokümana dayalı cevap veren bir asistansın. "
                        "Sadece kullanıcıya verilen kaynak metinlere göre cevap verirsin. "
                        "Kaynakta cevap varsa açık ve sade şekilde yanıtlarsın; kaynakta cevap yoksa bulunamadı dersin."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": False,
            "options": {
                "temperature": 0.0
            }
        }

        response = requests.post(
            url,
            json=payload,
            timeout=OLLAMA_REQUEST_TIMEOUT_SECONDS
        )

        response.raise_for_status()

        data = response.json()
        answer = data.get("message", {}).get("content", "")

        if not answer:
            return "Cevap üretilemedi."

        return self._clean_answer(answer)



    def _polish_answer(self, answer: str, question: str) -> str:
        # üretilen cevap doğru bilgi içerse bile bazen karmaşık, tekrarlı veya doğal olmayan şekilde gelebiliyor
        # bu fonksiyon cevabı kaynak dışına çıkmadan daha sade ve anlaşılır hale getirmek için kullanılır

        if not answer:
            return "Cevap üretilemedi."

        if answer.strip().lower() == NO_ANSWER_MESSAGE.lower():
            return NO_ANSWER_MESSAGE

        polish_prompt = f"""
Aşağıdaki cevap, dokümana dayalı bir RAG sisteminden üretilmiştir.
Bu cevabı anlamını değiştirmeden sade, doğal ve anlaşılır Türkçe ile yeniden yaz.

Kurallar:
- Yeni bilgi ekleme.
- Cevaptaki anlamı değiştirme.
- Kullanıcının sorusunu tekrar etme.
- İngilizce kelime kullanma.
- Aynı cümleyi tekrar etme.
- Gereksiz giriş cümlelerini kaldır.
- Cevap kısa, net ve son kullanıcıya uygun olsun.
- Eğer cevap "Bu bilgi yüklenen dokümanda bulunamadı." ise aynen bırak.

Kullanıcı sorusu:
{question}

Düzenlenecek cevap:
{answer}

Düzenlenmiş final cevap:
""".strip()

        polished_answer = self._ask_ollama(polish_prompt)

        if not polished_answer:
            return answer

        if polished_answer.strip().lower() == NO_ANSWER_MESSAGE.lower() and answer.strip().lower() != NO_ANSWER_MESSAGE.lower():
            return answer

        return polished_answer   

    def answer_question(
            self,
            question: str,
            user_id: str,
            document_id: str | None = None,
            top_k: int = RAG_TOP_K
    ) -> dict:
        #kullanıcı sorusuna rag cevabı üretir

        query_embedding = self.embedding_service.embed_query(question)

        retrieved_results = self.qdrant_service.search_similar_chunks(
            query_embedding=query_embedding,
            top_k=top_k,
            user_id=user_id,
            document_id=document_id
        )

        retrieved_results = self._deduplicate_results(retrieved_results)

        filtered_results = self._filter_result_by_score(retrieved_results)

# Eğer skor filtresi bütün sonuçları elediyse,
# tamamen cevap yok demek yerine en iyi birkaç sonucu tekrar kullanıyoruz.
# Çünkü bazı doğru sonuçların skoru eşik altında kalabilir.
        if filtered_results:
            retrieved_results = filtered_results
        else:
            retrieved_results = retrieved_results[:3]

        if not retrieved_results:
            return {
        "answer": NO_ANSWER_MESSAGE,
        "sources": [],
        "retrieved_count": 0
    }

        context = self._build_context(retrieved_results)
        prompt = self._build_prompt(
            question=question,
            context=context
        )

        answer = self._ask_ollama(prompt)

        if self._is_weak_answer(answer, question):
            retry_prompt = self._build_retry_prompt(
                question=question,
                context=context
            )
            retry_answer = self._ask_ollama(retry_prompt)

            if not self._is_weak_answer(retry_answer, question):
                answer = retry_answer

        if answer.strip().lower() == NO_ANSWER_MESSAGE.lower():
            return {
                "answer": NO_ANSWER_MESSAGE,
                "sources": [],
                "retrieved_count": 0
            }

        answer = self._polish_answer(answer, question)

        if answer.strip().lower() == NO_ANSWER_MESSAGE.lower():
            return {
                "answer": NO_ANSWER_MESSAGE,
                "sources": [],
                "retrieved_count": 0
            }

        sources = self._build_sources(retrieved_results)

        return {
            "answer": answer,
            "sources": sources,
            "retrieved_count": len(retrieved_results)
        }