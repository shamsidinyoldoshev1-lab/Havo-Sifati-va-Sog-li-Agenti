"""
TZ-06 bo'yicha belgilangan 8 ta rasmiy Tool to'plami:
1. get_air_quality(lat, lon)
2. nearest_stations(lat, lon)
3. get_weather(lat, lon)
4. personal_advice(aqi, profile)
5. subscribe(user_id, lat, lon, threshold)
6. forecast(lat, lon)
7. weekly_report(user_id)
8. search_health_docs(query)
"""
from typing import Dict, Any, List, Optional

from sensor_service import (
    get_air_quality as _get_air_quality,
    nearest_stations as _nearest_stations,
)
from weather_service import get_weather as _get_weather
from advisor import (
    personal_advice as _personal_advice,
    is_medical_query,
    get_medical_guardrail_response,
)
from forecast_service import forecast as _forecast
from report_service import weekly_report as _weekly_report
from rag_service import search_health_docs as _search_health_docs
from database import add_subscription, get_user


# 1. get_air_quality(lat, lon)
def get_air_quality(lat: float, lon: float) -> Dict[str, Any]:
    """
    Eng yaqin sensordan PM2.5, PM10 va AQI ko'rsatkichini oladi.
    sensor.community va Open-Meteo orqali ishlaydi.
    """
    return _get_air_quality(lat, lon)


# 2. nearest_stations(lat, lon)
def nearest_stations(lat: float, lon: float, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Berilgan koordinata atrofidagi eng yaqin havo stansiyalari ro'yxatini qaytaradi.
    """
    return _nearest_stations(lat, lon, limit=limit)


# 3. get_weather(lat, lon)
def get_weather(lat: float, lon: float) -> Dict[str, Any]:
    """
    Open-Meteo orqali harorat, shamol tezligi, namlik va yog'in ehtimolini oladi.
    Smog tarqalishi va harorat inversiyasi tahlilini beradi.
    """
    return _get_weather(lat, lon)


# 4. personal_advice(aqi, profile)
def personal_advice(aqi: int, profile: str = "umumiy", lang: str = "uz") -> Dict[str, Any]:
    """
    Foydalanuvchi profiliga mos (bola, astma, sport, yurak, keksa, umumiy)
    US EPA va JSST (WHO) rasmiy standartlari asosidagi tavsiyani shakllantiradi.
    """
    return _personal_advice(aqi, profile, lang=lang)


# 5. subscribe(user_id, lat, lon, threshold)
def subscribe(user_id: int, lat: float, lon: float, threshold: int = 100, location_name: str = "Toshkent") -> Dict[str, Any]:
    """
    Foydalanuvchini AQI chegarasi oshganda ogohlantirishga obuna qiladi (F3).
    """
    sub_id = add_subscription(
        user_id=user_id,
        lat=lat,
        lon=lon,
        threshold=threshold,
        location_name=location_name,
    )
    return {
        "success": True,
        "subscription_id": sub_id,
        "user_id": user_id,
        "lat": lat,
        "lon": lon,
        "threshold": threshold,
        "location_name": location_name,
        "message": f"Muvaffaqiyatli obuna bo'ldingiz! AQI {threshold} dan oshsa xabar beriladi.",
    }


# 6. forecast(lat, lon)
def forecast(lat: float, lon: float, lang: str = "uz") -> Dict[str, Any]:
    """
    Keyingi 24 soatlik havo sifati va ob-havo prognozini hisoblaydi (F4).
    Sayr qilish va derazalarni yopish uchun eng qulay va xavfli vaqtlarni aniqlaydi.
    """
    return _forecast(lat, lon, lang=lang)


# 7. weekly_report(user_id)
def weekly_report(user_id: int, lat: Optional[float] = None, lon: Optional[float] = None, lang: str = "uz") -> Dict[str, Any]:
    """
    Foydalanuvchi uchun haftalik AQI grafigi (matplotlib) va tahliliy hisobot yaratadi (F6).
    """
    return _weekly_report(user_id, lat=lat, lon=lon, lang=lang)


# 8. search_health_docs(query)
def search_health_docs(query: str, lang: str = "uz") -> Dict[str, Any]:
    """
    WHO va EPA bo'yicha niqoblar (N95/KN95), HEPA filtrlar, shamollatish qoidalari
    bo'yicha RAG bilimlari bazasidan qidiradi (F5).
    """
    # Guardrail tekshiruvi: agar tibbiy savol bo'lsa
    if is_medical_query(query):
        return get_medical_guardrail_response(lang=lang)

    return _search_health_docs(query, lang=lang)


# Tool ta'riflari (LLM Function Calling uchun JSON Schema)
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_air_quality",
            "description": "Eng yaqin sensordan joriy PM2.5, PM10 va AQI darajasini oladi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Kenglik (Latitude)"},
                    "lon": {"type": "number", "description": "Uzunlik (Longitude)"},
                },
                "required": ["lat", "lon"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "nearest_stations",
            "description": "Yaqin-atrofdagi barcha havo stansiyalari va sensorlar ro'yxatini qaytaradi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Kenglik"},
                    "lon": {"type": "number", "description": "Uzunlik"},
                },
                "required": ["lat", "lon"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Shamol, harorat, namlik va atmosfera inversiyasi tahlilini oladi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Kenglik"},
                    "lon": {"type": "number", "description": "Uzunlik"},
                },
                "required": ["lat", "lon"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "personal_advice",
            "description": "AQI va profil (bola, astma, sport, yurak, keksa, umumiy) bo'yicha tavsiya beradi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "aqi": {"type": "integer", "description": "AQI qiymati"},
                    "profile": {"type": "string", "description": "Profil turi (bola, astma, sport, yurak, keksa, umumiy)"},
                },
                "required": ["aqi"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "subscribe",
            "description": "Foydalanuvchini AQI chegarasi oshganda bildirishnoma olishga obuna qiladi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "Foydalanuvchi ID raqami"},
                    "lat": {"type": "number", "description": "Kenglik"},
                    "lon": {"type": "number", "description": "Uzunlik"},
                    "threshold": {"type": "integer", "description": "Ogohlantirish chegarasi (masalan 100 yoki 150)"},
                },
                "required": ["user_id", "lat", "lon", "threshold"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forecast",
            "description": "24 soatlik havo sifati va atmosfera prognozini hisoblaydi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Kenglik"},
                    "lon": {"type": "number", "description": "Uzunlik"},
                },
                "required": ["lat", "lon"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "weekly_report",
            "description": "Haftalik AQI grafigi va tahliliy hisobotini oladi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "Foydalanuvchi ID raqami"},
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_health_docs",
            "description": "Niqoblar (N95/KN95), HEPA filtrlar va shamollatish bo'yicha RAG bazasidan qidiradi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Qidiruv so'rovi"},
                },
                "required": ["query"],
            },
        },
    },
]
