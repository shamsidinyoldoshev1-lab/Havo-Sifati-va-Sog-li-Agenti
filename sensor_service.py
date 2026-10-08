"""
Sensor va havo sifati ma'lumotlarini yig'ish xizmati.
Manbalar:
- sensor.community (Ochiq havo sensorlari, SDS011 PM2.5/PM10)
- Open-Meteo Air Quality API (Atmosfera ifloslanishi modeli, bepul va ochiq)
- OpenAQ API (Ixtiyoriy)
"""
import math
import time
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from config import OPENAQ_API_KEY, STALE_SENSOR_MINUTES
from aqi_calc import calculate_aqi, get_aqi_level
from database import save_aqi_history

# Aloqa seansini saqlab qolish uchun umumiy mijoz
_client = httpx.Client(timeout=8.0, follow_redirects=True)
_CACHE: Dict[str, Any] = {}
_CACHE_TTL = 60.0  # 60 soniya

def _get_from_cache(key: str) -> Optional[Any]:
    entry = _CACHE.get(key)
    if entry and time.time() < entry["expires"]:
        return entry["data"]
    return None

def _save_to_cache(key: str, data: Any, ttl: float = _CACHE_TTL):
    _CACHE[key] = {"data": data, "expires": time.time() + ttl}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Ikki nuqta orasidagi masofani (km) hisoblaydi."""
    R = 6371.0  # Yer radiusi (km)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


def parse_iso_or_custom_time(ts_str: str) -> Optional[datetime]:
    """Har xil formatdagi vaqtni datetime obyektiga o'giradi."""
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(ts_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def fetch_sensor_community_stations(lat: float, lon: float, radius_km: float = 30.0) -> List[Dict[str, Any]]:
    """sensor.community dan yaqin-atrofdagi sensorlarni oladi."""
    cache_key = f"sc_{round(lat, 1)}_{round(lon, 1)}_{radius_km}"
    raw_items = _get_from_cache(cache_key)

    if raw_items is None:
        url = f"https://data.sensor.community/airrohr/v1/filter/area={lat},{lon},{radius_km}"
        raw_items = []
        try:
            resp = _client.get(url)
            if resp.status_code == 200:
                raw_items = resp.json()
                _save_to_cache(cache_key, raw_items, ttl=60.0)
        except Exception:
            pass

    stations = []
    now = datetime.now(timezone.utc)

    for item in raw_items:
        sensor = item.get("sensor", {})
        sensor_type = sensor.get("sensor_type", {}).get("name", "")
        loc = item.get("location", {})
        
        try:
            s_lat = float(loc.get("latitude", 0))
            s_lon = float(loc.get("longitude", 0))
        except (ValueError, TypeError):
            continue

        # Faqat zarrachalar (PM) sensorlarini ajratib olish
        vals = {v.get("value_type"): v.get("value") for v in item.get("sensordatavalues", [])}
        pm25_val = vals.get("P2")
        pm10_val = vals.get("P1")

        if pm25_val is None and pm10_val is None:
            continue

        try:
            pm25 = float(pm25_val) if pm25_val is not None else None
            pm10 = float(pm10_val) if pm10_val is not None else None
        except (ValueError, TypeError):
            continue

        ts_str = item.get("timestamp", "")
        ts_dt = parse_iso_or_custom_time(ts_str)
        age_minutes = 9999
        is_stale = True

        if ts_dt:
            age_minutes = int((now - ts_dt).total_seconds() / 60)
            is_stale = age_minutes > STALE_SENSOR_MINUTES

        dist = haversine_distance(lat, lon, s_lat, s_lon)
        aqi, dominant = calculate_aqi(pm25, pm10)

        stations.append({
            "station_id": f"sc_{item.get('id')}",
            "name": f"sensor.community {sensor_type} #{sensor.get('id')}",
            "sensor_type": sensor_type,
            "lat": s_lat,
            "lon": s_lon,
            "distance_km": dist,
            "pm25": pm25,
            "pm10": pm10,
            "aqi": aqi,
            "dominant_pollutant": dominant,
            "timestamp": ts_str,
            "age_minutes": age_minutes,
            "is_stale": is_stale,
            "source": "sensor.community",
            "is_physical": True,
        })

    # Masofa bo'yicha saralash
    stations.sort(key=lambda s: s["distance_km"])
    return stations


def fetch_open_meteo_air_quality(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Open-Meteo Air Quality API dan real-time ma'lumot oladi."""
    cache_key = f"om_{round(lat, 2)}_{round(lon, 2)}"
    cached_val = _get_from_cache(cache_key)
    if cached_val:
        return dict(cached_val)

    url = (
        f"https://air-quality-api.open-meteo.com/v1/air-quality"
        f"?latitude={lat}&longitude={lon}"
        f"&current=pm10,pm2_5,european_aqi,us_aqi,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone"
        f"&hourly=pm10,pm2_5,us_aqi"
        f"&timezone=auto"
    )
    try:
        resp = _client.get(url)
        if resp.status_code == 200:
            data = resp.json()
            curr = data.get("current", {})
            hourly = data.get("hourly", {})
            
            pm25 = curr.get("pm2_5")
            pm10 = curr.get("pm10")
            api_us_aqi = curr.get("us_aqi")

            calculated_aqi, dominant = calculate_aqi(pm25, pm10)
            final_aqi = api_us_aqi if api_us_aqi is not None else calculated_aqi

            station_data = {
                "station_id": f"om_{round(lat, 4)}_{round(lon, 4)}",
                "name": "Open-Meteo Copernicus CAMS (Atmosfera stansiyasi)",
                "lat": lat,
                "lon": lon,
                "distance_km": 0.0,
                "pm25": pm25,
                "pm10": pm10,
                "aqi": final_aqi,
                "dominant_pollutant": dominant,
                "co": curr.get("carbon_monoxide"),
                "no2": curr.get("nitrogen_dioxide"),
                "so2": curr.get("sulphur_dioxide"),
                "o3": curr.get("ozone"),
                "timestamp": curr.get("time", datetime.now().strftime("%Y-%m-%d %H:%M")),
                "is_stale": False,
                "source": "Open-Meteo (Copernicus CAMS)",
                "is_physical": False,
                "hourly": hourly,
            }
            _save_to_cache(cache_key, station_data, ttl=60.0)
            return station_data
    except Exception:
        pass
    return None


def nearest_stations(lat: float, lon: float, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Eng yaqin sensor stansiyalarini qaytaradi (F1 va Tool talabi).
    """
    stations = fetch_sensor_community_stations(lat, lon, radius_km=50.0)
    
    # Doim Open-Meteo model ma'lumotini ham qo'shamiz
    om_station = fetch_open_meteo_air_quality(lat, lon)
    if om_station:
        stations.append(om_station)

    stations.sort(key=lambda s: s["distance_km"])
    return stations[:limit]


def get_air_quality(lat: float, lon: float, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Asosiy Tool: get_air_quality(lat, lon).
    Eng yaqin sensor ma'lumotini oladi.
    Guardrails:
    - Agar sensor ma'lumoti > 2 soat eskirgan yoki yo'q bo'lsa -> 'taxmin' deb belgilaydi
    - Manba va sana har doim ko'rsatiladi
    """
    all_stations = nearest_stations(lat, lon, limit=5)
    
    selected = None
    is_estimate = False
    status_note = ""

    # 1. Yaqin va yangi fizik sensorni qidirish (< 25km va < 2 soat)
    for st in all_stations:
        if st.get("is_physical") and not st.get("is_stale") and st.get("distance_km", 999) <= 25.0:
            selected = st
            status_note = "Haqiqiy fizik sensor (Jonli o'lchov)"
            break

    # 2. Agar yangi fizik sensor bo'lmasa, Open-Meteo atmosfera modeli
    if not selected:
        for st in all_stations:
            if not st.get("is_physical"):
                selected = st
                status_note = "Atmosfera modeli (Open-Meteo CAMS)"
                break

    # 3. Agar faqat eskirgan sensor bo'lsa
    if not selected and all_stations:
        selected = all_stations[0]
        if selected.get("is_stale"):
            is_estimate = True
            status_note = "⚠️ Diqqat: Sensor ma'lumoti eskirgan (>2 soat). Ko'rsatkich taxminiy."

    # 4. Agar umuman internet/stansiya topilmasa (Zaxira mock)
    if not selected:
        is_estimate = True
        selected = {
            "station_id": "fallback_tashkent",
            "name": "Toshkent shahar markaziy stansiyasi (Zaxira hisob-kitob)",
            "lat": lat,
            "lon": lon,
            "distance_km": 0.0,
            "pm25": 14.5,
            "pm10": 28.0,
            "aqi": 55,
            "dominant_pollutant": "PM2.5",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "is_stale": True,
            "source": "Zaxira hisob-kitob (Oflayn)",
            "is_physical": False,
        }
        status_note = "⚠️ Diqqat: Jonli sensorga ulanib bo'lmadi. Ko'rsatkich taxminiy."

    aqi = selected.get("aqi", 50)
    level_info = get_aqi_level(aqi)

    result = {
        "aqi": aqi,
        "pm25": selected.get("pm25"),
        "pm10": selected.get("pm10"),
        "dominant_pollutant": selected.get("dominant_pollutant", "PM2.5"),
        "level": level_info["key"],
        "level_title": level_info["title"],
        "level_emoji": level_info["emoji"],
        "level_color": level_info["color"],
        "station_name": selected.get("name"),
        "station_id": selected.get("station_id"),
        "distance_km": selected.get("distance_km", 0.0),
        "timestamp": selected.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M")),
        "source": selected.get("source", "sensor.community / Open-Meteo"),
        "is_estimate": is_estimate or (not selected.get("is_physical")),
        "status_note": status_note,
        "lat": lat,
        "lon": lon,
    }

    # Baza tarixiga yozish
    save_aqi_history(
        lat=lat,
        lon=lon,
        aqi=aqi,
        pm25=result["pm25"] or 0.0,
        pm10=result["pm10"] or 0.0,
        category=level_info["key"],
        source=result["source"],
        user_id=user_id,
    )

    return result
