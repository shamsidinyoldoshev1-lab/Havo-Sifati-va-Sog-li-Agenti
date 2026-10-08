"""
Shaxsiy tavsiyalar va Guardrails moduli.
Foydalanuvchi profiliga mos (bola, astma, yurak, sportchi, keksalar, umumiy) EPA/WHO tavsiyalari.
Tibbiy tashxis va dori-darmon tavsiyalarini qat'iy bloklaydi.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from aqi_calc import get_aqi_level

# Tibbiy savollar va dori-darmon so'rovlarini aniqlash kalit so'zlari (Uzbek va Rus tillarida)
MEDICAL_TRIGGER_KEYWORDS = [
    # O'zbekcha (Lotin va Kirill)
    "dori", "tabletka", "ichishim kerak", "ichsam bo'ladi", "qaysi preparat",
    "antibiotik", "salbutamol", "ingalyator", "doza", "tashxis", "davolash",
    "retsept", "kapli", "ukol", "maz", "prednizolon", "og'riyapti", "sanchyapti",
    "дори", "таблетка", "антибиотик", "сальбутамол", "ингалятор", "доза",
    # Ruscha (Kirill va Lotin)
    "лекарств", "таблетк", "выпить", "принять", "препарат", "антибиотик",
    "сальбутамол", "ингалятор", "дозировк", "диагноз", "лечени", "рецепт",
    "капли", "укол", "мазь", "преднизолон", "болит", "приступ",
    "lekarstvo", "tabletki", "prinimat", "preparat", "diagnoz", "lecheniye",
]


def is_medical_query(query: str) -> bool:
    """Foydalanuvchi tibbiy tashxis yoki dori so'rayotganini aniqlaydi."""
    q = query.lower()
    return any(kw in q for kw in MEDICAL_TRIGGER_KEYWORDS)


def get_medical_guardrail_response(lang: str = "uz") -> Dict[str, Any]:
    """Tibbiy savollarga qat'iy guardrail javobi."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    if lang == "ru":
        text = (
            "⚠️ **ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ (МЕДИЦИНСКИЙ ОТКАЗ ОТ ОТВЕТСТВЕННОСТИ)**:\n"
            "Бот-ассистент **НЕ ставит медицинские диагнозы и НЕ назначает лекарственные препараты**.\n\n"
            "🩺 **Что делать при ухудшении самочувствия:**\n"
            "1. Немедленно обратитесь к вашему лечащему врачу (терапевту/пульмонологу) или вызовите скорую помощь (103).\n"
            "2. Принимайте только те препараты, которые были ранее индивидуально выписаны вашим доктором по утвержденному плану действий.\n"
            "3. Как общая мера защиты от грязного воздуха: оставайтесь в закрытом помещении с включенным HEPA-очистителем и не открывайте окна до улучшения ситуации.\n\n"
            "📌 *Основание: Международные протоколы ВОЗ и регламент безопасности здоровья.*"
        )
    else:
        text = (
            "⚠️ **MUHIM OGOHLANTIRISH (TIBBIY CHEKLOV / GUARDRAIL)**:\n"
            "Mazkur agent **tibbiy tashxis qo'ymaydi va dori-darmon vositalarini tavsiya etmaydi**.\n\n"
            "🩺 **Ahvol yomonlashganda nima qilish kerak:**\n"
            "1. Zudlik bilan shaxsiy davolovchi shifokoringizga (terapevt/pulmonolog) murojaat qiling yoki 103 tez yordamiga qo'ng'iroq qiling.\n"
            "2. Faqat shifokoringiz tomonidan oldindan buyurilgan shaxsiy reja asosidagi dori vositalaridan foydalaning.\n"
            "3. Iflos havodan himoyalanish bo'yicha umumiy tavsiya: darhol derazalarni yopib, havoni tozalash uskunasi (HEPA filtr) bor yopiq xonada qoling.\n\n"
            "📌 *Asos: JSST (WHO) xalqaro xavfsizlik qoidalari va tibbiy etika mezonlari.*"
        )

    return {
        "text": text,
        "is_guardrail_triggered": True,
        "source": "WHO Health Guidelines / Medical Safety Guardrail",
        "timestamp": now_str,
    }


def personal_advice(aqi: int, profile: str = "umumiy", lang: str = "uz") -> Dict[str, Any]:
    """
    AQI darajasi va profil bo'yicha moslashtirilgan tavsiya (F2 va Tool talabi).
    Profillar: bola, astma, yurak, sport, keksa, maktab, umumiy.
    """
    level_info = get_aqi_level(aqi)
    key = level_info["key"]
    color = level_info["color"]
    emoji = level_info["emoji"]
    title = level_info["title"].get(lang, level_info["title"]["uz"])
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    prof = profile.lower() if profile else "umumiy"

    # Maxsus profillar bo'yicha tavsiyalar
    advice_map = {
        "bola": {
            "good": {
                "uz": "Havo a'lo darajada toza. Bolalarning ochiq havoda o'ynashi, sayr qilishi va jismoniy faolligi uchun to'liq xavfsiz.",
                "ru": "Воздух чистый и безопасный. Дети могут свободно играть на открытом воздухе и гулять.",
            },
            "moderate": {
                "uz": "Havo qoniqarli. Bolalar odatdagidek tashqarida bo'lishi mumkin. Juda sezgir bolalarda o'ta uzoq chopishlarni biroz cheklash kifoya.",
                "ru": "Воздух приемлемый. Обычные прогулки безопасны, очень чувствительным детям лучше избегать изнурительного бега.",
            },
            "unhealthy_sensitive": {
                "uz": "Diqqat: Bolalarda nafas olish tezligi kattalarnikiga nisbatan yuqori. Ochiq havoda uzoq vaqt faol yugurishni kamaytiring. Sayr vaqtini qisqartiring.",
                "ru": "Внимание: У детей дыхание чаще. Ограничьте продолжительные подвижные игры на воздухе, сократите время прогулок.",
            },
            "unhealthy": {
                "uz": "⚠️ Bugun bolani tashqariga chiqarmang! Ochiq havodagi jismoniy tarbiya darslari va sayrlarni bekor qiling. Xona derazalarini yopib, havo tozalagichni yoqing.",
                "ru": "⚠️ Сегодня не выпускайте детей на улицу! Отмените прогулки и уроки физкультуры на свежем воздухе. Закройте окна.",
            },
            "very_unhealthy": {
                "uz": "🚨 Qat'iy ogohlantirish: Bolalarni faqat yopiq xonada saqlang. Ochiq havoga chiqish taqiqlanadi. Xonada HEPA filtrli tozalagich ishlashi shart.",
                "ru": "🚨 Строгое предупреждение: Дети должны находиться только дома. Выход на улицу запрещен, используйте HEPA-очиститель.",
            },
            "hazardous": {
                "uz": "🛑 Favqulodda xavfli havo! Bolalarni xonadan aslo chiqarmang. Deraza tirqishlarini jipslang, ichki havoni maksimal tozalang.",
                "ru": "🛑 Опасная ситуация! Полная изоляция от уличного воздуха. Герметично закройте окна.",
            },
        },
        "astma": {
            "good": {
                "uz": "Havo toza. Nafas yo'llari uchun xavf yo'q. Xonalarni bemalol shamollatishingiz mumkin.",
                "ru": "Воздух чистый, риска для дыхательных путей нет. Можно свободно проветривать помещения.",
            },
            "moderate": {
                "uz": "Havo o'rtacha. Odatdagi ehtiyotkorlik yetarli, shaxsiy shifokor ko'rsatgan profilaktika qoidalariga rioya qiling.",
                "ru": "Воздух умеренный. Соблюдайте стандартный план контроля астмы, предписанный врачом.",
            },
            "unhealthy_sensitive": {
                "uz": "Ogohlantirish: Chang va PM2.5 zarrachalari nafas yo'lini qo'zg'atishi mumkin. Ochiq havoda uzoq qolishdan saqlaning, shifokor tavsiya qilgan shaxsiy vositalaringiz yoningizda bo'lsin.",
                "ru": "Внимание: Микрочастицы PM2.5 могут вызвать раздражение. Сократите пребывание на улице, держите ингалятор при себе.",
            },
            "unhealthy": {
                "uz": "⚠️ Xavfli daraja! Tashqariga chiqmang, derazalarni mahkam yoping. Ko'chaga chiqishga majbur bo'lsangiz N95/KN95 respirator taqing. Nafas qisishi kuchaysa zudlik bilan shifokor bilan bog'laning.",
                "ru": "⚠️ Опасный уровень! Оставайтесь дома, закройте окна, включите очиститель воздуха. При выходе надевайте респиратор N95. При симптомах свяжитесь с врачом.",
            },
            "very_unhealthy": {
                "uz": "🚨 Juda xavfli! Xonadan mutlaqo chiqmang. Barcha deraza va eshiklarni germetik yoping, HEPA filtrni maksimal quvvatga qo'ying. Holat og'irlashsa darhol shifokorga murojaat qiling.",
                "ru": "🚨 Очень опасно! Категорически избегайте выхода наружу. Включите HEPA-фильтр на полную мощность. При одышке срочно обратитесь к врачу.",
            },
            "hazardous": {
                "uz": "🛑 Favqulodda xavf! Og'ir astma xuruji xavfi yuqori. Tashqi havoni xonaga kiritmang. Shifokor bilan doimiy aloqada bo'ling.",
                "ru": "🛑 Критическая опасность! Высокий риск приступа. Полная изоляция от внешнего воздуха, связь с врачом.",
            },
        },
        "sport": {
            "good": {
                "uz": "A'lo daraja! Yugurish, marafon, velosiped va ochiq havodagi har qanday intensiv mashg'ulotlar uchun juda qulay.",
                "ru": "Отличные условия! Идеально подходит для бега, кроссфита и уличных тренировок.",
            },
            "moderate": {
                "uz": "Qoniqarli. Tashqi mashqlarni bajarsangiz bo'ladi. Agar uzoq masofaga yugursangiz, erta tongda o'tkazish yaxshiroq.",
                "ru": "Приемлемо. Тренировки на улице допустимы. Длительные пробежки лучше проводить рано утром.",
            },
            "unhealthy_sensitive": {
                "uz": "Diqqat: Yuqori jismoniy yuklama paytida o'pka 10 barobar ko'proq ifloslangan havo yutadi. Intensiv kardio mashqlarni yopiq sport zaliga ko'chiring.",
                "ru": "Внимание: При интенсивном беге легкие вдыхают в разы больше взвешенных частиц. Перенесите кардио в спортзал.",
            },
            "unhealthy": {
                "uz": "⚠️ Ochiq havoda mashq qilish qat'iyan taqiqlanadi! PM2.5 zarralari o'pka alveolalariga chuqur o'tiradi. Faqat havosi tozalangan yopiq zalda mashq qiling.",
                "ru": "⚠️ Тренировки на улице запрещены! Глубокое дыхание занесет токсичные частицы глубоко в легкие. Тренируйтесь только в помещении с фильтрацией воздуха.",
            },
            "very_unhealthy": {
                "uz": "🚨 Jiddiy xavf: Ochiq havoda hech qanday sport bilan shug'ullanmang. Hatto yopiq zalda ham og'ir kardio yuklamalarni yengillashtiring.",
                "ru": "🚨 Серьезная опасность: Полный отказ от уличного спорта. В зале снизьте интенсивность нагрузок.",
            },
            "hazardous": {
                "uz": "🛑 Favqulodda holat: Har qanday intensiv sport faoliyatini vaqtincha to'xtating.",
                "ru": "🛑 Чрезвычайная ситуация: Любые интенсивные спортивные нагрузки полностью исключаются.",
            },
        },
        "yurak": {
            "good": {
                "uz": "Havo toza. Ochiq havoda bemalol sayr qilish va yengil piyoda yurish foydali.",
                "ru": "Воздух чистый. Полезны пешие прогулки на свежем воздухе.",
            },
            "moderate": {
                "uz": "Havo o'rtacha. Odatdagi sayrlar xavfsiz. O'zingizni ortiqcha toliqtirmang.",
                "ru": "Воздух умеренный. Обычные прогулки допустимы, избегайте переутомления.",
            },
            "unhealthy_sensitive": {
                "uz": "Diqqat: Mayda zarrachalar qon tomirlariga ta'sir qilishi mumkin. Ochiq havoda ortiqcha jismoniy zo'riqishdan saqlaning.",
                "ru": "Внимание: Микрочастицы создают нагрузку на сосуды. Избегайте физических нагрузок на воздухе.",
            },
            "unhealthy": {
                "uz": "⚠️ Tashqariga chiqmang! Havo iflosligi qon bosimi va yurak ritmiga salbiy ta'sir ko'rsatishi mumkin. Xonada dam oling, shifokor tavsiyalariga rioya qiling.",
                "ru": "⚠️ Не выходите на улицу! Загрязнение повышает нагрузку на сердце. Отдыхайте в помещении, следуйте назначениям врача.",
            },
            "very_unhealthy": {
                "uz": "🚨 Yuqori xavf: Tashqariga chiqish qat'iyan man etiladi. Ichki havoni tozalang, ko'krakda noxushlik sezilsa darhol shifokorga murojaat qiling.",
                "ru": "🚨 Высокий риск: Запрет на выход наружу. Очищайте воздух дома, при дискомфорте в груди срочно обратитесь к врачу.",
            },
            "hazardous": {
                "uz": "🛑 Favqulodda holat: To'liq uy rejimi. Har qanday stress va tashqi havodan saqlaning.",
                "ru": "🛑 Критическая опасность: Строгий постельный/домашний режим в очищенном помещении.",
            },
        },
        "maktab": {
            "good": {
                "uz": "Havo toza. Maktabda ochiq havodagi jismoniy tarbiya darslari va sayrlar to'liq o'tkazilishi mumkin.",
                "ru": "Воздух чистый. Уроки физкультуры и перемены на свежем воздухе разрешены.",
            },
            "moderate": {
                "uz": "Havo o'rtacha. Ochiq havoda mashg'ulotlar mumkin, sezgir o'quvchilarga e'tibor qarating.",
                "ru": "Воздух умеренный. Уличные занятия разрешены с вниманием к чувствительным детям.",
            },
            "unhealthy_sensitive": {
                "uz": "Diqqat: Maktab hovlisidagi uzoq muddatli yugurish va jismoniy musobaqalarni sport zaliga o'tkazish tavsiya etiladi.",
                "ru": "Внимание: Длительный бег на спортплощадке рекомендуется перенести в школьный спортзал.",
            },
            "unhealthy": {
                "uz": "⚠️ Barcha ochiq havodagi darslar va tanaffuslarni bekor qiling! O'quvchilar binoning ichida bo'lishi, derazalar yopilishi shart.",
                "ru": "⚠️ Отмените все уличные уроки и линейки! Ученики должны находиться строго внутри здания.",
            },
            "very_unhealthy": {
                "uz": "🚨 Barcha ochiq havoga chiqishlar taqiqlanadi. Maktab sinflarida havo tozalash uskunalari yoqilsin.",
                "ru": "🚨 Выход детей во двор запрещен. В классах должны работать воздухоочистители.",
            },
            "hazardous": {
                "uz": "🛑 Favqulodda holat: Ta'limni masofaviy shaklga o'tkazish tavsiya etiladi.",
                "ru": "🛑 Чрезвычайная ситуация: Рекомендуется перевод на дистанционное обучение.",
            },
        },
        "umumiy": {
            "good": {
                "uz": "Havo toza va musaffo. Derazalarni ochib xonani shamollatish, sayr qilish uchun eng qulay vaqt.",
                "ru": "Воздух чистый. Идеальное время для проветривания квартиры и прогулок.",
            },
            "moderate": {
                "uz": "Havo qoniqarli darajada. Kundalik faoliyat cheklovsiz davom etishi mumkin.",
                "ru": "Качество воздуха умеренное. Обычная повседневная деятельность без ограничений.",
            },
            "unhealthy_sensitive": {
                "uz": "Ochiq havoda uzoq vaqt og'ir jismoniy mehnat qilishni kamaytiring. Shamollatishni cheklang.",
                "ru": "Сократите тяжелый физический труд на открытом воздухе. Ограничьте проветривание.",
            },
            "unhealthy": {
                "uz": "⚠️ Havo zararli. Tashqariga faqat zarur hollarda chiqing, N95/KN95 respirator taqing, derazalarni yoping.",
                "ru": "⚠️ Воздух вреден. Сократите выходы на улицу, надевайте респираторы N95/KN95, закройте окна.",
            },
            "very_unhealthy": {
                "uz": "🚨 Juda ifloslangan havo. Uyda qoling, derazalarni ochmang, havo tozalagichdan foydalaning.",
                "ru": "🚨 Очень грязный воздух. Оставайтесь дома, не открывайте окна, используйте очистители воздуха.",
            },
            "hazardous": {
                "uz": "🛑 Favqulodda iflos havo! Ko'chaga mutlaqo chiqmang. Uy ichidagi havoni maksimal tozalang.",
                "ru": "🛑 Опасный уровень! Полная изоляция от уличного смога.",
            },
        },
    }

    # Profilga mos tavsiyani topish
    profile_advices = advice_map.get(prof, advice_map["umumiy"])
    advice_text = profile_advices.get(key, advice_map["umumiy"][key]).get(lang, "Tavsiya mavjud emas.")

    # Guardrails: Tibbiy eslatma va manba
    if lang == "ru":
        disclaimer = "⚠️ *Рекомендации носят профилактический характер (ВОЗ/EPA). При заболеваниях обязательно консультируйтесь с врачом.*"
    else:
        disclaimer = "⚠️ *Eslatma: Tavsiyalar umumiy profilaktik xususiyatga ega (JSST/EPA). Kasallik va dorilar bo'yicha shifokor bilan maslahatlashing.*"

    full_text = (
        f"{emoji} **AQI {aqi} — {title}**\n\n"
        f"📋 **Profil:** {prof.capitalize()}\n"
        f"💡 **Tavsiya:**\n{advice_text}\n\n"
        f"{disclaimer}\n"
        f"📌 *Manba: US EPA & WHO Air Quality Standards · {now_str}*"
    )

    return {
        "aqi": aqi,
        "profile": prof,
        "level_key": key,
        "title": title,
        "emoji": emoji,
        "color": color,
        "advice_text": advice_text,
        "formatted_message": full_text,
        "source": "US EPA & WHO Air Quality Guidelines",
        "timestamp": now_str,
    }
