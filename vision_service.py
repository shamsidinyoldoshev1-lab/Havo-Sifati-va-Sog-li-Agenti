"""
Vision xizmati: Osmon va tuman rasmlarini tahlil qilish (F7 talabi).
Gemini Flash Vision / PIL gipotezasi orqali vizual tahlil.
Guardrail: Vision bahosi hech qachon fizik sensor o'rnini bosa olmaydi.
"""
import os
from datetime import datetime
from typing import Dict, Any, Optional
from PIL import Image, ImageStat
from config import GEMINI_API_KEY


def analyze_image_with_gemini(image_path: str, lang: str = "uz") -> Optional[str]:
    """Gemini 2.5 Flash orqali rasmni tahlil qilish."""
    if not GEMINI_API_KEY:
        return None

    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        prompt_uz = (
            "Ushbu osmon, shahar yoki atmosfera fotosuratini havo iflosligi (smog, tuman, PM2.5 changi) "
            "nuqtai nazaridan tahlil qiling. Osmonning rangi, ufqning ko'rinishi (visibility), "
            "tutun qatlami zichligini baholang va 1-2 xatboshida vizual taxminiy xulosa bering. "
            "Javob o'zbek tilida bo'lsin."
        )
        prompt_ru = (
            "Проанализируйте данную фотографию неба/города на предмет смога, пыли или загрязнения воздуха. "
            "Оцените дальность видимости, цвет горизонта, плотность дымки. "
            "Дайте краткий визуальный ориентир на русском языке в 1-2 абзацах."
        )

        prompt = prompt_ru if lang == "ru" else prompt_uz
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=[image_bytes, prompt]
        )
        if response and response.text:
            return response.text.strip()
    except Exception:
        pass

    return None


def analyze_image_heuristics(image_path: str, lang: str = "uz") -> Dict[str, Any]:
    """
    Rasmning kontrasti, yorug'ligi va rang kanallari balansi orqali
    oftob/tuman/smog zichligini tahlil qiluvchi zaxira algoritm.
    """
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            stat = ImageStat.Stat(img)
            
            # Rang kanallari o'rtachasi
            r, g, b = stat.mean
            # Kontrast (standart og'ish)
            rms = stat.rms
            contrast = sum(rms) / 3.0
            
            # Agar kontrast past va rang kulrang/xira bo'lsa -> tuman yoki tutun
            gray_diff = abs(r - g) + abs(g - b) + abs(r - b)
            
            if contrast < 40 and gray_diff < 25:
                smog_level = "yuqori"
                level_ru = "высокий уровень смога/тумана"
                est_aqi = "150-200 (Zararli / Вредно)"
                desc_uz = "Ufq deyarli ko'rinmaydi, past kontrast va kulrang parda mavjud. Zich smog yoki qalin tuman alomatlari yaqqol seziladi."
                desc_ru = "Горизонт практически скрыт за серой дымкой, контрастность низкая. Признаки плотного смога или тумана."
            elif contrast < 55:
                smog_level = "o'rtacha"
                level_ru = "умеренная дымка"
                est_aqi = "100-150 (Nozik guruhlar uchun zararli)"
                desc_uz = "Yengil tuman yoki tutunli xiralik kuzatilmoqda. Uzoqdagi binolar va tepaliklar konturi xiralashgan."
                desc_ru = "Наблюдается умеренная дымка. Контуры дальних строений размыты."
            else:
                smog_level = "past"
                level_ru = "низкая задымленность / ясное небо"
                est_aqi = "30-70 (Yaxshi yoki O'rtacha)"
                desc_uz = "Osmon tiniq, kontrast yuqori va ko'rish masofasi yetarlicha yaxshi. Vizual ifloslanish belgilari kam."
                desc_ru = "Небо относительно чистое, контраст высокий, хорошая видимость."

            return {
                "smog_level": smog_level,
                "est_aqi": est_aqi,
                "description": desc_ru if lang == "ru" else desc_uz,
                "contrast": round(contrast, 1),
            }
    except Exception:
        return {
            "smog_level": "noma'lum",
            "est_aqi": "50-100",
            "description": "Rasmni to'liq tahlil qilish imkoni bo'lmadi.",
            "contrast": 50.0,
        }


def analyze_sky_photo(image_path: str, lang: str = "uz") -> Dict[str, Any]:
    """
    F7 talabi: Rasm (osmon/tuman) bo'yicha tahlil.
    Guardrails:
    - Vision baho hech qachon sensor o'rniga o'tmaydi!
    - Manba va sana har javobda ko'rsatiladi.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 1. Gemini orqali tahlil qilishga urinish
    gemini_text = analyze_image_with_gemini(image_path, lang=lang)
    heuristic = analyze_image_heuristics(image_path, lang=lang)

    if gemini_text:
        analysis_content = gemini_text
        source_name = "Gemini Flash Vision AI"
    else:
        analysis_content = (
            f"🔎 **Vizual baho:** {heuristic['smog_level'].capitalize()} ifloslanish ehtimoli.\n"
            f"📊 **Taxminiy AQI diapazoni:** {heuristic['est_aqi']}\n"
            f"📝 **Izoh:** {heuristic['description']}"
            if lang == "uz" else
            f"🔎 **Визуальная оценка:** {heuristic['smog_level']}.\n"
            f"📊 **Ориентировочный AQI:** {heuristic['est_aqi']}\n"
            f"📝 **Описание:** {heuristic['description']}"
        )
        source_name = "Algoritmik vizual tahlil (PIL Contrast & Haze Analysis)"

    if lang == "ru":
        guardrail_warning = (
            "⚠️ **ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ (GUARDRAIL)**:\n"
            "Оценка по фотографии является исключительно вспомогательным визуальным ориентиром "
            "и **НИКОГДА не заменяет физические лазерные датчики качества воздуха (PM2.5/PM10)**! "
            "Точные данные смотрите по датчикам через команду /air."
        )
        final_message = (
            f"📸 **Анализ фотографии неба и горизонта**\n\n"
            f"{analysis_content}\n\n"
            f"{guardrail_warning}\n\n"
            f"📌 *Источник: {source_name} · {now_str}*"
        )
    else:
        guardrail_warning = (
            "⚠️ **QAT'IY OGOHLANTIRISH (GUARDRAIL)**:\n"
            "Fotosurat orqali berilgan baho faqat yordamchi ko'rgazmali indikator hisoblanadi "
            "va **HECH QACHON haqiqiy fizik lazer sensorlar (PM2.5/PM10) o'rnini bosa olmaydi**! "
            "Aniq va tasdiqlangan ko'rsatkichni bilish uchun /air buyrug'i orqali stansiya ma'lumotlarini oling."
        )
        final_message = (
            f"📸 **Osmon va ufq fotosurati tahlili**\n\n"
            f"{analysis_content}\n\n"
            f"{guardrail_warning}\n\n"
            f"📌 *Manba: {source_name} · {now_str}*"
        )

    return {
        "analysis": analysis_content,
        "is_estimate": True,
        "guardrail_warning": guardrail_warning,
        "formatted_message": final_message,
        "source": source_name,
        "timestamp": now_str,
    }
