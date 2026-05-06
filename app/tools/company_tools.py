# agent doğrudan service’e gitmek yerine tool üzerinden çağırabilir.

from app.services.company_info_service import get_company_info

def company_info_tool(topic: str) -> str:
    return get_company_info(topic)