import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Optional

import gradio as gr
import redis
import requests


# =========================================================
# Demo ayarları
# =========================================================

API_BASE_URL = os.getenv("DEMO_CHAT_API_BASE_URL", "http://127.0.0.1:8001")
CHAT_API_URL = f"{API_BASE_URL}/api/chat"
HEALTH_API_URL = f"{API_BASE_URL}/api/health"

DEFAULT_USER_ID = "demo_user"
DEFAULT_CONVERSATION_ID = "demo_conversation"

DEFAULT_RAG_USER_ID = "rag_demo_user"
DEFAULT_DOCUMENT_ID = "demo_document_1"


# =========================================================
# Proje içi importlar
# =========================================================

from app.core.config import (
    REDIS_URL,
    RATE_LIMIT_MAX_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    LLM_CONCURRENCY_LIMIT_MAX_REQUESTS,
)

from app.services.history_service_factory import get_history_service


try:
    from app.core.rag_config import (
        QDRANT_URL,
        QDRANT_COLLECTION_NAME,
        RAG_EMBEDDING_MODEL,
        RAG_LLM_MODEL,
        RAG_TOP_K,
    )
except Exception:
    QDRANT_URL = "Bilinmiyor"
    QDRANT_COLLECTION_NAME = "Bilinmiyor"
    RAG_EMBEDDING_MODEL = "Bilinmiyor"
    RAG_LLM_MODEL = "Bilinmiyor"
    RAG_TOP_K = 5


_history_service = None
_rag_service = None


# =========================================================
# Ortak yardımcı fonksiyonlar
# =========================================================

def get_demo_history_service():
    global _history_service

    if _history_service is None:
        _history_service = get_history_service()

    return _history_service


def refresh_demo_history_service():
    global _history_service
    _history_service = get_history_service()
    return _history_service


def get_redis_client():
    try:
        return redis.Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=2,
        )
    except Exception:
        return None


def redis_status() -> tuple[bool, str]:
    client = get_redis_client()

    if client is None:
        return False, "Redis client oluşturulamadı"

    try:
        result = client.ping()
        return bool(result), "Redis bağlantısı başarılı" if result else "Redis ping başarısız"
    except Exception as e:
        return False, f"Redis bağlantı hatası: {type(e).__name__} - {e}"


def safe_value(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return str(value)


def markdown_table(rows: list[tuple[str, Any]]) -> str:
    lines = ["| Alan | Değer |", "|---|---|"]

    for key, value in rows:
        lines.append(f"| {key} | `{safe_value(value)}` |")

    return "\n".join(lines)


def read_response_headers(response: Optional[requests.Response]) -> Dict[str, str]:
    if response is None:
        return {}

    header_names = [
        "X-Request-Id",
        "X-Worker-Pid",
        "X-Response-Time-Ms",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "Retry-After",
        "X-LLM-Concurrency-Required",
        "X-LLM-Concurrency-Limit",
        "X-LLM-Concurrency-Current",
        "X-LLM-Concurrency-Remaining",
    ]

    return {
        header_name: response.headers.get(header_name, "-")
        for header_name in header_names
    }


def get_backend_health() -> str:
    try:
        response = requests.get(HEALTH_API_URL, timeout=3)

        if response.status_code == 200:
            return "Çalışıyor"

        return f"HTTP {response.status_code}"
    except Exception as e:
        return f"Ulaşılamadı: {type(e).__name__}"


def get_rate_limit_snapshot(user_id: str) -> dict:
    client = get_redis_client()
    ok, _ = redis_status()

    if not client or not ok:
        return {
            "key": "-",
            "count": "-",
            "ttl": "-",
        }

    key = f"rate_limit:user:{user_id}" if user_id else "rate_limit:anonymous"

    try:
        return {
            "key": key,
            "count": client.get(key) or "0",
            "ttl": client.ttl(key),
        }
    except Exception:
        return {
            "key": key,
            "count": "-",
            "ttl": "-",
        }



def delete_rate_limit_key(user_id: str) -> None:
    """
    Demo testlerinden önce ilgili kullanıcının rate limit sayacını temizler.
    Böylece test sonucu önceki denemelerden etkilenmez.
    """
    client = get_redis_client()
    ok, _ = redis_status()

    if not client or not ok:
        return

    key = f"rate_limit:user:{user_id}" if user_id else "rate_limit:anonymous"

    try:
        client.delete(key)
    except Exception:
        pass


def send_demo_chat_request(
    message: str,
    user_id: str,
    conversation_id: str,
    timeout: int = 20,
) -> dict:
    """
    Demo panelindeki rate limit ve worker testleri için /api/chat endpoint'ine istek atar.
    Response status, header ve cevap özetini tek sözlükte döndürür.
    """
    try:
        response = requests.post(
            CHAT_API_URL,
            json={
                "message": message,
                "user_id": user_id,
                "conversation_id": conversation_id,
            },
            timeout=timeout,
        )

        try:
            data = response.json()
        except Exception:
            data = {}

        return {
            "ok": True,
            "status_code": response.status_code,
            "headers": read_response_headers(response),
            "answer": data.get("answer") or data.get("detail") or response.text[:160],
        }

    except Exception as e:
        return {
            "ok": False,
            "status_code": "-",
            "headers": {},
            "answer": f"{type(e).__name__}: {e}",
        }


def get_concurrency_snapshot() -> dict:
    client = get_redis_client()
    ok, _ = redis_status()

    if not client or not ok:
        return {
            "key": "concurrency:llm:active",
            "active": "-",
        }

    try:
        return {
            "key": "concurrency:llm:active",
            "active": client.get("concurrency:llm:active") or "0",
        }
    except Exception:
        return {
            "key": "concurrency:llm:active",
            "active": "-",
        }


def format_recent_history(history: list[dict], limit: int = 6) -> str:
    if not history:
        return "Henüz konuşma geçmişi yok."

    selected = history[-limit:]
    lines = []

    for item in selected:
        role = item.get("role", "-")
        content = item.get("content", "")
        content = content.replace("\n", " ").strip()

        if len(content) > 120:
            content = content[:120] + "..."

        lines.append(f"- **{role}:** {content}")

    return "\n".join(lines)


# =========================================================
# Chatbot teknik panel
# =========================================================

def build_chat_technical_panel(
    user_id: str,
    conversation_id: str,
    response_headers: Optional[Dict[str, str]] = None,
    status_code: Optional[int] = None,
) -> str:
    user_id = user_id.strip() if user_id else DEFAULT_USER_ID
    conversation_id = conversation_id.strip() if conversation_id else DEFAULT_CONVERSATION_ID

    response_headers = response_headers or {}

    redis_ok, redis_message = redis_status()

    try:
        history_service = get_demo_history_service()
        backend_name = history_service.__class__.__name__

        history = history_service.get_history(
            conversation_id=conversation_id,
            user_id=user_id,
        )

        topic = history_service.get_topic(
            conversation_id=conversation_id,
            user_id=user_id,
        )

        weather_city = history_service.get_weather_city(
            conversation_id=conversation_id,
            user_id=user_id,
        )

        math_result = history_service.get_math_result(
            conversation_id=conversation_id,
            user_id=user_id,
        )

        company_detail = history_service.get_company_detail(
            conversation_id=conversation_id,
            user_id=user_id,
        )

    except Exception as e:
        backend_name = "Okunamadı"
        history = []
        topic = "-"
        weather_city = "-"
        math_result = "-"
        company_detail = "-"
        redis_message = f"{redis_message} | State okuma hatası: {type(e).__name__}"

    rate = get_rate_limit_snapshot(user_id)
    concurrency = get_concurrency_snapshot()

    rate_limit = rate["count"]
    rate_limit_remaining = response_headers.get("X-RateLimit-Remaining", "-")
    llm_required = response_headers.get("X-LLM-Concurrency-Required", "-")
    worker_pid = response_headers.get("X-Worker-Pid", "-")
    request_id = response_headers.get("X-Request-Id", "-")
    response_time = response_headers.get("X-Response-Time-Ms", "-")

    rows = [
        ("Backend API", API_BASE_URL),
        ("Backend sağlık", get_backend_health()),
        ("Son HTTP status", status_code if status_code is not None else "-"),

        ("Geçmiş/state backend", backend_name),
        ("Redis durumu", redis_message),

        ("Son worker PID", worker_pid),
        ("Son request id", request_id),
        ("Son cevap süresi", f"{response_time} ms" if response_time != "-" else "-"),

        ("Son konu", topic),
        ("Son hava şehri", weather_city),
        ("Son matematik sonucu", math_result),
        ("Son şirket detayı", company_detail),
        ("History mesaj sayısı", len(history)),

        ("Rate limit", f"{rate_limit} / {RATE_LIMIT_MAX_REQUESTS}"),
        ("Rate limit kalan", rate_limit_remaining),
        ("Rate limit TTL", rate["ttl"]),

        ("LLM gerekli mi?", llm_required),
        ("Aktif LLM isteği", concurrency["active"]),
        ("LLM concurrency limit", LLM_CONCURRENCY_LIMIT_MAX_REQUESTS),
    ]
    note = ""

    if backend_name == "InMemoryHistoryService":
        note = (
            "\n\n> Not: Backend InMemory kullanıyorsa Gradio ayrı process olduğu için "
            "state bilgisi backend ile ortak görünmeyebilir. Sunum için Redis bağlantısının aktif olması daha doğru olur."
        )

    return (
        "### Teknik Durum Paneli\n\n"
        + markdown_table(rows)
        + "\n\n### Son Konuşma Geçmişi\n\n"
        + format_recent_history(history)
        + note
    )


# =========================================================
# Chatbot aksiyonları
# =========================================================

def chat_with_api(
    message: str,
    history: list,
    user_id: str,
    conversation_id: str,
):
    user_id = user_id.strip() if user_id else DEFAULT_USER_ID
    conversation_id = conversation_id.strip() if conversation_id else DEFAULT_CONVERSATION_ID

    if not message or not message.strip():
        technical_panel = build_chat_technical_panel(user_id, conversation_id)
        return "", history, technical_panel

    payload = {
        "message": message,
        "user_id": user_id,
        "conversation_id": conversation_id,
    }

    response = None

    try:
        response = requests.post(
            CHAT_API_URL,
            json=payload,
            timeout=60,
        )

        headers = read_response_headers(response)

        try:
            data = response.json()
        except Exception:
            data = {}

        if response.status_code >= 400:
            detail = data.get("detail") or response.text
            answer = f"API hata ({response.status_code}): {detail}"
        else:
            answer = data.get("answer", "Cevap alınamadı.")

    except Exception as e:
        headers = {}
        answer = f"İstek gönderilirken hata oluştu: {type(e).__name__} - {e}"

    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": answer},
    ]

    technical_panel = build_chat_technical_panel(
        user_id=user_id,
        conversation_id=conversation_id,
        response_headers=headers,
        status_code=response.status_code if response else None,
    )

    return "", history, technical_panel


def refresh_chat_status(user_id: str, conversation_id: str):
    refresh_demo_history_service()
    return build_chat_technical_panel(user_id, conversation_id)


def clear_chat_history(user_id: str, conversation_id: str):
    user_id = user_id.strip() if user_id else DEFAULT_USER_ID
    conversation_id = conversation_id.strip() if conversation_id else DEFAULT_CONVERSATION_ID

    try:
        history_service = get_demo_history_service()
        history_service.clear_history(
            conversation_id=conversation_id,
            user_id=user_id,
        )
    except Exception:
        pass

    return [], build_chat_technical_panel(user_id, conversation_id)


def reset_rate_limit(user_id: str, conversation_id: str):
    user_id = user_id.strip() if user_id else DEFAULT_USER_ID
    delete_rate_limit_key(user_id)
    return build_chat_technical_panel(user_id, conversation_id)



def run_rate_limit_test(user_id: str, conversation_id: str):
    """
    Aynı kullanıcı ile kısa sürede limitten fazla istek gönderir.
    Amaç: Redis tabanlı rate limit mekanizmasının 429 döndürdüğünü sunumda göstermek.
    """
    user_id = user_id.strip() if user_id else DEFAULT_USER_ID
    conversation_id = conversation_id.strip() if conversation_id else DEFAULT_CONVERSATION_ID

    # Test önceki sayaçlardan etkilenmesin.
    delete_rate_limit_key(user_id)

    total_requests = RATE_LIMIT_MAX_REQUESTS + 3
    results = []

    for index in range(total_requests):
        result = send_demo_chat_request(
            message=f"5+{index}",
            user_id=user_id,
            conversation_id=conversation_id,
            timeout=15,
        )
        results.append(result)

    status_counts = Counter(str(item["status_code"]) for item in results)
    success_count = sum(
        1
        for item in results
        if isinstance(item["status_code"], int) and 200 <= item["status_code"] < 300
    )
    rate_limited_count = status_counts.get("429", 0)

    last_response = results[-1] if results else {}
    last_headers = last_response.get("headers", {})

    lines = [
        "### Rate Limit Test Sonucu",
        "",
        f"- Aynı kullanıcı ile gönderilen istek sayısı: **{total_requests}**",
        f"- Başarılı istek sayısı: **{success_count}**",
        f"- 429 alan istek sayısı: **{rate_limited_count}**",
        f"- Tanımlı limit: **{RATE_LIMIT_MAX_REQUESTS} istek / {RATE_LIMIT_WINDOW_SECONDS} sn**",
        "",
        "| HTTP status | Adet |",
        "|---|---|",
    ]

    for status, count in sorted(status_counts.items()):
        lines.append(f"| `{status}` | `{count}` |")

    lines.extend(
        [
            "",
            "Bu test, aynı `user_id` için kısa sürede çok fazla istek geldiğinde backend'in "
            "`429 Too Many Requests` döndürdüğünü gösterir.",
        ]
    )

    technical_panel = build_chat_technical_panel(
        user_id=user_id,
        conversation_id=conversation_id,
        response_headers=last_headers,
        status_code=last_response.get("status_code") if last_response else None,
    )

    return "\n".join(lines), technical_panel


def run_worker_test(user_id: str, conversation_id: str):
    """
    Aynı anda birden fazla istek gönderir ve response header'lardan worker PID değerlerini toplar.
    Amaç: Backend'in --workers 2 ile çalıştığında isteklerin farklı process'lere dağılabildiğini göstermek.
    """
    base_user_id = user_id.strip() if user_id else DEFAULT_USER_ID
    base_conversation_id = conversation_id.strip() if conversation_id else DEFAULT_CONVERSATION_ID

    # Worker testi rate limit'e takılmasın diye ayrı bir demo kullanıcısı kullanıyoruz.
    worker_test_user = f"{base_user_id}_worker_test"
    worker_test_conversation = f"{base_conversation_id}_worker_test"

    delete_rate_limit_key(worker_test_user)

    total_requests = 8
    messages = [f"worker testi {index}" for index in range(total_requests)]
    results = []

    with ThreadPoolExecutor(max_workers=total_requests) as executor:
        futures = [
            executor.submit(
                send_demo_chat_request,
                message,
                worker_test_user,
                worker_test_conversation,
                40,
            )
            for message in messages
        ]

        for future in as_completed(futures):
            results.append(future.result())

    worker_pids = [
        item.get("headers", {}).get("X-Worker-Pid", "-")
        for item in results
        if item.get("headers", {}).get("X-Worker-Pid", "-") != "-"
    ]

    pid_counts = Counter(worker_pids)
    status_counts = Counter(str(item["status_code"]) for item in results)

    last_response = results[-1] if results else {}
    last_headers = last_response.get("headers", {})

    lines = [
        "### Çok Worker Test Sonucu",
        "",
        f"- Eş zamanlı gönderilen istek sayısı: **{total_requests}**",
        f"- Görülen farklı worker PID sayısı: **{len(pid_counts)}**",
        "",
        "| Worker PID | İstek sayısı |",
        "|---|---|",
    ]

    if pid_counts:
        for pid, count in pid_counts.items():
            lines.append(f"| `{pid}` | `{count}` |")
    else:
        lines.append("| `PID okunamadı` | `0` |")

    lines.extend(
        [
            "",
            "| HTTP status | Adet |",
            "|---|---|",
        ]
    )

    for status, count in sorted(status_counts.items()):
        lines.append(f"| `{status}` | `{count}` |")

    lines.extend(
        [
            "",
            "Bu test, backend `uvicorn main:app --host 127.0.0.1 --port 8001 --workers 2` "
            "komutu ile çalışırken isteklerin hangi worker process'leri tarafından karşılandığını gösterir.",
        ]
    )

    if len(pid_counts) < 2:
        lines.append(
            "\n> Not: Burada tek PID görünürse backend gerçekten `--workers 2` ile açık mı kontrol edilmeli. "
            "Bazen çok hızlı lokal isteklerde işletim sistemi istekleri tek worker'a da verebilir; testi tekrar çalıştırmak yeterli olabilir."
        )

    technical_panel = build_chat_technical_panel(
        user_id=base_user_id,
        conversation_id=base_conversation_id,
        response_headers=last_headers,
        status_code=last_response.get("status_code") if last_response else None,
    )

    return "\n".join(lines), technical_panel


# =========================================================
# RAG yardımcıları
# =========================================================

def get_demo_rag_service():
    global _rag_service

    if _rag_service is None:
        from app.services.rag.rag_service import RagService
        _rag_service = RagService()

    return _rag_service


def get_file_path(file_obj) -> Optional[str]:
    if file_obj is None:
        return None

    if isinstance(file_obj, str):
        return file_obj

    if hasattr(file_obj, "name"):
        return file_obj.name

    return None


def build_rag_technical_panel(
    user_id: str,
    document_id: str,
    last_chunk_count: Optional[int] = None,
    last_saved_count: Optional[int] = None,
    last_retrieved_count: Optional[int] = None,
) -> str:
    rows = [
        ("Qdrant URL", QDRANT_URL),
        ("Qdrant collection", QDRANT_COLLECTION_NAME),
        ("Embedding modeli", RAG_EMBEDDING_MODEL),
        ("RAG LLM modeli", RAG_LLM_MODEL),
        ("Top-K", RAG_TOP_K),
        ("RAG user_id", user_id),
        ("document_id", document_id),
        ("Son chunk sayısı", last_chunk_count if last_chunk_count is not None else "-"),
        ("Son kaydedilen chunk", last_saved_count if last_saved_count is not None else "-"),
        ("Son retrieved count", last_retrieved_count if last_retrieved_count is not None else "-"),
    ]

    try:
        rag_service = get_demo_rag_service()
        collection_exists = rag_service.qdrant_service.collection_exists()
        rows.append(("Qdrant collection var mı", collection_exists))

        if user_id and document_id:
            count = rag_service.qdrant_service.count_document_chunks(
                user_id=user_id,
                document_id=document_id,
            )
            rows.append(("Bu dokümana ait Qdrant chunk sayısı", count))

    except Exception as e:
        rows.append(("Qdrant/RAG durumu", f"Okunamadı: {type(e).__name__} - {e}"))

    return "### RAG Teknik Durum Paneli\n\n" + markdown_table(rows)


def format_sources(sources: list[dict]) -> str:
    if not sources:
        return "Kaynak gösterilecek sonuç yok."

    lines = [
        "| No | Dosya | Chunk | Document ID | Skor |",
        "|---|---|---|---|---|",
    ]

    for source in sources:
        score = source.get("score")

        if isinstance(score, float):
            score_text = f"{score:.4f}"
        else:
            score_text = safe_value(score)

        lines.append(
            "| "
            f"{safe_value(source.get('source_no'))} | "
            f"{safe_value(source.get('file_name'))} | "
            f"{safe_value(source.get('chunk_index'))} | "
            f"{safe_value(source.get('document_id'))} | "
            f"{score_text} |"
        )

    return "\n".join(lines)


# =========================================================
# RAG aksiyonları
# =========================================================

def ingest_document(file_obj, user_id: str, document_id: str):
    user_id = user_id.strip() if user_id else DEFAULT_RAG_USER_ID
    document_id = document_id.strip() if document_id else DEFAULT_DOCUMENT_ID

    file_path = get_file_path(file_obj)

    if not file_path:
        return (
            "Dosya seçilmedi.",
            "",
            build_rag_technical_panel(user_id, document_id),
        )

    try:
        from app.services.rag.file_reader import read_document
        from app.services.rag.chunker import build_chunk_metadata, split_text_into_chunks

        rag_service = get_demo_rag_service()

        text = read_document(file_path)
        chunks = split_text_into_chunks(text)

        if not chunks:
            return (
                "Dokümandan işlenebilir metin çıkarılamadı.",
                "",
                build_rag_technical_panel(user_id, document_id),
            )

        file_name = Path(file_path).name

        metadatas = [
            build_chunk_metadata(
                file_name=file_name,
                chunk_index=index,
                user_id=user_id,
                document_id=document_id,
            )
            for index, _ in enumerate(chunks)
        ]

        embeddings = rag_service.embedding_service.embed_documents(chunks)

        saved_count = rag_service.qdrant_service.upsert_document_chunks(
            chunks=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            user_id=user_id,
            document_id=document_id,
            delete_existing=True,
        )

        preview_text = text.strip().replace("\n", " ")

        if len(preview_text) > 900:
            preview_text = preview_text[:900] + "..."

        status = (
            f"Doküman işlendi ve Qdrant'a kaydedildi.\n\n"
            f"- Dosya: {file_name}\n"
            f"- Chunk sayısı: {len(chunks)}\n"
            f"- Kaydedilen chunk: {saved_count}\n"
            f"- user_id: {user_id}\n"
            f"- document_id: {document_id}"
        )

        technical_panel = build_rag_technical_panel(
            user_id=user_id,
            document_id=document_id,
            last_chunk_count=len(chunks),
            last_saved_count=saved_count,
        )

        return status, preview_text, technical_panel

    except Exception as e:
        status = f"Doküman işlenirken hata oluştu: {type(e).__name__} - {e}"
        return status, "", build_rag_technical_panel(user_id, document_id)


def answer_rag_question(question: str, user_id: str, document_id: str):
    user_id = user_id.strip() if user_id else DEFAULT_RAG_USER_ID
    document_id = document_id.strip() if document_id else DEFAULT_DOCUMENT_ID

    if not question or not question.strip():
        return (
            "Lütfen dokümanla ilgili bir soru yaz.",
            "Kaynak yok.",
            build_rag_technical_panel(user_id, document_id),
        )

    try:
        rag_service = get_demo_rag_service()

        result = rag_service.answer_question(
            question=question,
            user_id=user_id,
            document_id=document_id,
            top_k=RAG_TOP_K,
        )

        answer = result.get("answer", "Cevap üretilemedi.")
        sources = result.get("sources", [])
        retrieved_count = result.get("retrieved_count", 0)

        technical_panel = build_rag_technical_panel(
            user_id=user_id,
            document_id=document_id,
            last_retrieved_count=retrieved_count,
        )

        return answer, format_sources(sources), technical_panel

    except Exception as e:
        return (
            f"RAG cevabı üretilirken hata oluştu: {type(e).__name__} - {e}",
            "Kaynak yok.",
            build_rag_technical_panel(user_id, document_id),
        )


def refresh_rag_status(user_id: str, document_id: str):
    user_id = user_id.strip() if user_id else DEFAULT_RAG_USER_ID
    document_id = document_id.strip() if document_id else DEFAULT_DOCUMENT_ID
    return build_rag_technical_panel(user_id, document_id)


# =========================================================
# Arayüz
# =========================================================

CUSTOM_CSS = """
.gradio-container {
    max-width: 1500px !important;
    margin: auto !important;
}

body {
    background: #f7f8fb !important;
}

.header-box {
    padding: 18px 22px;
    border-radius: 18px;
    background: linear-gradient(135deg, #eef4ff 0%, #ffffff 70%);
    border: 1px solid #dbe6ff;
    margin-bottom: 14px;
}

.header-box h1 {
    margin: 0;
    font-size: 30px;
    color: #0f172a !important;
    font-weight: 800 !important;
}

.header-box p {
    margin-top: 8px;
    color: #334155 !important;
    font-size: 15px;
    line-height: 1.6;
}

.header-box * {
    color: #0f172a !important;
}

.panel-note {
    padding: 10px 14px;
    border-radius: 12px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    font-size: 14px;
}

textarea {
    font-size: 15px !important;
}

button {
    border-radius: 12px !important;
}
"""


with gr.Blocks(
    title="HexaOps Demo Paneli",
    theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate"),
    css=CUSTOM_CSS,
) as demo:
    gr.HTML(
        """
        <div class="header-box">
            <h1>HexaOps Demo Paneli</h1>
            <p>
                Normal chatbot, Redis history/state, rate limit, worker header bilgileri ve
                RAG doküman asistanını tek sunum ekranında göstermek için hazırlanmıştır.
            </p>
        </div>
        """
    )

    with gr.Tabs():
        # -------------------------------------------------
        # Chatbot tab
        # -------------------------------------------------
        with gr.Tab("1. Sohbet Botu + Redis / Rate Limit Paneli"):
            with gr.Row():
                with gr.Column(scale=2):
                    gr.Markdown(
                        """
                        ### HexaOps Sohbet Botu

                        Bu ekranda hava durumu, matematik, mesai bilgisi ve follow-up senaryoları test edilir.
                        Sağdaki panelde Redis/InMemory durumu, rate limit, worker PID, request id ve konuşma state bilgileri görünür.
                        """
                    )

                    with gr.Row():
                        chat_user_id = gr.Textbox(
                            label="user_id",
                            value=DEFAULT_USER_ID,
                            lines=1,
                        )
                        chat_conversation_id = gr.Textbox(
                            label="conversation_id",
                            value=DEFAULT_CONVERSATION_ID,
                            lines=1,
                        )

                    chatbot = gr.Chatbot(
                        label="Sohbet",
                        height=540,
                    )

                    message_box = gr.Textbox(
                        label="Mesaj",
                        placeholder="Örnek: rize de hava nasıl / yarın nasıl / 5+3 / sonuca 2 ekle / mesai saatleri kaç",
                        lines=1,
                    )

                    with gr.Row():
                        send_button = gr.Button("Gönder", variant="primary")
                        clear_button = gr.Button("Konuşmayı Temizle")
                        refresh_button = gr.Button("Teknik Durumu Yenile")
                        reset_rate_button = gr.Button("Rate Limit Sıfırla")

                    with gr.Row():
                        worker_test_button = gr.Button("Çok Worker Testi")
                        rate_limit_test_button = gr.Button("Rate Limit Testi", variant="secondary")

                    test_result_panel = gr.Markdown(
                        value=(
                            "### Demo Test Sonuçları\n\n"
                            "Rate limit veya çok worker testi çalıştırıldığında sonuçlar burada görünecek."
                        )
                    )

                    gr.Examples(
                        examples=[
                            "rize de hava nasıl",
                            "yarın nasıl",
                            "5+3",
                            "sonuca 2 ekle",
                            "mesai saatleri kaç",
                            "09.30'da gelirsem ne olur",
                            "bana kendini tanıt",
                        ],
                        inputs=message_box,
                    )

                with gr.Column(scale=1):
                    chat_technical_panel = gr.Markdown(
                        value=build_chat_technical_panel(
                            DEFAULT_USER_ID,
                            DEFAULT_CONVERSATION_ID,
                        )
                    )

            send_button.click(
                fn=chat_with_api,
                inputs=[message_box, chatbot, chat_user_id, chat_conversation_id],
                outputs=[message_box, chatbot, chat_technical_panel],
            )

            message_box.submit(
                fn=chat_with_api,
                inputs=[message_box, chatbot, chat_user_id, chat_conversation_id],
                outputs=[message_box, chatbot, chat_technical_panel],
            )

            clear_button.click(
                fn=clear_chat_history,
                inputs=[chat_user_id, chat_conversation_id],
                outputs=[chatbot, chat_technical_panel],
            )

            refresh_button.click(
                fn=refresh_chat_status,
                inputs=[chat_user_id, chat_conversation_id],
                outputs=chat_technical_panel,
            )

            reset_rate_button.click(
                fn=reset_rate_limit,
                inputs=[chat_user_id, chat_conversation_id],
                outputs=chat_technical_panel,
            )

            rate_limit_test_button.click(
                fn=run_rate_limit_test,
                inputs=[chat_user_id, chat_conversation_id],
                outputs=[test_result_panel, chat_technical_panel],
            )

            worker_test_button.click(
                fn=run_worker_test,
                inputs=[chat_user_id, chat_conversation_id],
                outputs=[test_result_panel, chat_technical_panel],
            )

        # -------------------------------------------------
        # RAG tab
        # -------------------------------------------------
        with gr.Tab("2. RAG Doküman Asistanı + Qdrant Paneli"):
            with gr.Row():
                with gr.Column(scale=2):
                    gr.Markdown(
                        """
                        ### HexaOps RAG Doküman Asistanı

                        Bu ekranda PDF, DOCX veya TXT dokümanı yüklenir; metin çıkarılır,
                        chunk'lara bölünür, embedding üretilir, Qdrant'a kaydedilir ve dokümana göre cevap üretilir.
                        """
                    )

                    with gr.Row():
                        rag_user_id = gr.Textbox(
                            label="RAG user_id",
                            value=DEFAULT_RAG_USER_ID,
                            lines=1,
                        )
                        rag_document_id = gr.Textbox(
                            label="document_id",
                            value=DEFAULT_DOCUMENT_ID,
                            lines=1,
                        )

                    file_input = gr.File(
                        label="Doküman yükle",
                        file_types=[".pdf", ".docx", ".txt"],
                        type="filepath",
                    )

                    with gr.Row():
                        ingest_button = gr.Button("Dokümanı İşle ve Qdrant'a Kaydet", variant="primary")
                        rag_refresh_button = gr.Button("RAG Durumunu Yenile")

                    ingest_status = gr.Markdown(label="İşlem Durumu")

                    document_preview = gr.Textbox(
                        label="Dokümandan çıkarılan metin önizlemesi",
                        lines=8,
                        interactive=False,
                    )

                    rag_question = gr.Textbox(
                        label="Dokümana soru sor",
                        placeholder="Örnek: RAG sistemi dokümanları nasıl işler?",
                        lines=1,
                    )

                    ask_rag_button = gr.Button("Dokümana Göre Cevapla", variant="primary")

                    rag_answer = gr.Textbox(
                        label="Cevap",
                        lines=8,
                        interactive=False,
                    )

                    rag_sources = gr.Markdown(
                        label="Kaynaklar",
                        value="Kaynak yok.",
                    )

                    gr.Examples(
                        examples=[
                            "RAG sistemi dokümanları nasıl işler?",
                            "Bu dokümanda hangi bileşenler anlatılıyor?",
                            "Dokümanda chunking neden önemli?",
                            "Qdrant neden kullanılıyor?",
                        ],
                        inputs=rag_question,
                    )

                with gr.Column(scale=1):
                    rag_technical_panel = gr.Markdown(
                        value=build_rag_technical_panel(
                            DEFAULT_RAG_USER_ID,
                            DEFAULT_DOCUMENT_ID,
                        )
                    )

            ingest_button.click(
                fn=ingest_document,
                inputs=[file_input, rag_user_id, rag_document_id],
                outputs=[ingest_status, document_preview, rag_technical_panel],
            )

            ask_rag_button.click(
                fn=answer_rag_question,
                inputs=[rag_question, rag_user_id, rag_document_id],
                outputs=[rag_answer, rag_sources, rag_technical_panel],
            )

            rag_question.submit(
                fn=answer_rag_question,
                inputs=[rag_question, rag_user_id, rag_document_id],
                outputs=[rag_answer, rag_sources, rag_technical_panel],
            )

            rag_refresh_button.click(
                fn=refresh_rag_status,
                inputs=[rag_user_id, rag_document_id],
                outputs=rag_technical_panel,
            )


if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=7865,
        share=False,
    )