from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    """
    API'nin sağlık durumunu kontrol eder.
    """
    return {
        "status": "ok",
        "message": "API sağlıklı ve çalışıyor."
    }