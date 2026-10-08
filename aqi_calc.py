"""
AQI (Air Quality Index) hisoblash va tasniflash moduli.
US EPA (AQSh Atrof-muhitni muhofaza qilish agentligi) rasmiy standarti asosida.
"""
from typing import Dict, Any, Tuple, Optional

# US EPA PM2.5 chegaralari (ug/m3) -> AQI
PM25_BREAKPOINTS = [
    (0.0, 12.0, 0, 50),
    (12.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 150.4, 151, 200),
    (150.5, 250.4, 201, 300),
    (250.5, 350.4, 301, 400),
    (350.5, 500.4, 401, 500),
]

# US EPA PM10 chegaralari (ug/m3) -> AQI
PM10_BREAKPOINTS = [
    (0, 54, 0, 50),
    (55, 154, 51, 100),
    (155, 254, 101, 150),
    (255, 354, 151, 200),
    (355, 424, 201, 300),
    (425, 504, 301, 400),
    (505, 604, 401, 500),
]

# AQI darajalari tafsilotlari
AQI_LEVELS = [
    {
        "key": "good",
        "min": 0,
        "max": 50,
        "color": "#00E400",
        "emoji": "🟢",
        "title": {"uz": "Yaxshi", "ru": "Хорошо"},
        "desc": {
            "uz": "Havo sifati toza, xavf mavjud emas. Ochiq havoda erkin sayr qilish va mashq qilish mumkin.",
            "ru": "Качество воздуха отличное, рисков нет. Отлично для прогулок и активного отдыха.",
        },
    },
    {
        "key": "moderate",
        "min": 51,
        "max": 100,
        "color": "#FFFF00",
        "emoji": "🟡",
        "title": {"uz": "O'rtacha (Qoniqarli)", "ru": "Умеренно"},
        "desc": {
            "uz": "Havo sifati maqbul. Biroq, juda sezgir insonlarda yengil noqulaylik sezilishi mumkin.",
            "ru": "Качество воздуха приемлемое. У особо чувствительных людей может быть легкий дискомфорт.",
        },
    },
    {
        "key": "unhealthy_sensitive",
        "min": 101,
        "max": 150,
        "color": "#FF7E00",
        "emoji": "🟠",
        "title": {"uz": "Nozik guruhlar uchun zararli", "ru": "Вредно для уязвимых групп"},
        "desc": {
            "uz": "Bolalar, keksalar, astma va yurak kasalliklari borlar tashqi faollikni cheklashi kerak.",
            "ru": "Дети, пожилые люди и лица с астмой/сердечными заболеваниями должны ограничить нагрузку на улице.",
        },
    },
    {
        "key": "unhealthy",
        "min": 151,
        "max": 200,
        "color": "#FF0000",
        "emoji": "🔴",
        "title": {"uz": "Zararli", "ru": "Вредно для всех"},
        "desc": {
            "uz": "Barcha shahar aholisi uchun zararli. Tashqi faoliyatni kamaytiring, bolalarni ko'chaga chiqarmang.",
            "ru": "Вредно для всех жителей. Рекомендуется оставаться в помещении, закрыть окна.",
        },
    },
    {
        "key": "very_unhealthy",
        "min": 201,
        "max": 300,
        "color": "#8F3F97",
        "emoji": "🟣",
        "title": {"uz": "Juda zararli", "ru": "Очень вредно"},
        "desc": {
            "uz": "Sog'liq uchun jiddiy xavf! Ochiq havoda bo'lishdan mutlaqo saqlaning, N95 niqob va havo tozalagich zarur.",
            "ru": "Серьезный риск для здоровья! Избегайте выхода на улицу, используйте фильтры HEPA и маски N95.",
        },
    },
    {
        "key": "hazardous",
        "min": 301,
        "max": 9999,
        "color": "#7E0023",
        "emoji": "🟤",
        "title": {"uz": "Favqulodda xavfli", "ru": "Опасно (Чрезвычайно)"},
        "desc": {
            "uz": "Favqulodda ifloslanish! Tashqariga chiqish qat'iyan taqiqlanadi. O'tkir respirator alomatlar xavfi yuqori.",
            "ru": "Критическое загрязнение! Полный запрет на физическую активность на воздухе.",
        },
    },
]


def calculate_aqi_from_concentration(c: float, breakpoints: list) -> int:
    """
    US EPA tenglamasi:
    Ip = [(Ihi - Ilo) / (BPhi - BPlo)] * (Cp - BPlo) + Ilo
    """
    if c is None or c < 0:
        return 0
    
    # Eng yuqori diapazondan oshsa
    if c > breakpoints[-1][1]:
        # Ekstrapolyatsiya
        bp = breakpoints[-1]
        aqi = round(((bp[3] - bp[2]) / (bp[1] - bp[0])) * (c - bp[0]) + bp[2])
        return min(aqi, 500)

    for bp_lo, bp_hi, i_lo, i_hi in breakpoints:
        if bp_lo <= c <= bp_hi:
            aqi = round(((i_hi - i_lo) / (bp_hi - bp_lo)) * (c - bp_lo) + i_lo)
            return aqi
            
    return 0


def calculate_aqi(pm25: Optional[float] = None, pm10: Optional[float] = None) -> Tuple[int, str]:
    """
    PM2.5 va PM10 bo'yicha AQI ni hisoblaydi va dominant moddani qaytaradi.
    AQI = max(AQI_PM25, AQI_PM10)
    """
    aqi_pm25 = calculate_aqi_from_concentration(pm25, PM25_BREAKPOINTS) if pm25 is not None else 0
    aqi_pm10 = calculate_aqi_from_concentration(pm10, PM10_BREAKPOINTS) if pm10 is not None else 0

    if aqi_pm25 >= aqi_pm10:
        return aqi_pm25, "PM2.5"
    else:
        return aqi_pm10, "PM10"


def get_aqi_level(aqi: int) -> Dict[str, Any]:
    """AQI qiymati bo'yicha tafsilotlar va rangni qaytaradi."""
    for level in AQI_LEVELS:
        if level["min"] <= aqi <= level["max"]:
            return level
    return AQI_LEVELS[-1]
