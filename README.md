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
├── ai_provider.py   زنجیره‌ی ارائه‌دهنده‌های AI + بودجه‌ی زمانی + جانشینی
├── market_data.py   استخراج قیمت از TGJU و CoinGecko (با کش ۱۰ ثانیه‌ای)
├── news_scraper.py  جمع‌آوری و مرتب‌سازی اخبار
├── currencies.py    فهرست ارزها، طلا و رمزارزها
└── utils.py         ابزار تبدیل عدد و متن فارسی
web/                 خروجی استاتیک (outputDirectory در vercel.json)
├── index.html / app.js / design-tokens.css
├── sw.js            سرویس‌ورکر (آفلاین + آخرین قیمت‌های کش‌شده)
├── manifest.json    نصب روی گوشی
└── icon.svg
tests/               تست‌های آفلاین (pytest) برای تحلیل‌گر قیمت، اندپوینت‌ها و کلاینت AI
vercel.json          تنظیمات ورسل
requirements.txt     وابستگی‌های پایتون
requirements-dev.txt وابستگی‌های توسعه (pytest)
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
| `MISTRAL_API_KEY` | نه | **پیشنهاد اول برای چت** — پلن Free بدون کارت بانکی |
| `GROQ_API_KEY` | نه | جایگزین سریع، سازگار با OpenAI |
| `GEMINI_API_KEY` | نه | پلن رایگان Google AI Studio |
| `AI_API_KEY` | نه | سرویس عمومی سازگار با OpenAI (در دسترس عموم، صف مشترک) |
| `AI_BASE_URL` | نه | پیش‌فرض `https://top-tools-ai.com/api/v1` |
| `AI_MODEL` | نه | پیش‌فرض `DeepSeek-V4.1-Flash` |
| `AI_FALLBACK_MODELS` | نه | پیش‌فرض `Step-5-Preview,GLM-5.3-Flash` |
| `AI_MAX_TOKENS` | نه | پیش‌فرض `700` |
| `AI_TOTAL_BUDGET` | نه | بودجه‌ی زمانی کل پاسخ (ثانیه)، پیش‌فرض `55` |
| `AI_FIRST_ATTEMPT` | نه | بودجه‌ی تلاش اول، پیش‌فرض `45` |
| `MISTRAL_MODEL` / `GROQ_MODEL` / `GEMINI_MODEL` | نه | بازنویسی شناسه‌ی مدل بدون تغییر کد |

### ترتیب ارائه‌دهنده‌های چت

ترتیب دقیقاً بر اساس «کلیدهایی که ست شده‌اند» ساخته می‌شود؛ هر ارائه‌دهنده یک بار
(و در صورت خطای موقتی ۴۲۹/۵۰۳، دو بار) امتحان می‌شود و بعد نوبت بعدی است:

```
Mistral  →  Groq  →  Gemini  →  سرویس عمومی AI_*  →  پیام مناسب به کاربر
```

این ساختار از یک درد واقعی آمده: سرویس عمومی کلیدش با اپ‌های دیگر هم‌استفاده می‌شود
و وقتی ظرفیتش پر شود `503 gateway_queue_full` می‌دهد. یک کلید اختصاصی کافی است تا چت
از کار نیفتد. اگر هیچ کلیدی ست نباشد، `/api/ai_chat` باز هم خراب نمی‌شود و پیام
«سرویس AI فعال نیست» برمی‌گرداند.

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

## تست‌ها

تست‌ها آفلاین‌اند و به اینترنت یا کلید AI نیاز ندارند: تحلیل‌گر قیمت TGJU با یک
fixture شبیه‌سازی می‌شود، هر اندپوینت روی یک پورت لوپ‌بک واقعاً سرو می‌شود و
درخواست‌های بیرونی جعل می‌شوند.

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

پوشش فعلی:

* `tests/test_market_data.py` — تبدیل ریال به تومان، «ین ژاپن (100 ین)»، ردیف‌های
  تزئینی بدون `data-price`، ویجت‌های مخفی که نام ارز دیگر را در خود دارند،
  `tgju_exclude` (مثقال/آبشده) و گرم نقره در برابر انس نقره.
* `tests/test_api_endpoints.py` — کد وضعیت، قرارداد JSON، CORS و کشِ هر اندپوینت،
  هم‌چنین بررسی اینکه هر مسیر `/api/...` در فرانت‌اند معادل واقعی در `api/` دارد
  (همان باگ قبلی که مسیر فرانت با نام فایل فانکشن نمی‌خواند).
* `tests/test_ai_provider.py` — ترتیب زنجیره‌ی ارائه‌دهنده‌ها، جانشینی، یک بار تلاش
  دوباره روی ۴۲۹/۵۰۳، شکل درخواست OpenAI/Gemini و پیام‌های کاربر.

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
