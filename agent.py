"""
Havo sifati va sog'liq agenti (Asosiy Agent Orkestratori).
TZ-06 bo'yicha barcha 8 ta tool va 7 ta funksional stsenariyni birlashtiradi.
"""
from typing import Dict, Any, Optional
from datetime import datetime

import tools
from database import (
    upsert_user,
    get_user,
    set_user_language,
    set_user_profile,
    get_user_profile,
    add_subscription,
    get_user_subscriptions,
    cancel_subscription,
)
from advisor import is_medical_query, get_medical_guardrail_response
from vision_service import analyze_sky_photo
from llm_client import llm_client
from config import DEFAULT_LAT, DEFAULT_LON


class AirQualityAgent:
    def __init__(self):
        pass

    def handle_location_query(
        self,
        lat: float,
        lon: float,
        user_id: int = 1,
        lang: str = "uz",
    ) -> Dict[str, Any]:
        """
        F1 stsenariysi: 'Hozir havo qanday?' (joylashuv bo'yicha)
        Natija: Eng yaqin sensor, PM2.5/PM10/AQI, daraja, oddiy tilda tavsiya.
        """
        # 1. Havoni o'lchash
        aq = tools.get_air_quality(lat, lon)
        aqi = aq["aqi"]

        # 2. Foydalanuvchi profilini olish (F2)
        prof_data = get_user_profile(user_id)
        profile_type = prof_data.get("profile_type", "umumiy")

        # 3. Profilga mos tavsiya
        adv = tools.personal_advice(aqi, profile=profile_type, lang=lang)

        # 4. Ob-havo qo'shimchasi
        w = tools.get_weather(lat, lon)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        status_tag = f"\n⚠️ *Eslatma: {aq['status_note']}*" if aq.get("is_estimate") else ""

        if lang == "ru":
            message = (
                f"{aq['level_emoji']} **Качество воздуха сейчас: {aq['level_title']['ru']}**\n\n"
                f"📊 **Индекс AQI:** {aqi} (US EPA)\n"
                f"🌫 **PM2.5:** {aq['pm25']} мкг/м³\n"
                f"💨 **PM10:** {aq['pm10']} мкг/м³\n"
                f"🌡 **Погода:** {w['temperature']}°C, ветер {w['wind_speed_ms']} м/с, {w['weather_description']['ru']}\n"
                f"📡 **Станция:** {aq['station_name']} ({aq['distance_km']} км от вас)\n"
                f"{status_tag}\n\n"
                f"👤 **Ваш профиль:** {profile_type.capitalize()}\n"
                f"💡 **Рекомендация:**\n{adv['advice_text']}\n\n"
                f"📌 *Источник: {aq['source']} · {aq['timestamp']}*"
            )
        else:
            message = (
                f"{aq['level_emoji']} **Hozirgi havo sifati: {aq['level_title']['uz']}**\n\n"
                f"📊 **AQI ko'rsatkichi:** {aqi} (AQSh EPA)\n"
                f"🌫 **PM2.5 (mayda zarrachalar):** {aq['pm25']} mkg/m³\n"
                f"💨 **PM10 (chang):** {aq['pm10']} mkg/m³\n"
                f"🌡 **Ob-havo:** {w['temperature']}°C, shamol {w['wind_speed_ms']} m/s, {w['weather_description']['uz']}\n"
                f"📡 **Sensor stansiyasi:** {aq['station_name']} (masofa: {aq['distance_km']} km)\n"
                f"{status_tag}\n\n"
                f"👤 **Sizning profilingiz:** {profile_type.capitalize()}\n"
                f"💡 **Oddiy tildagi tavsiya:**\n{adv['advice_text']}\n\n"
                f"📌 *Manba: {aq['source']} · {aq['timestamp']}*"
            )

        return {
            "aqi": aqi,
            "pm25": aq["pm25"],
            "pm10": aq["pm10"],
            "level": aq["level"],
            "station": aq["station_name"],
            "distance_km": aq["distance_km"],
            "profile": profile_type,
            "advice": adv["advice_text"],
            "weather": w,
            "formatted_message": message,
            "is_estimate": aq["is_estimate"],
            "timestamp": aq["timestamp"],
            "source": aq["source"],
        }

    def set_profile(self, user_id: int, profile_type: str, notes: str = "", lang: str = "uz") -> Dict[str, Any]:
        """F2 stsenariysi: Shaxsiy profilni sozlash."""
        valid_profiles = ["bola", "astma", "yurak", "sport", "keksa", "maktab", "umumiy"]
        prof = profile_type.lower()
        if prof not in valid_profiles:
            prof = "umumiy"

        set_user_profile(user_id, prof, notes)

        if lang == "ru":
            msg = (
                f"✅ **Профиль успешно обновлен!**\n\n"
                f"Текущий профиль: **{prof.capitalize()}**.\n"
                f"Теперь все рекомендации по качеству воздуха будут адаптированы под ваши особенности."
            )
        else:
            msg = (
                f"✅ **Shaxsiy profilingiz muvaffaqiyatli saqlandi!**\n\n"
                f"Tanlangan profil: **{prof.capitalize()}**.\n"
                f"Endi barcha havo sifati tavsiyalari sizning holatingizga to'liq moslashtiriladi."
            )

        return {"user_id": user_id, "profile": prof, "message": msg}

    def create_subscription(
        self,
        user_id: int,
        lat: float,
        lon: float,
        threshold: int = 100,
        location_name: str = "Toshkent",
        lang: str = "uz",
    ) -> Dict[str, Any]:
        """F3 stsenariysi: Obuna bo'lish."""
        res = tools.subscribe(user_id, lat, lon, threshold, location_name)

        if lang == "ru":
            msg = (
                f"🔔 **Подписка оформлена!**\n\n"
                f"📍 Локация: {location_name}\n"
                f"🎯 Порог оповещения: AQI {threshold}\n\n"
                f"Если загрязнение воздуха превысит этот уровень, бот автоматически пришлет вам уведомление."
            )
        else:
            msg = (
                f"🔔 **Havo sifati monitoringiga muvaffaqiyatli obuna bo'ldingiz!**\n\n"
                f"📍 Hudud: {location_name}\n"
                f"🎯 Chegara: AQI {threshold}\n\n"
                f"Agar havo sifati ushbu ko'rsatkichdan oshsa, agent darhol sizga ogohlantirish yuboradi."
            )

        return {"success": True, "subscription_id": res["subscription_id"], "message": msg}

    def get_forecast(self, lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON, lang: str = "uz") -> Dict[str, Any]:
        """F4 stsenariysi: 24 soatlik prognoz."""
        return tools.forecast(lat, lon, lang=lang)

    def ask_rag_or_health(self, query: str, lang: str = "uz") -> Dict[str, Any]:
        """
        F5 stsenariysi va umumiy savollar:
        Qaysi niqob/filtr? Shamollatish qoidalari?
        Tibbiy savollarni Guardrail orqali tutish.
        """
        # 1. Tibbiy guardrail
        if is_medical_query(query):
            guard_data = get_medical_guardrail_response(lang=lang)
            return {
                "answer": guard_data["text"],
                "is_guardrail": True,
                "source": guard_data["source"],
                "timestamp": guard_data["timestamp"],
            }

        # 2. RAG bazasidan qidirish
        rag_res = tools.search_health_docs(query, lang=lang)
        return {
            "answer": rag_res["formatted_message"],
            "is_guardrail": False,
            "source": rag_res["source"],
            "timestamp": rag_res["timestamp"],
        }

    def get_weekly_report(self, user_id: int, lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON, lang: str = "uz") -> Dict[str, Any]:
        """F6 stsenariysi: Hafta hisoboti."""
        return tools.weekly_report(user_id, lat=lat, lon=lon, lang=lang)

    def analyze_sky_image(self, image_path: str, lang: str = "uz") -> Dict[str, Any]:
        """F7 stsenariysi: Osmon/tuman rasmini tahlil qilish."""
        return analyze_sky_photo(image_path, lang=lang)


# Singleton
agent = AirQualityAgent()
