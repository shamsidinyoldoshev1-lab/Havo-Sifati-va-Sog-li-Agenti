"""
Konsol (CLI) interfeysi: Barcha 8 ta tool va 7 ta stsenariyni
to'g'ridan-to'g'ri terminalda interaktiv tekshirish va sinovdan o'tkazish.
"""
import os
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from datetime import datetime

import tools
from agent import agent
from config import DEFAULT_LAT, DEFAULT_LON, REPORTS_DIR


def print_banner():
    print("=" * 70)
    print("      HAVO SIFATI VA SOG'LIQ AGENTI (TZ-06) — CLI INTERFEYS      ")
    print("          Toshkent shahri va O'zbekiston hududlari uchun         ")
    print("=" * 70)


def print_menu(lang: str = "uz"):
    if lang == "ru":
        print("\n--- ГЛАВНОЕ МЕНЮ ---")
        print("1. 📍 Качество воздуха сейчас (F1 / get_air_quality)")
        print("2. 📡 Ближайшие датчики (nearest_stations)")
        print("3. 🌤 Погода и рассеивание смога (get_weather)")
        print("4. 👤 Настройка профиля здоровья (F2 / personal_advice)")
        print("5. 🔔 Подписка на превышение порога AQI (F3 / subscribe)")
        print("6. 📈 Прогноз качества воздуха на 24ч (F4 / forecast)")
        print("7. 🛡 Вопросы по маскам N95 и фильтрам HEPA (F5 / RAG)")
        print("8. 📊 Создать недельный график и отчет (F6 / weekly_report)")
        print("9. 📸 Анализ смога по фото неба (F7 / Vision)")
        print("10. 🧪 Запустить тест оценки (Eval Suite — 20 точек, 15 профилей, 10 guardrail)")
        print("11. 🌐 Сменить язык (UZ / RU)")
        print("0. Выход")
    else:
        print("\n--- ASOSIY MENYU ---")
        print("1. 📍 Hozirgi havo sifati (F1 / get_air_quality)")
        print("2. 📡 Eng yaqin sensorlar ro'yxati (nearest_stations)")
        print("3. 🌤 Ob-havo va tutun tarqalishi (get_weather)")
        print("4. 👤 Sog'liq profilini sozlash (F2 / personal_advice)")
        print("5. 🔔 AQI chegarasiga obuna bo'lish (F3 / subscribe)")
        print("6. 📈 24 soatlik havo prognozi (F4 / forecast)")
        print("7. 🛡 Niqoblar (N95) va filtrlar (HEPA) bo'yicha RAG (F5)")
        print("8. 📊 Haftalik grafik hisobot yaratish (F6 / weekly_report)")
        print("9. 📸 Osmon rasmini tahlil qilish (F7 / Vision)")
        print("10. 🧪 To'liq Eval test to'plamini yurgizish (20 koordinata, 15 profil, 10 guardrail)")
        print("11. 🌐 Tilni almashtirish (UZ / RU)")
        print("0. Chiqish")


def main():
    print_banner()
    lang = "uz"
    user_id = 101

    while True:
        print_menu(lang)
        choice = input("\nTanlovingizni kiriting / Ваш выбор (0-11): ").strip()

        if choice == "0":
            print("Xayr! Salomat bo'ling.")
            break

        elif choice == "1":
            print("\n[F1] Koordinatalar bo'yicha havo sifatini aniqlash...")
            c_input = input(f"Koordinatalarni kiriting [lat,lon] (Enter: {DEFAULT_LAT},{DEFAULT_LON}): ").strip()
            if c_input and "," in c_input:
                parts = c_input.split(",")
                lat, lon = float(parts[0]), float(parts[1])
            else:
                lat, lon = DEFAULT_LAT, DEFAULT_LON

            res = agent.handle_location_query(lat, lon, user_id=user_id, lang=lang)
            print("\n" + res["formatted_message"])

        elif choice == "2":
            print("\n[Tool: nearest_stations] Yaqin stansiyalarni qidirish...")
            stations = tools.nearest_stations(DEFAULT_LAT, DEFAULT_LON)
            print(f"Topilgan stansiyalar soni: {len(stations)}\n")
            for i, s in enumerate(stations, 1):
                st_type = "Fizik sensor" if s.get("is_physical") else "Atmosfera modeli"
                print(f"{i}. {s['name']} | Masofa: {s['distance_km']} km | AQI: {s.get('aqi')} | Tur: {st_type}")
                print(f"   PM2.5: {s.get('pm25')} | PM10: {s.get('pm10')} | Vaqt: {s.get('timestamp')}\n")

        elif choice == "3":
            print("\n[Tool: get_weather] Ob-havo ma'lumotlari...")
            w = tools.get_weather(DEFAULT_LAT, DEFAULT_LON)
            print(f"Harorat: {w['temperature']}°C")
            print(f"Namlik: {w['humidity']}%")
            print(f"Shamol tezligi: {w['wind_speed_ms']} m/s ({w['wind_speed_kmh']} km/soat)")
            print(f"Holat: {w['weather_description'].get(lang, w['weather_description']['uz'])}")
            print(f"Smog tarqalish sharoiti: {w['dispersion_condition'].get(lang, w['dispersion_condition']['uz'])}")
            print(f"Manba: {w['source']} · {w['timestamp']}")

        elif choice == "4":
            print("\n[F2] Profilni tanlang:")
            profs = ["bola", "astma", "sport", "yurak", "keksa", "maktab", "umumiy"]
            for idx, p in enumerate(profs, 1):
                print(f"{idx}. {p.capitalize()}")
            p_idx = input("Tanlang (1-7): ").strip()
            try:
                selected_prof = profs[int(p_idx) - 1]
            except Exception:
                selected_prof = "umumiy"

            res = agent.set_profile(user_id, selected_prof, lang=lang)
            print("\n" + res["message"])

            # Tanlangan profil uchun hozirgi AQI tavsiyasini ko'rsatish
            aq = tools.get_air_quality(DEFAULT_LAT, DEFAULT_LON)
            adv = tools.personal_advice(aq["aqi"], profile=selected_prof, lang=lang)
            print("\n" + adv["formatted_message"])

        elif choice == "5":
            print("\n[F3] Havo ifloslanishiga obuna bo'lish:")
            thresh_input = input("Ogohlantirish chegarasi AQI (masalan 50, 100, 150) [Enter: 100]: ").strip()
            thresh = int(thresh_input) if thresh_input.isdigit() else 100
            res = agent.create_subscription(user_id, DEFAULT_LAT, DEFAULT_LON, threshold=thresh, location_name="Toshkent markazi", lang=lang)
            print("\n" + res["message"])

        elif choice == "6":
            print("\n[F4] 24 soatlik prognozni hisoblash...")
            fc = agent.get_forecast(DEFAULT_LAT, DEFAULT_LON, lang=lang)
            print("\n" + fc["formatted_message"])

        elif choice == "7":
            print("\n[F5] Niqoblar, filtrlar yoki sog'liq bo'yicha savol bering:")
            print("(Namuna: 'Qaysi niqob PM2.5 dan himoya qiladi?', 'HEPA filtr nima?', 'Menda astma bor qaysi dori ichay?')")
            q = input("Savolingiz: ").strip()
            if not q:
                q = "PM2.5 uchun qaysi niqob samarali?"
            ans = agent.ask_rag_or_health(q, lang=lang)
            print("\n" + ans["answer"])

        elif choice == "8":
            print("\n[F6] Haftalik hisobot va matplotlib grafigini yaratish...")
            rep = agent.get_weekly_report(user_id, DEFAULT_LAT, DEFAULT_LON, lang=lang)
            print("\n" + rep["formatted_message"])
            print(f"🖼 Saqlangan grafik rasm yo'li: {rep.get('image_path')}")

        elif choice == "9":
            print("\n[F7] Rasm (osmon/tuman) tahlili:")
            img_path = input("Rasm fayli yo'lini kiriting (yoki sinov namunasi uchun Enter bosing): ").strip()
            if not img_path or not os.path.exists(img_path):
                # Sinov rasmi yaratish (PIL orqali tutunli namuna)
                from PIL import Image, ImageDraw
                sample_img = REPORTS_DIR / "sample_sky.jpg"
                img = Image.new("RGB", (300, 300), color=(180, 185, 190))
                draw = ImageDraw.Draw(img)
                draw.rectangle([50, 200, 250, 290], fill=(130, 135, 140))
                img.save(str(sample_img))
                img_path = str(sample_img)
                print(f"Sinov uchun namuna rasm yaratildi: {img_path}")

            v_res = agent.analyze_sky_image(img_path, lang=lang)
            print("\n" + v_res["formatted_message"])

        elif choice == "10":
            print("\n[Eval Suite] Avtomatlashtirilgan baholash to'plami ishga tushirilmoqda...")
            from eval_suite import run_all_evals
            run_all_evals()

        elif choice == "11":
            lang = "ru" if lang == "uz" else "uz"
            print(f"Til o'zgartirildi: {lang.upper()}")


if __name__ == "__main__":
    main()
