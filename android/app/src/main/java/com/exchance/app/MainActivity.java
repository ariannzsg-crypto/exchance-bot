package com.exchance.app;

import android.Manifest;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;

import com.exchance.app.widget.AlertScheduler;
import com.exchance.app.widget.PriceStore;
import com.exchance.app.widget.PriceWidgetProvider;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    private static final int REQUEST_NOTIFICATIONS = 91;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // بعد از ریبوت یا به‌روزرسانی، آلارم‌ها را دوباره سرِ کار بیاور
        AlertScheduler.sync(this);
    }

    @Override
    public void onStart() {
        super.onStart();
        // باز شدن اپ = بهترین وقت برای تازه کردن ویجت
        PriceWidgetProvider.refreshAsync(this);
        askForNotificationsIfNeeded();
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
