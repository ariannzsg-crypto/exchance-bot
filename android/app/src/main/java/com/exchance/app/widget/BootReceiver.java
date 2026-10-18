package com.exchance.app.widget;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** بعد از روشن شدن گوشی، آلارم‌ها و قیمت ویجت‌ها را دوباره سرِ کار می‌آورد. */
public class BootReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent == null ? "" : String.valueOf(intent.getAction());
        // آپدیت اپ هم آلارم‌ها را پاک می‌کند؛ بدون این حالت، هشدارها بعد از
        // هر به‌روزرسانی از فروشگاه تا باز شدن دستی اپ خاموش می‌مانند.
        if (!Intent.ACTION_BOOT_COMPLETED.equals(action)
                && !Intent.ACTION_MY_PACKAGE_REPLACED.equals(action)) {
            return;
        }
        Context app = context.getApplicationContext();
        AlertScheduler.sync(app);
        PriceWidgetProvider.refreshAsync(app);
    }
}
