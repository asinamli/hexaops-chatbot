#middleware ve route dosyalarını içe aktarıyoruz
import os
import time
import uuid

from fastapi import Request


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# route dosyalarındaki routerları alıyoruz
from app.api.routes.health import router as health_router
from app.api.routes.chat import router as chat_router

# FastAPI uygulamasını oluşturuyoruz ve route dosyalarını ekliyoruz
app = FastAPI(
    title = "HexaOps Chatbot API",
    description = "Function calling tabanlı bir chatbot API'si",
    version = "0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
    "X-RateLimit-Limit",
    "X-RateLimit-Remaining",
    "Retry-After",
    "X-Worker-Pid",
    "X-Request-Id",
    "X-Response-Time-Ms",
    "X-LLM-Concurrency-Required",
    "X-LLM-Concurrency-Limit",
    "X-LLM-Concurrency-Current",
    "X-LLM-Concurrency-Remaining"
]
)

#bunu çoklu istek testi için yapıyrouz
# artık her istek için hangi workerin cevap evrdiğğini ne kadar sürdüğün ve request id sini görebilicez
@app.middleware("http")
async def log_request_timing(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    worker_pid = os.getpid()
    start_time = time.time()

    response = await call_next(request)

    duration_ms = round((time.time() - start_time) * 1000, 2)

    print(
        f"[request_id={request_id}] "
        f"[worker_pid={worker_pid}] "
        f"{request.method} {request.url.path} "
        f"status={response.status_code} "
        f"duration_ms={duration_ms}"
    )

    response.headers["X-Request-Id"] = request_id
    response.headers["X-Worker-Pid"] = str(worker_pid)
    response.headers["X-Response-Time-Ms"] = str(duration_ms)

    return response

# health ve chat route'larını ekliyoruz
app.include_router(health_router, prefix = "/api",tags = ["Health"])
app.include_router(chat_router, prefix = "/api",tags = ["Chat"])

# ANA SAYFA 
@app.get("/")
def home():
    return {
        "message": "HexaOps Chatbot API çalışıyor.",
        "docs": "/docs",
        "health": "/api/health",
    }