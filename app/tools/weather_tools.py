from app.services.weather_service import get_current_weather

def weather_tool(city: str)-> str:
    return get_current_weather(city)

