#  chunkları prompt içine koyar ve Ollama’ya gönderir

import requests

from app.core.config import OLLAMA_BASE_URL, OLLAMA_MODEL

try:
    from app.core.rag_config import OLLAMA_REQUEST_TIMEOUT_SECONDS
except ImportError:
    OLLAMA_REQUEST_TIMEOUT_SECONDS = 45


from app.core.rag_config import (
    RAG_MAX_CONTEXT_CHARS,
    RAG_MIN_SCORE,
    RAG_TOP_K,
)

from app.services.rag.embedding_service import EmbeddingService
from app.services.rag.qdrant_service import QdrantService

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
        # qdranttan gelen chunkları llme verilecek context metinene dönüştürür
        # kaynak bilg,ilerini burda vermiuoruz cünkü cevap içinde dosya-chunk bilgşsi yazmasını istemiyoruz
        # kaynak bilgileri _build_sources fonksiyonunda ayrıca hazırlanıyor 

        context_parts = []
        current_length = 0 

        for index, result in enumerate(results, start= 1):
            text = result.get("text") or ""
           
            context_item = f"parça{index}:\n{text}"

            if current_length + len(context_item) > RAG_MAX_CONTEXT_CHARS:
                break

            context_parts.append(context_item)
            current_length += len(context_item)

        return "\n".join(context_parts)
    

    def _build_sources(self, results:list[dict]) -> list[dict]:
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
                    "score" : result.get("score"),
                    
                }
            )
        return sources
    

    def _build_prompt(self, question: str, context: str) -> str:
        # llm e gönderilecek rag promptunu oluşturur
        #burda amaç cevabu sadece verilen kaynaklara dayandırmak

        return f"""
Sen bir RAG cevaplama asistanısın.

Görevin:
Kullanıcı sorusuna SADECE verilen metin parçalarındaki bilgilerle cevap vermek.

Kesin kurallar:
- Sadece kaynak metinlerde açıkça geçen bilgileri kullan.
- Kendi genel bilgini ekleme.
- Kaynak metinleri aynen kopyalama.
- "Parça 1", "Parça 2", "Kaynak", "chunk", "skor", "dosya" gibi teknik kaynak ifadelerini cevaba yazma.
- Madde madde kaynak listesi yazma.
- İngilizce kelime kullanma; cevabı tamamen Türkçe yaz.
- Cevap tekrar eden cümleler içermesin.
- En fazla 3 cümlelik kısa ve net bir cevap ver.
- Kaynaklarda cevap yoksa sadece şu cümleyi yaz:
"Bu bilgi yüklenen dokümanda bulunamadı."

Kaynak metinler:
{context}

Kullanıcı sorusu:
{question}

Sadece final cevabı yaz:
""".strip()
    

    def _clean_answer(self, answer: str) -> str:
        # model bazen cevap içine kaynak/parça bilgisi veya bağlam listesini yazabiliyor
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

        if not cleaned_answer:
            return "Cevap üretilemedi."

        return cleaned_answer
    
    
    def _ask_ollama(self, prompt: str) -> str:
        #oluşturulan rag promptunu ollamaya gönderir

        url = f"{OLLAMA_BASE_URL}/api/chat"

        payload ={
            "model":OLLAMA_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content":(
                        "Sen kaynak dışına çıkmayan bir RAG cevaplama asistanısın. "
                        "Sadece kullanıcı mesajında verilen kaynak parçalarındaki bilgileri kullanırsın. "
                        "Kaynaklarda açıkça bulunmayan hiçbir bilgiyi eklemezsin."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": False,
            "options":{
                "temperature":0.0
            }
        }

        response = requests.post(
            url,
            json=payload,
            timeout=OLLAMA_REQUEST_TIMEOUT_SECONDS
        )

        response.raise_for_status()

        data = response.json()
        answer = data.get("message",{}).get("content","")

        if not answer:
            return "Cevap üretilemedi."
        
        return self._clean_answer(answer)
    


    def answer_question(
            self,
            question: str,
            user_id: str,
            document_id: str| None= None,
            top_k: int =RAG_TOP_K
    ) -> dict:
        #kullanıcı sorusuna rag cevabı üretir

        query_embedding =self.embedding_service.embed_query(question)

        retrieved_results = self.qdrant_service.search_similar_chunks(
            query_embedding=query_embedding,
            top_k=top_k,
            user_id=user_id,
            document_id=document_id
        )


        retrieved_results = self._deduplicate_results(retrieved_results)
        retrieved_results = self._filter_result_by_score(retrieved_results)

        if not retrieved_results:
            return{
                "answer": "bu bilgi yüklenen dokümanda bulunamadı",
                "sources": [],
                "retrieved_count":0
            }
        

        context = self._build_context(retrieved_results)
        prompt = self._build_prompt(
            question=question,
            context=context
        )

        answer = self._ask_ollama(prompt)

        if "Bu bilgi yüklenen dokümanda bulunamadı" in answer:
            return {
        "answer": answer,
        "sources": [],
        "retrieved_count": 0
    }

        sources = self._build_sources(retrieved_results)

        return {
        "answer": answer,
        "sources": sources,
        "retrieved_count": len(retrieved_results)
}