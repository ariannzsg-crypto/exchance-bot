package com.exchance.app.widget;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.widget.RemoteViews;

import com.exchance.app.MainActivity;
import com.exchance.app.R;

/**
 * اعلان مخصوص اپ: یک کانال جدا با اهمیت بالا و ویبره‌ی خودش، و چیدمان سفارشی
 * (پرچم، نام، قیمت، تغییر) به‌جای اعلان پیش‌فرض اندروید.
 */
public final class Notifier {

    public static final String CHANNEL_ID = "ex_price_alerts";

    private Notifier() {
    }

    /** اندروید ۱۳ به بعد اجازه‌ی اعلان را باید کاربر بدهد. */
    public static boolean canNotify(Context ctx) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            return true;
        }
        return ctx.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                == PackageManager.PERMISSION_GRANTED;
    }

    public static void ensureChannel(Context ctx) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return;
        }
        NotificationManager nm =
                (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null || nm.getNotificationChannel(CHANNEL_ID) != null) {
            return;
        }
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                ctx.getString(R.string.ex_notif_channel),
                NotificationManager.IMPORTANCE_HIGH);
        channel.setDescription(ctx.getString(R.string.ex_notif_channel_desc));
        channel.enableVibration(true);
        channel.setVibrationPattern(new long[]{0L, 220L, 120L, 220L});
        channel.setShowBadge(true);
        nm.createNotificationChannel(channel);
    }

    /**
     * خبر دادن از عبور قیمت از حدی که کاربر گذاشته.
     *
     * @param high اگر true باشد یعنی از حدِ بالا رد شده، وگرنه به حد پایین رسیده.
     */
    public static void post(Context ctx, Price p, double level, boolean high) {
        if (!canNotify(ctx)) {
            return;
        }
        ensureChannel(ctx);
        NotificationManager nm =
                (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) {
            return;
        }

        String priceText = Money.price(p.value) + " " + p.unit;
        String levelText = Money.price(level) + " " + p.unit;
        String title = ctx.getString(
                high ? R.string.ex_notif_high_title : R.string.ex_notif_low_title, p.name);
        String body = ctx.getString(R.string.ex_notif_body, priceText, levelText);

        RemoteViews view = new RemoteViews(ctx.getPackageName(), R.layout.ex_notification_price);
        view.setTextViewText(R.id.ex_notif_flag, p.flag.isEmpty() ? "💱" : p.flag);
        view.setTextViewText(R.id.ex_notif_name, p.name);
        view.setTextViewText(R.id.ex_notif_price, priceText);
        view.setTextViewText(R.id.ex_notif_change, Money.change(p.change));
        int changeColor = Money.isUp(p.change) ? R.color.ex_up
                : p.change < 0 ? R.color.ex_down : R.color.ex_text_dim;
        view.setTextColor(R.id.ex_notif_change, ctx.getColor(changeColor));
        view.setTextViewText(R.id.ex_notif_note, body);

        Intent open = new Intent(ctx, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP)
                .putExtra("ex_symbol", p.code);
        PendingIntent tap = PendingIntent.getActivity(ctx, p.code.hashCode() ^ (high ? 1 : 2),
                open, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(ctx, CHANNEL_ID)
                : new Notification.Builder(ctx);
        builder.setSmallIcon(R.drawable.ex_stat_price)
                .setContentTitle(title)
                .setContentText(body)
                .setStyle(new Notification.BigTextStyle().bigText(body))
                .setCustomContentView(view)
                .setContentIntent(tap)
                .setAutoCancel(true)
                .setWhen(System.currentTimeMillis())
                .setShowWhen(true);
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            builder.setPriority(Notification.PRIORITY_HIGH);
            builder.setVibrate(new long[]{0L, 220L, 120L, 220L});
        }

        nm.notify((p.code + (high ? "_high" : "_low")).hashCode(), builder.build());
    }
}
