package com.exchance.app.widget;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** بعد از روشن شدن گوشی، آلارم‌ها و قیمت ویجت‌ها را دوباره سرِ کار می‌آورد. */
public class BootReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || !Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) {
            return;
        }
        Context app = context.getApplicationContext();
        AlertScheduler.sync(app);
        PriceWidgetProvider.refreshAsync(app);
    }
}
