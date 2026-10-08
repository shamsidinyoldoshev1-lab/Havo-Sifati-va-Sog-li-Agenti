"""
Telegram Bot moduli (python-telegram-bot v21).
Foydalanuvchi interfeysi: Joylashuv yuborish, profillar, obuna,
prognoz, haftalik grafik hisobot, RAG savol-javob va rasm tahlili.
"""
import os
import logging
from datetime import datetime
from pathlib import Path
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, DEFAULT_LAT, DEFAULT_LON, REPORTS_DIR
from database import (
    upsert_user,
    get_user,
    set_user_language,
    get_user_profile,
    get_user_subscriptions,
    set_user_location,
    get_user_location,
)
from agent import agent
from scheduler_service import SubscriptionMonitor

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Ommabop tuman va shaharlar koordinatalari
POPULAR_LOCATIONS = {
    # Toshkent tumanlari
    "chilonzor": {"name": "Toshkent, Chilonzor tumani", "name_ru": "Ташкент, Чиланзарский р-н", "lat": 41.2825, "lon": 69.2045},
    "yunusobod": {"name": "Toshkent, Yunusobod tumani", "name_ru": "Ташкент, Юнусабадский р-н", "lat": 41.3644, "lon": 69.2882},
    "mirzo_ulugbek": {"name": "Toshkent, Mirzo Ulug'bek tumani", "name_ru": "Ташкент, Мирзо-Улугбекский р-н", "lat": 41.3415, "lon": 69.3522},
    "mirobod": {"name": "Toshkent, Mirobod tumani", "name_ru": "Ташкент, Мирабадский р-н", "lat": 41.2907, "lon": 69.2796},
    "yakkasaroy": {"name": "Toshkent, Yakkasaroy tumani", "name_ru": "Ташкент, Яккасарайский р-н", "lat": 41.2785, "lon": 69.2554},
    "sergeli": {"name": "Toshkent, Sergeli tumani", "name_ru": "Ташкент, Сергелийский р-н", "lat": 41.2241, "lon": 69.2215},
    "yashnobod": {"name": "Toshkent, Yashnobod tumani", "name_ru": "Ташкент, Яшнабадский р-н", "lat": 41.2982, "lon": 69.3245},
    "olmazor": {"name": "Toshkent, Olmazor tumani", "name_ru": "Ташкент, Алмазарский р-н", "lat": 41.3541, "lon": 69.2214},
    "shayxontohur": {"name": "Toshkent, Shayxontohur tumani", "name_ru": "Ташкент, Шайхантахурский р-н", "lat": 41.3215, "lon": 69.2412},
    "uchtepa": {"name": "Toshkent, Uchtepa tumani", "name_ru": "Ташкент, Учтепинский р-н", "lat": 41.2954, "lon": 69.1784},
    "bektemir": {"name": "Toshkent, Bektemir tumani", "name_ru": "Ташкент, Бектемирский р-н", "lat": 41.2085, "lon": 69.3354},
    "yangihayot": {"name": "Toshkent, Yangihayot tumani", "name_ru": "Ташкент, Янгихаётский р-н", "lat": 41.1945, "lon": 69.2154},
    "toshkent": {"name": "Toshkent (Markaz)", "name_ru": "Ташкент (Центр)", "lat": 41.2995, "lon": 69.2401},

    # Boshqa viloyat markazlari
    "samarqand": {"name": "Samarqand shahri", "name_ru": "г. Самарканд", "lat": 39.6542, "lon": 66.9597},
    "buxoro": {"name": "Buxoro shahri", "name_ru": "г. Бухара", "lat": 39.7681, "lon": 64.4556},
    "andijon": {"name": "Andijon shahri", "name_ru": "г. Андижан", "lat": 40.7821, "lon": 72.3442},
    "fargona": {"name": "Farg'ona shahri", "name_ru": "г. Фергана", "lat": 40.3842, "lon": 71.7843},
    "namangan": {"name": "Namangan shahri", "name_ru": "г. Наманган", "lat": 40.9983, "lon": 71.6726},
    "qarshi": {"name": "Qarshi shahri", "name_ru": "г. Карши", "lat": 38.8606, "lon": 65.7891},
    "nukus": {"name": "Nukus shahri", "name_ru": "г. Нукус", "lat": 42.4619, "lon": 59.6166},
    "navoiy": {"name": "Navoiy shahri", "name_ru": "г. Навои", "lat": 40.1031, "lon": 65.3739},
    "urganch": {"name": "Urganch shahri", "name_ru": "г. Ургенч", "lat": 41.5562, "lon": 60.6313},
    "termiz": {"name": "Termiz shahri", "name_ru": "г. Термез", "lat": 37.2242, "lon": 67.2783},
    "jizzax": {"name": "Jizzax shahri", "name_ru": "г. Джизак", "lat": 40.1158, "lon": 67.8422},
    "guliston": {"name": "Guliston shahri", "name_ru": "г. Гулистан", "lat": 40.4897, "lon": 68.7844},
    "chirchiq": {"name": "Chirchiq shahri", "name_ru": "г. Чирчик", "lat": 41.4689, "lon": 69.5822},
    "yangiyol": {"name": "Yangiyo'l shahri", "name_ru": "г. Янгиюль", "lat": 41.1154, "lon": 69.0485},
    "nurafshon": {"name": "Nurafshon shahri", "name_ru": "г. Нурафшан", "lat": 41.0425, "lon": 69.3541},
}


def get_air_inline_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Havo sifati natijasi ostidagi inline boshqaruv tugmalari."""
    if lang == "ru":
        kb = [
            [
                InlineKeyboardButton("🔄 Обновить", callback_data="air_refresh"),
                InlineKeyboardButton("🏙 Районы Ташкента", callback_data="air_districts"),
            ],
            [
                InlineKeyboardButton("🇺🇿 Другие города", callback_data="air_cities"),
                InlineKeyboardButton("📍 Как отправить локацию", callback_data="air_loc_help"),
            ],
        ]
    else:
        kb = [
            [
                InlineKeyboardButton("🔄 Yangilash", callback_data="air_refresh"),
                InlineKeyboardButton("🏙 Toshkent tumanlari", callback_data="air_districts"),
            ],
            [
                InlineKeyboardButton("🇺🇿 Boshqa shaharlar", callback_data="air_cities"),
                InlineKeyboardButton("📍 Lokatsiya yuborish", callback_data="air_loc_help"),
            ],
        ]
    return InlineKeyboardMarkup(kb)


def get_districts_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Toshkent tumanlarini tanlash inline menyusi."""
    kb = [
        [
            InlineKeyboardButton("Chilonzor", callback_data="loc_chilonzor"),
            InlineKeyboardButton("Yunusobod", callback_data="loc_yunusobod"),
        ],
        [
            InlineKeyboardButton("Mirzo Ulug'bek", callback_data="loc_mirzo_ulugbek"),
            InlineKeyboardButton("Mirobod", callback_data="loc_mirobod"),
        ],
        [
            InlineKeyboardButton("Yakkasaroy", callback_data="loc_yakkasaroy"),
            InlineKeyboardButton("Sergeli", callback_data="loc_sergeli"),
        ],
        [
            InlineKeyboardButton("Yashnobod", callback_data="loc_yashnobod"),
            InlineKeyboardButton("Olmazor", callback_data="loc_olmazor"),
        ],
        [
            InlineKeyboardButton("Shayxontohur", callback_data="loc_shayxontohur"),
            InlineKeyboardButton("Uchtepa", callback_data="loc_uchtepa"),
        ],
        [
            InlineKeyboardButton("Bektemir", callback_data="loc_bektemir"),
            InlineKeyboardButton("Yangihayot", callback_data="loc_yangihayot"),
        ],
        [
            InlineKeyboardButton("🔙 " + ("Назад" if lang == "ru" else "Orqaga"), callback_data="air_back"),
        ],
    ]
    return InlineKeyboardMarkup(kb)


def get_cities_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """O'zbekistonning boshqa shaharlari inline menyusi."""
    kb = [
        [
            InlineKeyboardButton("Toshkent (Markaz)", callback_data="loc_toshkent"),
            InlineKeyboardButton("Samarqand", callback_data="loc_samarqand"),
        ],
        [
            InlineKeyboardButton("Buxoro", callback_data="loc_buxoro"),
            InlineKeyboardButton("Andijon", callback_data="loc_andijon"),
        ],
        [
            InlineKeyboardButton("Farg'ona", callback_data="loc_fargona"),
            InlineKeyboardButton("Namangan", callback_data="loc_namangan"),
        ],
        [
            InlineKeyboardButton("Qarshi", callback_data="loc_qarshi"),
            InlineKeyboardButton("Nukus", callback_data="loc_nukus"),
        ],
        [
            InlineKeyboardButton("Navoiy", callback_data="loc_navoiy"),
            InlineKeyboardButton("Urganch (Xiva)", callback_data="loc_urganch"),
        ],
        [
            InlineKeyboardButton("Termiz", callback_data="loc_termiz"),
            InlineKeyboardButton("Jizzax", callback_data="loc_jizzax"),
        ],
        [
            InlineKeyboardButton("Guliston", callback_data="loc_guliston"),
            InlineKeyboardButton("Chirchiq", callback_data="loc_chirchiq"),
        ],
        [
            InlineKeyboardButton("🔙 " + ("Назад" if lang == "ru" else "Orqaga"), callback_data="air_back"),
        ],
    ]
    return InlineKeyboardMarkup(kb)


def get_main_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Asosiy menyu klaviaturasi (Telegram Desktop va Mobile uchun birdek ishlaydi)."""
    if lang == "ru":
        kb = [
            [KeyboardButton("📍 Качество воздуха сейчас")],
            [KeyboardButton("👤 Мой профиль"), KeyboardButton("🔔 Подписка")],
            [KeyboardButton("📈 Прогноз на 24ч"), KeyboardButton("📊 Недельный отчет (График)")],
            [KeyboardButton("🛡 Маски и Фильтры (RAG)"), KeyboardButton("🌐 Сменить язык (UZ/RU)")],
        ]
    else:
        kb = [
            [KeyboardButton("📍 Hozirgi havo (Joylashuv)")],
            [KeyboardButton("👤 Mening profilim"), KeyboardButton("🔔 Obuna bo'lish")],
            [KeyboardButton("📈 24 soatlik prognoz"), KeyboardButton("📊 Haftalik hisobot (Grafik)")],
            [KeyboardButton("🛡 Niqob va Filtrlar (RAG)"), KeyboardButton("🌐 Tilni o'zgartirish (UZ/RU)")],
        ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start buyrug'i."""
    user = update.effective_user
    u_data = upsert_user(user.id, user.username or "", user.first_name or "", language="uz")
    lang = u_data.get("language", "uz")

    if lang == "ru":
        welcome = (
            f"👋 Здравствуйте, {user.first_name}!\n\n"
            f"Я — **Интеллектуальный агент по качеству воздуха и здоровью (Ташкент)**.\n\n"
            f"🌟 **Что я умею:**\n"
            f"• 📍 Определение PM2.5, PM10 и AQI по вашей геолокации\n"
            f"• 👤 Индивидуальные рекомендации (для детей, при астме, спортсменам)\n"
            f"• 🔔 Авто-оповещения при превышении опасного порога загрязнения\n"
            f"• 📈 Прогноз воздуха и погоды на 24 часа\n"
            f"• 📊 График динамики воздуха за неделю\n"
            f"• 🛡 Консультации по маскам N95, фильтрам HEPA и проветриванию\n"
            f"• 📸 Анализ смога по фото неба\n\n"
            f"Нажмите кнопку ниже или отправьте геолокацию!"
        )
    else:
        welcome = (
            f"👋 Assalomu alaykum, {user.first_name}!\n\n"
            f"Men — **Toshkent shahri havo sifati va salomatlik bo'yicha shaxsiy AI agentingizman**.\n\n"
            f"🌟 **Mening imkoniyatlarim:**\n"
            f"• 📍 Eng yaqin sensordan real-vaqtda PM2.5, PM10 va AQI darajasini ko'rsatish\n"
            f"• 👤 Shaxsiy profil (bolalar, astma, sportchilar, keksalar) uchun maxsus tavsiyalar\n"
            f"• 🔔 Havo ifloslanganda avtomatik ogohlantirish (obuna)\n"
            f"• 📈 24 soatlik havo sifati va ob-havo prognozi\n"
            f"• 📊 7 kunlik AQI grafigi va tahliliy hisoboti\n"
            f"• 🛡 N95 niqoblar, HEPA filtrlar va shamollatish bo'yicha RAG bilimlari\n"
            f"• 📸 Osmon yoki tuman rasmini vizual baholash (Vision)\n\n"
            f"Pastdagi tugmalar orqali xizmatlardan foydalanishingiz mumkin:"
        )

    await update.message.reply_text(welcome, reply_markup=get_main_keyboard(lang), parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam buyrug'i."""
    user = update.effective_user
    u_data = get_user(user.id) or {}
    lang = u_data.get("language", "uz")

    if lang == "ru":
        text = (
            "📖 **Команды бота:**\n\n"
            "• /start — Перезапуск меню\n"
            "• /air — Качество воздуха сейчас\n"
            "• /profile — Настройка профиля (дети, астма, спорт)\n"
            "• /subscribe — Оформить оповещения\n"
            "• /forecast — Прогноз на 24 часа\n"
            "• /report — График воздуха за 7 дней\n"
            "• /rag — Справка по маскам N95 и HEPA\n"
            "• /lang — Сменить язык интерфейса\n"
            "• Отправьте фото неба — для визуальной оценки смога"
        )
    else:
        text = (
            "📖 **Bot buyruqlari:**\n\n"
            "• /start — Menuni qayta ishga tushirish\n"
            "• /air — Hozirgi havo sifati (Toshkent)\n"
            "• /profile — Shaxsiy profilni sozlash (bola, astma, sport)\n"
            "• /subscribe — Chegara oshganda ogohlantirishga obuna\n"
            "• /forecast — 24 soatlik prognoz\n"
            "• /report — 7 kunlik grafik hisobot\n"
            "• /rag — Niqoblar va filtrlar bo'yicha yo'riqnoma\n"
            "• /lang — Tilni o'zgartirish (UZ/RU)\n"
            "• Osmon rasmini yuboring — tutun va tuman tahlili uchun"
        )

    await update.message.reply_text(text, parse_mode="Markdown")


async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi yuborgan geolokatsiyani qabul qilish (F1)."""
    loc = update.message.location
    user = update.effective_user
    u_data = get_user(user.id) or {}
    lang = u_data.get("language", "uz")

    # Foydalanuvchi yuborgan koordinatani saqlash
    set_user_location(user.id, loc.latitude, loc.longitude, "Geolokatsiya")

    loading_text = "🔄 Eng yaqin sensor ma'lumotlari yuklanmoqda..." if lang == "uz" else "🔄 Определение качества воздуха..."
    loading_msg = await update.message.reply_text(loading_text)
    res = agent.handle_location_query(loc.latitude, loc.longitude, user_id=user.id, lang=lang)
    await loading_msg.delete()
    await update.message.reply_text(
        res["formatted_message"],
        reply_markup=get_air_inline_keyboard(lang),
        parse_mode="Markdown",
    )


async def air_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hozirgi joylashuv bo'yicha havo sifati (F1)."""
    user = update.effective_user
    u_data = get_user(user.id) or {}
    lang = u_data.get("language", "uz")

    lat, lon, loc_name = get_user_location(user.id)

    loading_text = "🔄 Havo sifati aniqlanmoqda..." if lang == "uz" else "🔄 Определение качества воздуха..."
    loading_msg = await update.message.reply_text(loading_text)
    res = agent.handle_location_query(lat, lon, user_id=user.id, lang=lang)
    await loading_msg.delete()
    await update.message.reply_text(
        res["formatted_message"],
        reply_markup=get_air_inline_keyboard(lang),
        parse_mode="Markdown",
    )


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Profilni sozlash menyusi (F2)."""
    user = update.effective_user
    u_data = get_user(user.id) or {}
    lang = u_data.get("language", "uz")
    cur_prof = get_user_profile(user.id).get("profile_type", "umumiy")

    if lang == "ru":
        text = (
            f"👤 **Ваш текущий профиль:** {cur_prof.capitalize()}\n\n"
            f"Выберите подходящую категорию здоровья, чтобы получать персональные рекомендации:"
        )
        keyboard = [
            [InlineKeyboardButton("👶 Дети (0-14 лет)", callback_data="prof_bola")],
            [InlineKeyboardButton("🫁 Астма / Легкие", callback_data="prof_astma")],
            [InlineKeyboardButton("🏃‍♂️ Спортсмен", callback_data="prof_sport")],
            [InlineKeyboardButton("❤️ Сердечно-сосудистые", callback_data="prof_yurak")],
            [InlineKeyboardButton("🧓 Пожилые люди (65+)", callback_data="prof_keksa")],
            [InlineKeyboardButton("🏫 Школа / Учреждение", callback_data="prof_maktab")],
            [InlineKeyboardButton("👥 Общее население", callback_data="prof_umumiy")],
        ]
    else:
        text = (
            f"👤 **Sizning joriy profilingiz:** {cur_prof.capitalize()}\n\n"
            f"O'zingizga mos sog'liq toifasini tanlang. Agent tavsiyalarni aynan shu profilga moslashtiradi:"
        )
        keyboard = [
            [InlineKeyboardButton("👶 Bolalar (0-14 yosh)", callback_data="prof_bola")],
            [InlineKeyboardButton("🫁 Astma / Nafas yo'llari", callback_data="prof_astma")],
            [InlineKeyboardButton("🏃‍♂️ Sportchi / Faol mashg'ulot", callback_data="prof_sport")],
            [InlineKeyboardButton("❤️ Yurak-qon tomir", callback_data="prof_yurak")],
            [InlineKeyboardButton("🧓 Keksalar (65+ yosh)", callback_data="prof_keksa")],
            [InlineKeyboardButton("🏫 Maktab / Bog'cha", callback_data="prof_maktab")],
            [InlineKeyboardButton("👥 Umumiy aholi", callback_data="prof_umumiy")],
        ]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obuna bo'lish menyusi (F3)."""
    user = update.effective_user
    u_data = get_user(user.id) or {}
    lang = u_data.get("language", "uz")

    subs = get_user_subscriptions(user.id)
    sub_info = ""
    if subs:
        sub_info = "\n📌 *Mavjud faol obunangiz:* " + ", ".join([f"AQI {s['threshold']}" for s in subs])

    if lang == "ru":
        text = (
            f"🔔 **Настройка автоматических оповещений**\n\n"
            f"Бот проверяет воздух каждые 30 минут. "
            f"Выберите порог AQI, при превышении которого вам придет тревожное сообщение:{sub_info}"
        )
        keyboard = [
            [InlineKeyboardButton("🟡 AQI 50 (Чувствительный)", callback_data="sub_50")],
            [InlineKeyboardButton("🟠 AQI 100 (Умеренный)", callback_data="sub_100")],
            [InlineKeyboardButton("🔴 AQI 150 (Опасный)", callback_data="sub_150")],
            [InlineKeyboardButton("🟣 AQI 200 (Критический)", callback_data="sub_200")],
        ]
    else:
        text = (
            f"🔔 **Havo ifloslanishidan avtomatik ogohlantirish (Obuna)**\n\n"
            f"Agent har 30 daqiqada havoni tekshiradi. "
            f"Qaysi AQI darajasidan oshganda sizga xabar yuborilsin?{sub_info}"
        )
        keyboard = [
            [InlineKeyboardButton("🟡 AQI 50 (O'ta sezgir)", callback_data="sub_50")],
            [InlineKeyboardButton("🟠 AQI 100 (Nozik guruhlar)", callback_data="sub_100")],
            [InlineKeyboardButton("🔴 AQI 150 (Zararli daraja)", callback_data="sub_150")],
            [InlineKeyboardButton("🟣 AQI 200 (Juda xavfli)", callback_data="sub_200")],
        ]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def forecast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """24 soatlik prognoz (F4)."""
    user = update.effective_user
    u_data = get_user(user.id) or {}
    lang = u_data.get("language", "uz")

    loading = await update.message.reply_text("🔄 24 soatlik atmosfera prognozi hisoblanmoqda...")
    res = agent.get_forecast(DEFAULT_LAT, DEFAULT_LON, lang=lang)
    await loading.delete()
    await update.message.reply_text(res["formatted_message"], parse_mode="Markdown")


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Haftalik grafik hisobot (F6)."""
    user = update.effective_user
    u_data = get_user(user.id) or {}
    lang = u_data.get("language", "uz")

    loading = await update.message.reply_text("🔄 7 kunlik havo tahlili va grafik chizilmoqda...")
    res = agent.get_weekly_report(user.id, lat=DEFAULT_LAT, lon=DEFAULT_LON, lang=lang)
    await loading.delete()

    img_path = res.get("image_path")
    if img_path and os.path.exists(img_path):
        with open(img_path, "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=res["formatted_message"],
                parse_mode="Markdown",
            )
    else:
        await update.message.reply_text(res["formatted_message"], parse_mode="Markdown")


async def rag_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """RAG: Niqoblar va filtrlar bo'yicha umumiy qo'llanma (F5)."""
    user = update.effective_user
    u_data = get_user(user.id) or {}
    lang = u_data.get("language", "uz")

    res = agent.ask_rag_or_health("Qaysi niqob va filtr yaxshi?", lang=lang)
    await update.message.reply_text(res["answer"], parse_mode="Markdown")


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tilni tanlash menyusi."""
    keyboard = [
        [InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
    ]
    await update.message.reply_text(
        "🌐 Tilni tanlang / Выберите язык:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rasm yuklanganda Vision tahlil (F7)."""
    user = update.effective_user
    u_data = get_user(user.id) or {}
    lang = u_data.get("language", "uz")

    loading = await update.message.reply_text("🔄 Fotosurat qabul qilindi. Ufq va tutun qatlami tahlil qilinmoqda...")

    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    temp_dir = Path("reports")
    temp_dir.mkdir(exist_ok=True)
    file_path = temp_dir / f"user_sky_{user.id}_{int(datetime.now().timestamp())}.jpg"
    await photo_file.download_to_drive(str(file_path))

    res = agent.analyze_sky_image(str(file_path), lang=lang)
    await loading.delete()
    await update.message.reply_text(res["formatted_message"], parse_mode="Markdown")


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha matnli xabarlarni qayta ishlash."""
    text = update.message.text.strip()
    user = update.effective_user
    u_data = get_user(user.id) or {}
    lang = u_data.get("language", "uz")

    # Matnli tugmalar tekshiruvi
    if text in [
        "📍 Hozirgi havo (Joylashuv)",
        "📍 Hozirgi havo",
        "📍 Hozirgi havo sifati",
        "📍 Качество воздуха сейчас",
        "📍 Качество воздуха (Локация)",
        "/air",
    ]:
        await air_command(update, context)
        return
    elif text in ["👤 Mening profilim", "👤 Мой профиль"]:
        await profile_command(update, context)
        return
    elif text in ["🔔 Obuna bo'lish", "🔔 Подписка"]:
        await subscribe_command(update, context)
        return
    elif text in ["📈 24 soatlik prognoz", "📈 Прогноз на 24ч"]:
        await forecast_command(update, context)
        return
    elif text in ["📊 Haftalik hisobot (Grafik)", "📊 Недельный отчет (График)"]:
        await report_command(update, context)
        return
    elif text in ["🛡 Niqob va Filtrlar (RAG)", "🛡 Маски и Фильтры (RAG)"]:
        await rag_command(update, context)
        return
    elif text in ["🌐 Tilni o'zgartirish (UZ/RU)", "🌐 Сменить язык (UZ/RU)"]:
        await lang_command(update, context)
        return

    # Foydalanuvchi tuman yoki shahar nomini yozgan bo'lsa (masalan: Chilonzor, Samarqand, Yunusobod...)
    clean_text = text.lower().replace("'", "").replace("‘", "").replace("`", "").strip()
    for l_key, l_info in POPULAR_LOCATIONS.items():
        key_clean = l_key.replace("'", "").replace("‘", "").replace("`", "")
        # Aniq moslik yoki so'z sifatida kiritilgan bo'lsa
        if clean_text == key_clean or (len(clean_text) >= 4 and clean_text == key_clean.split("_")[0]):
            name = l_info["name_ru"] if lang == "ru" else l_info["name"]
            set_user_location(user.id, l_info["lat"], l_info["lon"], name)
            loading_msg = await update.message.reply_text(
                f"🔄 {name} bo'yicha havo sifati aniqlanmoqda..." if lang == "uz"
                else f"🔄 Определение качества воздуха ({name})..."
            )
            res = agent.handle_location_query(l_info["lat"], l_info["lon"], user_id=user.id, lang=lang)
            await loading_msg.delete()
            await update.message.reply_text(
                res["formatted_message"],
                reply_markup=get_air_inline_keyboard(lang),
                parse_mode="Markdown",
            )
            return

    # Savol-javob: Guardrail yoki RAG yoki LLM
    res = agent.ask_rag_or_health(text, lang=lang)
    await update.message.reply_text(res["answer"], parse_mode="Markdown")


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline tugmalar callbacklarini boshqarish."""
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user
    u_data = get_user(user.id) or {}
    lang = u_data.get("language", "uz")

    if data.startswith("prof_"):
        prof_type = data.replace("prof_", "")
        res = agent.set_profile(user.id, prof_type, lang=lang)
        await query.edit_message_text(res["message"], parse_mode="Markdown")

    elif data.startswith("sub_"):
        threshold = int(data.replace("sub_", ""))
        lat, lon, _ = get_user_location(user.id)
        res = agent.create_subscription(
            user_id=user.id,
            lat=lat,
            lon=lon,
            threshold=threshold,
            location_name="Tanlangan hudud",
            lang=lang,
        )
        await query.edit_message_text(res["message"], parse_mode="Markdown")

    elif data.startswith("lang_"):
        new_lang = data.replace("lang_", "")
        set_user_language(user.id, new_lang)
        msg = "🇺🇿 Til o'zbekchaga o'zgartirildi!" if new_lang == "uz" else "🇷🇺 Язык успешно изменен на русский!"
        await query.edit_message_text(msg)
        await query.message.reply_text("Menyu:", reply_markup=get_main_keyboard(new_lang))

    elif data == "air_refresh":
        lat, lon, _ = get_user_location(user.id)
        res = agent.handle_location_query(lat, lon, user_id=user.id, lang=lang)
        try:
            await query.edit_message_text(
                res["formatted_message"],
                reply_markup=get_air_inline_keyboard(lang),
                parse_mode="Markdown",
            )
        except Exception:
            pass

    elif data == "air_districts":
        title = "🏙 **Toshkent tumanlaridan birini tanlang:**" if lang == "uz" else "🏙 **Выберите район Ташкента:**"
        await query.edit_message_text(title, reply_markup=get_districts_keyboard(lang), parse_mode="Markdown")

    elif data == "air_cities":
        title = "🇺🇿 **Shahar yoki viloyat markazini tanlang:**" if lang == "uz" else "🇺🇿 **Выберите город:**"
        await query.edit_message_text(title, reply_markup=get_cities_keyboard(lang), parse_mode="Markdown")

    elif data == "air_back":
        lat, lon, _ = get_user_location(user.id)
        res = agent.handle_location_query(lat, lon, user_id=user.id, lang=lang)
        try:
            await query.edit_message_text(
                res["formatted_message"],
                reply_markup=get_air_inline_keyboard(lang),
                parse_mode="Markdown",
            )
        except Exception:
            pass

    elif data.startswith("loc_"):
        loc_key = data.replace("loc_", "")
        if loc_key in POPULAR_LOCATIONS:
            loc_info = POPULAR_LOCATIONS[loc_key]
            lat = loc_info["lat"]
            lon = loc_info["lon"]
            name = loc_info.get("name_ru" if lang == "ru" else "name", loc_info["name"])
            set_user_location(user.id, lat, lon, name)

            res = agent.handle_location_query(lat, lon, user_id=user.id, lang=lang)
            try:
                await query.edit_message_text(
                    res["formatted_message"],
                    reply_markup=get_air_inline_keyboard(lang),
                    parse_mode="Markdown",
                )
            except Exception:
                pass

    elif data == "air_loc_help":
        if lang == "ru":
            help_loc = (
                "📍 **Как отправить точную геолокацию:**\n\n"
                "💻 **В Telegram Desktop (на компьютере):**\n"
                "1. Нажмите на значок скрепки (📎) слева от поля ввода текста.\n"
                "2. Выберите **Локация (Location)**.\n"
                "3. Отметьте точку на карте и нажмите **Отправить**.\n\n"
                "📱 **На смартфоне:**\n"
                "1. Нажмите скрепку (📎) ➡️ **Геопозиция**.\n"
                "2. Выберите **Отправить мою геопозицию**.\n\n"
                "💡 *Также вы можете просто написать в чат название района или города (например: «Чиланзар» или «Самарканд»)!*"
            )
        else:
            help_loc = (
                "📍 **Aniq geolokatsiyani yuborish yo'riqnomasi:**\n\n"
                "💻 **Telegram Desktop (Kompyuterda):**\n"
                "1. Xabar yozish maydoni chapidagi **qisqich (📎)** belgisini bosing.\n"
                "2. **Location (Joylashuv)** bo'limini tanlang.\n"
                "3. Xaritadan o'zingiz turgan joyni belgilab, **Send (Yuborish)** tugmasini bosing.\n\n"
                "📱 **Smartfonda:**\n"
                "1. **Qisqich (📎)** belgisini bosing ➡️ **Geopozitsiya / Joylashuv**.\n"
                "2. **Hozirgi joylashuvimni yuborish** tugmasini bosing.\n\n"
                "💡 *Shuningdek, shunchaki tuman yoki shahar nomini yozib yuborsangiz ham bo'ladi (masalan: «Chilonzor» yoki «Samarqand»)!*"
            )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 " + ("Назад" if lang == "ru" else "Orqaga"), callback_data="air_back")]])
        await query.edit_message_text(help_loc, reply_markup=back_kb, parse_mode="Markdown")


def create_bot_application() -> Application:
    """Telegram bot ilovasini yaratish va handlerlarni ro'yxatga olish."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN topilmadi! Iltimos .env faylini tekshiring.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("air", air_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("subscribe", subscribe_command))
    app.add_handler(CommandHandler("forecast", forecast_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("rag", rag_command))
    app.add_handler(CommandHandler("lang", lang_command))

    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(CallbackQueryHandler(callback_query_handler))

    return app


async def run_bot_with_scheduler():
    """Bot va APScheduler ni birga ishga tushirish."""
    app = create_bot_application()

    # Callback: Scheduler orqali xabar yuborish
    async def send_alert_to_telegram(user_id: int, message: str):
        try:
            await app.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Xabar yuborishda xato: {e}")

    monitor = SubscriptionMonitor(notify_callback=send_alert_to_telegram)
    monitor.start()

    logger.info("Bot va APScheduler ishga tushmoqda...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    # Doimiy ishlash
    try:
        import asyncio
        while True:
            await asyncio.sleep(3600)
    finally:
        monitor.stop()
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_bot_with_scheduler())
