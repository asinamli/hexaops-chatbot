import requests


def get_coordinates(city: str):
    url = "https://geocoding-api.open-meteo.com/v1/search"

    params = {
        "name": city,
        "count": 1,
        "language": "tr",
        "format": "json"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException:
        return None
    except ValueError:
        return None

    results = data.get("results")

    if not results:
        return None

    first_result = results[0]

    return {
        "name": first_result["name"],
        "latitude": first_result["latitude"],
        "longitude": first_result["longitude"],
    }


def get_weather_data(city: str):
    location = get_coordinates(city)

    if not location:
        return None, f"{city} için konum bulunamadı."

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "current": "temperature_2m,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,wind_speed_10m_max",
        "timezone": "auto",
        "forecast_days": 7
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException:
        return None, "Hava durumu servisine şu an ulaşılamadı."
    except ValueError:
        return None, "Hava durumu servisinden geçerli veri alınamadı."

    return {
        "location": location,
        "data": data
    }, None


def get_current_weather(city: str) -> str:
    weather_result, error = get_weather_data(city)

    if error:
        return error

    location = weather_result["location"]
    data = weather_result["data"]

    current = data.get("current")

    if not current:
        return f"{city} için güncel hava durumu bulunamadı."

    temperature = current.get("temperature_2m")
    windspeed = current.get("wind_speed_10m")

    return f"{location['name']} için güncel hava durumu: Sıcaklık {temperature}°C, Rüzgar Hızı {windspeed} km/s"


def get_tomorrow_weather(city: str) -> str:
    weather_result, error = get_weather_data(city)

    if error:
        return error

    location = weather_result["location"]
    data = weather_result["data"]

    daily = data.get("daily")

    if not daily:
        return f"{city} için günlük hava tahmini bulunamadı."

    times = daily.get("time", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    max_winds = daily.get("wind_speed_10m_max", [])

    if len(times) < 2 or len(max_temps) < 2 or len(min_temps) < 2 or len(max_winds) < 2:
        return f"{city} için yarın hava tahmini bulunamadı."

    tomorrow_date = times[1]
    tomorrow_max = max_temps[1]
    tomorrow_min = min_temps[1]
    tomorrow_wind = max_winds[1]

    return (
        f"{location['name']} için yarın ({tomorrow_date}) hava tahmini: "
        f"En düşük {tomorrow_min}°C, en yüksek {tomorrow_max}°C, "
        f"maksimum rüzgar hızı {tomorrow_wind} km/s"
    )


def get_weekly_weather(city: str) -> str:
    weather_result, error = get_weather_data(city)

    if error:
        return error

    location = weather_result["location"]
    data = weather_result["data"]

    daily = data.get("daily")

    if not daily:
        return f"{city} için haftalık hava tahmini bulunamadı."

    times = daily.get("time", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    max_winds = daily.get("wind_speed_10m_max", [])

    if not times or not max_temps or not min_temps or not max_winds:
        return f"{city} için haftalık hava tahmini bulunamadı."

    lines = [f"{location['name']} için 7 günlük hava tahmini:"]

    day_count = min(len(times), len(max_temps), len(min_temps), len(max_winds))

    for i in range(day_count):
        lines.append(
            f"{times[i]} -> En düşük {min_temps[i]}°C, "
            f"en yüksek {max_temps[i]}°C, "
            f"maksimum rüzgar {max_winds[i]} km/s"
        )

    return "\n".join(lines)