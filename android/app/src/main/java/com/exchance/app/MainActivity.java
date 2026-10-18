package com.exchance.app;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.webkit.WebView;

import com.exchance.app.widget.AlertScheduler;
import com.exchance.app.widget.PriceStore;
import com.exchance.app.widget.PriceWidgetProvider;
import com.getcapacitor.Bridge;
import com.getcapacitor.BridgeActivity;

import java.util.Locale;

public class MainActivity extends BridgeActivity {

    private static final int REQUEST_NOTIFICATIONS = 91;
    private static final long SYMBOL_RETRY_MS = 400L;
    private static final int SYMBOL_RETRIES = 25;

    /** نمادی که از ویجت/اعلان آمده و هنوز به صفحه نرسیده است. */
    private String pendingSymbol;
    private int symbolTries;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // بعد از ریبوت یا به‌روزرسانی، آلارم‌ها را دوباره سرِ کار بیاور
        AlertScheduler.sync(this);
        readSymbol(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        readSymbol(intent);
        openPendingSymbol();
    }

    @Override
    public void onStart() {
        super.onStart();
        // باز شدن اپ = بهترین وقت برای تازه کردن ویجت
        PriceWidgetProvider.refreshAsync(this);
        askForNotificationsIfNeeded();
        openPendingSymbol();
    }

    /**
     * کد نماد را از اکسترای ویجت/اعلان می‌خواند.
     *
     * <p>فقط حروف/ارقام/خط تیره می‌ماند تا مقدارِ داخل اکسترا هرگز نتواند
     * به کد جاوااسکریپت تزریق شود.
     */
    private void readSymbol(Intent intent) {
        if (intent == null) {
            return;
        }
        String raw = intent.getStringExtra("ex_symbol");
        if (raw == null) {
            return;
        }
        String clean = raw.trim().toLowerCase(Locale.US).replaceAll("[^a-z0-9_-]", "");
        if (clean.isEmpty()) {
            return;
        }
        pendingSymbol = clean;
        symbolTries = 0;
    }

    /**
     * از صفحه‌ی وب می‌خواهد نمودار همان نماد را باز کند.
     *
     * <p>صفحه ممکن است هنوز بارگذاری نشده باشد؛ پس چند بار (با فاصله‌ی کوتاه)
     * تلاش می‌کنیم تا تابعِ {@code exOpenSymbol} در دسترس قرار بگیرد.
     */
    private void openPendingSymbol() {
        final String code = pendingSymbol;
        if (code == null) {
            return;
        }
        Bridge bridge = getBridge();
        WebView web = bridge == null ? null : bridge.getWebView();
        if (web == null) {
            retrySymbol();
            return;
        }
        String js = "(function(){try{return !!(window.exOpenSymbol && window.exOpenSymbol('"
                + code + "'));}catch(e){return false;}})()";
        web.evaluateJavascript(js, value -> {
            if ("true".equals(value)) {
                pendingSymbol = null;
            } else {
                retrySymbol();
            }
        });
    }

    private void retrySymbol() {
        if (pendingSymbol == null) {
            return;
        }
        if (symbolTries++ >= SYMBOL_RETRIES) {
            pendingSymbol = null;   // صفحه بالا نیامد؛ دیگر تلاشی نکن
            return;
        }
        View root = getWindow() == null ? null : getWindow().getDecorView();
        if (root == null) {
            pendingSymbol = null;
            return;
        }
        root.postDelayed(this::openPendingSymbol, SYMBOL_RETRY_MS);
    }

    /**
     * اجازه‌ی اعلان را وقتی می‌خواهیم که واقعاً به آن نیاز داریم: کاربر یا حد
     * هشدار گذاشته، یا ویجت روی صفحه دارد. در غیر این صورت مزاحم نمی‌شویم.
     */
    private void askForNotificationsIfNeeded() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            return;   // قبل از اندروید ۱۳ اجازه‌ی جدا لازم نبود
        }
        boolean wanted = !PriceStore.alertCodes(this).isEmpty()
                || PriceWidgetProvider.anyInstalled(this);
        if (!wanted || checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                == PackageManager.PERMISSION_GRANTED) {
            return;
        }
        requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, REQUEST_NOTIFICATIONS);
    }
}
