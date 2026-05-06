# llm in döneceği cevabı temsil edecek bir schema yazıyoruz

from typing import Optional

from pydantic import BaseModel

from app.schemas.tools import ToolCall


# llm den dönen cevabı temsil edecek schema
class LLMResponse(BaseModel):
    content: Optional[str] = None # normal mesaj için 
    tool_call: Optional[ToolCall] = None # toollar için 