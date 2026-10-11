"use strict";

/* =========================================================
   EXCHANCE — Web App v80
   ========================================================= */

const $ = id => document.getElementById(id);
const fiatGrid = $("fiatGrid"), cryptoGrid = $("cryptoGrid");
const loading = $("loading"), errorBox = $("errorBox"), errorText = $("errorText");
const retryBtn = $("retryBtn"), refreshBtn = $("refreshBtn");
const searchInput = $("searchInput"), clearSearch = $("clearSearch");
const categoryTabs = document.querySelectorAll(".tab");
const currencyCount = $("currencyCount"), marketStatus = $("marketStatus");
const lastUpdate = $("lastUpdate"), sourceText = $("sourceText");
const emptyState = $("emptyState"), themeToggle = $("themeToggle");
const tickerTrack = $("tickerTrack");
const paletteBtn = $("paletteBtn"), themePop = $("themePop");
const modal = $("chartModal"), modalPanel = $("modalPanel");
const clockTime = $("clockTime"), clockDate = $("clockDate");
const statsBar = $("statsBar"), statusBar = $("statusBar");

const convBtn = $("convBtn"), convModal = $("convModal"), convClose = $("convClose");
const convAmount = $("convAmount"), convFrom = $("convFrom"), convTo = $("convTo");
const convSwap = $("convSwap"), convValue = $("convValue"), convRate = $("convRate");

const newsSection = $("newsSection"), newsGrid = $("newsGrid");
const newsChips = document.querySelectorAll(".news-chip");

/* پایهٔ آدرس API: در وب خالی است (همان مبدأ) و در اپ اندروید از config.js می‌آید */
const API_BASE = (window.API_BASE || "").replace(/\/+$/, "");
const api = (path) => API_BASE + path;


const langBtn = $("langBtn"), langPop = $("langPop");
const settingsBtn = $("settingsBtn");

const gainersList = $("gainersList"), losersList = $("losersList");
const gainersCount = $("gainersCount"), losersCount = $("losersCount");

const fngBar = $("fngBar"), fngMarker = $("fngMarker");
const fngVal = $("fngVal"), fngClass = $("fngClass");

const pwaInstallBtn = $("pwaInstallBtn"), pwaClose = $("pwaClose");

const volatilitySection = $("volatilitySection");
const volList = $("volList"), volCount = $("volCount");

const cmdBtn = $("cmdBtn"), cmdModal = $("cmdModal"), cmdInput = $("cmdInput"), cmdResults = $("cmdResults");

const compareModal = $("compareModal"), cmpClose = $("cmpClose");
const cmpA = $("cmpA"), cmpB = $("cmpB");
const cmpLegend = $("cmpLegend"), cmpChart = $("cmpChart"), cmpTable = $("cmpTable");

const settingsModal = $("settingsModal"), setClose = $("setClose");
const setSound = $("setSound"), setAutoDark = $("setAutoDark"), setCompact = $("setCompact");
const setRefresh = $("setRefresh"), setExportAll = $("setExportAll"), setReset = $("setReset");

const goldAmount = $("goldAmount"), goldUnit = $("goldUnit"), goldKarat = $("goldKarat"), goldTarget = $("goldTarget");
const goldValue = $("goldValue"), goldRate = $("goldRate");

const toastContainer = $("toastContainer");

/* =========================================================
   STATE
========================================================= */

let currencies = [];
let currentTheme = localStorage.getItem("ex_theme") || "light";
let currentPalette = localStorage.getItem("ex_palette") || "aurora";
let currentLang = localStorage.getItem("ex_lang") || "fa";
let activeCategory = "all";
let prevPrices = {};
let currentChart = null;
let REFRESH_MS = parseInt(localStorage.getItem("ex_refresh_ms") || "10000", 10);

let newsItems = [];
let newsLoaded = false;
let newsLang = "all";
let newsRevealObserver = null;


let pollTimer = null;
let wsConnected = false;

let liveChartData = [];
let liveChartMaxPoints = 100;
let currentTimeframe = "7d";
let timeframeLoading = false;

let fngData = null;
let deferredInstallPrompt = null;

let watchlist = safeJSON("ex_watchlist", []);
let portfolio = safeJSON("ex_portfolio", []);
let alerts = safeJSON("ex_alerts", []);
let recentSearches = safeJSON("ex_recent_searches", []);

let settings = {
    sound: localStorage.getItem("ex_set_sound") === "1",
    autoDark: localStorage.getItem("ex_set_autodark") === "1",
    compact: localStorage.getItem("ex_set_compact") === "1",
};

let compareState = { a: null, b: null };

let cmdSelectedIndex = 0;
let cmdFiltered = [];

let currentConvTab = "currency";

/* =========================================================
   HELPERS
========================================================= */

function safeJSON(key, fallback) {
    try {
        const v = JSON.parse(localStorage.getItem(key) || "null");
        return v || fallback;
    } catch { return fallback; }
}

const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

function haptic() {
    if (prefersReducedMotion.matches) return;   // کاربر حرکت/لرزش کمتر خواسته است
    try { navigator.vibrate?.(10); } catch (e) {}
}

function esc(v) {
    return String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

/* =========================================================
   MODAL HELPERS — قفل اسکرول صفحه، فوکوس و aria
========================================================= */

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

let lastFocused = null;
let openModalCount = 0;

function lockScroll(on) {
    openModalCount = Math.max(0, openModalCount + (on ? 1 : -1));
    document.body.style.overflow = openModalCount ? "hidden" : "";
}

function openModal(el, focusSelector) {
    if (!el || el.classList.contains("on")) return;
    el.classList.add("on");
    el.setAttribute("aria-hidden", "false");
    lockScroll(true);
    lastFocused = document.activeElement;
    const target = (focusSelector && el.querySelector(focusSelector)) || el.querySelector(FOCUSABLE);
    if (target) setTimeout(() => { try { target.focus({ preventScroll: true }); } catch (e) {} }, 60);
}

function closeModal(el) {
    if (!el || !el.classList.contains("on")) return;
    el.classList.remove("on");
    el.setAttribute("aria-hidden", "true");
    lockScroll(false);
    if (lastFocused && document.contains(lastFocused)) {
        try { lastFocused.focus({ preventScroll: true }); } catch (e) {}
    }
    lastFocused = null;
}

/* فوکوس با Tab داخل همین مودال بچرخد */
function trapFocus(e) {
    const open = [...document.querySelectorAll(".modal.on, .cmd-modal.on")];
    const top = open[open.length - 1];
    if (!top) return;
    const nodes = [...top.querySelectorAll(FOCUSABLE)].filter(n => n.offsetParent !== null);
    if (!nodes.length) return;
    const first = nodes[0], last = nodes[nodes.length - 1];
    const active = document.activeElement;
    if (e.shiftKey && (active === first || !top.contains(active))) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && (active === last || !top.contains(active))) { e.preventDefault(); first.focus(); }
}

function fmtNum(v) {
    if (v === null || v === undefined || v === "") return "—";
    const n = Number(String(v).replace(/,/g, "").replace(/[^\d.-]/g, ""));
    if (!Number.isFinite(n)) return String(v);
    const locale = currentLang === "fa" ? "fa-IR" : "en-US";
    return new Intl.NumberFormat(locale).format(n);
}

function fmtUsd(v) {
    if (v === null || v === undefined || v === "") return "—";
    const n = Number(v);
    if (!Number.isFinite(n)) return String(v);
    if (Math.abs(n) > 0 && Math.abs(n) < 1) {
        return "$" + n.toFixed(6).replace(/0+$/, "").replace(/\.$/, "");
    }
    return "$" + new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(n);
}

function fmtPct(v) {
    if (v === null || v === undefined || v === "") return "";
    const n = Number(String(v).replace(/,/g, "").replace("%", ""));
    if (!Number.isFinite(n)) return String(v);
    const locale = currentLang === "fa" ? "fa-IR" : "en-US";
    return (n > 0 ? "+" : "") + new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(n) + "%";
}

function fmtTime(s) {
    if (!s) return "--:--";
    const d = new Date(s);
    if (Number.isNaN(d.getTime())) return "--:--";
    const locale = currentLang === "fa" ? "fa-IR" : "en-US";
    return new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit" }).format(d);
}

function trendOf(c) {
    const n = Number(String(c ?? "").replace(/,/g, "").replace("%", "").replace(/[^\d.-]/g, ""));
    if (!Number.isFinite(n) || n === 0) return { cls: "fl", text: "— 0%" };
    if (n > 0) return { cls: "up", text: "▲ " + fmtPct(n) };
    return { cls: "dn", text: "▼ " + fmtPct(n) };
}

function toast(msg, type = "") {
    if (!toastContainer) return;
    const el = document.createElement("div");
    el.className = "toast" + (type ? " " + type : "");
    el.textContent = msg;
    toastContainer.appendChild(el);
    setTimeout(() => {
        el.classList.add("out");
        setTimeout(() => el.remove(), 300);
    }, 2600);
}

function playBeep() {
    if (!settings.sound) return;
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = 880;
        osc.type = "sine";
        gain.gain.setValueAtTime(0.15, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
        osc.start();
        osc.stop(ctx.currentTime + 0.4);
    } catch (e) {}
}

function addRecentSearch(q) {
    q = (q || "").trim().toLowerCase();
    if (!q || q.length < 2) return;
    recentSearches = [q, ...recentSearches.filter(x => x !== q)].slice(0, 8);
    localStorage.setItem("ex_recent_searches", JSON.stringify(recentSearches));
}

/* =========================================================
   I18N
========================================================= */

const I18N = {
    fa: {
        search: "جستجوی ارز، طلا یا رمزارز...",
        tabAll: "همه", tabFiat: "ارز و طلا", tabCrypto: "رمزارز", tabNews: "📰 اخبار", tabWatch: "⭐",
        marketLabel: "بازار", countLabel: "تعداد نمادها", updateLabel: "بروزرسانی",
        liveStatus: "قیمت‌ها زنده (Polling هر ۱۰s)",
        errTitle: "دریافت قیمت‌ها ممکن نشد", errSub: "اتصال به سرور برقرار نشد.",
        retry: "تلاش مجدد", emptyTitle: "ارزی پیدا نشد", emptySub: "عبارت جستجو را تغییر دهید.",
        emptyWatchTitle: "هنوز علاقه‌مندی نداری", emptyWatchSub: "با زدن ستاره ⭐ روی هر ارز، به لیست اضافه کن.",
        sourceText: "قیمت‌ها از TGJU و CoinGecko", reportIssue: "گزارش مشکل",
        topGainers: "پرسودترین", topLosers: "پرضررترین",
        volatileTitle: "پُرنوسان‌ترین امروز",
        newsAll: "همه", newsFa: "🇮🇷 ایرانی", newsEn: "🌍 خارجی",
        portfolioTitle: "💼 پورتفولیو", totalValue: "ارزش کل", totalPnl: "سود/ضرر",
        amountPh: "مقدار", buyPh: "قیمت خرید", pricePh: "قیمت",
        alertsTitle: "🔔 هشدار قیمت", dirAbove: "بالاتر از", dirBelow: "پایین‌تر از",
        convTitle: "💱 تبدیل ارز", convAmount: "مبلغ", convFrom: "از", convTo: "به", convResult: "نتیجه",
        convCurrency: "💱 ارز", convGold: "🥇 طلا",
        goldAmount: "مقدار", goldUnit: "واحد", goldKarat: "عیار", goldTarget: "تبدیل به", goldResult: "نتیجه",
        marketBull: "صعودی", marketBear: "نزولی", marketFlat: "خنثی",
        unit: "تومان", price: "قیمت", source: "منبع",
        chartHigh: "بیشترین", chartLow: "کمترین", chartAvg: "میانگین",
        chartType: "نوع", beforeNow: "قبل‌تر", nowLabel: "اکنون",
        fiatLabel: "ارز و طلا", cryptoLabel: "رمزارز",
        agoNow: "همین حالا", agoMin: "دقیقه پیش", agoHour: "ساعت پیش", agoDay: "روز پیش",
        portEmpty: "هنوز دارایی‌ای اضافه نکردی", alertEmpty: "هنوز هشداری تنظیم نکردی",
        fngLabel: "شاخص ترس و طمع", pwaInstall: "نصب روی گوشی",
        tf1d: "۱ روز", tf7d: "۷ روز", tf30d: "۳۰ روز", tf90d: "۹۰ روز", tf1y: "۱ سال",
        share: "اشتراک‌گذاری",
        compareTitle: "📊 مقایسه ارزها", cmpFirst: "ارز اول", cmpSecond: "ارز دوم",
        settingsTitle: "⚙️ تنظیمات",
        setSound: "صدای هشدار", setSoundSub: "پخش صدا وقتی هشدار فعال شد",
        setAutoDark: "حالت تاریک خودکار", setAutoDarkSub: "فعال‌سازی در شب (۱۸ تا ۷)",
        setCompact: "حالت فشرده", setCompactSub: "نمایش کارت‌های کوچک‌تر",
        setRefresh: "فاصله بروزرسانی", setRefreshSub: "هر چند ثانیه قیمت‌ها آپدیت شوند",
        setExportAll: "📥 خروجی کامل", setReset: "🗑 ریست",
        cmdSearch: "جستجو یا اجرای دستور...",
        cmdCurrencies: "ارزها", cmdActions: "دستورات", cmdRecent: "جستجوهای اخیر",
        cmdNoResults: "چیزی پیدا نشد",
        cmdGoTo: "رفتن به", cmdTheme: "تغییر تم به", cmdLang: "تغییر زبان به",
        toastCopied: "کپی شد!", toastReset: "همه چیز ریست شد", toastExported: "خروجی دانلود شد",
        toastAlertTriggered: "🔔 هشدار فعال شد!",
        alertTriggered: "هشدار فعال شد!",
        todayHigh: "سقف ۲۴h", todayLow: "کف ۲۴h",
        navCmd: "پالت دستورات", navLang: "تغییر زبان",         navPortfolio: "پورتفولیو", navAlerts: "هشدارهای قیمت", navConvert: "تبدیل ارز",
        navThemes: "رنگ‌بندی‌ها", navSettings: "تنظیمات", navTheme: "تغییر تم روشن/تاریک",
        searchLabel: "جستجو در ارزها، طلا و رمزارز", clearSearch: "پاک کردن جستجو",
        filterGroup: "فیلتر دسته‌بندی", tabWatchAria: "علاقه‌مندی‌ها", newsFilterGroup: "فیلتر زبان خبر",
        refreshNow: "بروزرسانی قیمت‌ها", closeDialog: "بستن", chooseCurrency: "انتخاب ارز",
        addAction: "افزودن", swapAction: "جابجایی دو طرف", direction: "جهت هشدار",
        priceChart: "نمودار قیمت", compareChart: "مقایسه", watchItem: "افزودن/حذف از علاقه‌مندی‌ها",
        themeGroup: "انتخاب رنگ‌بندی", langGroup: "انتخاب زبان", cmdTitle: "پالت دستورات",
        cmpAction: "📊 مقایسه", alertAction: "🔔 هشدار",
    },
    en: {
        search: "Search currency, gold or crypto...",
        tabAll: "All", tabFiat: "Currency", tabCrypto: "Crypto", tabNews: "📰 News", tabWatch: "⭐",
        marketLabel: "Market", countLabel: "Symbols", updateLabel: "Updated",
        liveStatus: "Live prices (Polling 10s)",
        errTitle: "Failed to load prices", errSub: "Could not connect to server.",
        retry: "Retry", emptyTitle: "No results", emptySub: "Try a different search.",
        emptyWatchTitle: "No favorites yet", emptyWatchSub: "Tap the star ⭐ on any currency.",
        sourceText: "Prices from TGJU & CoinGecko", reportIssue: "Report issue",
        topGainers: "Top Gainers", topLosers: "Top Losers",
        volatileTitle: "Most volatile today",
        newsAll: "All", newsFa: "🇮🇷 Iranian", newsEn: "🌍 International",
        portfolioTitle: "💼 Portfolio", totalValue: "Total Value", totalPnl: "P&L",
        amountPh: "Amount", buyPh: "Buy Price", pricePh: "Price",
        alertsTitle: "🔔 Price Alerts", dirAbove: "Above", dirBelow: "Below",
        convTitle: "💱 Currency Converter", convAmount: "Amount", convFrom: "From", convTo: "To", convResult: "Result",
        convCurrency: "💱 Currency", convGold: "🥇 Gold",
        goldAmount: "Amount", goldUnit: "Unit", goldKarat: "Karat", goldTarget: "Convert to", goldResult: "Result",
        marketBull: "Bullish", marketBear: "Bearish", marketFlat: "Neutral",
        unit: "Toman", price: "Price", source: "Source",
        chartHigh: "High", chartLow: "Low", chartAvg: "Avg",
        chartType: "Type", beforeNow: "Earlier", nowLabel: "Now",
        fiatLabel: "Currency", cryptoLabel: "Crypto",
        agoNow: "Just now", agoMin: "min ago", agoHour: "hr ago", agoDay: "d ago",
        portEmpty: "No assets added yet", alertEmpty: "No alerts set yet",
        fngLabel: "Fear & Greed Index", pwaInstall: "Install app",
        tf1d: "1D", tf7d: "7D", tf30d: "30D", tf90d: "90D", tf1y: "1Y",
        share: "Share",
        compareTitle: "📊 Compare Currencies", cmpFirst: "First", cmpSecond: "Second",
        settingsTitle: "⚙️ Settings",
        setSound: "Alert sound", setSoundSub: "Play sound when alert triggers",
        setAutoDark: "Auto dark mode", setAutoDarkSub: "Enable at night (18:00–07:00)",
        setCompact: "Compact mode", setCompactSub: "Show smaller cards",
        setRefresh: "Refresh interval", setRefreshSub: "How often to update prices",
        setExportAll: "📥 Export all", setReset: "🗑 Reset",
        cmdSearch: "Search or run command...",
        cmdCurrencies: "Currencies", cmdActions: "Actions", cmdRecent: "Recent searches",
        cmdNoResults: "Nothing found",
        cmdGoTo: "Go to", cmdTheme: "Change theme to", cmdLang: "Change language to",
        toastCopied: "Copied!", toastReset: "All reset", toastExported: "Exported",
        toastAlertTriggered: "🔔 Alert triggered!",
        alertTriggered: "Alert triggered!",
        todayHigh: "24h High", todayLow: "24h Low",
        navCmd: "Command palette", navLang: "Change language",         navPortfolio: "Portfolio", navAlerts: "Price alerts", navConvert: "Currency converter",
        navThemes: "Color palettes", navSettings: "Settings", navTheme: "Switch light/dark theme",
        searchLabel: "Search currencies, gold and crypto", clearSearch: "Clear search",
        filterGroup: "Category filter", tabWatchAria: "Watchlist", newsFilterGroup: "News language filter",
        refreshNow: "Refresh prices", closeDialog: "Close", chooseCurrency: "Choose currency",
        addAction: "Add", swapAction: "Swap sides", direction: "Alert direction",
        priceChart: "Price chart", compareChart: "Compare", watchItem: "Add or remove from watchlist",
        themeGroup: "Choose palette", langGroup: "Choose language", cmdTitle: "Command palette",
        cmpAction: "📊 Compare", alertAction: "🔔 Alert",
    },
    ar: {
        search: "ابحث عن عملة أو ذهب أو عملة رقمية...",
        tabAll: "الكل", tabFiat: "العملات", tabCrypto: "العملات الرقمية", tabNews: "📰 الأخبار", tabWatch: "⭐",
        marketLabel: "السوق", countLabel: "الأصول", updateLabel: "التحديث",
        liveStatus: "الأسعار مباشرة",
        errTitle: "فشل تحميل الأسعار", errSub: "تعذر الاتصال بالخادم.",
        retry: "إعادة المحاولة", emptyTitle: "لا نتائج", emptySub: "جرب بحثاً آخر.",
        emptyWatchTitle: "لا مفضلات بعد", emptyWatchSub: "انقر على النجمة ⭐",
        sourceText: "الأسعار من TGJU و CoinGecko", reportIssue: "الإبلاغ عن مشكلة",
        topGainers: "الأعلى ربحاً", topLosers: "الأكثر خسارة",
        volatileTitle: "الأكثر تقلباً اليوم",
        newsAll: "الكل", newsFa: "🇮🇷 إيرانية", newsEn: "🌍 دولية",
        portfolioTitle: "💼 المحفظة", totalValue: "القيمة الإجمالية", totalPnl: "الربح/الخسارة",
        amountPh: "الكمية", buyPh: "سعر الشراء", pricePh: "السعر",
        alertsTitle: "🔔 تنبيهات الأسعار", dirAbove: "أعلى من", dirBelow: "أقل من",
        convTitle: "💱 محول العملات", convAmount: "المبلغ", convFrom: "من", convTo: "إلى", convResult: "النتيجة",
        convCurrency: "💱 عملات", convGold: "🥇 ذهب",
        goldAmount: "الكمية", goldUnit: "الوحدة", goldKarat: "العيار", goldTarget: "تحويل إلى", goldResult: "النتيجة",
        marketBull: "صاعد", marketBear: "هابط", marketFlat: "محايد",
        unit: "تومان", price: "السعر", source: "المصدر",
        chartHigh: "الأعلى", chartLow: "الأدنى", chartAvg: "المتوسط",
        chartType: "النوع", beforeNow: "سابقاً", nowLabel: "الآن",
        fiatLabel: "العملات", cryptoLabel: "العملات الرقمية",
        agoNow: "الآن", agoMin: "دقيقة", agoHour: "ساعة", agoDay: "يوم",
        portEmpty: "لم تضف أصولاً بعد", alertEmpty: "لم تضبط تنبيهات بعد",
        fngLabel: "مؤشر الخوف والجشع", pwaInstall: "ثبّت التطبيق",
        tf1d: "يوم", tf7d: "أسبوع", tf30d: "شهر", tf90d: "٩٠ يوم", tf1y: "سنة",
        share: "مشاركة",
        compareTitle: "📊 مقارنة العملات", cmpFirst: "الأولى", cmpSecond: "الثانية",
        settingsTitle: "⚙️ الإعدادات",
        setSound: "صوت التنبيه", setSoundSub: "تشغيل صوت عند التنبيه",
        setAutoDark: "الوضع الداكن التلقائي", setAutoDarkSub: "تفعيل ليلاً",
        setCompact: "الوضع المضغوط", setCompactSub: "بطاقات أصغر",
        setRefresh: "فترة التحديث", setRefreshSub: "معدل تحديث الأسعار",
        setExportAll: "📥 تصدير الكل", setReset: "🗑 إعادة تعيين",
        cmdSearch: "ابحث أو نفّذ...",
        cmdCurrencies: "العملات", cmdActions: "الأوامر", cmdRecent: "الأخيرة",
        cmdNoResults: "لا نتائج",
        cmdGoTo: "اذهب إلى", cmdTheme: "تغيير الثيم إلى", cmdLang: "تغيير اللغة إلى",
        toastCopied: "تم النسخ!", toastReset: "تمت إعادة التعيين", toastExported: "تم التصدير",
        toastAlertTriggered: "🔔 تم تفعيل التنبيه!",
        alertTriggered: "تم تفعيل التنبيه!",
        todayHigh: "أعلى ٢٤س", todayLow: "أدنى ٢٤س",
        navCmd: "لوحة الأوامر", navLang: "تغيير اللغة",         navPortfolio: "المحفظة", navAlerts: "تنبيهات الأسعار", navConvert: "محول العملات",
        navThemes: "الألوان", navSettings: "الإعدادات", navTheme: "تبديل الوضع الفاتح/الداكن",
        searchLabel: "ابحث في العملات والذهب والعملات الرقمية", clearSearch: "مسح البحث",
        filterGroup: "تصفية الفئات", tabWatchAria: "المفضلة", newsFilterGroup: "تصفية لغة الأخبار",
        refreshNow: "تحديث الأسعار", closeDialog: "إغلاق", chooseCurrency: "اختر العملة",
        addAction: "إضافة", swapAction: "تبديل الطرفين", direction: "اتجاه التنبيه",
        priceChart: "مخطط السعر", compareChart: "مقارنة", watchItem: "إضافة أو إزالة من المفضلة",
        themeGroup: "اختر النمط", langGroup: "اختر اللغة", cmdTitle: "لوحة الأوامر",
        cmpAction: "📊 مقارنة", alertAction: "🔔 تنبيه",
    }
};

function t(key) {
    return I18N[currentLang]?.[key] || I18N.fa[key] || key;
}

/* =========================================================
   WATCHLIST
========================================================= */

function isWatched(code) {
    return watchlist.includes(String(code || "").toLowerCase());
}

function toggleWatch(code) {
    code = String(code || "").toLowerCase();
    const idx = watchlist.indexOf(code);
    if (idx >= 0) watchlist.splice(idx, 1);
    else {
        watchlist.push(code);
        toast("⭐ " + (CURRENCIES_NAME[code] || code.toUpperCase()), "success");
    }
    localStorage.setItem("ex_watchlist", JSON.stringify(watchlist));
    haptic();
    applyFilter();
}

let CURRENCIES_NAME = {};

/* =========================================================
   FEAR & GREED
========================================================= */

function fngCls(v) {
    if (v <= 25) return "fear";
    if (v >= 75) return "greed";
    return "neutral";
}

function fngLabelOf(cls) {
    const map = {
        "Extreme Fear": { fa: "ترس شدید", en: "Extreme Fear", ar: "خوف شديد", emoji: "😱" },
        "Fear": { fa: "ترس", en: "Fear", ar: "خوف", emoji: "😨" },
        "Neutral": { fa: "خنثی", en: "Neutral", ar: "محايد", emoji: "😐" },
        "Greed": { fa: "طمع", en: "Greed", ar: "جشع", emoji: "😊" },
        "Extreme Greed": { fa: "طمع شدید", en: "Extreme Greed", ar: "جشع شديد", emoji: "🤑" },
    };
    const item = map[cls] || map["Neutral"];
    return { label: item[currentLang] || item.fa, emoji: item.emoji };
}

async function loadFearGreed() {
    try {
        const res = await fetch(api("/api/fear_greed?_=" + Date.now()), { cache: "no-store" });
        const data = await res.json();
        if (!data.success || !data.data) return;
        fngData = data.data;
        renderFng();
    } catch (e) {}
}

function renderFng() {
    if (!fngData || !fngBar) return;
    const v = Math.max(0, Math.min(100, Number(fngData.value) || 50));
    const meta = fngLabelOf(fngData.classification);
    fngBar.classList.add("on");
    if (fngMarker) fngMarker.style.left = v + "%";
    if (fngVal) fngVal.textContent = v;
    if (fngClass) {
        fngClass.textContent = meta.label;
        fngClass.className = "fng-class " + fngCls(v);
    }
    const ico = fngBar.querySelector(".fng-ico");
    if (ico) ico.textContent = meta.emoji;
}

/* =========================================================
   I18N APPLY + THEME
========================================================= */

function setLiveStatus(online) {
    wsConnected = online;
    const live = document.querySelector("#statusBar .live");
    if (!live) return;
    live.textContent = online ? t("liveStatus") : t("errSub");
    live.style.color = online ? "" : "var(--dim)";
}

function applyI18n() {
    document.documentElement.lang = currentLang;
    document.body.classList.remove("lang-fa", "lang-en", "lang-ar");
    document.body.classList.add("lang-" + currentLang);

    const isRTL = currentLang === "fa" || currentLang === "ar";
    document.documentElement.dir = isRTL ? "rtl" : "ltr";
    document.body.dir = isRTL ? "rtl" : "ltr";

    document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
        el.placeholder = t(el.dataset.i18nPlaceholder);
    });
    document.querySelectorAll("[data-i18n]").forEach(el => {
        const val = t(el.dataset.i18n);
        if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") el.placeholder = val;
        else el.textContent = val;
    });
    document.querySelectorAll("[data-i18n-aria]").forEach(el => {
        el.setAttribute("aria-label", t(el.dataset.i18nAria));
    });
    categoryTabs.forEach(tab => tab.setAttribute("aria-pressed", String(tab.dataset.category === activeCategory)));
    newsChips.forEach(chip => chip.setAttribute("aria-pressed", String(chip.dataset.lang === newsLang)));
    document.querySelectorAll("#langPop button").forEach(b => {
        b.classList.toggle("active", b.dataset.lang === currentLang);
    });

    setLiveStatus(wsConnected);
    renderFng();
    applyFilter();
    renderTopMovers();
    renderVolatility();
    renderTicker(currencies);
    if (marketStatus) {
        const st = marketStatusOf(currencies);
        marketStatus.textContent = st.text;
    }
    if (modal && modal.classList.contains("on") && currentChart) renderModal();
}

function setLang(lang) {
    if (!I18N[lang]) return;
    currentLang = lang;
    localStorage.setItem("ex_lang", lang);
    applyI18n();
    haptic();
}

function setTheme(th) {
    currentTheme = th;
    document.body.classList.toggle("dark", th === "dark");
    localStorage.setItem("ex_theme", th);
    if (themeToggle) {
        themeToggle.textContent = th === "dark" ? "🌙" : "☀️";
        themeToggle.setAttribute("aria-pressed", th === "dark" ? "true" : "false");
    }
}

function setPalette(p) {
    currentPalette = p;
    document.body.setAttribute("data-theme", p);
    localStorage.setItem("ex_palette", p);
    document.querySelectorAll(".swatch").forEach(s => {
        const on = s.dataset.theme === p;
        s.classList.toggle("on", on);
        s.setAttribute("aria-pressed", on ? "true" : "false");
    });
}

function applyAutoDark() {
    if (!settings.autoDark) return;
    const h = new Date().getHours();
    const shouldBeDark = h >= 18 || h < 7;
    setTheme(shouldBeDark ? "dark" : "light");
}

function applyCompact() {
    document.body.classList.toggle("compact", settings.compact);
}

/* =========================================================
   AVATARS
========================================================= */

const ISO = {
    usd:"US", eur:"EU", gbp:"GB", aed:"AE", try:"TR", chf:"CH",
    cny:"CN", jpy:"JP", krw:"KR", cad:"CA", aud:"AU", rub:"RU",
    inr:"IN", iqd:"IQ", afn:"AF", sar:"SA", qar:"QA", kwd:"KW",
    bhd:"BH", omr:"OM", hkd:"HK", myr:"MY", thb:"TH", nzd:"NZ"
};

const FIAT_C = {
    usd:"#1e3a5f", eur:"#1e2f5f", gbp:"#3a1e5f", aed:"#1e5f3a",
    try:"#5f2e1e", chf:"#3a3a3a", cny:"#5f1e1e", jpy:"#5f1e3a",
    krw:"#1e3a5f", cad:"#3a1e4a", aud:"#1e4a5f", rub:"#5f3a1e",
    inr:"#5f4a1e", iqd:"#4a3a1e", afn:"#4a1e1e", sar:"#1e5f2e",
    qar:"#3a1e5f", kwd:"#2e5f1e", bhd:"#4a2e1e", omr:"#5f2e2e",
    hkd:"#5f1e1e", myr:"#1e5f5f", thb:"#5f1e3a", nzd:"#1e4a3a"
};

const CRYPTO_C = {
    btc:"#f7931a", eth:"#627eea", usdt:"#26a17b", usdc:"#2775ca",
    ton:"#0098ea", trx:"#eb0029", sol:"#9945ff", xrp:"#23292f",
    doge:"#c2a633", ada:"#0033ad", shib:"#f00500", dot:"#e6007a",
    ltc:"#345d9d", bnb:"#f0b90b", avax:"#e84142", link:"#2a5ada",
    uni:"#ff007a", xlm:"#14b6e7", xmr:"#ff6600", bch:"#8dc351",
    near:"#00c1de", matic:"#8247e5", arb:"#12aaff", op:"#ff0420",
    atom:"#2e3148", pepe:"#3d8130", sui:"#4da2ff", apt:"#000000",
    tia:"#7b2bf9", sei:"#9e1f19"
};

function avatarHtml(c, big) {
    const code = String(c.code || "").toLowerCase();
    const cls = "c-ico" + (big ? " big" : "");
    let bg;
    if (c.type === "crypto") bg = CRYPTO_C[code] || "#2a2d35";
    else if (code.startsWith("gold")) bg = "linear-gradient(135deg, #b8860b, #ffd700, #fbbf24)";
    else if (code === "silver") bg = "linear-gradient(135deg, #6b7280, #d1d5db, #9ca3af)";
    else bg = FIAT_C[code] || "#2e3a4a";

    if (c.flag && /\p{Emoji}/u.test(c.flag)) {
        const fs = big ? "26px" : "19px";
        return '<div class="' + cls + '" style="background:' + bg + ';font-size:' + fs + ';text-shadow:0 1px 2px rgba(0,0,0,0.3)">' + esc(c.flag) + '</div>';
    }
    const label = ISO[code] || code.slice(0, 2).toUpperCase();
    return '<div class="' + cls + '" style="background:' + bg + '">' + esc(label) + '</div>';
}

/* =========================================================
   CHART HELPERS
========================================================= */

function hash(s) { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0; return h || 1; }

function seededRand(seed) {
    let x = seed;
    return function () {
        x ^= x << 13; x >>>= 0; x ^= x >> 17; x ^= x << 5; x >>>= 0;
        return (x % 1000) / 1000;
    };
}

function smoothArr(values, passes) {
    passes = passes || 2;
    let out = values.slice();
    for (let p = 0; p < passes; p++) {
        if (out.length < 3) break;
        const nxt = [out[0]];
        for (let i = 1; i < out.length - 1; i++) nxt.push((out[i-1] + out[i]*2 + out[i+1]) / 4);
        nxt.push(out[out.length - 1]);
        out = nxt;
    }
    return out;
}

function resample(values, target) {
    if (values.length < 2) return values.slice();
    if (values.length === target) return values.slice();
    const out = [];
    const n = values.length - 1;
    for (let i = 0; i < target; i++) {
        const tt = i / (target - 1);
        const pos = tt * n;
        const idx = Math.floor(pos);
        const frac = pos - idx;
        if (idx >= n) out.push(values[n]);
        else out.push(values[idx] * (1 - frac) + values[idx + 1] * frac);
    }
    return out;
}

function synthPoints(code, cls, count) {
    count = count || 60;
    const r = seededRand(hash(code));
    const drift = cls === "up" ? 0.5 : cls === "dn" ? -0.5 : 0;
    const out = [];
    let v = 50 + (r() - 0.5) * 8;
    for (let i = 0; i < count; i++) {
        v += drift + (r() - 0.5) * 2.2;
        v = Math.max(15, Math.min(85, v));
        out.push(v);
    }
    return smoothArr(out, 2);
}

function prepareChartPoints(raw, code, cls, targetCount) {
    targetCount = targetCount || 60;
    if (raw && raw.length >= 8) {
        let vals = raw.map(Number).filter(Number.isFinite);
        if (vals.length >= 8) {
            const sorted = [...vals].sort((a, b) => a - b);
            const median = sorted[Math.floor(sorted.length / 2)];
            if (median > 0) vals = vals.filter(v => v >= median * 0.5 && v <= median * 2.0);
            if (vals.length >= 8) {
                vals = smoothArr(vals, 1);
                vals = resample(vals, targetCount);
                vals = smoothArr(vals, 2);
                return vals;
            }
        }
    }
    return synthPoints(code, cls, targetCount);
}

function sparkSvg(values, cls) {
    if (!values || !values.length) return "";
    const w = 100, h = 32;
    let scaled;
    if (values.length > 1) {
        const min = Math.min(...values), max = Math.max(...values);
        const range = max - min;
        scaled = range === 0 ? values.map(() => 50) : values.map(v => 8 + ((v - min) / range) * 84);
    } else scaled = [50];
    const step = scaled.length > 1 ? w / (scaled.length - 1) : 0;
    const line = scaled.map((p, i) => (i === 0 ? "M" : "L") + " " + (i * step).toFixed(1) + " " + (h - (p / 100) * h).toFixed(1)).join(" ");
    const fill = line + " L " + w + " " + h + " L 0 " + h + " Z";
    return '<div class="c-spark ' + cls + '"><svg viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="none"><path class="fl" d="' + fill + '"></path><path class="ln" d="' + line + '"></path></svg></div>';
}

function bigChartSvg(values, cls, live, loading) {
    if (!values || values.length < 2) return "";
    const w = 300, h = 180;
    const padTop = 14, padBottom = 14;
    const chartH = h - padTop - padBottom;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const padding = range * 0.18;
    const yMin = min - padding;
    const yMax = max + padding;
    const yRange = yMax - yMin;
    const step = values.length > 1 ? w / (values.length - 1) : 0;
    const coords = values.map((v, i) => {
        const x = i * step;
        const y = padTop + chartH - ((v - yMin) / yRange) * chartH;
        return [x, y];
    });
    const linePath = coords.map(([x, y], i) => (i === 0 ? "M" : "L") + " " + x.toFixed(2) + " " + y.toFixed(2)).join(" ");
    const fillPath = linePath + " L " + w + " " + h + " L 0 " + h + " Z";
    let grid = "";
    for (let i = 1; i <= 4; i++) {
        const y = padTop + (chartH * i / 5);
        grid += '<line class="grid" x1="0" y1="' + y.toFixed(1) + '" x2="' + w + '" y2="' + y.toFixed(1) + '"/>';
    }
    const minIdx = values.indexOf(min);
    const maxIdx = values.indexOf(max);
    const minPoint = coords[minIdx];
    const maxPoint = coords[maxIdx];
    const dots = '<circle class="dot dot-min" cx="' + minPoint[0].toFixed(1) + '" cy="' + minPoint[1].toFixed(1) + '" r="3"/><circle class="dot dot-max" cx="' + maxPoint[0].toFixed(1) + '" cy="' + maxPoint[1].toFixed(1) + '" r="3"/>';
    const endPoint = coords[coords.length - 1];
    const endDot = live
        ? '<circle class="dot dot-end" cx="' + endPoint[0].toFixed(1) + '" cy="' + endPoint[1].toFixed(1) + '" r="4"/>'
        : '<circle class="dot" cx="' + endPoint[0].toFixed(1) + '" cy="' + endPoint[1].toFixed(1) + '" r="4"/>';
    const gradId = "grad-" + Math.random().toString(36).slice(2, 8);
    const liveBadge = live ? '<div class="m-chart-live-badge">● LIVE</div>' : "";
    const loadingCls = loading ? " loading-chart" : "";
    return '<div class="m-chart ' + cls + loadingCls + '">' + liveBadge +
        '<svg viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="none">' +
            '<defs><linearGradient id="' + gradId + '" x1="0" y1="0" x2="0" y2="1">' +
                '<stop offset="0%" stop-color="currentColor" stop-opacity="0.35"/>' +
                '<stop offset="100%" stop-color="currentColor" stop-opacity="0.02"/>' +
            '</linearGradient></defs>' + grid +
            '<path class="fl" d="' + fillPath + '" fill="url(#' + gradId + ')"/>' +
            '<path class="ln" d="' + linePath + '"/>' + dots + endDot +
        '</svg></div>';
}

/* =========================================================
   CARD
========================================================= */

function getHistory(c) {
    for (const k of ["history", "history_7d", "week_history"]) {
        const a = c[k];
        if (Array.isArray(a) && a.length >= 2) {
            const vals = a.map(v => typeof v === "object" ? (v.price ?? v.value) : v).map(Number).filter(Number.isFinite);
            if (vals.length >= 2) return vals;
        }
    }
    return null;
}

function marketStatusOf(list) {
    const f = list.filter(c => Number.isFinite(Number(c.change)) && Number(c.change) !== 0);
    if (!f.length) return { text: t("marketFlat"), cls: "" };
    const up = f.filter(c => Number(c.change) > 0).length;
    const dn = f.filter(c => Number(c.change) < 0).length;
    if (up > dn * 1.4) return { text: t("marketBull"), cls: "bull" };
    if (dn > up * 1.4) return { text: t("marketBear"), cls: "bear" };
    return { text: t("marketFlat"), cls: "" };
}

function cardInnerHtml(c) {
    const code = String(c.code || "");
    const codeLc = code.toLowerCase();
    const name = c.name || code.toUpperCase();
    const price = c.price ?? "";
    const usdPrice = c.usd_price;
    const source = c.source || "TGJU";
    const trend = trendOf(c.change);
    const watched = isWatched(codeLc);
    const rawHistory = getHistory(c);
    const points = prepareChartPoints(rawHistory, codeLc, trend.cls, 40);
    const sparkHtml = sparkSvg(points, trend.cls);
    const usdHtml = c.type === "crypto"
        ? '<div class="c-usd">$ <b class="mono">' + esc(fmtUsd(usdPrice)) + '</b></div>' : "";
    const nPrice = Number(price);
    const prev = prevPrices[codeLc];
    let flash = "", deltaBubble = "";
    if (Number.isFinite(nPrice) && prev !== undefined && prev !== nPrice) {
        const diff = nPrice - prev;
        flash = diff > 0 ? "flash-up" : "flash-dn";
        const diffAbs = Math.abs(diff);
        let diffStr;
        if (diffAbs >= 1000) diffStr = Math.round(diffAbs).toLocaleString("en-US");
        else if (diffAbs >= 1) diffStr = diffAbs.toFixed(0);
        else diffStr = diffAbs.toFixed(2);
        const sign = diff > 0 ? "+" : "-";
        const cls = diff > 0 ? "up" : "dn";
        deltaBubble = '<span class="delta-bubble ' + cls + '">' + sign + diffStr + '</span>';
    }
    const typeLabel = c.type === "crypto" ? t("cryptoLabel") : t("fiatLabel");

    // محاسبه سقف/کف ۲۴ ساعته از history
    let high24 = "—", low24 = "—";
    if (points && points.length) {
        high24 = fmtNum(Math.max(...points));
        low24 = fmtNum(Math.min(...points));
    }

    const detailsHtml = '<div class="c-det"><div class="d-row"><span>' + t("source") + '</span><b>' + esc(source) + '</b></div><div class="d-row"><span>' + t("chartType") + '</span><b>' + esc(typeLabel) + '</b></div><div class="d-row"><span>' + t("todayHigh") + '</span><b class="mono">' + high24 + '</b></div><div class="d-row"><span>' + t("todayLow") + '</span><b class="mono">' + low24 + '</b></div></div>';
    const html =
        '<button class="chart-btn" type="button">📈</button>' +
        '<button class="cmp-btn" type="button" title="Compare">📊</button>' +
        '<div class="c-head"><div class="c-coin">' + avatarHtml(c) +
            '<div class="c-meta"><span class="c-name">' + esc(name) + '</span>' +
            '<span class="c-sub">' + esc(code.toUpperCase()) + '</span></div></div>' +
            '<button class="star-btn ' + (watched ? "on" : "") + '" type="button">' + (watched ? "★" : "☆") + '</button>' +
            '<div class="c-chg ' + trend.cls + '">' + esc(trend.text) + '</div></div>' +
        sparkHtml +
        '<div class="c-price">' + deltaBubble +
            '<span class="lbl">' + t("price") + '</span>' +
            '<div class="vl mono ' + flash + '">' + fmtNum(price) + '<span class="un">' + t("unit") + '</span></div></div>' +
        usdHtml +
        '<div class="c-foot"><span>' + t("source") + ': ' + esc(source) + '</span></div>' + detailsHtml;
    return html;
}

/* =========================================================
   CARD DOM — به‌روزرسانی درجای کارت‌ها به‌جای ساخت مجدد گرید
========================================================= */

let firstPaintDone = false;   // در رندرهای بعدی، انیمیشن ورود پخش نمی‌شود

function flashStateOf(c) {
    const price = Number(c.price);
    const prev = prevPrices[String(c.code || "").toLowerCase()];
    if (!Number.isFinite(price) || prev === undefined || prev === price) return "";
    return price > prev ? "up" : "dn";
}

/* امضای محتوای کارت: اگر تغییر نکرده باشد، DOM دست‌نخورده می‌ماند */
function cardSignature(c) {
    const history = getHistory(c);
    return [
        c.price, c.change, c.usd_price || "", c.source || "",
        isWatched(c.code) ? 1 : 0, flashStateOf(c),
        currentLang, settings.compact ? 1 : 0,
        Array.isArray(history) ? history.length : 0,
    ].join("|");
}

function wireCard(card, c) {
    const codeLc = String(c.code || "").toLowerCase();
    const label = c.name || codeLc;
    const chartBtn = card.querySelector(".chart-btn");
    if (chartBtn) {
        chartBtn.setAttribute("aria-label", t("priceChart") + " — " + label);
        chartBtn.addEventListener("click", (e) => { e.stopPropagation(); openChart(c); });
    }
    const cmpBtn = card.querySelector(".cmp-btn");
    if (cmpBtn) {
        cmpBtn.setAttribute("aria-label", t("compareChart") + " — " + label);
        cmpBtn.addEventListener("click", (e) => { e.stopPropagation(); openCompare(codeLc); });
    }
    const starBtn = card.querySelector(".star-btn");
    if (starBtn) {
        starBtn.setAttribute("aria-pressed", isWatched(codeLc) ? "true" : "false");
        starBtn.setAttribute("aria-label", t("watchItem") + " " + label);
        starBtn.addEventListener("click", (e) => { e.stopPropagation(); toggleWatch(codeLc); });
    }
}

function createCard(c) {
    const card = document.createElement("article");
    card.className = "card" + (firstPaintDone ? " reveal" : "");
    card.dataset.code = String(c.code || "").toLowerCase();
    card.dataset.sig = cardSignature(c);
    card.innerHTML = cardInnerHtml(c);
    card.addEventListener("click", () => { card.classList.toggle("expanded"); haptic(); });
    wireCard(card, c);
    return card;
}

/* فقط کارت‌هایی که محتوایشان عوض شده بازسازی می‌شوند */
function updateCard(card, c) {
    const sig = cardSignature(c);
    if (card.dataset.sig === sig) return;
    card.dataset.sig = sig;
    card.innerHTML = cardInnerHtml(c);
    wireCard(card, c);
}

function renderTicker(list) {
    if (!tickerTrack) return;
    if (!list.length) { tickerTrack.innerHTML = ""; return; }
    const picked = list.slice(0, 12);
    const html = picked.map(c => {
        const tr = trendOf(c.change);
        const flag = c.flag || "💱";
        return '<div class="tick">' +
            '<span class="tf">' + esc(flag) + '</span>' +
            '<span class="nm">' + esc(c.name || c.code) + '</span>' +
            '<span class="vl mono">' + fmtNum(c.price) + '</span>' +
            '<span class="ch ' + tr.cls + '">' + esc(tr.text) + '</span>' +
        '</div>';
    }).join("");
    tickerTrack.innerHTML = html + html;
}

/* =========================================================
   TOP MOVERS
========================================================= */

function renderTopMovers() {
    if (!gainersList || !losersList) return;
    const valid = currencies.filter(c => Number.isFinite(Number(c.change)) && Number(c.change) !== 0 && Number(c.price) > 0);
    if (!valid.length) {
        gainersList.innerHTML = '<div class="port-empty">—</div>';
        losersList.innerHTML = '<div class="port-empty">—</div>';
        if (gainersCount) gainersCount.textContent = "0";
        if (losersCount) losersCount.textContent = "0";
        return;
    }
    const sorted = [...valid].sort((a, b) => Number(b.change) - Number(a.change));
    const gainers = sorted.filter(c => Number(c.change) > 0).slice(0, 5);
    const losers = sorted.filter(c => Number(c.change) < 0).slice(-5).reverse();
    if (gainersCount) gainersCount.textContent = gainers.length;
    if (losersCount) losersCount.textContent = losers.length;
    const buildRow = (c) => {
        const chg = Number(c.change);
        const cls = chg > 0 ? "up" : "dn";
        const flag = c.flag || "💱";
        const name = c.short || c.name || c.code.toUpperCase();
        const sign = chg > 0 ? "+" : "";
        return '<a class="mover-row" href="#" data-code="' + esc(c.code) + '"><div class="mr-flag">' + esc(flag) + '</div><div class="mr-name">' + esc(name) + '</div><div class="mr-chg ' + cls + '">' + sign + Number(chg).toFixed(2) + '%</div></a>';
    };
    gainersList.innerHTML = gainers.length ? gainers.map(buildRow).join("") : '<div class="port-empty">—</div>';
    losersList.innerHTML = losers.length ? losers.map(buildRow).join("") : '<div class="port-empty">—</div>';
    document.querySelectorAll(".mover-row").forEach(row => {
        row.addEventListener("click", (e) => {
            e.preventDefault();
            const code = row.dataset.code;
            const c = currencies.find(x => x.code === code);
            if (c) openChart(c);
        });
    });
}

/* =========================================================
   VOLATILITY
========================================================= */

function renderVolatility() {
    if (!volList || !volatilitySection) return;
    if (volatilitySection.style.display === "none") return;
    const valid = currencies
        .filter(c => Number.isFinite(Number(c.change)) && Number(c.price) > 0)
        .map(c => ({ ...c, abs: Math.abs(Number(c.change)) }))
        .sort((a, b) => b.abs - a.abs)
        .slice(0, 12);
    if (!valid.length) { volList.innerHTML = '<div class="port-empty">—</div>'; return; }
    const maxAbs = valid[0].abs || 1;
    volCount.textContent = valid.length;
    volList.innerHTML = valid.map(c => {
        const pct = Math.min(100, (c.abs / maxAbs) * 100);
        const cls = Number(c.change) > 0 ? "up" : "dn";
        const sign = Number(c.change) > 0 ? "+" : "";
        return '<div class="vol-item" data-code="' + esc(c.code) + '">' +
            '<div class="vi-top"><span>' + esc(c.flag || "💱") + '</span><span>' + esc(c.short || c.code) + '</span></div>' +
            '<div class="vi-bar"><div class="vi-fill" style="width:' + pct + '%"></div></div>' +
            '<div class="vi-val ' + cls + '">' + sign + Number(c.change).toFixed(2) + '%</div>' +
        '</div>';
    }).join("");
    volList.querySelectorAll(".vol-item").forEach(item => {
        item.addEventListener("click", () => {
            const c = currencies.find(x => x.code === item.dataset.code);
            if (c) openChart(c);
        });
    });
}

function toggleVolatility() {
    const hidden = volatilitySection.style.display === "none";
    volatilitySection.style.display = hidden ? "block" : "none";
    if (hidden) renderVolatility();
}

/* =========================================================
   COMPARE
========================================================= */

function openCompare(code) {
    if (!compareModal) return;
    fillCompareSelects();
    if (code) {
        if (!cmpA.value) cmpA.value = code;
        else if (!cmpB.value || cmpB.value === code) cmpB.value = code;
    }
    if (!cmpA.value && currencies[0]) cmpA.value = currencies[0].code;
    if (!cmpB.value && currencies[1]) cmpB.value = currencies[1].code;
    compareState.a = cmpA.value;
    compareState.b = cmpB.value;
    renderCompare();
    openModal(compareModal, "#cmpClose");
    haptic();
}

function closeCompare() {
    closeModal(compareModal);
}

function fillCompareSelects() {
    if (!cmpA || !cmpB) return;
    const build = () => currencies.map(c => '<option value="' + esc(c.code) + '">' + esc(c.flag || "💱") + ' ' + esc(c.name || c.code) + '</option>').join("");
    const aVal = cmpA.value, bVal = cmpB.value;
    cmpA.innerHTML = build();
    cmpB.innerHTML = build();
    if (aVal) cmpA.value = aVal;
    if (bVal) cmpB.value = bVal;
}

function renderCompare() {
    if (!compareState.a || !compareState.b) return;
    const a = currencies.find(c => c.code === compareState.a);
    const b = currencies.find(c => c.code === compareState.b);
    if (!a || !b) return;

    const aPts = prepareChartPoints(getHistory(a), a.code, trendOf(a.change).cls, 60);
    const bPts = prepareChartPoints(getHistory(b), b.code, trendOf(b.change).cls, 60);

    // نرمال‌سازی به ۱۰۰
    const norm = (arr) => {
        if (!arr.length) return [];
        const base = arr[0];
        return arr.map(v => (v / base) * 100);
    };
    const aN = norm(aPts);
    const bN = norm(bPts);

    const allMin = Math.min(...aN, ...bN);
    const allMax = Math.max(...aN, ...bN);
    const range = allMax - allMin || 1;

    const W = 300, H = 220, padT = 15, padB = 15;
    const chartH = H - padT - padB;

    const makePath = (arr, color) => {
        if (arr.length < 2) return "";
        const step = W / (arr.length - 1);
        return arr.map((v, i) => {
            const x = i * step;
            const y = padT + chartH - ((v - allMin) / range) * chartH;
            return (i === 0 ? "M" : "L") + " " + x.toFixed(1) + " " + y.toFixed(1);
        }).join(" ");
    };

    const aColor = "#10a86a";
    const bColor = "#d6409f";

    cmpChart.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none">' +
        '<path d="' + makePath(aN, aColor) + '" fill="none" stroke="' + aColor + '" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>' +
        '<path d="' + makePath(bN, bColor) + '" fill="none" stroke="' + bColor + '" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>' +
    '</svg>';

    const ta = trendOf(a.change), tb = trendOf(b.change);
    cmpLegend.innerHTML =
        '<div class="cmp-legend-item"><span class="clr-box" style="background:' + aColor + '"></span><span class="cl-name">' + esc(a.short || a.code) + '</span><span class="cl-val ' + ta.cls + '">' + esc(ta.text) + '</span></div>' +
        '<div class="cmp-legend-item"><span class="clr-box" style="background:' + bColor + '"></span><span class="cl-name">' + esc(b.short || b.code) + '</span><span class="cl-val ' + tb.cls + '">' + esc(tb.text) + '</span></div>';

    const aHigh = aPts.length ? Math.max(...aPts) : 0;
    const bHigh = bPts.length ? Math.max(...bPts) : 0;
    const aLow = aPts.length ? Math.min(...aPts) : 0;
    const bLow = bPts.length ? Math.min(...bPts) : 0;
    const aVol = aPts.length > 1 ? ((aHigh - aLow) / aLow * 100) : 0;
    const bVol = bPts.length > 1 ? ((bHigh - bLow) / bLow * 100) : 0;
    const diff = Math.abs(Number(a.change) - Number(b.change));

    cmpTable.innerHTML =
        '<div class="header">—</div>' +
        '<div class="header">' + esc(a.short || a.code) + '</div>' +
        '<div class="header">' + esc(b.short || b.code) + '</div>' +
        '<div>قیمت</div><div class="val">' + fmtNum(a.price) + '</div><div class="val">' + fmtNum(b.price) + '</div>' +
        '<div>تغییر</div><div class="val ' + ta.cls + '">' + Number(a.change).toFixed(2) + '%</div><div class="val ' + tb.cls + '">' + Number(b.change).toFixed(2) + '%</div>' +
        '<div>سقف</div><div class="val">' + fmtNum(aHigh) + '</div><div class="val">' + fmtNum(bHigh) + '</div>' +
        '<div>کف</div><div class="val">' + fmtNum(aLow) + '</div><div class="val">' + fmtNum(bLow) + '</div>' +
        '<div>نوسان</div><div class="val">' + aVol.toFixed(2) + '%</div><div class="val">' + bVol.toFixed(2) + '%</div>' +
        '<div>اختلاف</div><div class="val" style="grid-column:span 2; text-align:center">' + diff.toFixed(2) + '%</div>';
}

/* =========================================================
   REVEAL
========================================================= */

let revealObserver = null;
let revealIndexCounter = 0;

function initRevealObserver() {
    if (!("IntersectionObserver" in window)) {
        document.querySelectorAll(".card:not(.reveal)").forEach(c => c.classList.add("reveal"));
        return;
    }
    if (!revealObserver) {
        revealObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const el = entry.target;
                    const delay = parseFloat(el.dataset.revealDelay || "0");
                    setTimeout(() => el.classList.add("reveal"), delay);
                    revealObserver.unobserve(el);
                }
            });
        }, { root: null, rootMargin: "0px 0px -50px 0px", threshold: 0.05 });
    }
    revealIndexCounter = 0;
    document.querySelectorAll(".card:not(.reveal)").forEach((el) => {
        const delay = Math.min(revealIndexCounter * 40, 300);
        el.dataset.revealDelay = delay;
        revealIndexCounter++;
        revealObserver.observe(el);
    });
}

function renderGroup(el, list) {
    if (!el) return;
    if (!list.length) { el.innerHTML = ""; el.style.display = "none"; return; }
    el.style.display = "grid";

    // اگر همان کارت‌ها با همان ترتیب هستند، فقط محتوای تغییرکرده را به‌روز کن؛
    // این‌طور در هر پول‌ینگ کل گرید بازسازی و انیمیشن ورود دوباره پخش نمی‌شود.
    const existing = el.children;
    let reusable = existing.length === list.length;
    if (reusable) {
        for (let i = 0; i < list.length; i++) {
            if (existing[i].dataset.code !== String(list[i].code || "").toLowerCase()) { reusable = false; break; }
        }
    }
    if (reusable) {
        for (let i = 0; i < list.length; i++) updateCard(existing[i], list[i]);
        return;
    }

    el.innerHTML = "";
    const frag = document.createDocumentFragment();
    list.forEach(c => frag.appendChild(createCard(c)));
    el.appendChild(frag);
    setTimeout(initRevealObserver, 30);
}

function renderAll(list) {
    const fiat = list.filter(c => c.type !== "crypto");
    const crypto = list.filter(c => c.type === "crypto");
    renderGroup(fiatGrid, fiat);
    renderGroup(cryptoGrid, crypto);
    if (emptyState) {
        const isEmpty = !list.length;
        emptyState.classList.toggle("on", isEmpty);
        if (isEmpty) {
            const h = emptyState.querySelector("h3");
            const p = emptyState.querySelector("p");
            if (activeCategory === "watchlist") {
                if (h) h.textContent = t("emptyWatchTitle");
                if (p) p.textContent = t("emptyWatchSub");
            } else {
                if (h) h.textContent = t("emptyTitle");
                if (p) p.textContent = t("emptySub");
            }
        }
    }
    if (currencyCount) currencyCount.textContent = fmtNum(list.length);
}

function applyFilter() {
    const q = (searchInput?.value || "").trim().toLowerCase();
    if (clearSearch) clearSearch.classList.toggle("on", !!q);

    if (activeCategory === "news") {
        if (fiatGrid) fiatGrid.style.display = "none";
        if (cryptoGrid) cryptoGrid.style.display = "none";
        if (statsBar) statsBar.style.display = "none";
        if (statusBar) statusBar.style.display = "none";
        const movers = document.getElementById("moversSection");
        if (movers) movers.style.display = "none";
        if (volatilitySection) volatilitySection.style.display = "none";
        if (newsSection) newsSection.style.display = "block";
        if (emptyState) emptyState.classList.remove("on");
        loadNews();
        return;
    }

    if (newsSection) newsSection.style.display = "none";
    if (statsBar) statsBar.style.display = "grid";
    if (statusBar) statusBar.style.display = "flex";
    const movers = document.getElementById("moversSection");
    if (movers) movers.style.display = "grid";

    let list = currencies;
    if (activeCategory === "watchlist") list = list.filter(c => isWatched(c.code));
    else if (activeCategory !== "all") list = list.filter(c => (c.type || "fiat") === activeCategory);

    if (q) list = list.filter(c => {
        const code = String(c.code || "").toLowerCase();
        const name = String(c.name || "").toLowerCase();
        return code.includes(q) || name.includes(q);
    });

    if (activeCategory === "all") {
        list = [...list].sort((a, b) => {
            const aw = isWatched(a.code) ? 0 : 1;
            const bw = isWatched(b.code) ? 0 : 1;
            return aw - bw;
        });
    }
    renderAll(list);
}

/* =========================================================
   CHART MODAL
========================================================= */

async function fetchHistory(code, days) {
    try {
        const res = await fetch(api(`/api/history?code=${encodeURIComponent(code)}&days=${days}&_=${Date.now()}`), { cache: "no-store" });
        const data = await res.json();
        if (data.success && Array.isArray(data.prices)) return data.prices;
    } catch (e) {}
    return null;
}

async function setTimeframe(tf) {
    if (!currentChart || timeframeLoading) return;
    const daysMap = { "1d": 1, "7d": 7, "30d": 30, "90d": 90, "1y": 365 };
    const days = daysMap[tf] || 7;
    currentTimeframe = tf;
    timeframeLoading = true;
    modalPanel?.querySelectorAll(".tf-btn").forEach(b => {
        b.classList.toggle("on", b.dataset.tf === tf);
        b.disabled = true;
    });
    const chartEl = modalPanel?.querySelector(".m-chart");
    if (chartEl) chartEl.classList.add("loading-chart");
    try {
        const prices = await fetchHistory(currentChart.code, days);
        if (prices && prices.length >= 2) {
            liveChartData = prepareChartPoints(prices, currentChart.code, trendOf(currentChart.change).cls, 100);
        } else if (!liveChartData.length) {
            liveChartData = synthPoints(currentChart.code, trendOf(currentChart.change).cls, 80);
        }
    } catch (e) {}
    timeframeLoading = false;
    renderModal();
    haptic();
}

function openChart(currency) {
    currentChart = currency;
    currentTimeframe = "7d";
    const history = getHistory(currency);
    if (history && history.length >= 8) {
        liveChartData = prepareChartPoints(history, currency.code, trendOf(currency.change).cls, 60);
    } else {
        liveChartData = synthPoints(currency.code, trendOf(currency.change).cls, 60);
    }
    renderModal();
    openModal(modal, "#modalClose");
    haptic();
}

function closeChart() {
    closeModal(modal);
    currentChart = null;
    liveChartData = [];
    currentTimeframe = "7d";
    timeframeLoading = false;
}

function appendLiveChartPoint(price) {
    if (!Number.isFinite(price)) return;
    if (!liveChartData.length) return;
    if (currentTimeframe !== "1d" && currentTimeframe !== "7d") return;
    liveChartData.push(price);
    if (liveChartData.length > liveChartMaxPoints) liveChartData = liveChartData.slice(-liveChartMaxPoints);
}

function renderModal() {
    if (!currentChart || !modalPanel) return;
    const c = currentChart;
    const code = String(c.code || "");
    const name = c.name || code.toUpperCase();
    const price = c.price ?? "";
    const trend = trendOf(c.change);
    const typeLabel = c.type === "crypto" ? t("cryptoLabel") : t("fiatLabel");
    const watched = isWatched(code.toLowerCase());
    const chartHtml = bigChartSvg(liveChartData, trend.cls, currentTimeframe === "1d" || currentTimeframe === "7d", timeframeLoading);

    let statsHtml = "";
    if (liveChartData && liveChartData.length >= 2) {
        const high = Math.max(...liveChartData);
        const low = Math.min(...liveChartData);
        const avg = liveChartData.reduce((a, b) => a + b, 0) / liveChartData.length;
        statsHtml = '<div class="m-stat"><span class="lbl">' + t("chartHigh") + '</span><span class="vl mono">' + fmtNum(high) + '</span></div>' +
                    '<div class="m-stat"><span class="lbl">' + t("chartLow") + '</span><span class="vl mono">' + fmtNum(low) + '</span></div>' +
                    '<div class="m-stat"><span class="lbl">' + t("chartAvg") + '</span><span class="vl mono">' + fmtNum(Math.round(avg)) + '</span></div>';
    }

    const usdRow = c.type === "crypto"
        ? '<div class="d-row" style="margin-top:12px;padding-top:10px;border-top:1px dashed var(--edge)"><span>USD</span><b class="mono">' + esc(fmtUsd(c.usd_price)) + '</b></div>' : "";

    const tfList = [
        { key: "1d", label: t("tf1d") }, { key: "7d", label: t("tf7d") },
        { key: "30d", label: t("tf30d") }, { key: "90d", label: t("tf90d") },
        { key: "1y", label: t("tf1y") },
    ];
    const tfHtml = tfList.map(x => '<button class="tf-btn ' + (x.key === currentTimeframe ? "on" : "") + '" data-tf="' + x.key + '" type="button" ' + (timeframeLoading ? "disabled" : "") + '>' + x.label + '</button>').join("");

    modalPanel.innerHTML =
        '<button class="modal-close" type="button" id="modalClose">✕</button>' +
        '<button class="star-btn ' + (watched ? "on" : "") + '" type="button" id="modalStar" style="position:absolute;top:14px;right:56px;width:32px;height:32px;font-size:17px;">' + (watched ? "★" : "☆") + '</button>' +
        '<div class="m-head">' + avatarHtml(c, true) + '<div class="m-head-text"><div class="nm">' + esc(name) + '</div><div class="sub">' + esc(code.toUpperCase()) + ' · ' + esc(typeLabel) + '</div></div></div>' +
        '<div class="m-price"><div class="vl mono">' + fmtNum(price) + '<span class="un">' + t("unit") + '</span></div><div class="chg ' + trend.cls + '">' + esc(trend.text) + '</div></div>' +
        '<div class="m-timeframes">' + tfHtml + '</div>' + chartHtml +
        '<div class="m-chart-labels"><span>' + t("beforeNow") + '</span><span>' + t("nowLabel") + '</span></div>' +
        '<div class="m-stats">' + statsHtml + '</div>' + usdRow +
        '<div class="m-actions">' +
            '<button class="m-action-btn" id="modalShare" type="button">📤 ' + t("share") + '</button>' +
            '<button class="m-action-btn" id="modalCompare" type="button">' + t("cmpAction") + '</button>' +
            '<button class="m-action-btn" id="modalAlert" type="button">' + t("alertAction") + '</button>' +
        '</div>';

    const modalCloseBtn = document.getElementById("modalClose");
    if (modalCloseBtn) modalCloseBtn.addEventListener("click", closeChart);
    const modalStar = document.getElementById("modalStar");
    if (modalStar) modalStar.addEventListener("click", (e) => {
        e.stopPropagation();
        toggleWatch(code.toLowerCase());
        const now = isWatched(code.toLowerCase());
        modalStar.classList.toggle("on", now);
        modalStar.textContent = now ? "★" : "☆";
    });
    modalPanel.querySelectorAll(".tf-btn").forEach(btn => {
        btn.addEventListener("click", () => setTimeframe(btn.dataset.tf));
    });
    const shareBtn = document.getElementById("modalShare");
    if (shareBtn) shareBtn.addEventListener("click", () => shareCurrency(c));
    const cmpBtn = document.getElementById("modalCompare");
    if (cmpBtn) cmpBtn.addEventListener("click", () => { closeChart(); openCompare(code.toLowerCase()); });
    const alertBtn = document.getElementById("modalAlert");
    if (alertBtn) alertBtn.addEventListener("click", () => { closeChart(); openAlerts(); setTimeout(() => { if ($("alertCode")) $("alertCode").value = code.toLowerCase(); }, 100); });
}

function updateModalLiveData(fresh) {
    if (!modalPanel) return;
    const priceEl = modalPanel.querySelector(".m-price .vl");
    if (priceEl) priceEl.innerHTML = fmtNum(fresh.price) + '<span class="un">' + t("unit") + '</span>';
    const chgEl = modalPanel.querySelector(".m-price .chg");
    if (chgEl) {
        const trend = trendOf(fresh.change);
        chgEl.className = "chg " + trend.cls;
        chgEl.textContent = trend.text;
    }
    if (!timeframeLoading) {
        const chartEl = modalPanel.querySelector(".m-chart");
        if (chartEl) {
            const trend = trendOf(fresh.change);
            const isLive = currentTimeframe === "1d" || currentTimeframe === "7d";
            const newChart = bigChartSvg(liveChartData, trend.cls, isLive, false);
            const tmp = document.createElement("div");
            tmp.innerHTML = newChart;
            const newNode = tmp.firstElementChild;
            if (newNode) chartEl.replaceWith(newNode);
        }
    }
}

/* =========================================================
   SHARE
========================================================= */

async function shareCurrency(c) {
    try {
        const canvas = document.createElement("canvas");
        canvas.width = 800; canvas.height = 500;
        const ctx = canvas.getContext("2d");
        const grad = ctx.createLinearGradient(0, 0, 800, 500);
        grad.addColorStop(0, "#0e0a1e");
        grad.addColorStop(0.5, "#1a1035");
        grad.addColorStop(1, "#0e0a1e");
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, 800, 500);
        const flag = c.flag || "💱";
        ctx.font = "64px 'Noto Color Emoji', 'Apple Color Emoji', 'Segoe UI Emoji', 'Vazirmatn', sans-serif";
        ctx.textAlign = "right";
        ctx.fillText(flag, 750, 130);
        ctx.font = "bold 32px 'Vazirmatn', Tahoma, sans-serif";
        ctx.fillStyle = "#f0f0fa";
        ctx.textAlign = "right";
        ctx.direction = "rtl";
        ctx.fillText(c.name || c.code.toUpperCase(), 700, 130);
        const price = Number(c.price) || 0;
        const priceStr = Math.round(price).toLocaleString("en-US");
        ctx.font = "bold 72px 'JetBrains Mono', monospace";
        ctx.fillStyle = "#ffffff";
        ctx.textAlign = "right";
        ctx.direction = "ltr";
        ctx.fillText(priceStr, 700, 260);
        ctx.font = "500 20px 'Vazirmatn', Tahoma, sans-serif";
        ctx.fillStyle = "rgba(160, 160, 190, 1)";
        ctx.direction = "rtl";
        ctx.textAlign = "right";
        ctx.fillText("تومان", 700, 295);
        const blob = await new Promise(res => canvas.toBlob(res, "image/png", 0.95));
        if (!blob) throw new Error("no_blob");
        const file = new File([blob], `${c.code}-price.png`, { type: "image/png" });
        if (navigator.share && navigator.canShare && navigator.canShare({ files: [file] })) {
            await navigator.share({ files: [file], title: c.name || c.code, text: `${c.name} — ${fmtNum(c.price)} تومان` });
        } else {
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url; a.download = `${c.code}-price.png`;
            document.body.appendChild(a); a.click();
            setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 100);
        }
        haptic();
    } catch (e) { console.error("Share error:", e); }
}

/* =========================================================
   POLLING
========================================================= */

async function fetchPrices() {
    try {
        const res = await fetch(api("/api/market?_=" + Date.now()), { cache: "no-store" });
        if (!res.ok) { setLiveStatus(false); return; }
        const data = await res.json();
        if (data.success && data.currencies) {
            setLiveStatus(true);
            handleSnapshot(data.currencies, new Date().toISOString());
        }
    } catch (e) { setLiveStatus(false); }
}

function connectWS() {
    if (pollTimer) clearInterval(pollTimer);
    fetchPrices();
    pollTimer = setInterval(() => {
        if (!document.hidden) fetchPrices();
    }, REFRESH_MS);
}

function handleSnapshot(list, updatedAt) {
    if (!Array.isArray(list)) return;
    currencies = list;
    CURRENCIES_NAME = {};
    currencies.forEach(c => { CURRENCIES_NAME[c.code] = c.name || c.code; });

    applyFilter();
    renderTicker(currencies);
    renderTopMovers();
    renderVolatility();

    const st = marketStatusOf(currencies);
    if (marketStatus) {
        marketStatus.textContent = st.text;
        marketStatus.className = "val " + st.cls;
    }

    currencies.forEach(c => {
        const p = Number(c.price);
        if (Number.isFinite(p)) prevPrices[String(c.code || "").toLowerCase()] = p;
    });

    if (updatedAt && lastUpdate) lastUpdate.textContent = fmtTime(updatedAt);
    if (loading) loading.classList.add("off");

    if (currentChart && modal && modal.classList.contains("on")) {
        const fresh = currencies.find(x => x.code === currentChart.code);
        if (fresh) {
            currentChart = fresh;
            const newPrice = Number(fresh.price);
            if (Number.isFinite(newPrice) && newPrice > 0) {
                appendLiveChartPoint(newPrice);
                updateModalLiveData(fresh);
            }
        }
    }

    checkPriceAlerts();
    renderPortfolio();

    // از این به بعد کارت‌های تازه‌ساخته‌شده بدون تکرار انیمیشن ورود نمایش داده می‌شوند
    firstPaintDone = true;
}

/* =========================================================
   PORTFOLIO
========================================================= */

function savePortfolio() { localStorage.setItem("ex_portfolio", JSON.stringify(portfolio)); }

function portAddItem() {
    const code = $("portCode")?.value;
    const amount = parseFloat(($("portAmount")?.value || "").replace(/[^\d.]/g, ""));
    const buy = parseFloat(($("portBuy")?.value || "").replace(/[^\d.]/g, ""));
    if (!code || !Number.isFinite(amount) || amount <= 0 || !Number.isFinite(buy) || buy <= 0) return;
    const existing = portfolio.find(p => p.code === code);
    if (existing) {
        const totalAmount = existing.amount + amount;
        const totalCost = (existing.amount * existing.buyPrice) + (amount * buy);
        existing.amount = totalAmount;
        existing.buyPrice = totalCost / totalAmount;
    } else {
        portfolio.push({ code, amount, buyPrice: buy, ts: new Date().toISOString() });
    }
    savePortfolio();
    renderPortfolio();
    if ($("portAmount")) $("portAmount").value = "";
    if ($("portBuy")) $("portBuy").value = "";
    haptic();
    toast("✅ افزوده شد", "success");
}

function portRemoveItem(code) {
    portfolio = portfolio.filter(p => p.code !== code);
    savePortfolio();
    renderPortfolio();
    haptic();
}

function renderPortfolio() {
    const list = $("portList"), totalEl = $("portTotal"), pnlEl = $("portPnl");
    if (!list) return;
    if (!portfolio.length) {
        list.innerHTML = '<div class="port-empty">' + t("portEmpty") + '</div>';
        if (totalEl) totalEl.textContent = "0";
        if (pnlEl) pnlEl.textContent = "0";
        return;
    }
    let totalValue = 0, totalCost = 0;
    const html = portfolio.map(p => {
        const c = currencies.find(x => x.code === p.code);
        const currentPrice = c ? Number(c.price) : 0;
        const value = currentPrice * p.amount;
        const cost = p.buyPrice * p.amount;
        const pnl = value - cost;
        totalValue += value; totalCost += cost;
        const flag = c?.flag || "💱";
        const name = c?.short || p.code.toUpperCase();
        const pnlClass = pnl >= 0 ? "up" : "dn";
        const sign = pnl >= 0 ? "+" : "";
        return `<div class="port-item"><div class="ico" style="background: var(--accent-glow); font-size: 14px;">${esc(flag)}</div><div class="info"><div class="nm">${esc(name)} · ${p.amount}</div><div class="sub">${fmtNum(p.buyPrice)} › ${fmtNum(currentPrice)}</div></div><div class="pnl ${pnlClass}">${sign}${fmtNum(Math.round(pnl))}</div><button class="del" type="button" data-del="${esc(p.code)}">✕</button></div>`;
    }).join("");
    list.innerHTML = html;
    if (totalEl) totalEl.textContent = fmtNum(Math.round(totalValue));
    if (pnlEl) {
        const totalPnl = totalValue - totalCost;
        const sign = totalPnl >= 0 ? "+" : "";
        pnlEl.textContent = `${sign}${fmtNum(Math.round(totalPnl))}`;
        pnlEl.style.color = totalPnl >= 0 ? "var(--up)" : "var(--down)";
    }
    list.querySelectorAll("[data-del]").forEach(btn => {
        btn.addEventListener("click", (e) => { e.stopPropagation(); portRemoveItem(btn.dataset.del); });
    });
}

function fillPortfolioSelect() {
    const sel = $("portCode");
    if (!sel) return;
    const cur = sel.value;
    sel.innerHTML = currencies.map(c => `<option value="${esc(c.code)}">${esc(c.flag || "💱")} ${esc(c.name || c.code)}</option>`).join("");
    if (cur) sel.value = cur;
}

/* =========================================================
   ALERTS
========================================================= */

function saveAlerts() { localStorage.setItem("ex_alerts", JSON.stringify(alerts)); }

function requestNotifPermission() {
    if (!("Notification" in window)) return;
    if (Notification.permission === "default") Notification.requestPermission().catch(() => {});
}

function alertAddItem() {
    const code = $("alertCode")?.value;
    const dir = $("alertDir")?.value || "above";
    const target = parseFloat(($("alertPrice")?.value || "").replace(/[^\d.]/g, ""));
    if (!code || !Number.isFinite(target) || target <= 0) return;
    alerts.push({ id: Date.now() + Math.random().toString(36).slice(2, 8), code, direction: dir, target, created_at: new Date().toISOString(), triggered: false });
    saveAlerts(); renderAlerts(); requestNotifPermission();
    if ($("alertPrice")) $("alertPrice").value = "";
    haptic();
    toast("🔔 هشدار تنظیم شد", "success");
}

function alertRemoveItem(id) {
    alerts = alerts.filter(a => a.id !== id);
    saveAlerts(); renderAlerts(); haptic();
}

function renderAlerts() {
    const list = $("alertList");
    if (!list) return;
    if (!alerts.length) { list.innerHTML = '<div class="port-empty">' + t("alertEmpty") + '</div>'; return; }
    list.innerHTML = alerts.map(a => {
        const c = currencies.find(x => x.code === a.code);
        const flag = c?.flag || "💱";
        const name = c?.short || a.code.toUpperCase();
        const dirLabel = a.direction === "above" ? t("dirAbove") : t("dirBelow");
        return `<div class="port-item ${a.triggered ? "triggered" : ""}"><div class="ico" style="background: var(--accent-glow); font-size: 14px;">${esc(flag)}</div><div class="info"><div class="nm">${esc(name)}</div><div class="sub">${dirLabel} ${fmtNum(a.target)}</div></div><button class="del" type="button" data-del-alert="${esc(a.id)}">✕</button></div>`;
    }).join("");
    list.querySelectorAll("[data-del-alert]").forEach(btn => {
        btn.addEventListener("click", (e) => { e.stopPropagation(); alertRemoveItem(btn.dataset.delAlert); });
    });
}

function checkPriceAlerts() {
    if (!alerts.length || !currencies.length) return;
    let triggered = false;
    alerts.forEach(a => {
        if (a.triggered) return;
        const c = currencies.find(x => x.code === a.code);
        if (!c) return;
        const price = Number(c.price);
        if (!Number.isFinite(price)) return;
        let hit = false;
        if (a.direction === "above" && price >= a.target) hit = true;
        if (a.direction === "below" && price <= a.target) hit = true;
        if (hit) {
            a.triggered = true; triggered = true;
            playBeep();
            toast("🔔 " + (c.name || c.code) + " — " + fmtNum(price), "success");
            if ("Notification" in window && Notification.permission === "granted") {
                try { new Notification(`🔔 ${c.name || c.code}`, { body: `${a.direction === "above" ? t("dirAbove") : t("dirBelow")} ${fmtNum(a.target)}\n${fmtNum(price)} ${t("unit")}`, tag: a.id }); } catch (e) {}
            }
        }
    });
    if (triggered) { saveAlerts(); renderAlerts(); }
}

function fillAlertSelect() {
    const sel = $("alertCode");
    if (!sel) return;
    const cur = sel.value;
    sel.innerHTML = currencies.map(c => `<option value="${esc(c.code)}">${esc(c.flag || "💱")} ${esc(c.name || c.code)}</option>`).join("");
    if (cur) sel.value = cur;
}

/* =========================================================
   MODAL CONTROLS
========================================================= */

const portfolioBtn = $("portfolioBtn"), portfolioModal = $("portfolioModal");
const portClose = $("portClose"), portAdd = $("portAdd");
const alertsBtn = $("alertsBtn"), alertsModal = $("alertsModal");
const alertClose = $("alertClose"), alertAdd = $("alertAdd");

function openPortfolio() {
    if (!portfolioModal) return;
    fillPortfolioSelect(); renderPortfolio();
    openModal(portfolioModal, "#portClose");
    haptic();
}
function closePortfolio() {
    closeModal(portfolioModal);
}
function openAlerts() {
    if (!alertsModal) return;
    fillAlertSelect(); renderAlerts();
    openModal(alertsModal, "#alertClose");
    requestNotifPermission(); haptic();
}
function closeAlerts() {
    closeModal(alertsModal);
}

function openSettings() {
    if (!settingsModal) return;
    if (setSound) setSound.checked = settings.sound;
    if (setAutoDark) setAutoDark.checked = settings.autoDark;
    if (setCompact) setCompact.checked = settings.compact;
    if (setRefresh) setRefresh.value = String(REFRESH_MS);
    openModal(settingsModal, "#setClose");
    haptic();
}
function closeSettings() {
    closeModal(settingsModal);
}

/* =========================================================
   COMMAND PALETTE
========================================================= */

function openCmd() {
    if (!cmdModal) return;
    cmdInput.value = "";
    cmdSelectedIndex = 0;
    renderCmdResults("");
    openModal(cmdModal, "#cmdInput");
    haptic();
}
function closeCmd() {
    closeModal(cmdModal);
}

const ACTIONS = [
    { id: "act:compare", icon: "📊", title: "مقایسه ارزها", sub: "Compare", run: () => { closeCmd(); openCompare(); } },
    { id: "act:gold", icon: "🥇", title: "محاسبه طلا", sub: "Gold calculator", run: () => { closeCmd(); openConverter(); setTimeout(() => switchConvTab("gold"), 100); } },
    { id: "act:volatility", icon: "🔥", title: "پُرنوسان‌ترین", sub: "Volatility", run: () => { closeCmd(); toggleVolatility(); } },
    { id: "act:portfolio", icon: "💼", title: "پورتفولیو", sub: "Portfolio", run: () => { closeCmd(); openPortfolio(); } },
    { id: "act:alerts", icon: "🔔", title: "هشدار قیمت", sub: "Alerts", run: () => { closeCmd(); openAlerts(); } },
    { id: "act:settings", icon: "⚙️", title: "تنظیمات", sub: "Settings", run: () => { closeCmd(); openSettings(); } },
    { id: "act:theme-light", icon: "☀️", title: "تم روشن", sub: "Light", run: () => { setTheme("light"); closeCmd(); } },
    { id: "act:theme-dark", icon: "🌙", title: "تم تاریک", sub: "Dark", run: () => { setTheme("dark"); closeCmd(); } },
    { id: "act:export-csv", icon: "📥", title: "خروجی CSV", sub: "Export", run: () => { exportData("csv"); closeCmd(); } },
    { id: "act:export-json", icon: "📄", title: "خروجی JSON", sub: "Export", run: () => { exportData("json"); closeCmd(); } },
    { id: "act:refresh", icon: "🔄", title: "بروزرسانی", sub: "Refresh", run: () => { closeCmd(); fetchPrices(); } },
];

const THEMES = [
    { id: "aurora", name: "Aurora", icon: "🌈" },
    { id: "gold", name: "Gold", icon: "🏆" },
    { id: "ocean", name: "Ocean", icon: "🌊" },
    { id: "forest", name: "Forest", icon: "🌲" },
    { id: "sunset", name: "Sunset", icon: "🌅" },
    { id: "neon", name: "Neon", icon: "💫" },
    { id: "cyberpunk", name: "Cyberpunk", icon: "🤖" },
    { id: "matrix", name: "Matrix", icon: "🟢" },
    { id: "paper", name: "Paper", icon: "📄" },
];

function renderCmdResults(q) {
    q = (q || "").trim().toLowerCase();
    const items = [];

    // Currencies
    const matchedCurrencies = q
        ? currencies.filter(c => {
            const code = String(c.code || "").toLowerCase();
            const name = String(c.name || "").toLowerCase();
            return code.includes(q) || name.includes(q);
        }).slice(0, 6)
        : currencies.slice(0, 6);

    if (matchedCurrencies.length) {
        items.push({ type: "section", title: t("cmdCurrencies") });
        matchedCurrencies.forEach(c => {
            items.push({
                type: "item",
                icon: c.flag || "💱",
                title: c.name || c.code,
                sub: fmtNum(c.price) + " " + t("unit"),
                run: () => { closeCmd(); openChart(c); },
            });
        });
    }

    // Actions
    const matchedActions = q
        ? ACTIONS.filter(a => a.title.toLowerCase().includes(q) || a.sub.toLowerCase().includes(q))
        : ACTIONS.slice(0, 6);
    if (matchedActions.length) {
        items.push({ type: "section", title: t("cmdActions") });
        matchedActions.forEach(a => {
            items.push({
                type: "item",
                icon: a.icon,
                title: a.title,
                sub: a.sub,
                run: a.run,
            });
        });
    }

    // Recent
    if (!q && recentSearches.length) {
        items.push({ type: "section", title: t("cmdRecent") });
        recentSearches.slice(0, 4).forEach(rs => {
            items.push({
                type: "item",
                icon: "🕐",
                title: rs,
                sub: "",
                run: () => { cmdInput.value = rs; renderCmdResults(rs); },
            });
        });
    }

    // Render
    cmdFiltered = items.filter(x => x.type === "item");
    cmdSelectedIndex = 0;

    if (!cmdFiltered.length) {
        cmdResults.innerHTML = '<div class="cmd-empty">' + t("cmdNoResults") + '</div>';
        return;
    }

    let html = "";
    let itemIndex = 0;
    items.forEach((it, i) => {
        if (it.type === "section") {
            html += '<div class="cmd-section-title">' + esc(it.title) + '</div>';
        } else {
            const idx = itemIndex++;
            html += '<div class="cmd-item' + (idx === 0 ? " selected" : "") + '" data-idx="' + idx + '">' +
                '<span class="cmd-item-ico">' + esc(it.icon) + '</span>' +
                '<span class="cmd-item-text"><span class="cmd-item-name">' + esc(it.title) + '</span>' +
                (it.sub ? '<span class="cmd-item-sub">' + esc(it.sub) + '</span>' : '') +
                '</span></div>';
        }
    });
    cmdResults.innerHTML = html;

    cmdResults.querySelectorAll(".cmd-item").forEach(el => {
        el.addEventListener("click", () => {
            const idx = parseInt(el.dataset.idx, 10);
            const item = cmdFiltered[idx];
            if (item && item.run) item.run();
        });
        el.addEventListener("mouseenter", () => {
            cmdSelectedIndex = parseInt(el.dataset.idx, 10);
            updateCmdSelection();
        });
    });
}

function updateCmdSelection() {
    cmdResults.querySelectorAll(".cmd-item").forEach((el, i) => {
        el.classList.toggle("selected", i === cmdSelectedIndex);
    });
}

/* =========================================================
   EXPORT
========================================================= */

function exportData(format) {
    try {
        let data, filename, mime;
        if (format === "csv") {
            const headers = ["code", "name", "short", "type", "price", "change", "usd_price", "source"];
            const rows = currencies.map(c => [
                c.code, c.name, c.short, c.type,
                c.price, c.change, c.usd_price || "", c.source || ""
            ]);
            const csv = [headers.join(","), ...rows.map(r => r.map(x => `"${String(x).replace(/"/g, '""')}"`).join(","))].join("\n");
            data = csv;
            filename = `exchance-${Date.now()}.csv`;
            mime = "text/csv;charset=utf-8";
        } else {
            data = JSON.stringify({
                exported_at: new Date().toISOString(),
                count: currencies.length,
                currencies,
                watchlist,
                portfolio,
                alerts,
            }, null, 2);
            filename = `exchance-${Date.now()}.json`;
            mime = "application/json";
        }
        const blob = new Blob([data], { type: mime });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = filename;
        document.body.appendChild(a); a.click();
        setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 100);
        toast(t("toastExported"), "success");
    } catch (e) { console.error(e); }
}

/* =========================================================
   CLOCK
========================================================= */

function updateClock() {
    if (!clockTime || document.hidden) return;
    const now = new Date();
    clockTime.textContent = `${String(now.getHours()).padStart(2,"0")}:${String(now.getMinutes()).padStart(2,"0")}:${String(now.getSeconds()).padStart(2,"0")}`;
    if (clockDate) {
        try {
            const locale = currentLang === "fa" ? "fa-IR" : (currentLang === "ar" ? "ar-SA" : "en-US");
            clockDate.textContent = new Intl.DateTimeFormat(locale, { weekday: "short", day: "numeric", month: "short" }).format(now);
        } catch (e) {}
    }
}

/* =========================================================
   CONVERTER + GOLD CALC
========================================================= */

function switchConvTab(tab) {
    currentConvTab = tab;
    document.querySelectorAll(".conv-tab").forEach(b => {
        b.classList.toggle("active", b.dataset.convTab === tab);
    });
    const curSec = $("convCurrencySec");
    const goldSec = $("convGoldSec");
    if (curSec) curSec.classList.toggle("on", tab === "currency");
    if (goldSec) goldSec.classList.toggle("on", tab === "gold");
    if (tab === "currency") updateConversion();
    else updateGoldCalc();
}

function getPriceToman(code) {
    if (code === "toman") return 1;
    const c = currencies.find(x => x.code === code);
    if (!c) return null;
    const p = parseFloat(c.price);
    return Number.isFinite(p) ? p : null;
}

function shortNameOf(code) {
    if (code === "toman") return t("unit");
    const c = currencies.find(x => x.code === code);
    return c ? (c.short || c.name || c.code.toUpperCase()) : code.toUpperCase();
}

function populateCurrencySelects() {
    if (!convFrom || !convTo) return;
    const cf = convFrom.value, ct = convTo.value;
    const options = [{ code: "toman", label: "🇮🇷 " + t("unit") }];
    const sorted = [...currencies].sort((a, b) => {
        const aF = a.type !== "crypto", bF = b.type !== "crypto";
        if (aF !== bF) return aF ? -1 : 1;
        return 0;
    });
    for (const c of sorted) {
        const flag = c.flag && /\p{Emoji}/u.test(c.flag) ? c.flag + " " : "";
        options.push({ code: c.code, label: flag + (c.name || c.code.toUpperCase()) });
    }
    const build = () => options.map(o => '<option value="' + o.code + '">' + esc(o.label) + '</option>').join("");
    convFrom.innerHTML = build(); convTo.innerHTML = build();
    convFrom.value = cf || "usd";
    convTo.value = ct || "toman";
}

function formatConvResult(value) {
    if (!Number.isFinite(value)) return "—";
    const abs = Math.abs(value);
    const max = abs >= 1000 ? 0 : abs >= 1 ? 2 : abs >= 0.01 ? 4 : 6;
    const locale = currentLang === "fa" ? "fa-IR" : "en-US";
    return new Intl.NumberFormat(locale, { maximumFractionDigits: max }).format(value);
}

function updateConversion() {
    if (!convValue) return;
    const raw = (convAmount?.value || "").trim();
    if (!raw) { convValue.textContent = "—"; if (convRate) convRate.textContent = ""; return; }
    const normalized = raw.replace(/[۰-۹]/g, d => "۰۱۲۳۴۵۶۷۸۹".indexOf(d)).replace(/[٠-٩]/g, d => "٠١٢٣٤٥٦٧٨٩".indexOf(d)).replace(/,/g, "").replace(/[^\d.\-]/g, "");
    const amount = parseFloat(normalized);
    if (!Number.isFinite(amount) || amount < 0) return;
    const fromCode = convFrom.value, toCode = convTo.value;
    const fromPrice = getPriceToman(fromCode), toPrice = getPriceToman(toCode);
    if (fromPrice === null || toPrice === null) return;
    const result = (amount * fromPrice) / toPrice;
    convValue.textContent = formatConvResult(result);
    const rate = fromPrice / toPrice;
    if (convRate) convRate.textContent = "1 " + shortNameOf(fromCode) + " = " + formatConvResult(rate) + " " + shortNameOf(toCode);
}

// Gold calculator
// 1 mithqal = 4.6083 g
// 1 ounce = 31.1035 g
const GRAMS_PER_MITHQAL = 4.6083;
const GRAMS_PER_OUNCE = 31.1035;

function goldGramPrice(karat) {
    const key = karat === 24 ? "gold24" : "gold18";
    const c = currencies.find(x => x.code === key);
    if (c) return Number(c.price) || null;
    // fallback: از gold18 استفاده کن
    const g18 = currencies.find(x => x.code === "gold18");
    if (g18) {
        const p18 = Number(g18.price) || 0;
        if (karat === 24) return p18 * (24 / 18);
        return p18;
    }
    return null;
}

function goldToGrams(amount, unit) {
    if (unit === "gram") return amount;
    if (unit === "mithqal") return amount * GRAMS_PER_MITHQAL;
    if (unit === "ounce") return amount * GRAMS_PER_OUNCE;
    return amount;
}

function updateGoldCalc() {
    if (!goldValue) return;
    const amount = parseFloat((goldAmount?.value || "").replace(/[^\d.]/g, ""));
    const unit = goldUnit?.value || "gram";
    const karat = parseInt(goldKarat?.value || "18", 10);
    const target = goldTarget?.value || "toman";

    if (!Number.isFinite(amount) || amount <= 0) {
        goldValue.textContent = "—";
        if (goldRate) goldRate.textContent = "";
        return;
    }

    const gramPrice = goldGramPrice(karat);
    if (!gramPrice) {
        goldValue.textContent = "—";
        if (goldRate) goldRate.textContent = "قیمت طلا در دسترس نیست";
        return;
    }

    const totalGrams = goldToGrams(amount, unit);
    const totalToman = totalGrams * gramPrice;

    if (target === "toman") {
        goldValue.textContent = formatConvResult(totalToman);
        if (goldRate) goldRate.textContent = "۱ گرم " + karat + " عیار = " + fmtNum(gramPrice) + " " + t("unit");
    } else if (target === "gram") {
        const grams = totalToman / gramPrice;
        goldValue.textContent = formatConvResult(grams);
        if (goldRate) goldRate.textContent = "گرم " + karat + " عیار";
    } else if (target === "mithqal") {
        const mithqal = totalToman / gramPrice / GRAMS_PER_MITHQAL;
        goldValue.textContent = formatConvResult(mithqal);
        if (goldRate) goldRate.textContent = "مثقال " + karat + " عیار";
    } else if (target === "ounce") {
        const ounce = totalToman / gramPrice / GRAMS_PER_OUNCE;
        goldValue.textContent = formatConvResult(ounce);
        if (goldRate) goldRate.textContent = "اونس " + karat + " عیار";
    }
}

function openConverter() {
    if (!convModal) return;
    populateCurrencySelects();
    if (!convFrom.value) convFrom.value = "usd";
    if (!convTo.value) convTo.value = "toman";
    updateConversion();
    updateGoldCalc();
    openModal(convModal, "#convClose");
    haptic();
}
function closeConverter() {
    closeModal(convModal);
}

/* =========================================================
   NEWS
========================================================= */

function timeAgo(isoStr) {
    if (!isoStr) return "";
    try {
        const d = new Date(isoStr);
        if (Number.isNaN(d.getTime())) return "";
        const diff = (Date.now() - d.getTime()) / 1000;
        if (diff < 60) return t("agoNow");
        if (diff < 3600) return Math.floor(diff / 60) + " " + t("agoMin");
        if (diff < 86400) return Math.floor(diff / 3600) + " " + t("agoHour");
        if (diff < 604800) return Math.floor(diff / 86400) + " " + t("agoDay");
        const locale = currentLang === "fa" ? "fa-IR" : "en-US";
        return new Intl.DateTimeFormat(locale, { day: "numeric", month: "short" }).format(d);
    } catch (e) { return ""; }
}

function newsCardHtml(item) {
    const flag = item.source_flag || "📰";
    const sourceName = item.source_name || "";
    const cat = item.category || "";
    const thumb = item.image
        ? '<img class="news-thumb" src="' + esc(item.image) + '" alt="" loading="lazy" onerror="this.outerHTML=\'<div class=&quot;news-thumb-placeholder&quot;>📰</div>\'">'
        : '<div class="news-thumb-placeholder">📰</div>';
    const summary = item.summary ? '<p class="news-summary">' + esc(item.summary) + '</p>' : "";
    return '<a class="news-card" href="' + esc(item.link || "#") + '" target="_blank" rel="noopener">' + thumb +
        '<div class="news-body"><div class="news-source-row"><span class="flag">' + esc(flag) + '</span><span>' + esc(sourceName) + '</span>' + (cat ? '<span class="cat">' + esc(cat) + '</span>' : '') + '</div>' +
        '<h3 class="news-title">' + esc(item.title) + '</h3>' + summary +
        '<div class="news-time"><span>' + timeAgo(item.published) + '</span><span class="arrow">↗</span></div></div></a>';
}

function initNewsReveal() {
    if (!newsGrid) return;
    if (!("IntersectionObserver" in window)) {
        document.querySelectorAll(".news-card:not(.reveal)").forEach(c => c.classList.add("reveal"));
        return;
    }
    if (!newsRevealObserver) {
        newsRevealObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const el = entry.target;
                    const delay = parseFloat(el.dataset.revealDelay || "0");
                    setTimeout(() => el.classList.add("reveal"), delay);
                    newsRevealObserver.unobserve(el);
                }
            });
        }, { root: null, rootMargin: "0px 0px -50px 0px", threshold: 0.05 });
    }
    let idx = 0;
    document.querySelectorAll(".news-card:not(.reveal)").forEach((el) => {
        el.dataset.revealDelay = Math.min(idx * 30, 300);
        idx++;
        newsRevealObserver.observe(el);
    });
}

function renderNews() {
    if (!newsGrid) return;
    let filtered = newsItems;
    if (newsLang !== "all") filtered = filtered.filter(it => it.lang === newsLang);
    if (!filtered.length) { newsGrid.innerHTML = '<div class="news-loading">—</div>'; return; }
    newsGrid.innerHTML = filtered.map(newsCardHtml).join("");
    setTimeout(initNewsReveal, 30);
}

async function loadNews() {
    if (!newsGrid) return;
    if (newsLoaded && newsItems.length) { renderNews(); return; }
    newsGrid.innerHTML = '<div class="news-loading"><div></div></div>';
    try {
        const res = await fetch(api("/api/news?_=" + Date.now()), { cache: "no-store" });
        const data = await res.json();
        if (data.success) {
            newsItems = data.items || [];
            newsLoaded = true;
            renderNews();
        } else {
            newsGrid.innerHTML = '<div class="news-loading">❌</div>';
        }
    } catch (e) {
        newsGrid.innerHTML = '<div class="news-loading">❌</div>';
    }
}

/* =========================================================
   WIRE EVENTS
========================================================= */

if (themeToggle) themeToggle.addEventListener("click", () => { setTheme(currentTheme === "light" ? "dark" : "light"); haptic(); });
if (paletteBtn) paletteBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (themePop) themePop.classList.toggle("on");
    if (langPop) langPop.classList.remove("on");
    paletteBtn.setAttribute("aria-expanded", themePop && themePop.classList.contains("on") ? "true" : "false");
    if (langBtn) langBtn.setAttribute("aria-expanded", "false");
    haptic();
});
document.querySelectorAll(".swatch").forEach(s => {
    s.addEventListener("click", (e) => { e.stopPropagation(); setPalette(s.dataset.theme); if (themePop) themePop.classList.remove("on"); haptic(); toast("🎨 " + s.dataset.theme, "success"); });
});
if (langBtn) langBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (langPop) langPop.classList.toggle("on");
    if (themePop) themePop.classList.remove("on");
    langBtn.setAttribute("aria-expanded", langPop && langPop.classList.contains("on") ? "true" : "false");
    if (paletteBtn) paletteBtn.setAttribute("aria-expanded", "false");
    haptic();
});
if (langPop) langPop.querySelectorAll("button").forEach(b => b.addEventListener("click", (e) => { e.stopPropagation(); setLang(b.dataset.lang); langPop.classList.remove("on"); }));
document.addEventListener("click", () => {
    if (themePop) themePop.classList.remove("on");
    if (langPop) langPop.classList.remove("on");
    if (paletteBtn) paletteBtn.setAttribute("aria-expanded", "false");
    if (langBtn) langBtn.setAttribute("aria-expanded", "false");
});

categoryTabs.forEach(tab => tab.addEventListener("click", () => {
    activeCategory = tab.dataset.category;
    categoryTabs.forEach(t => {
        t.classList.toggle("active", t.dataset.category === activeCategory);
        t.setAttribute("aria-pressed", String(t.dataset.category === activeCategory));
    });
    haptic(); applyFilter();
}));
if (searchInput) {
    searchInput.addEventListener("input", applyFilter);
    searchInput.addEventListener("keydown", (e) => { if (e.key === "Enter") addRecentSearch(searchInput.value); });
}
if (clearSearch) clearSearch.addEventListener("click", () => { searchInput.value = ""; applyFilter(); searchInput.focus(); });
if (refreshBtn) refreshBtn.addEventListener("click", () => { haptic(); fetchPrices(); });
if (retryBtn) retryBtn.addEventListener("click", () => { haptic(); fetchPrices(); });
if (modal) modal.addEventListener("click", (e) => { if (e.target.dataset.close === "1") closeChart(); });

// Quick Actions
if ($("qaCompare")) $("qaCompare").addEventListener("click", () => openCompare());
if ($("qaGold")) $("qaGold").addEventListener("click", () => { openConverter(); setTimeout(() => switchConvTab("gold"), 100); });
if ($("qaVolatility")) $("qaVolatility").addEventListener("click", toggleVolatility);
if ($("qaExport")) $("qaExport").addEventListener("click", () => exportData("csv"));
if ($("qaRandom")) $("qaRandom").addEventListener("click", () => {
    if (!currencies.length) return;
    const random = currencies[Math.floor(Math.random() * currencies.length)];
    openChart(random);
});

// Converter
if (convBtn) convBtn.addEventListener("click", openConverter);
if (convClose) convClose.addEventListener("click", closeConverter);
if (convModal) convModal.addEventListener("click", (e) => { if (e.target.dataset.closeConv === "1") closeConverter(); });
if (convAmount) convAmount.addEventListener("input", updateConversion);
if (convFrom) convFrom.addEventListener("change", updateConversion);
if (convTo) convTo.addEventListener("change", updateConversion);
if (convSwap) convSwap.addEventListener("click", () => {
    const tmp = convFrom.value;
    convFrom.value = convTo.value; convTo.value = tmp;
    updateConversion(); haptic();
});
document.querySelectorAll(".conv-quick button").forEach(btn => {
    btn.addEventListener("click", () => { if (convAmount) convAmount.value = btn.dataset.amount; updateConversion(); haptic(); });
});
document.querySelectorAll(".conv-tab").forEach(btn => {
    btn.addEventListener("click", () => switchConvTab(btn.dataset.convTab));
});
[goldAmount, goldUnit, goldKarat, goldTarget].forEach(el => {
    if (el) el.addEventListener("input", updateGoldCalc);
    if (el) el.addEventListener("change", updateGoldCalc);
});

// News
newsChips.forEach(chip => chip.addEventListener("click", () => {
    newsLang = chip.dataset.lang;
    newsChips.forEach(c => {
        c.classList.toggle("active", c === chip);
        c.setAttribute("aria-pressed", String(c === chip));
    });
    renderNews(); haptic();
}));

// Portfolio
if (portfolioBtn) portfolioBtn.addEventListener("click", openPortfolio);
if (portClose) portClose.addEventListener("click", closePortfolio);
if (portfolioModal) portfolioModal.addEventListener("click", (e) => { if (e.target.dataset.closePort === "1") closePortfolio(); });
if (portAdd) portAdd.addEventListener("click", portAddItem);

// Alerts
if (alertsBtn) alertsBtn.addEventListener("click", openAlerts);
if (alertClose) alertClose.addEventListener("click", closeAlerts);
if (alertsModal) alertsModal.addEventListener("click", (e) => { if (e.target.dataset.closeAlert === "1") closeAlerts(); });
if (alertAdd) alertAdd.addEventListener("click", alertAddItem);

// Settings
if (settingsBtn) settingsBtn.addEventListener("click", openSettings);
if (setClose) setClose.addEventListener("click", closeSettings);
if (settingsModal) settingsModal.addEventListener("click", (e) => { if (e.target.dataset.closeSet === "1") closeSettings(); });
if (setSound) setSound.addEventListener("change", () => {
    settings.sound = setSound.checked;
    localStorage.setItem("ex_set_sound", settings.sound ? "1" : "0");
    if (settings.sound) playBeep();
});
if (setAutoDark) setAutoDark.addEventListener("change", () => {
    settings.autoDark = setAutoDark.checked;
    localStorage.setItem("ex_set_autodark", settings.autoDark ? "1" : "0");
    if (settings.autoDark) applyAutoDark();
});
if (setCompact) setCompact.addEventListener("change", () => {
    settings.compact = setCompact.checked;
    localStorage.setItem("ex_set_compact", settings.compact ? "1" : "0");
    applyCompact();
});
if (setRefresh) setRefresh.addEventListener("change", () => {
    REFRESH_MS = parseInt(setRefresh.value, 10) || 10000;
    localStorage.setItem("ex_refresh_ms", String(REFRESH_MS));
    connectWS();
    toast("⏱ " + setRefresh.options[setRefresh.selectedIndex].text, "success");
});
if (setExportAll) setExportAll.addEventListener("click", () => exportData("json"));
if (setReset) setReset.addEventListener("click", () => {
    if (!confirm("همه‌چیز ریست شود؟")) return;
    ["ex_watchlist", "ex_portfolio", "ex_alerts", "ex_recent_searches",
     "ex_theme", "ex_palette", "ex_lang", "ex_set_sound", "ex_set_autodark",
     "ex_set_compact", "ex_refresh_ms"].forEach(k => localStorage.removeItem(k));
    toast(t("toastReset"), "success");
    setTimeout(() => location.reload(), 800);
});

// Compare
if (cmpClose) cmpClose.addEventListener("click", closeCompare);
if (compareModal) compareModal.addEventListener("click", (e) => { if (e.target.dataset.closeCmp === "1") closeCompare(); });
if (cmpA) cmpA.addEventListener("change", () => { compareState.a = cmpA.value; renderCompare(); });
if (cmpB) cmpB.addEventListener("change", () => { compareState.b = cmpB.value; renderCompare(); });

// Command Palette
if (cmdBtn) cmdBtn.addEventListener("click", openCmd);
if (cmdModal) cmdModal.addEventListener("click", (e) => { if (e.target.dataset.closeCmd === "1") closeCmd(); });
if (cmdInput) {
    cmdInput.addEventListener("input", () => renderCmdResults(cmdInput.value));
    cmdInput.addEventListener("keydown", (e) => {
        if (e.key === "ArrowDown") {
            e.preventDefault();
            if (cmdSelectedIndex < cmdFiltered.length - 1) cmdSelectedIndex++;
            updateCmdSelection();
            cmdResults.querySelector(".cmd-item.selected")?.scrollIntoView({ block: "nearest" });
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            if (cmdSelectedIndex > 0) cmdSelectedIndex--;
            updateCmdSelection();
            cmdResults.querySelector(".cmd-item.selected")?.scrollIntoView({ block: "nearest" });
        } else if (e.key === "Enter") {
            e.preventDefault();
            const item = cmdFiltered[cmdSelectedIndex];
            if (item && item.run) item.run();
        } else if (e.key === "Escape") {
            closeCmd();
        }
    });
}

// PWA
if (pwaInstallBtn) pwaInstallBtn.addEventListener("click", (e) => { if (e.target.id === "pwaClose") return; installPWA(); });
if (pwaClose) pwaClose.addEventListener("click", (e) => { e.stopPropagation(); hidePwaInstall(); localStorage.setItem("ex_pwa_dismissed", "1"); });

function showPwaInstall() {
    if (!pwaInstallBtn) return;
    if (localStorage.getItem("ex_pwa_dismissed") === "1") return;
    pwaInstallBtn.classList.add("on");
}
function hidePwaInstall() {
    if (!pwaInstallBtn) return;
    pwaInstallBtn.classList.remove("on");
}
window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredInstallPrompt = e;
    showPwaInstall();
});
window.addEventListener("appinstalled", () => {
    deferredInstallPrompt = null;
    hidePwaInstall();
    localStorage.setItem("ex_pwa_dismissed", "1");
});
async function installPWA() {
    if (!deferredInstallPrompt) return;
    try {
        deferredInstallPrompt.prompt();
        const { outcome } = await deferredInstallPrompt.userChoice;
        if (outcome === "accepted") hidePwaInstall();
        deferredInstallPrompt = null;
    } catch (e) { hidePwaInstall(); }
}

// Keyboard shortcuts
document.addEventListener("keydown", (e) => {
    // Ctrl+K یا Cmd+K
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        openCmd();
        return;
    }
    // Escape
    if (e.key === "Escape") {
        if (cmdModal && cmdModal.classList.contains("on")) closeCmd();
        if (modal && modal.classList.contains("on")) closeChart();
        if (convModal && convModal.classList.contains("on")) closeConverter();
        if (portfolioModal && portfolioModal.classList.contains("on")) closePortfolio();
        if (alertsModal && alertsModal.classList.contains("on")) closeAlerts();
        if (settingsModal && settingsModal.classList.contains("on")) closeSettings();
        if (compareModal && compareModal.classList.contains("on")) closeCompare();
        return;
    }
    // Tab داخل مودال باز بچرخد (focus trap)
    if (e.key === "Tab") { trapFocus(e); return; }
    // / برای focus search
    if (e.key === "/" && !e.ctrlKey && !e.metaKey && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
        e.preventDefault();
        if (searchInput) searchInput.focus();
        return;
    }
    // r برای refresh
    if (e.key.toLowerCase() === "r" && !e.ctrlKey && !e.metaKey && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
        e.preventDefault();
        fetchPrices();
        toast("🔄 بروزرسانی", "success");
        return;
    }
});

/* =========================================================
   INIT
========================================================= */

setPalette(currentPalette);
setTheme(currentTheme);
applyAutoDark();
applyCompact();
applyI18n();

updateClock();
setInterval(updateClock, 1000);

connectWS();
document.addEventListener("visibilitychange", () => {
    if (!document.hidden) fetchPrices();   // برگشت به تب = قیمت تازه
});
loadFearGreed();
setInterval(loadFearGreed, 3600000);
setInterval(applyAutoDark, 300000);

setInterval(() => {
    if (activeCategory === "news" && !document.hidden) {
        newsLoaded = false;
        loadNews();
    }
}, 300000);

if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
        navigator.serviceWorker.register("/sw.js").catch(err => console.log("SW failed:", err));
    });
}