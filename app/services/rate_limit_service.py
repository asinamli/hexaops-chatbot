# rate limit mantığı
"""
production ortamında slowapi gibi hazır rate limit kütüphaneleri de değerlendirilebilir 
bu sürümde mnatığı daha iyi anlamak için custom service yazdım

"""

from typing import Optional

from app.core.config import RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS

class RateLimitService:
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.max_requests = RATE_LIMIT_MAX_REQUESTS
        self.window_seconds = RATE_LIMIT_WINDOW_SECONDS


    def _build_rate_limit_key(  # kullanıcıya özel bir rate limit key üretioruz
        self,
        user_id: Optional[str] = None,
        client_ip: Optional[str] = None # istemci bilgisi
    ) -> str:
        if user_id:
            return f"rate_limit:user:{user_id}" # önce user_id ye göre yapıyoruz 
            
        if client_ip:
            return f"rate_limit:ip:{client_ip}" # eğer user_id yoksa client_ip ye göre yapıyoruz
            
        return "rate_limit:anonymous"
        

    def check_rate_limit(
        self,
        user_id: Optional[str] = None,
        client_ip: Optional[str] = None
    ) -> tuple[bool, int, int]: # bool izin var mı int mevcut istek sayısıı ,int kalan hak
        key = self._build_rate_limit_key(user_id=user_id, client_ip=client_ip)

        current_count = self.redis_client.get(key) # rediste bu kullancı için sayaç var mı bakıyoruz 

        if current_count is None:
            self.redis_client.set(key, 1, ex=self.window_seconds) # yoksa sayaç başlatıoruz ve ttl veriyoruz 60 sn sonra sınfılanacak şekilde config 
            remaining = self.max_requests - 1
            return True, 1, remaining
        
        current_count = int(current_count) # sayaç varsa onu sayıya çevirioruz

        if current_count >= self.max_requests: # limit dolmuş mu 
            remaining = 0
            return False, current_count, remaining
        
        new_count = self.redis_client.incr(key) #dolmamışsa sayaç 1 artıyor
        remaining = max(self.max_requests - new_count, 0)

        return True, new_count, remaining
    

    def get_retry_after(
            self,
            user_id: Optional[str] = None,
            client_ip: Optional[str] = None
    ) -> int:
        key = self._build_rate_limit_key(user_id=user_id, client_ip=client_ip)
        ttl = self.redis_client.ttl(key) # rediste o keyin kalan ömrünü okuyoruz

        if ttl is None or ttl < 0:
            return self.window_seconds
        
        return ttl