"""
APScheduler orqali orqa fonda muntazam tekshiruv (30 daqiqada bir).
Foydalanuvchi obunalarini (F3) monitoring qilish va chegara oshganda ogohlantirish yuborish.
"""
import logging
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler

from config import CHECK_INTERVAL_MINUTES
from database import (
    get_all_active_subscriptions,
    update_subscription_notified,
    log_alert,
    get_user,
    get_user_profile,
)
from sensor_service import get_air_quality
from advisor import personal_advice
from aqi_calc import get_aqi_level

logger = logging.getLogger(__name__)


class SubscriptionMonitor:
    def __init__(self, notify_callback: Optional[Callable] = None):
        """
        notify_callback: async yoki sync funksiya:
        def notify_callback(user_id: int, message: str)
        """
        self.notify_callback = notify_callback
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    async def check_subscriptions_once(self) -> int:
        """Barcha faol obunalarni bir marta to'liq tekshiradi."""
        active_subs = get_all_active_subscriptions()
        alert_count = 0
        now = datetime.now()

        for sub in active_subs:
            try:
                sub_id = sub["id"]
                user_id = sub["user_id"]
                lat = sub["lat"]
                lon = sub["lon"]
                threshold = sub["threshold"]
                loc_name = sub.get("location_name", "Toshkent")
                last_notified_str = sub.get("last_notified_at")

                # Agar oxirgi 2 soat ichida ogohlantirilgan bo'lsa, spam qilmaslik
                if last_notified_str:
                    try:
                        last_notified = datetime.fromisoformat(last_notified_str)
                        if (now - last_notified) < timedelta(hours=2):
                            continue
                    except ValueError:
                        pass

                # Havo sifatini tekshirish
                aq_data = get_air_quality(lat, lon, user_id=user_id)
                current_aqi = aq_data.get("aqi", 0)

                # Agar belgilangan chegaradan oshsa
                if current_aqi >= threshold:
                    user = get_user(user_id) or {}
                    lang = user.get("language", "uz")
                    prof_data = get_user_profile(user_id)
                    profile_type = prof_data.get("profile_type", "umumiy")

                    level = get_aqi_level(current_aqi)
                    adv = personal_advice(current_aqi, profile=profile_type, lang=lang)

                    if lang == "ru":
                        msg = (
                            f"🚨 **ВНИМАНИЕ! Превышен порог качества воздуха!**\n\n"
                            f"📍 **Локация:** {loc_name}\n"
                            f"📊 **Текущий AQI:** {current_aqi} ({level['title']['ru']} {level['emoji']})\n"
                            f"🎯 **Ваш порог:** {threshold}\n"
                            f"👤 **Ваш профиль:** {profile_type.capitalize()}\n\n"
                            f"💡 **Рекомендация:**\n{adv['advice_text']}\n\n"
                            f"📌 *Источник: {aq_data.get('source')} · {aq_data.get('timestamp')}*"
                        )
                    else:
                        msg = (
                            f"🚨 **DIQQAT! Havo ifloslanishi chegarasi oshdi!**\n\n"
                            f"📍 **Joylashuv:** {loc_name}\n"
                            f"📊 **Hozirgi AQI:** {current_aqi} ({level['title']['uz']} {level['emoji']})\n"
                            f"🎯 **Siz o'rnatgan chegara:** {threshold}\n"
                            f"👤 **Sizning profilingiz:** {profile_type.capitalize()}\n\n"
                            f"💡 **Tavsiya:**\n{adv['advice_text']}\n\n"
                            f"📌 *Manba: {aq_data.get('source')} · {aq_data.get('timestamp')}*"
                        )

                    # Callback orqali yuborish
                    if self.notify_callback:
                        try:
                            import inspect
                            if inspect.iscoroutinefunction(self.notify_callback):
                                await self.notify_callback(user_id, msg)
                            else:
                                self.notify_callback(user_id, msg)
                        except Exception as e:
                            logger.error(f"Xabar yuborishda xato (user {user_id}): {e}")

                    # Baza yangilash
                    update_subscription_notified(sub_id)
                    log_alert(sub_id, user_id, current_aqi, threshold, msg)
                    alert_count += 1

            except Exception as e:
                logger.error(f"Obunani tekshirishda xato: {e}")

        return alert_count

    def start(self):
        """APScheduler ni 30 daqiqalik interval bilan ishga tushirish."""
        if not self.is_running:
            self.scheduler.add_job(
                self.check_subscriptions_once,
                "interval",
                minutes=CHECK_INTERVAL_MINUTES,
                id="air_quality_monitor",
                replace_existing=True,
            )
            self.scheduler.start()
            self.is_running = True
            logger.info(f"APScheduler ishga tushirildi ({CHECK_INTERVAL_MINUTES} daqiqalik interval).")

    def stop(self):
        """Schedulerni to'xtatish."""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
