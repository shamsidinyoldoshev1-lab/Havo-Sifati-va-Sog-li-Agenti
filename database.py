"""
SQLite ma'lumotlar bazasi boshqaruvi.
Users, Profiles, Subscriptions, AQI History, Alert Logs jadvallari.
"""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from config import DATABASE_PATH, DEFAULT_LAT, DEFAULT_LON


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Baza jadvallarini yaratish."""
    conn = get_connection()
    cursor = conn.cursor()

    # Foydalanuvchilar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            language TEXT DEFAULT 'uz',
            last_lat REAL,
            last_lon REAL,
            last_location_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Mavjud bazalar uchun yangi ustunlarni qo'shish
    for col_name, col_type in [("last_lat", "REAL"), ("last_lon", "REAL"), ("last_location_name", "TEXT")]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass

    # Shaxsiy sog'liq profillari
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            profile_type TEXT DEFAULT 'umumiy',
            notes TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # Obunalar jadvali (AQI monitoring)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            location_name TEXT DEFAULT 'Toshkent',
            threshold INTEGER DEFAULT 100,
            is_active INTEGER DEFAULT 1,
            last_notified_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # AQI o'lchovlari tarixi
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aqi_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            aqi INTEGER NOT NULL,
            pm25 REAL,
            pm10 REAL,
            category TEXT,
            source TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Yuborilgan ogohlantirishlar jurnali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alert_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscription_id INTEGER,
            user_id INTEGER NOT NULL,
            aqi INTEGER NOT NULL,
            threshold INTEGER NOT NULL,
            message TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# --- Foydalanuvchilar ---

def upsert_user(user_id: int, username: str = "", first_name: str = "", language: str = "uz") -> Dict[str, Any]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO users (user_id, username, first_name, language)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            language = COALESCE(users.language, excluded.language)
    """, (user_id, username, first_name, language))
    conn.commit()
    conn.close()
    return get_user(user_id)


def set_user_language(user_id: int, language: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET language = ? WHERE user_id = ?", (language, user_id))
    conn.commit()
    conn.close()


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def set_user_location(user_id: int, lat: float, lon: float, location_name: str = ""):
    """Foydalanuvchining oxirgi lokatsiyasini saqlash."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE users 
        SET last_lat = ?, last_lon = ?, last_location_name = ?
        WHERE user_id = ?
    """, (lat, lon, location_name, user_id))
    conn.commit()
    conn.close()


def get_user_location(user_id: int) -> tuple[float, float, str]:
    """Foydalanuvchining oxirgi koordinatalarini olish (yoki standart Toshkent)."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT last_lat, last_lon, last_location_name FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row and row["last_lat"] is not None and row["last_lon"] is not None:
        return float(row["last_lat"]), float(row["last_lon"]), row["last_location_name"] or ""
    return DEFAULT_LAT, DEFAULT_LON, "Toshkent (Markaz)"


# --- Profil boshqaruvi ---

def set_user_profile(user_id: int, profile_type: str, notes: str = ""):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("""
        INSERT INTO profiles (user_id, profile_type, notes, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            profile_type = excluded.profile_type,
            notes = excluded.notes,
            updated_at = excluded.updated_at
    """, (user_id, profile_type, notes, now))
    conn.commit()
    conn.close()


def get_user_profile(user_id: int) -> Dict[str, Any]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"user_id": user_id, "profile_type": "umumiy", "notes": ""}


# --- Obunalar (F3) ---

def add_subscription(user_id: int, lat: float, lon: float, threshold: int = 100, location_name: str = "Toshkent") -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO subscriptions (user_id, lat, lon, threshold, location_name, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, 1, ?)
    """, (user_id, lat, lon, threshold, location_name, datetime.now().isoformat()))
    sub_id = c.lastrowid
    conn.commit()
    conn.close()
    return sub_id


def get_user_subscriptions(user_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM subscriptions WHERE user_id = ? AND is_active = 1", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_active_subscriptions() -> List[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM subscriptions WHERE is_active = 1")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_subscription_notified(sub_id: int):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("UPDATE subscriptions SET last_notified_at = ? WHERE id = ?", (now, sub_id))
    conn.commit()
    conn.close()


def cancel_subscription(sub_id: int, user_id: int) -> bool:
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE subscriptions SET is_active = 0 WHERE id = ? AND user_id = ?", (sub_id, user_id))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0


# --- Tarix (AQI History) ---

def save_aqi_history(lat: float, lon: float, aqi: int, pm25: float, pm10: float, category: str, source: str, user_id: Optional[int] = None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO aqi_history (user_id, lat, lon, aqi, pm25, pm10, category, source, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, lat, lon, aqi, pm25, pm10, category, source, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_aqi_history(days: int = 7, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    since = (datetime.now() - timedelta(days=days)).isoformat()
    if user_id:
        c.execute("SELECT * FROM aqi_history WHERE user_id = ? AND timestamp >= ? ORDER BY timestamp ASC", (user_id, since))
    else:
        c.execute("SELECT * FROM aqi_history WHERE timestamp >= ? ORDER BY timestamp ASC", (since,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Ogohlantirish jurnali ---

def log_alert(subscription_id: int, user_id: int, aqi: int, threshold: int, message: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO alert_logs (subscription_id, user_id, aqi, threshold, message, sent_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (subscription_id, user_id, aqi, threshold, message, datetime.now().isoformat()))
    conn.commit()
    conn.close()


# Dastur ishga tushganda bazani ishga tushirish
init_db()
