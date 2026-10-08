"""
LLM muloqot mijozi: Gemini Flash va Groq (zaxira).
Tibbiy guardrails, manba va sana majburiyligi hamda zaxira rejimlarini boshqaradi.
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from config import GEMINI_API_KEY, GROQ_API_KEY, DEFAULT_LANG
from advisor import is_medical_query, get_medical_guardrail_response

SYSTEM_PROMPT = """
Sen Toshkent shahri va O'zbekiston aholisi uchun Havo sifati va sog'liq bo'yicha sun'iy intellekt agentisan.
Sening vazifang — PM2.5, PM10 va AQI ko'rsatkichlari bo'yicha fuqarolarga (ota-onalar, sportchilar, keksalar, astma bilan og'riganlarga) aniq, tushunarli va hayotiy xavfsizlik tavsiyalarini berishdir.

QAT'IY GUARDRAILLAR (QOIDALAR):
1. TIBBIY TASHXIS VA DORI-DARMON YO'Q: Hech qachon foydalanuvchiga tibbiy tashxis qo'yma, hech qanday dori preparatini (salbutamol, antibiotik, tabletka va h.k.) tavsiya qilma. Sog'liq profili bo'yicha faqat JSST (WHO) va AQSh EPA umumiy profilaktik tavsiyalarini ber va har doim "shifokor bilan maslahatlashing" deb uqtir.
2. SENSOR MA'LUMOTI ESKIRGAN BO'LSA: Agar sensor ma'lumoti 2 soatdan eski yoki yo'q bo'lsa, buni aniq ta'kidlab "taxminiy ko'rsatkich" deb ko'rsat.
3. RASM/VISION BAHOSI: Fotosurat orqali berilgan baho hech qachon fizik PM2.5 lazer sensorlari o'rnini bosa olmaydi.
4. MANBA VA SANA: Har bir javobing oxirida ma'lumot manbasi (masalan, sensor.community, Open-Meteo, WHO, EPA) va joriy sana/vaqtni ko'rsatish majburiy.
5. TIL: Foydalanuvchi so'ragan tilda (o'zbek yoki rus) samimiy, aniq va lo'nda javob ber.
"""


class AirQualityLLM:
    def __init__(self):
        self.gemini_client = None
        self.groq_client = None

        if GEMINI_API_KEY:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception:
                pass

        if GROQ_API_KEY:
            try:
                from openai import OpenAI
                self.groq_client = OpenAI(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=GROQ_API_KEY,
                )
            except Exception:
                pass

    def generate_response(
        self,
        user_message: str,
        context: Optional[str] = None,
        lang: str = "uz"
    ) -> str:
        """
        Matnli savollarga javob generatsiya qilish.
        1. Tibbiy guardrail tekshiruvi.
        2. Gemini Flash.
        3. Groq (zaxira).
        4. Deterministik zaxira javob.
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 1. Tibbiy savol bo'lsa darhol Guardrail ishga tushadi
        if is_medical_query(user_message):
            guard_resp = get_medical_guardrail_response(lang=lang)
            return guard_resp["text"]

        # Prompt tuzish
        user_prompt = f"Foydalanuvchi savoli: {user_message}\n"
        if context:
            user_prompt = f"Tizim ma'lumotlari (Kontekst):\n{context}\n\n{user_prompt}"

        # 2. Gemini orqali urinish
        if self.gemini_client:
            try:
                resp = self.gemini_client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=[
                        {"role": "user", "parts": [{"text": f"{SYSTEM_PROMPT}\n\n{user_prompt}"}]}
                    ],
                )
                if resp and resp.text:
                    text = resp.text.strip()
                    if "Manba:" not in text and "Источник:" not in text:
                        text += f"\n\n📌 *Manba: WHO & US EPA Air Quality Guidelines · {now_str}*"
                    return text
            except Exception:
                pass

        # 3. Groq orqali urinish (Zaxira LLM)
        if self.groq_client:
            try:
                # Mavjud Groq modellaridan biri
                model_name = "qwen/qwen3.8-27b"
                resp = self.groq_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=600,
                    temperature=0.3,
                )
                if resp and resp.choices and resp.choices[0].message.content:
                    text = resp.choices[0].message.content.strip()
                    if "Manba:" not in text and "Источник:" not in text:
                        text += f"\n\n📌 *Manba: WHO & US EPA Air Quality Guidelines · {now_str}*"
                    return text
            except Exception:
                pass

        # 4. Deterministik zaxira (Hech qaysi API ishlamasa ham foydalanuvchiga to'liq javob qaytarish)
        if lang == "ru":
            fallback = (
                "Здравствуйте! В Ташкенте для защиты от загрязнения воздуха (PM2.5) "
                "рекомендуется следить за текущим индексом AQI, закрывать окна при превышении 100-150 пунктов, "
                "использовать комнатные воздухоочистители с фильтрами HEPA H13 и респираторы N95/KN95 при выходе на улицу.\n\n"
                "📌 *Источник: Рекомендации ВОЗ и US EPA · {now_str}*"
            )
        else:
            fallback = (
                "Assalomu alaykum! Toshkent shahrida atmosfera havosi ifloslanishidan (PM2.5) himoyalanish uchun "
                "AQI ko'rsatkichi 100 dan oshganda tashqi faollikni cheklash, derazalarni mahkam yopish, "
                "xonada HEPA H13 filtrli havo tozalagich yoqish va ko'chaga chiqqanda N95/KN95 respirator taqish tavsiya etiladi.\n\n"
                f"📌 *Manba: JSST (WHO) va US EPA yo'riqnomalari · {now_str}*"
            )

        return fallback


# Singleton
llm_client = AirQualityLLM()
