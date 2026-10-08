"""
Konfiguratsiya moduli (TZ-06: Havo sifati va sog'liq agenti)
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# API Kalitlar
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY", "").strip()

# Baza va hisobotlar yo'li
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "air_quality.db"))
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)

# Birlamchi koordinatalar (Toshkent markazi)
DEFAULT_LAT = float(os.getenv("DEFAULT_LAT", "41.2995"))
DEFAULT_LON = float(os.getenv("DEFAULT_LON", "69.2401"))

# Tekshiruv intervali
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "30"))

# Sensor ma'lumoti eskirgan hisoblanadigan vaqt chegarasi (daqiqa)
STALE_SENSOR_MINUTES = 120  # 2 soat

# Qo'llab-quvvatlanadigan tillar
SUPPORTED_LANGUAGES = ["uz", "ru"]
DEFAULT_LANG = "uz"

# Qo'llab-quvvatlanadigan profillar
PROFILES = {
    "bola": {"uz": "Bolalar (0-14 yosh)", "ru": "Дети (0-14 лет)"},
    "astma": {"uz": "Astma / Nafas yo'llari kasalliklari", "ru": "Астма / Болезни дыхательных путей"},
    "yurak": {"uz": "Yurak-qon tomir kasalliklari", "ru": "Сердечно-сосудистые заболевания"},
    "sport": {"uz": "Sportchi / Faol mashg'ulot", "ru": "Спортсмен / Активные тренировки"},
    "keksa": {"uz": "Keksalar (65+ yosh)", "ru": "Пожилые люди (65+ лет)"},
    "maktab": {"uz": "Maktab / Ta'lim muassasasi", "ru": "Школа / Образовательное учреждение"},
    "umumiy": {"uz": "Umumiy shahar aholisi", "ru": "Общее население"},
}

# Standart ogohlantirish chegaralari
DEFAULT_ALERT_THRESHOLDS = [50, 100, 150, 200]
