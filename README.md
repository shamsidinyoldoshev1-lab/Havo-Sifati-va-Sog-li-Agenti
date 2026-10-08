# TZ-06 · Havo sifati va sog'liq agenti (Tashkent Air Quality & Health AI Agent)

> **Versiya:** 1.0 · 12.09.2026  
> **Tizim:** Python 3.10+, SQLite, APScheduler, Telegram Bot API, Open-Meteo, sensor.community, Groq (Qwen 2.5), Gemini Flash Vision, Matplotlib.

---

## 1. Loyiha haqida va Muammo
Toshkent qish oylarida dunyodagi eng ifloslangan shaharlar ro'yxatiga kiradi (PM2.5 ko'rsatkichlari bo'yicha). Shahar aholisi (ayniqsa ota-onalar, keksalar, sportchilar, astma va yurak kasalligi bor fuqarolar) har kuni:
- Tashqariga bola bilan chiqish xavfsizmi?
- Derazalarni ochib shamollatish mumkinmi?
- Qaysi niqob (N95/KN95) yoki havo tozalagich (HEPA) samarali?
- Qachon ko'chada yugurish yoki mashq qilish mumkin?

Ushbu agent real-vaqtdagi ochiq sensorlar (`sensor.community`, `Open-Meteo Copernicus CAMS`), ob-havo prognozi, JSST (WHO) va AQSh EPA standartlariga tayangan holda oddiy va tushunarli tilda shaxsiylashtirilgan tavsiyalar beradi.

---

## 2. Funksional imkoniyatlar (F1–F7)

| ID | Stsenariy | Tavsif va Natija |
|---|---|---|
| **F1** | "Hozir havo qanday?" | Foydalanuvchi joylashuvi bo'yicha eng yaqin fizik sensor yoki atmosfera modeli, PM2.5, PM10, AQI, toifa darajasi va oddiy tildagi tavsiya. |
| **F2** | Shaxsiy profil | 7 xil toifa: `bola`, `astma`, `sport`, `yurak`, `keksa`, `maktab`, `umumiy`. Har bir profilga EPA mezoniga mos tavsiya. |
| **F3** | Avtomatik obuna | Belgilangan chegara (AQI 50, 100, 150, 200) oshganda APScheduler orqali foydalanuvchiga xabar yuborish. |
| **F4** | 24 soatlik prognoz | Keyingi 24 soatlik AQI va harorat/shamol grafigi, eng qulay sayr vaqti va eng xavfli soatlar tahlili. |
| **F5** | "Qaysi niqob/filtr?" (RAG) | N95/KN95 respiratorlari, HEPA H13/H14 tozalagichlari, CADR va shamollatish mezonlari bo'yicha WHO/EPA bilimlari. |
| **F6** | Hafta hisoboti | Matplotlib orqali yaratilgan 7 kunlik AQI grafigi, rangli toifalar va tahliliy xulosa. |
| **F7** | Rasm tahlili (Vision) | Osmon va ufq fotosuratini yuklash orqali tuman/smog zichligini vizual baholash (yordamchi indikator). |

---

## 3. Asosiy Tool'lar (8 ta rasmiy Tool)
1. `get_air_quality(lat, lon)` — Eng yaqin fizik sensordan yoki atmosfera modelidan real-vaqt ma'lumotlari.
2. `nearest_stations(lat, lon)` — Berilgan koordinata atrofidagi sensorlar ro'yxati (masofasi bilan).
3. `get_weather(lat, lon)` — Harorat, namlik, shamol tezligi va inversiya / tutun tarqalish sharoiti.
4. `personal_advice(aqi, profile)` — Profil va AQI kombinatsiyasi bo'yicha EPA/WHO tavsiyasi.
5. `subscribe(user_id, lat, lon, threshold)` — Chegara monitoringiga obuna bo'lish.
6. `forecast(lat, lon)` — 24 soatlik atmosfera va ifloslanish prognozi.
7. `weekly_report(user_id)` — 7 kunlik grafik tasviri va statistik hisoboti.
8. `search_health_docs(query)` — Niqoblar, filtrlar va mezonlar bo'yicha RAG bazasidan qidiruv.

---

## 4. Guardrails (Xavfsizlik choralari)
- **Tibbiy tashxis yo'q:** Agent hech qachon kasallik tashxisini qo'ymaydi va dori-darmonlar (antibiotik, salbutamol, tabletkalar va h.k.) tavsiya etmaydi. Qat'iy ravishda davolovchi shifokorga yoki 103 tez yordamga yo'naltiradi.
- **Sensor ma'lumoti eskirgan bo'lsa (>2 soat):** Ko'rsatkich "taxminiy" deb belgilanadi va ogohlantirish beriladi.
- **Vision bahosi:** Fotosurat orqali tahlil hech qachon fizik lazer sensorlar (PM2.5/PM10) o'rniga o'tmaydi.
- **Manba va sana:** Har bir javobda olingan ma'lumot manbasi (sensor.community, Open-Meteo, WHO, EPA) va sana/vaqt qayd etiladi.

---

## 5. Ishga tushirish yo'riqnomasi

### 5.1. Kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 5.2. Konfiguratsiya (.env)
`.env` faylida quyidagi parametrlarni sozlang:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key (ixtiyoriy)
DATABASE_PATH=data/air_quality.db
DEFAULT_LAT=41.2995
DEFAULT_LON=69.2401
CHECK_INTERVAL_MINUTES=30
```

### 5.3. Telegram Botni ishga tushirish
```bash
python telegram_bot.py
```

### 5.4. Konsol (CLI) orqali interaktiv tekshirish
```bash
python cli.py
```

### 5.5. Avtomatlashtirilgan baholash to'plami (Eval Suite)
```bash
python eval_suite.py
```
Natija:
- **EVAL 1:** 20 ta koordinata bo'yicha stansiya va AQI o'lchovi (20/20 PASS)
- **EVAL 2:** 15 ta profil × AQI kombinatsiyasi bo'yicha EPA mosligi (15/15 PASS)
- **EVAL 3:** 10 ta tibbiy savol guardrail testi (10/10 PASS)
- **Umumiy natija:** 45/45 (100.0%) muvaffaqiyatli!
