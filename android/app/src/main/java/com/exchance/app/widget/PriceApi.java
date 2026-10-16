package com.exchance.app.widget;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * خواندن قیمت‌ها از همان اندپوینتی که خود اپ استفاده می‌کند.
 *
 * <p>عمداً بدون هیچ کتابخانه‌ای: {@code HttpURLConnection} و {@code org.json}
 * هر دو داخل خود اندروید هستند، پس نه وابستگی جدیدی به پروژه اضافه می‌شود و نه
 * حجم APK بالا می‌رود.
 */
public final class PriceApi {

    private static final int TIMEOUT_MS = 12000;

    private PriceApi() {
    }

    /** فهرست نمادها با قیمت؛ در نبود شبکه استثنا می‌دهد و صداکننده کش را می‌خواند. */
    public static List<Price> fetch(Context ctx) throws Exception {
        String body = get(PriceStore.apiBase(ctx) + "/api/market");
        JSONArray arr = new JSONObject(body).optJSONArray("currencies");
        if (arr == null) {
            return Collections.emptyList();
        }
        List<Price> out = new ArrayList<>(arr.length());
        for (int i = 0; i < arr.length(); i++) {
            JSONObject o = arr.optJSONObject(i);
            if (o == null) {
                continue;
            }
            String code = o.optString("code", "");
            if (code.isEmpty()) {
                continue;
            }
            out.add(new Price(
                    code,
                    o.optString("name", code),
                    o.optString("flag", ""),
                    o.optString("unit", "تومان"),
                    o.optDouble("price", Double.NaN),
                    o.optDouble("change", 0d),
                    o.optDouble("usd_price", Double.NaN)));
        }
        return out;
    }

    private static String get(String url) throws Exception {
        HttpURLConnection conn = null;
        try {
            conn = (HttpURLConnection) new URL(url).openConnection();
            conn.setConnectTimeout(TIMEOUT_MS);
            conn.setReadTimeout(TIMEOUT_MS);
            conn.setRequestProperty("Accept", "application/json");
            conn.setRequestProperty("Cache-Control", "no-cache");
            int status = conn.getResponseCode();
            InputStream in = status >= 400 ? conn.getErrorStream() : conn.getInputStream();
            if (in == null) {
                throw new IllegalStateException("HTTP " + status);
            }
            StringBuilder sb = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(in, StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    sb.append(line);
                }
            }
            if (status >= 400) {
                throw new IllegalStateException("HTTP " + status);
            }
            return sb.toString();
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }
}
