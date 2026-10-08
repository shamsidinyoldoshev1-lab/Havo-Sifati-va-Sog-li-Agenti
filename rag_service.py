"""
RAG (Retrieval-Augmented Generation) xizmati.
WHO (JSST) va US EPA rasmiy yo'riqnomalari, niqoblar (N95/KN95/FFP2),
HEPA filtrlar, shamollatish qoidalari bo'yicha bilimlar bazasi.
"""
import math
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

KNOWLEDGE_DOCS = [
    {
        "id": "masks_n95_kn95",
        "category": "masks",
        "title": {
            "uz": "PM2.5 dan himoyalanish uchun qaysi niqoblar samarali?",
            "ru": "Какие маски эффективны против PM2.5?",
        },
        "content": {
            "uz": (
                "1. N95 / KN95 / FFP2 respiratorlari:\n"
                "- Ushbu respiratorlar 0.3 mikronli mikroskopik zarrachalarni kamida 94-95% ushlab qoladi.\n"
                "- PM2.5 chang va tutun zarralaridan himoyalanish uchun yagona samarali vositadir.\n"
                "- Asosiy shart: respirator chetlari yuzga to'liq, havo kirmaydigan darajada zich (tight fit) yopishishi shart. Soqol yoki ochiq tirqishlar samaradorlikni 60% gacha pasaytiradi.\n\n"
                "2. Tibbiy (jarrohlik) niqoblari:\n"
                "- Faqat yo'tal va aksirishdagi yirik tomchilarni to'sishga mo'ljallangan.\n"
                "- PM2.5 mikrozarralaridan deyarli himoya qilmaydi (chetlaridan erkin havo o'tadi va filtr qatlami yetarli emas).\n\n"
                "3. Mato (gazlama) niqoblar:\n"
                "- PM2.5 ga qarshi samaradorligi 5-10% dan oshmaydi, tutundan umuman himoya qilmaydi."
            ),
            "ru": (
                "1. Респираторы N95 / KN95 / FFP2:\n"
                "- Задерживают не менее 94-95% микрочастиц размером от 0.3 микрон.\n"
                "- Единственное доказанное эффективное средство защиты от смога и PM2.5.\n"
                "- Главное условие: плотное прилегание к лицу (tight fit). Зазоры и борода снижают защиту на 60%.\n\n"
                "2. Медицинские (хирургические) маски:\n"
                "- Защищают только от крупных капель при кашле/чихании.\n"
                "- Не защищают от PM2.5 из-за отсутствия прилегания и слабой фильтрации.\n\n"
                "3. Тканевые маски:\n"
                "- Эффективность против PM2.5 не превышает 5-10%. Бесполезны против смога."
            ),
        },
        "keywords": ["niqob", "maska", "n95", "kn95", "ffp2", "filtr", "jarrohlik", "mato", "himoya", "респиратор", "маски"],
        "source": "US NIOSH & WHO Personal Protective Equipment Guidelines",
    },
    {
        "id": "air_purifiers_hepa",
        "category": "filters",
        "title": {
            "uz": "Xonani tozalash uchun qanday havo tozalagich (filtr) tanlash kerak?",
            "ru": "Какой очиститель воздуха и фильтр выбрать для дома?",
        },
        "content": {
            "uz": (
                "1. HEPA filtri (H13 yoki H14 toifasi):\n"
                "- Xonadagi 0.3 mikronli zarralarning 99.95% - 99.97% ini filtrlaydi.\n"
                "- PM2.5, allergenlar, mayda chang va tutunni tozalashning oltin standarti.\n\n"
                "2. CADR (Clean Air Delivery Rate) ko'rsatkichi:\n"
                "- Tozalagichning quvvati xona hajmiga mos kelishi lozim. Formula: CADR (m3/soat) >= Xona maydoni (m2) * Balandlik * 3 (soatiga kamida 3 marta havo aylanishi).\n"
                "- Masalan, 20 m2 xona uchun kamida 150-200 m3/soat CADR quvvati zarur.\n\n"
                "3. Faollashtirilgan ugol (ugolli filtr):\n"
                "- Zaharli gazlar, hidlar va VOC (uchuvchi organik moddalar)ni yutadi. HEPA bilan birga ishlatilishi shart.\n\n"
                "4. Nimalardan saqlanish kerak:\n"
                "- Ozon hosil qiluvchi (ozonator) va ochiq ionizatorlardan saqlaning. Ozon o'pka to'qimalarini kuchli yallig'lantiradi va sog'liq uchun xavfli."
            ),
            "ru": (
                "1. Фильтры класса HEPA (H13 или H14):\n"
                "- Улавливают 99.95% - 99.97% частиц размером от 0.3 микрон.\n"
                "- Золотой стандарт защиты от PM2.5, пыли и аллергенов в доме.\n\n"
                "2. Показатель CADR (скорость подачи чистого воздуха):\n"
                "- Должен соответствовать площади. Формула: CADR >= Площадь * Высота * 3.\n"
                "- Для комнаты 20 м2 требуется производительность от 150-200 м3/час.\n\n"
                "3. Угольный фильтр (Activated Carbon):\n"
                "- Необходим для нейтрализации запахов, газов и летучих органических соединений (ЛОС).\n\n"
                "4. Чего избегать:\n"
                "- Не покупайте озонаторы и несертифицированные ионизаторы. Озон повреждает легочную ткань."
            ),
        },
        "keywords": ["havo tozalagich", "filtr", "hepa", "h13", "h14", "cadr", "ugol", "ochistitel", "ochistitel vozduha", "filtraciya", "ochistka"],
        "source": "US EPA Guide to Air Cleaners in the Home & WHO Indoor Air Quality",
    },
    {
        "id": "ventilation_rules",
        "category": "ventilation",
        "title": {
            "uz": "Smog paytida xonani qachon va qanday shamollatish (deraza ochish) kerak?",
            "ru": "Когда и как проветривать помещение во время смога?",
        },
        "content": {
            "uz": (
                "1. Qachon derazalarni ochmaslik kerak:\n"
                "- Kechki soat 20:00 dan erta tonggi 09:00 gacha. Bu paytda harorat inversiyasi tufayli isitish va avtomobil tutunlari yer sathiga cho'kadi va ifloslanish eng yuqori bo'ladi.\n"
                "- AQI ko'rsatkichi 150 dan oshganda derazalar butunlay yopiq turishi kerak.\n\n"
                "2. Qachon shamollatish mumkin:\n"
                "- Kunduzi soat 13:00 dan 16:00 gacha (quyosh havoni qizdirib, vertikal havo oqimi hosil bo'lganda va tutun siyraklashganda).\n"
                "- Kuchli shamol (4 m/s dan yuqori) esganda yoki yomg'ir yoqqandan keyin havo tozalanganda.\n\n"
                "3. Avtomobilda:\n"
                "- Tirbandlikda doimo havo sirkulyatsiyasini 'salondan' (ichki retsirkulyatsiya) rejimiga o'tkazing va salon filtrini muntazam yangilang."
            ),
            "ru": (
                "1. Когда нельзя открывать окна:\n"
                "- С 20:00 вечера до 09:00 утра. Из-за температурной инверсии выхлопы и дым скапливаются у земли.\n"
                "- При AQI выше 150 окна должны быть плотно закрыты.\n\n"
                "2. Когда проветривать безопасно:\n"
                "- Днем с 13:00 до 16:00, когда прогрев солнцем рассеивает приземный смог.\n"
                "- После дождя или при сильном ветре (более 4 м/с).\n\n"
                "3. В автомобиле:\n"
                "- В пробках включайте режим внутренней рециркуляции воздуха и используйте угольный салонный фильтр."
            ),
        },
        "keywords": ["shamollatish", "deraza", "oyna", "ochish", "inversiya", "mashina", "avtomobil", "salon", "provetrivaniye", "okna", "smog"],
        "source": "WHO Housing and Health Guidelines & EPA Ambient Air Monitoring",
    },
    {
        "id": "who_air_quality_standards",
        "category": "standards",
        "title": {
            "uz": "JSST (WHO) Havo sifati bo'yicha rasmiy me'yorlari (2021)",
            "ru": "Нормативы ВОЗ по качеству воздуха (2021)",
        },
        "content": {
            "uz": (
                "JSST (WHO) 2021-yilda e'lon qilgan qat'iy me'yorlar:\n"
                "- PM2.5 (o'ta mayda chang): Yillik me'yor 5 mkg/m3, 24 soatlik xavfsiz chegara 15 mkg/m3.\n"
                "- PM10 (qo'pol chang): Yillik me'yor 15 mkg/m3, 24 soatlik xavfsiz chegara 45 mkg/m3.\n"
                "- NO2 (azot dioksidi): 24 soatlik xavfsiz chegara 25 mkg/m3.\n"
                "- O3 (ozon): 8 soatlik mavsumiy chegara 60 mkg/m3.\n\n"
                "Toshkentda qish paytida PM2.5 konsentratsiyasi ko'pincha 50-150 mkg/m3 ga yetadi, bu JSST xavfsiz me'yoridan 5-10 baravargacha yuqoridir."
            ),
            "ru": (
                "Обновленные глобальные нормативы ВОЗ 2021 года:\n"
                "- PM2.5: среднегодовая норма 5 мкг/м3, суточный предел 15 мкг/м3.\n"
                "- PM10: среднегодовая норма 15 мкг/м3, суточный предел 45 мкг/м3.\n"
                "- NO2 (диоксид азота): суточный предел 25 мкг/м3.\n\n"
                "В Ташкенте зимой уровень PM2.5 часто превышает безопасные нормы ВОЗ в 5-10 раз."
            ),
        },
        "keywords": ["who", "jsst", "standart", "meyor", "pm2.5", "pm10", "norma", "voz", "voz meyorlari"],
        "source": "WHO Global Air Quality Guidelines (AQGs) 2021",
    },
]


def tokenize(text: str) -> List[str]:
    """Matnni so'zlarga ajratish va tozalash."""
    clean = re.sub(r"[^\w\s]", " ", text.lower())
    return [w for w in clean.split() if len(w) > 2]


def search_health_docs(query: str, lang: str = "uz") -> Dict[str, Any]:
    """
    RAG qidiruv: WHO/EPA qo'llanmalari bo'yicha savollarga javob beradi (F5 va Tool talabi).
    Niqob, filtr, HEPA, shamollatish va boshqalar.
    """
    query_tokens = tokenize(query)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    scored_docs = []
    for doc in KNOWLEDGE_DOCS:
        score = 0.0
        doc_text = (doc["title"].get(lang, "") + " " + doc["content"].get(lang, "")).lower()
        keywords = doc.get("keywords", [])

        # Tokenlar bo'yicha tekshirish
        for token in query_tokens:
            if token in keywords:
                score += 3.0
            if token in doc_text:
                score += 1.0

        if score > 0:
            scored_docs.append((score, doc))

    scored_docs.sort(key=lambda x: x[0], reverse=True)

    if not scored_docs:
        # Birlamchi eng yaqin umumiy hujjatni beramiz (niqob va HEPA)
        top_doc = KNOWLEDGE_DOCS[0]
    else:
        top_doc = scored_docs[0][1]

    title = top_doc["title"].get(lang, top_doc["title"]["uz"])
    content = top_doc["content"].get(lang, top_doc["content"]["uz"])
    source = top_doc["source"]

    formatted_response = (
        f"📚 **{title}**\n\n"
        f"{content}\n\n"
        f"📌 *Manba: {source} · {now_str}*"
    )

    return {
        "doc_id": top_doc["id"],
        "category": top_doc["category"],
        "title": title,
        "content": content,
        "source": source,
        "formatted_message": formatted_response,
        "timestamp": now_str,
    }
