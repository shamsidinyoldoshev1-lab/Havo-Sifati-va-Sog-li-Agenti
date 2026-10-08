"""
Ob-havo ma'lumotlarini olish xizmati (Open-Meteo Weather API).
Shamol, namlik, harorat va atmosfera inversiyasi/shamollanish tahlili.
"""
import httpx
from datetime import datetime
from typing import Dict, Any, Optional

WMO_WEATHER_CODES = {
    0: {"uz": "Ochiq havo", "ru": "Ясно"},
    1: {"uz": "Asosan ochiq", "ru": "В основном ясно"},
    2: {"uz": "Qisman bulutli", "ru": "Переменная облачность"},
    3: {"uz": "Bulutli", "ru": "Пасмурно"},
    45: {"uz": "Tuman", "ru": "Туман"},
    48: {"uz": "Qirovli tuman", "ru": "Туман с инеем"},
    51: {"uz": "Yengil mayda yomg'ir", "ru": "Легкая морось"},
    53: {"uz": "O'rtacha mayda yomg'ir", "ru": "Умеренная морось"},
    55: {"uz": "Qalin mayda yomg'ir", "ru": "Плотная морось"},
    61: {"uz": "Yengil yomg'ir", "ru": "Небольшой дождь"},
    63: {"uz": "O'rtacha yomg'ir", "ru": "Умеренный дождь"},
    65: {"uz": "Kuchli yomg'ir", "ru": "Сильный дождь"},
    71: {"uz": "Yengil qor", "ru": "Небольшой снег"},
    73: {"uz": "O'rtacha qor", "ru": "Умеренный снег"},
    75: {"uz": "Kuchli qor", "ru": "Сильный снегопад"},
    80: {"uz": "Yomg'ir jalasi", "ru": "Ливневый дождь"},
    95: {"uz": "Momaqaldiroq", "ru": "Гроза"},
}


def get_weather(lat: float, lon: float) -> Dict[str, Any]:
    """
    Open-Meteo dan joriy ob-havo ma'lumotlarini oladi (Tool talabi).
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m"
        f"&timezone=auto"
    )

    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                current = data.get("current", {})
                w_code = current.get("weather_code", 0)
                code_info = WMO_WEATHER_CODES.get(w_code, {"uz": "Noma'lum", "ru": "Неизвестно"})

                wind_kmh = current.get("wind_speed_10m", 0.0)
                wind_ms = round(wind_kmh / 3.6, 1)
                humidity = current.get("relative_humidity_2m", 0)
                temp = current.get("temperature_2m", 0.0)
                app_temp = current.get("apparent_temperature", temp)
                precip = current.get("precipitation", 0.0)

                # Tutun va smog tarqalishi tahlili
                if wind_ms < 1.5 and humidity > 65:
                    dispersion = {
                        "uz": "Og'ir (Inversiya xavfi yuqori, shamol deyarli yo'q, tutun to'planadi)",
                        "ru": "Тяжелая (Высокий риск температурной инверсии, штиль, смог застаивается)",
                    }
                elif wind_ms >= 4.0 or precip > 0.5:
                    dispersion = {
                        "uz": "Yaxshi (Shamol/yog'in havoni tozalamoqda)",
                        "ru": "Хорошая (Ветер или осадки способствуют рассеиванию смога)",
                    }
                else:
                    dispersion = {
                        "uz": "O'rtacha (Barqaror havo oqimi)",
                        "ru": "Умеренная (Обычное рассеивание)",
                    }

                return {
                    "temperature": temp,
                    "apparent_temperature": app_temp,
                    "humidity": humidity,
                    "wind_speed_ms": wind_ms,
                    "wind_speed_kmh": wind_kmh,
                    "wind_direction": current.get("wind_direction_10m", 0),
                    "precipitation": precip,
                    "weather_description": code_info,
                    "dispersion_condition": dispersion,
                    "timestamp": current.get("time", datetime.now().strftime("%Y-%m-%d %H:%M")),
                    "source": "Open-Meteo Weather API",
                }
    except Exception:
        pass

    # Zaxira (oflayn)
    return {
        "temperature": 22.0,
        "apparent_temperature": 22.0,
        "humidity": 45,
        "wind_speed_ms": 2.5,
        "wind_speed_kmh": 9.0,
        "wind_direction": 180,
        "precipitation": 0.0,
        "weather_description": {"uz": "Ochiq havo", "ru": "Ясно"},
        "dispersion_condition": {"uz": "O'rtacha", "ru": "Умеренная"},
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "Open-Meteo Weather API (Oflayn zaxira)",
    }
