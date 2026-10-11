/* آدرس API — تک نقطه‌ی تنظیم برای اپ‌های بومی.
 *
 *  • در مرورگر (وب/ورسل): خالی می‌ماند و همه‌ی درخواست‌ها نسبت به همان مبدأ
 *    زده می‌شوند (`/api/market`).
 *  • در اپ اندروید: صفحه از داخل خود اپ سرو می‌شود، پس مسیرهای نسبی به هیچ
 *    سروری نمی‌رسند؛ اینجا آدرس دیپلوی ورسل استفاده می‌شود.
 *
 *  ⚠️ بعد از اولین دیپلوی روی ورسل، فقط همین یک خط را با دامنه‌ی خودت عوض کن.
 */
(function () {
    "use strict";

    var DEPLOYED_API = "https://exchance-bot.vercel.app";

    var isNative = !!(window.Capacitor &&
        typeof window.Capacitor.isNativePlatform === "function" &&
        window.Capacitor.isNativePlatform());

    window.API_BASE = isNative ? DEPLOYED_API.replace(/\/+$/, "") : "";
})();
