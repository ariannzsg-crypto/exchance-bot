# EXCHANCE — قیمت لحظه‌ای ارز، طلا و رمزارز

وب‌اپ فارسی (راست‌به‌چپ) برای قیمت لحظه‌ای بازار ایران + دستیار هوشمند،
با بک‌اند پایتون روی Vercel Functions و فرانت‌اند استاتیک.

## ساختار پروژه

```
api/                 فانکشن‌های ورسل (هر فایل یک اندپوینت در /api/...)
├── market.py        قیمت‌های TGJU + CoinGecko
├── history.py       تاریخچه‌ی قیمت (CoinGecko) برای نمودار
├── news.py          اخبار RSS فارسی + TGJU
├── fear_greed.py    شاخص ترس و طمع
├── chart.py         لینک نمودار آماده (quickchart)
└── ai_chat.py       چت هوش مصنوعی (POST)
lib/                 کد مشترک
├── ai_provider.py   کلاینت AI سازگار با OpenAI + بودجه‌ی زمانی + مدل جانشین
├── market_data.py   استخراج قیمت از TGJU و CoinGecko (با کش ۱۰ ثانیه‌ای)
├── news_scraper.py  جمع‌آوری و مرتب‌سازی اخبار
├── currencies.py    فهرست ارزها، طلا و رمزارزها
└── utils.py         ابزار تبدیل عدد و متن فارسی
web/                 خروجی استاتیک (outputDirectory در vercel.json)
├── index.html / app.js / design-tokens.css
├── sw.js            سرویس‌ورکر (آفلاین + آخرین قیمت‌های کش‌شده)
├── manifest.json    نصب روی گوشی
└── icon.svg
vercel.json          تنظیمات ورسل
requirements.txt     وابستگی‌های پایتون
.env.example         نمونه‌ی متغیرهای محیطی (کلید واقعی داخلش نیست)
```

## اندپوینت‌ها

| متد | مسیر | توضیح |
| --- | --- | --- |
| GET | `/api/market` | فهرست ارزها، طلا و رمزارزها با قیمت تومانی |
| GET | `/api/history?code=btc&days=7` | تاریخچه‌ی قیمت (فقط رمزارزها) |
| GET | `/api/news` | اخبار اقتصادی فارسی |
| GET | `/api/fear_greed` | شاخص ترس و طمع |
| GET | `/api/chart?code=usd` | URL نمودار آماده |
| POST | `/api/ai_chat` | چت هوش مصنوعی (`{message, history, lang}`) |

## متغیرهای محیطی

فقط در ورسل ست شوند (Project → Settings → Environment Variables).
برای اجرای محلی، `.env.example` را به `.env` کپی کن.

| نام | اجباری | توضیح |
| --- | --- | --- |
| `AI_API_KEY` | بله (برای چت) | کلید سرویس سازگار با OpenAI |
| `AI_BASE_URL` | نه | پیش‌فرض `https://top-tools-ai.com/api/v1` |
| `AI_MODEL` | نه | پیش‌فرض `Top-Tools-Ai` |
| `AI_FALLBACK_MODELS` | نه | پیش‌فرض `MiniMax-M3,Step-5-Preview` |
| `AI_MAX_TOKENS` | نه | پیش‌فرض `700` |
| `AI_TOTAL_BUDGET` | نه | بودجه‌ی زمانی کل پاسخ (ثانیه)، پیش‌فرض `52` |
| `AI_FIRST_ATTEMPT` | نه | بودجه‌ی تلاش اول، پیش‌فرض `35` |
| `GEMINI_API_KEY` | نه | فقط پشتیبان |

### هشدار درباره‌ی کندی مدل

زمان پاسخ همین اندپوینت برای یک پرسش ۲۰ توکنی اندازه‌گیری شد:

| مدل | زمان |
| --- | --- |
| `Top-Tools-Ai` | ~۷۵ ثانیه (بار دوم بیش از ۱۲۰ ثانیه تایم‌اوت شد) |
| `MiniMax-M3` | ~۵۲ ثانیه |
| `Step-5-Preview` | ~۲۱ ثانیه |

چون سقف اجرای فانکشن روی پلن Hobby ورسل ۶۰ ثانیه است (`maxDuration` در `vercel.json`)،
پاسخ‌ها با بودجه‌ی زمانی محدود می‌شوند و اگر مدل دیر جواب بدهد کاربر پیام
«⏱ پاسخ مدل طول کشید» می‌گیرد. برای پاسخ سریع‌تر `AI_MODEL` را عوض کن.

## اجرای محلی

```bash
python -m venv venv
venv/Scripts/activate          # ویندوز
pip install -r requirements.txt

# کلیدها
cp .env.example .env           # و مقدار AI_API_KEY را بگذار

# اجرای فانکشن‌ها + فایل‌های استاتیک (شبیه ورسل)
npx vercel dev
```

بدون نصب Vercel CLI هم می‌توانی منطق بک‌اند را مستقیم تست کنی:

```bash
python -c "from lib.market_data import get_market; print(len(get_market()))"
python -c "from api.history import get_history; print(get_history('btc', 7)['source'])"
```

## دیپلوی روی Vercel

1. ریپو را در GitHub بساز و این پوشه را push کن.
2. در ورسل → **Add New → Project** و انتخاب همان ریپو.
3. Framework Preset را روی **Other** بگذار (پروژه build ندارد؛ خروجی استاتیک از `web/` سرو می‌شود).
4. در **Environment Variables** مقدار `AI_API_KEY` (و در صورت نیاز مدل‌ها) را ست کن.
5. Deploy. بعد از دیپلوی، این آدرس‌ها را چک کن: `/`، `/api/market`، `/api/history?code=btc`، `/api/ai_chat`. (مسیرهای قدیمی `/api/ai-chat` و `/api/fear-greed` با rewrite به مسیر جدید وصل می‌شوند.)

> کلیدها فقط در پنل ورسل ذخیره می‌شوند؛ `.env` در `.gitignore` است و هیچ کلیدی در کد نیست.

## نکته‌ی امنیتی

اگر کلید API جایی (چت، اسکرین‌شات، فایل عمومی) منتشر شده باشد، آن را باطل و
کلید تازه بساز. کلید فعلی فقط داخل `.env` محلی است و کامیت نمی‌شود.
