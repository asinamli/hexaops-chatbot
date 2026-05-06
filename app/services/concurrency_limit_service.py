from app.core.config import (
    LLM_CONCURRENCY_LIMIT_MAX_REQUESTS,
    LLM_CONCURRENCY_LOCK_TTL_SECONDS,
)


class ConcurrencyLimitService:
    """
    Redis tabanlı global LLM concurrency limit servisi.

    Bu servis tüm endpointi değil sadece LLM gerektiren
    ağır istekleri sınırlandırmak için kullanılacak.
    """

    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.key = "concurrency:llm:active"
        self.max_requests = LLM_CONCURRENCY_LIMIT_MAX_REQUESTS
        self.ttl_seconds = LLM_CONCURRENCY_LOCK_TTL_SECONDS

    def acquire(self) -> tuple[bool, int, int]:
        """
        LLM isteği için aktif slot almaya çalışır.

        return:
        - allowed: slot alınabildi mi?
        - current: aktif LLM isteği sayısı
        - remaining: kalan slot sayısı
        """

        try:
            current = self.redis_client.incr(self.key)
            self.redis_client.expire(self.key, self.ttl_seconds)

            if current > self.max_requests:
                self.redis_client.decr(self.key)
                return False, self.max_requests, 0

            remaining = max(self.max_requests - current, 0)
            return True, current, remaining

        except Exception as e:
            print(f"LLM concurrency limit hatası: {type(e).__name__} - {e}")

            # Redis tarafında geçici sorun olursa sistemi tamamen kilitlememek için
            # isteğe izin veriyoruz.
            return True, 0, self.max_requests

    def release(self) -> int:
        """
        LLM isteği tamamlandığında aktif slotu geri bırakır.
        """

        try:
            current = self.redis_client.decr(self.key)

            if current <= 0:
                self.redis_client.delete(self.key)
                return 0

            return current

        except Exception as e:
            print(f"LLM concurrency release hatası: {type(e).__name__} - {e}")
            return 0