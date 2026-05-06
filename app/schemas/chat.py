from typing import Optional

from pydantic import BaseModel

class ChatRequest(BaseModel): # bu /api/chat endpointine gelen isteğin yapısını temsil ediyor 
    message: str   # kullanıcıdan gelen asıl mesaj metni
   
    # mesajı gönderen kullanıcıyı ayırt etmek için 
    user_id: Optional[str] = None  # bu alanın gelmesi zorunlu tutulmadı şuanki sistem için 
    # mesajın hangi konuşma akışına ait olduğunu anlamak için 
    conversation_id: Optional[str] = None


# bu sınıf backendin frontende döndüğü cevabu temsil ediyor 
class ChatResponse(BaseModel):
    answer: str    