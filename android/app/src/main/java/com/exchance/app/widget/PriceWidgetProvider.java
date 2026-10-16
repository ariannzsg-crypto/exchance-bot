package com.exchance.app.widget;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.util.Log;
import android.widget.RemoteViews;

import com.exchance.app.MainActivity;
import com.exchance.app.R;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * ویجت قیمت: هر نمونه نماد خودش را نشان می‌دهد (دلار، طلا، سکه، بیت‌کوین…).
 *
 * <p>سه کار انجام می‌دهد:
 * <ol>
 *   <li>از حافظه‌ی نهان فوراً چیزی روی صفحه می‌گذارد (پس آفلاین هم خالی نیست)،</li>
 *   <li>در پس‌زمینه قیمت‌ها را تازه می‌کند،</li>
 *   <li>بعد از هر تازه‌سازی، حدهای هشدار را بررسی می‌کند.</li>
 * </ol>
 *
 * <p>شبکه در ترد پس‌زمینه انجام می‌شود و با {@code goAsync()} برادکست تا پایان
 * کار زنده می‌ماند؛ بدون این کار سیستم ممکن است پروسه را وسط درخواست بکشد.
 */
public class PriceWidgetProvider extends AppWidgetProvider {

    public static final String ACTION_REFRESH = "com.exchance.app.widget.REFRESH";
    public static final String ACTION_CHECK_ALERTS = "com.exchance.app.widget.CHECK_ALERTS";

    private static final String TAG = "ExWidget";
    private static final AtomicBoolean RUNNING = new AtomicBoolean(false);
    /** کمترین فاصله‌ی دو درخواست شبکه؛ جلوی اسپم (مثلاً کلیک پیاپی) را می‌گیرد. */
    private static final long MIN_INTERVAL_MS = 30000L;

    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent == null ? "" : String.valueOf(intent.getAction());
        if (AppWidgetManager.ACTION_APPWIDGET_UPDATE.equals(action)
                || ACTION_REFRESH.equals(action)
                || ACTION_CHECK_ALERTS.equals(action)) {
            final PendingResult pending = goAsync();
            final Context app = context.getApplicationContext();
            renderAll(app);                     // اول کش، تا کاربر بلافاصله چیزی ببیند
            new Thread(new Runnable() {
                @Override
                public void run() {
                    try {
                        refreshNow(app);
                    } finally {
                        pending.finish();
                    }
                }
            }, "ex-price-refresh").start();
            return;
        }
        super.onReceive(context, intent);
    }

    @Override
    public void onUpdate(Context context, AppWidgetManager manager, int[] ids) {
        // refreshAsync خودش اول از کش می‌کشد و بعد شبکه را می‌خواند
        refreshAsync(context.getApplicationContext());
    }

    @Override
    public void onDeleted(Context context, int[] ids) {
        Context app = context.getApplicationContext();
        for (int id : ids) {
            PriceStore.forgetWidget(app, id);
        }
        AlertScheduler.sync(app);
    }

    /** تازه‌سازی بدون انتظار — از اپ، از آلارم و از بوت صدا زده می‌شود. */
    public static void refreshAsync(Context context) {
        final Context app = context.getApplicationContext();
        renderAll(app);
        new Thread(new Runnable() {
            @Override
            public void run() {
                refreshNow(app);
            }
        }, "ex-price-refresh").start();
    }

    public static boolean anyInstalled(Context context) {
        AppWidgetManager manager = AppWidgetManager.getInstance(context);
        return manager != null
                && manager.getAppWidgetIds(new ComponentName(context, PriceWidgetProvider.class)).length > 0;
    }

    /** همه‌ی نمونه‌ها را از حافظه‌ی نهان به‌روز می‌کند. */
    public static void renderAll(Context context) {
        AppWidgetManager manager = AppWidgetManager.getInstance(context);
        if (manager == null) {
            return;
        }
        int[] ids = manager.getAppWidgetIds(new ComponentName(context, PriceWidgetProvider.class));
        for (int id : ids) {
            manager.updateAppWidget(id, viewFor(context, id));
        }
    }

    // --------------------------------------------------------------- درونی

    private static void refreshNow(Context context) {
        long updatedAt = PriceStore.updatedAt(context);
        if (updatedAt > 0 && System.currentTimeMillis() - updatedAt < MIN_INTERVAL_MS) {
            renderAll(context);      // قیمت کش تازه است؛ همان را نشان بده
            return;
        }
        if (!RUNNING.compareAndSet(false, true)) {
            return;
        }
        try {
            List<Price> prices = PriceApi.fetch(context);
            if (!prices.isEmpty()) {
                PriceStore.savePrices(context, prices);
                Alerts.evaluate(context, prices);
            }
        } catch (Exception e) {
            Log.w(TAG, "قیمت‌ها نیامد: " + e.getMessage());
        } finally {
            RUNNING.set(false);
            renderAll(context);
        }
    }

    private static RemoteViews viewFor(Context context, int widgetId) {
        RemoteViews view = new RemoteViews(context.getPackageName(), R.layout.ex_widget_price);
        String code = PriceStore.widgetCode(context, widgetId);

        view.setOnClickPendingIntent(R.id.ex_widget_refresh, refreshIntent(context));
        view.setOnClickPendingIntent(R.id.ex_widget_root,
                code.isEmpty() ? configIntent(context, widgetId) : openIntent(context, code));

        long at = PriceStore.updatedAt(context);
        if (at > 0) {
            String clock = new SimpleDateFormat("HH:mm", Locale.getDefault()).format(new Date(at));
            view.setTextViewText(R.id.ex_widget_time, context.getString(R.string.ex_widget_updated, clock));
        } else {
            view.setTextViewText(R.id.ex_widget_time, "");
        }

        if (code.isEmpty()) {
            view.setTextViewText(R.id.ex_widget_flag, "📈");
            view.setTextViewText(R.id.ex_widget_name, context.getString(R.string.ex_widget_label));
            view.setTextViewText(R.id.ex_widget_price, context.getString(R.string.ex_widget_no_symbol));
            view.setTextViewText(R.id.ex_widget_change, "");
            view.setTextViewText(R.id.ex_widget_unit, "");
            return view;
        }

        Price price = PriceStore.cached(context, code);
        if (price == null || !price.hasValue()) {
            view.setTextViewText(R.id.ex_widget_flag, "⏳");
            view.setTextViewText(R.id.ex_widget_name, code.toUpperCase(Locale.US));
            view.setTextViewText(R.id.ex_widget_price, context.getString(R.string.ex_widget_loading));
            view.setTextViewText(R.id.ex_widget_change, "");
            view.setTextViewText(R.id.ex_widget_unit, "");
            return view;
        }

        view.setTextViewText(R.id.ex_widget_flag, price.flag.isEmpty() ? "💱" : price.flag);
        view.setTextViewText(R.id.ex_widget_name, price.name);
        view.setTextViewText(R.id.ex_widget_price, Money.price(price.value));
        view.setTextViewText(R.id.ex_widget_unit, price.unit);
        view.setTextViewText(R.id.ex_widget_change, Money.change(price.change));
        view.setTextColor(R.id.ex_widget_change,
                context.getColor(Money.isUp(price.change) ? R.color.ex_up : R.color.ex_down));
        return view;
    }

    private static PendingIntent refreshIntent(Context context) {
        Intent intent = new Intent(context, PriceWidgetProvider.class).setAction(ACTION_REFRESH);
        return PendingIntent.getBroadcast(context, 11, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    private static PendingIntent openIntent(Context context, String code) {
        Intent intent = new Intent(context, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                .putExtra("ex_symbol", code);
        return PendingIntent.getActivity(context, 12, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    private static PendingIntent configIntent(Context context, int widgetId) {
        Intent intent = new Intent(context, WidgetConfigActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                .putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, widgetId);
        return PendingIntent.getActivity(context, 13, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }
}
