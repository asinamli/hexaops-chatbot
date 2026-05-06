# toollar sadece python fonksiyonuydular şimdi function-calling mantığına geçtiğimz için artık onları ortak bir veri yapısı ile temsil etmemiz gerekiyor 


from typing import Any, Dict

from pydantic import BaseModel

class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]


class ToolResult(BaseModel):
    name: str
    output: str