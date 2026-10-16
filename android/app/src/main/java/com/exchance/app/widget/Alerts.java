package com.exchance.app.widget;

import android.content.Context;

import java.util.List;

/**
 * تصمیم می‌گیرد کدام حد رد شده و چه زمانی باید خبر بدهد.
 *
 * <p>هر حد فقط یک بار خبر می‌دهد و تا وقتی قیمت به سمت سالم برنگردد دوباره
 * پیام نمی‌فرستد (هیسترزیس). بدون این کار، نمادی که روی مرز نوسان می‌کند
 * هر نیم‌ساعت یک اعلان تکراری می‌ساخت.
 */
public final class Alerts {

    /** ۰٫۲٪ فاصله برای «برگشتن به حالت سالم». */
    private static final double HYSTERESIS = 0.002;

    private Alerts() {
    }

    public static void evaluate(Context ctx, List<Price> prices) {
        if (prices == null || prices.isEmpty()) {
            return;
        }
        for (Price p : prices) {
            double high = PriceStore.alertHigh(ctx, p.code);
            double low = PriceStore.alertLow(ctx, p.code);
            if ((high <= 0 && low <= 0) || !p.hasValue()) {
                continue;
            }

            if (high > 0) {
                if (p.value >= high && !PriceStore.firedHigh(ctx, p.code)) {
                    Notifier.post(ctx, p, high, true);
                    PriceStore.setFiredHigh(ctx, p.code, true);
                } else if (p.value < high * (1 - HYSTERESIS) && PriceStore.firedHigh(ctx, p.code)) {
                    PriceStore.setFiredHigh(ctx, p.code, false);
                }
            }

            if (low > 0) {
                if (p.value <= low && !PriceStore.firedLow(ctx, p.code)) {
                    Notifier.post(ctx, p, low, false);
                    PriceStore.setFiredLow(ctx, p.code, true);
                } else if (p.value > low * (1 + HYSTERESIS) && PriceStore.firedLow(ctx, p.code)) {
                    PriceStore.setFiredLow(ctx, p.code, false);
                }
            }
        }
    }
}
