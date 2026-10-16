package com.exchance.app.widget;

import android.content.Context;
import android.content.SharedPreferences;

import com.exchance.app.R;

import java.util.ArrayList;
import java.util.List;

/**
 * تنها جایی که داده‌ی بومی نگه داشته می‌شود.
 *
 * <p>سه چیز اینجا زندگی می‌کنند: آخرین قیمت‌های گرفته‌شده (تا ویجت آفلاین هم
 * چیزی نشان بدهد)، نماد انتخابیِ هر ویجت، و حدهای هشدار هر نماد.
 */
public final class PriceStore {

    private static final String PREFS = "ex_price";
    private static final String CODES = "p_codes";
    private static final String UPDATED_AT = "p_at";

    private PriceStore() {
    }

    public static SharedPreferences prefs(Context ctx) {
        return ctx.getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public static String apiBase(Context ctx) {
        return ctx.getApplicationContext().getString(R.string.ex_api_base);
    }

    // ---------------------------------------------------------------- قیمت‌ها

    public static void savePrices(Context ctx, List<Price> prices) {
        SharedPreferences.Editor ed = prefs(ctx).edit();
        List<String> codes = new ArrayList<>(prices.size());
        for (Price p : prices) {
            codes.add(p.code);
            ed.putString("p_" + p.code + "_name", p.name);
            ed.putString("p_" + p.code + "_flag", p.flag);
            ed.putString("p_" + p.code + "_unit", p.unit);
            ed.putString("p_" + p.code + "_price", p.hasValue() ? String.valueOf(p.value) : "");
            ed.putString("p_" + p.code + "_change", String.valueOf(p.change));
            ed.putString("p_" + p.code + "_usd", Double.isFinite(p.usd) ? String.valueOf(p.usd) : "");
        }
        ed.putString(CODES, join(codes));
        ed.putLong(UPDATED_AT, System.currentTimeMillis());
        ed.apply();
    }

    public static Price cached(Context ctx, String code) {
        if (code == null || code.isEmpty()) {
            return null;
        }
        SharedPreferences p = prefs(ctx);
        String key = "p_" + code + "_price";
        if (!p.contains(key)) {
            return null;
        }
        return new Price(
                code,
                p.getString("p_" + code + "_name", code),
                p.getString("p_" + code + "_flag", ""),
                p.getString("p_" + code + "_unit", "تومان"),
                parse(p.getString(key, ""), Double.NaN),
                parse(p.getString("p_" + code + "_change", ""), 0d),
                parse(p.getString("p_" + code + "_usd", ""), Double.NaN));
    }

    public static List<Price> cachedAll(Context ctx) {
        List<Price> out = new ArrayList<>();
        for (String code : prefs(ctx).getString(CODES, "").split(",")) {
            if (code.isEmpty()) {
                continue;
            }
            Price p = cached(ctx, code);
            if (p != null) {
                out.add(p);
            }
        }
        return out;
    }

    public static long updatedAt(Context ctx) {
        return prefs(ctx).getLong(UPDATED_AT, 0L);
    }

    // ------------------------------------------------------- نماد هر ویجت

    public static String widgetCode(Context ctx, int widgetId) {
        return prefs(ctx).getString("w_" + widgetId + "_code", "");
    }

    public static void setWidgetCode(Context ctx, int widgetId, String code) {
        prefs(ctx).edit().putString("w_" + widgetId + "_code", code).apply();
    }

    public static void forgetWidget(Context ctx, int widgetId) {
        prefs(ctx).edit().remove("w_" + widgetId + "_code").apply();
    }

    // ------------------------------------------------------- حدهای هشدار

    public static void setAlerts(Context ctx, String code, double high, double low) {
        SharedPreferences.Editor ed = prefs(ctx).edit();
        if (high > 0) {
            ed.putString("a_" + code + "_high", String.valueOf(high));
        } else {
            ed.remove("a_" + code + "_high");
        }
        if (low > 0) {
            ed.putString("a_" + code + "_low", String.valueOf(low));
        } else {
            ed.remove("a_" + code + "_low");
        }
        // حد تازه باید بتواند بلافاصله خبر بدهد، پس وضعیت «قبلاً گفته» پاک می‌شود
        ed.remove("a_" + code + "_high_fired");
        ed.remove("a_" + code + "_low_fired");
        ed.apply();
    }

    public static double alertHigh(Context ctx, String code) {
        return parse(prefs(ctx).getString("a_" + code + "_high", ""), 0d);
    }

    public static double alertLow(Context ctx, String code) {
        return parse(prefs(ctx).getString("a_" + code + "_low", ""), 0d);
    }

    public static boolean firedHigh(Context ctx, String code) {
        return prefs(ctx).getBoolean("a_" + code + "_high_fired", false);
    }

    public static void setFiredHigh(Context ctx, String code, boolean fired) {
        prefs(ctx).edit().putBoolean("a_" + code + "_high_fired", fired).apply();
    }

    public static boolean firedLow(Context ctx, String code) {
        return prefs(ctx).getBoolean("a_" + code + "_low_fired", false);
    }

    public static void setFiredLow(Context ctx, String code, boolean fired) {
        prefs(ctx).edit().putBoolean("a_" + code + "_low_fired", fired).apply();
    }

    /** کدهایی که دست‌کم یک حد دارند. */
    public static List<String> alertCodes(Context ctx) {
        List<String> out = new ArrayList<>();
        for (String code : prefs(ctx).getString(CODES, "").split(",")) {
            if (code.isEmpty()) {
                continue;
            }
            if (alertHigh(ctx, code) > 0 || alertLow(ctx, code) > 0) {
                out.add(code);
            }
        }
        return out;
    }

    // ------------------------------------------------------------- کمکی‌ها

    private static String join(List<String> items) {
        StringBuilder sb = new StringBuilder();
        for (String s : items) {
            if (s == null || s.isEmpty()) {
                continue;
            }
            if (sb.length() > 0) {
                sb.append(',');
            }
            sb.append(s);
        }
        return sb.toString();
    }

    private static double parse(String raw, double fallback) {
        if (raw == null || raw.isEmpty()) {
            return fallback;
        }
        try {
            return Double.parseDouble(raw);
        } catch (NumberFormatException e) {
            return fallback;
        }
    }
}
