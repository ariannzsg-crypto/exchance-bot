package com.exchance.app.widget;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** آلارم دوره‌ای به اینجا می‌رسد و همان موتور تازه‌سازی ویجت را می‌چرخاند. */
public class AlertAlarmReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        Context app = context.getApplicationContext();
        AlertScheduler.sync(app);          // اگر کاربر حدها را پاک کرده باشد، لغو شود
        PriceWidgetProvider.refreshAsync(app);
    }
}
