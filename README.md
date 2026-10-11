# EXCHANCE — قیمت لحظه‌ای ارز، طلا و رمزارز

وب‌اپ فارسی (راست‌به‌چپ) برای قیمت لحظه‌ای بازار ایران + **اپ اندروید**،
با بک‌اند پایتون روی Vercel Functions و فرانت‌اند استاتیک.

بدون هیچ کلید API و بدون سرویس هوش مصنوعی: همه‌ی داده‌ها از منابع عمومی خوانده می‌شوند.

## آنچه در اپ هست

| بخش | توضیح |
| --- | --- |
| قیمت لحظه‌ای | ارز، طلا (۱۸ و ۲۴ عیار)، نقره و رمزارزها به تومان |
| نمودار | تاریخچه‌ی ۱ روز تا ۱ سال (رمزارزها از CoinGecko) |
| اخبار | RSS فارسی + TGJU با فیلتر ایرانی/خارجی |
| شاخص ترس و طمع | مقدار و وضعیت بازار |
| تبدیل ارز و طلا | ماشین‌حساب تبدیل با واحد و عیار |
| پورتفولیو | ارزش دارایی‌ها و سود/ضرر |
| هشدار قیمت | هشدار بالاتر/پایین‌تر از حد با نوتیفیکیشن مرورگر |
| مقایسه و پُرنوسان‌ترین | نمودار مقایسه‌ای و رتبه‌بندی تغییرات |
| علاقه‌مندی‌ها، پالت دستورات، تم روشن/تاریک، سه زبان | فارسی، انگلیسی، عربی |
| حالت آفلاین | سرویس‌ورکر آخرین قیمت‌ها را نگه می‌دارد |
| اپ اندروید | همین رابط کاربری، بسته‌بندی‌شده به‌صورت APK |

## ساختار پروژه

```
api/                 فانکشن‌های ورسل (هر فایل یک اندپوینت در /api/...)
├── market.py        قیمت‌های TGJU + CoinGecko
├── history.py       تاریخچه‌ی قیمت (CoinGecko) برای نمودار
├── news.py          اخبار RSS فارسی + TGJU
├── fear_greed.py    شاخص ترس و طمع
└── chart.py         لینک نمودار آماده (quickchart)
lib/                 کد مشترک
├── market_data.py   استخراج قیمت از TGJU و CoinGecko (با کش ۱۰ ثانیه‌ای)
├── news_scraper.py  جمع‌آوری و مرتب‌سازی اخبار
├── currencies.py    فهرست ارزها، طلا و رمزارزها
└── utils.py         ابزار تبدیل عدد و متن فارسی
web/                 خروجی استاتیک (outputDirectory در vercel.json)
├── index.html / app.js / design-tokens.css
├── config.js        مبدأ API برای اپ بومی (در وب خالی است)
├── sw.js            سرویس‌ورکر (آفلاین + آخرین قیمت‌های کش‌شده)
├── manifest.json    نصب روی گوشی
└── icon.svg
android/             پروژه‌ی اندروید (Capacitor 8) — با cap add android ساخته شده
resources/           تصویرهای مبدأ آیکون و اسپلش برای capacitor-assets
tests/               تست‌های آفلاین (pytest)
capacitor.config.json تنظیمات Capacitor (appId، webDir، scheme)
.github/workflows/   ساخت خودکار APK روی هر push
vercel.json          تنظیمات ورسل
requirements(-dev).txt وابستگی‌های پایتون (اجباری و توسعه)
package.json         وابستگی‌های Node/Capacitor
```

## اندپوینت‌ها

| متد | مسیر | توضیح |
| --- | --- | --- |
| GET | `/api/market` | فهرست ارزها، طلا و رمزارزها با قیمت تومانی |
| GET | `/api/history?code=btc&days=7` | تاریخچه‌ی قیمت (فقط رمزارزها) |
| GET | `/api/news` | اخبار اقتصادی فارسی |
| GET | `/api/fear_greed` | شاخص ترس و طمع |
| GET | `/api/chart?code=usd` | URL نمودار آماده |

در اپ اندروید همین اندپوینت‌ها روی دامنه‌ی ورسل صدا زده می‌شوند (پاسخ‌ها
`Access-Control-Allow-Origin: *` دارند، پس از داخل WebView هم کار می‌کنند).

## اجرای محلی

```bash
python -m venv venv
venv/Scripts/activate          # ویندوز
pip install -r requirements.txt

python -m _preview.devserver   # اگر devserver را داری
# یا خودِ ورسل:
npx vercel dev
```

بدون نصب Vercel CLI هم می‌توانی منطق بک‌اند را مستقیم تست کنی:

```bash
python -c "from lib.market_data import get_market; print(len(get_market()))"
python -c "from api.history import get_history; print(get_history('btc', 7)['source'])"
```

## تست‌ها

تست‌ها آفلاین‌اند و به اینترنت یا هیچ کلیدی نیاز ندارند: تحلیل‌گر قیمت TGJU با یک
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
  هم‌چنین بررسی اینکه هر مسیر `/api/...` در فرانت‌اند معادل واقعی در `api/` دارد.
* `tests/test_android_app.py` — شناسه‌ی بسته، پوشه‌ی وب، gradle wrapper، مجوز
  اینترنت، آیکون‌ها/اسپلش، مبدأ API در اپ بومی، نبودِ ردپای حذف‌شده‌ی هوش مصنوعی،
  و مسیر خروجی APK که باید با مسیر آپلود در workflow بخواند.

## اپ اندروید

رابط کاربری همان وب است و با [Capacitor 8](https://capacitorjs.com) داخل یک اپ
اندروید بومی بسته‌بندی می‌شود؛ پس هر تغییری در `web/` با یک sync به اپ می‌رسد.

### نکته‌ی مهم: مبدأ API

صفحه در اپ از داخل خودِ برنامه سرو می‌شود، بنابراین مسیرهای نسبی (`/api/market`)
به سرور نمی‌رسند. این کار در `web/config.js` حل شده است:

```js
var DEPLOYED_API = "https://exchance-bot.vercel.app";   // ← بعد از دیپلوی عوض کن
```

در مرورگر این مقدار خالی می‌ماند (همان مبدأ)، و در اپ اندروید استفاده می‌شود.

### گرفتن APK از گیت‌هاب (بدون نصب چیزی)

هر push روی `main` که فایل‌های `web/`, `android/`, `resources/` یا تنظیمات را
عوض کند، workflow `Android APK` را اجرا می‌کند. APK ساخته‌شده در همان اجرا زیر
**Artifacts** با نام `exchance-debug-apk` برای دانلود می‌گذارد. اجرای دستی هم از
تب Actions → Android APK → Run workflow ممکن است.

### ساخت محلی (اختیاری)

نیاز به JDK 21 و Android SDK دارد:

```bash
npm install
npx cap sync android          # کپی web/ داخل پروژه‌ی اندروید
cd android && ./gradlew assembleDebug
# خروجی: android/app/build/outputs/apk/debug/app-debug.apk
```

برای انتشار در بازار/گوگل‌پلی، نسخه‌ی release را با کلید خودت امضا کن
(`./gradlew assembleRelease`).

### عوض کردن آیکون و اسپلش

`resources/icon.png` (و `icon-foreground/background` و `splash(-dark)`) مبدأها
هستند. برای ساخت مجدد همه‌ی اندازه‌ها:

```bash
npm run android:assets
```

## دیپلوی روی Vercel

1. ریپو را در GitHub بساز و این پوشه را push کن.
2. در ورسل → **Add New → Project** و انتخاب همان ریپو.
3. Framework Preset را روی **Other** بگذار (پروژه build ندارد؛ خروجی استاتیک از `web/` سرو می‌شود).
4. **هیچ متغیر محیطی لازم نیست.** فقط Deploy را بزن.
5. بعد از دیپلوی، این آدرس‌ها را چک کن: `/`، `/api/market`، `/api/history?code=btc`،
   `/api/news`، `/api/fear_greed`، `/api/chart?code=usd`.
   (مسیر قدیمی `/api/fear-greed` با rewrite به مسیر جدید وصل می‌شود.)
6. دامنه‌ی نهایی را در `web/config.js` بگذار و push کن تا اپ اندروید هم به همان
   بک‌اند وصل شود.
