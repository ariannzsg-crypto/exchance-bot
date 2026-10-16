package com.exchance.app.widget;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;

/**
 * بررسی دوره‌ای هشدارها، حتی وقتی ویجتی روی صفحه نیست.
 *
 * <p>از آلارم «غیردقیق» استفاده می‌شود: نه اجازه‌ی خاصی می‌خواهد (برخلاف آلارم
 * دقیق در اندروید ۱۲+) و نه باتری را می‌خورد، چون خود سیستم زمان اجراها را
 * کنار هم دسته می‌کند. اگر هیچ حدی ثبت نشده باشد، آلارم لغو می‌شود.
 */
public final class AlertScheduler {

    private static final int REQUEST_CODE = 42;

    private AlertScheduler() {
    }

    public static void sync(Context ctx) {
        AlarmManager am = (AlarmManager) ctx.getSystemService(Context.ALARM_SERVICE);
        if (am == null) {
            return;
        }
        PendingIntent pi = pending(ctx);
        if (PriceStore.alertCodes(ctx).isEmpty()) {
            am.cancel(pi);
            pi.cancel();
            return;
        }
        am.setInexactRepeating(AlarmManager.RTC,
                System.currentTimeMillis() + AlarmManager.INTERVAL_HALF_HOUR,
                AlarmManager.INTERVAL_HALF_HOUR,
                pi);
    }

    private static PendingIntent pending(Context ctx) {
        Intent intent = new Intent(ctx, AlertAlarmReceiver.class)
                .setAction(PriceWidgetProvider.ACTION_CHECK_ALERTS);
        return PendingIntent.getBroadcast(ctx, REQUEST_CODE, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }
}
