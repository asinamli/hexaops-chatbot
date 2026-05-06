# ollamanın local adresi
OLLAMA_BASE_URL = "http://localhost:11434"

# kullanacağım model
OLLAMA_MODEL = "llama3.2"

# redis url 
REDIS_URL = "redis://localhost:6379/0"

#rate limiting
RATE_LIMIT_MAX_REQUESTS = 10  # 1 dakikada en fazla 10 istek
RATE_LIMIT_WINDOW_SECONDS = 60  #pencere süresi 60 saniye


# concurrency / backpressure
LLM_CONCURRENCY_LIMIT_MAX_REQUESTS = 4
LLM_CONCURRENCY_LOCK_TTL_SECONDS = 120
LLM_CONCURRENCY_RETRY_AFTER_SECONDS = 5

# ollama timeout
OLLAMA_REQUEST_TIMEOUT_SECONDS = 45