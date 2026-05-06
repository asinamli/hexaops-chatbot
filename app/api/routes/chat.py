# Endpoint
# AGENT_SERVİCE İLE KONUŞABİLİR DURUMDA 
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.config import (
    RATE_LIMIT_MAX_REQUESTS,
    LLM_CONCURRENCY_LIMIT_MAX_REQUESTS,
    LLM_CONCURRENCY_RETRY_AFTER_SECONDS,
)
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.agent_service import process_message, requires_llm_processing
from app.services.rate_limit_service_factory import get_rate_limit_service
from app.services.concurrency_limit_service_factory import get_concurrency_limit_service


router = APIRouter()
rate_limit_service = get_rate_limit_service()
concurrency_limit_service = get_concurrency_limit_service()


def build_common_headers(
    rate_remaining: int,
    llm_required: bool,
    llm_current: int = 0,
    llm_remaining: int | None = None
) -> dict:
    """
    Ortak response header'larını tek yerden üretmek için kullanılır.
    """

    if llm_remaining is None:
        llm_remaining = LLM_CONCURRENCY_LIMIT_MAX_REQUESTS

    return {
        "X-RateLimit-Limit": str(RATE_LIMIT_MAX_REQUESTS),
        "X-RateLimit-Remaining": str(rate_remaining),
        "X-LLM-Concurrency-Required": str(llm_required).lower(),
        "X-LLM-Concurrency-Limit": str(LLM_CONCURRENCY_LIMIT_MAX_REQUESTS),
        "X-LLM-Concurrency-Current": str(llm_current),
        "X-LLM-Concurrency-Remaining": str(llm_remaining),
        "X-Worker-Pid": str(os.getpid())
    }


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: Request, data: ChatRequest):
    """
    Kullanıcının mesajını alır ve chatbot cevabını döner.
    """

    client_ip = request.client.host if request.client else None

    is_allowed, current_count, rate_remaining = rate_limit_service.check_rate_limit(
        user_id=data.user_id,
        client_ip=client_ip
    )

    if not is_allowed:
        retry_after = rate_limit_service.get_retry_after(
            user_id=data.user_id,
            client_ip=client_ip
        )

        raise HTTPException(
            status_code=429,
            detail=f"Çok fazla istek gönderdin. Lütfen {retry_after} saniye sonra tekrar dene.",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(RATE_LIMIT_MAX_REQUESTS),
                "X-RateLimit-Remaining": "0",
                "X-Worker-Pid": str(os.getpid())
            }
        )

    llm_required = requires_llm_processing(
        message=data.message,
        user_id=data.user_id,
        conversation_id=data.conversation_id
    )

    # Mesaj LLM gerektirmiyorsa concurrency limit uygulanmadan cevaplanır.
    if not llm_required:
        answer = process_message(
            message=data.message,
            user_id=data.user_id,
            conversation_id=data.conversation_id
        )

        return JSONResponse(
            content={"answer": answer},
            headers=build_common_headers(
                rate_remaining=rate_remaining,
                llm_required=False
            )
        )

    llm_allowed, llm_current, llm_remaining = concurrency_limit_service.acquire()

    if not llm_allowed:
        raise HTTPException(
            status_code=503,
            detail="Yanıt üretme servisi şu anda yoğun. Lütfen kısa süre sonra tekrar dene.",
            headers={
                "Retry-After": str(LLM_CONCURRENCY_RETRY_AFTER_SECONDS),
                "X-RateLimit-Limit": str(RATE_LIMIT_MAX_REQUESTS),
                "X-RateLimit-Remaining": str(rate_remaining),
                "X-LLM-Concurrency-Required": "true",
                "X-LLM-Concurrency-Limit": str(LLM_CONCURRENCY_LIMIT_MAX_REQUESTS),
                "X-LLM-Concurrency-Current": str(llm_current),
                "X-LLM-Concurrency-Remaining": "0",
                "X-Worker-Pid": str(os.getpid())
            }
        )

    try:
        answer = process_message(
            message=data.message,
            user_id=data.user_id,
            conversation_id=data.conversation_id
        )

        return JSONResponse(
            content={"answer": answer},
            headers=build_common_headers(
                rate_remaining=rate_remaining,
                llm_required=True,
                llm_current=llm_current,
                llm_remaining=llm_remaining
            )
        )

    finally:
        concurrency_limit_service.release()
    
"""
APIRouter, ilgili endpoint’leri gruplayıp modüler bir yapı kurmamızı sağlar. Böylece route’lar ayrı dosyalarda tutulur ve ana uygulamaya main.py üzerinden eklenir.
"""

"""
LLM gerekmiyorsa:
    process_message direkt çalışır

LLM gerekiyorsa:
    önce Redis üzerinden slot alınır
    slot varsa process_message çalışır
    işlem bitince finally ile slot bırakılır
    slot yoksa 503 döner
"""