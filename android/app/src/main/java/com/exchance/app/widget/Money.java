package com.exchance.app.widget;

import java.text.NumberFormat;
import java.util.Locale;

/** قالب‌بندی عدد — همان منطقی که رابط وب برای قیمت‌ها دارد. */
public final class Money {

    private Money() {
    }

    /** قیمت با جداکننده‌ی هزارگان؛ برای عددهای کوچک دو رقم اعشار نگه می‌دارد. */
    public static String price(double v) {
        if (!Double.isFinite(v)) {
            return "—";
        }
        double abs = Math.abs(v);
        int digits = abs >= 100 ? 0 : (abs >= 1 ? 2 : 4);
        NumberFormat nf = NumberFormat.getNumberInstance(Locale.US);
        nf.setGroupingUsed(true);
        nf.setMaximumFractionDigits(digits);
        nf.setMinimumFractionDigits(0);
        return nf.format(v);
    }

    /** تغییر ۲۴ ساعته با علامت و درصد: «+۲٫۴۸٪» نه؛ علامت و درصد لاتین. */
    public static String change(double v) {
        if (!Double.isFinite(v) || v == 0d) {
            return "—";
        }
        String sign = v > 0 ? "▲ +" : "▼ ";
        return sign + String.format(Locale.US, "%.2f%%", Math.abs(v));
    }

    /** یکی از دو رنگ بالا/پایین برای متن تغییر. */
    public static boolean isUp(double change) {
        return Double.isFinite(change) && change > 0;
    }
}
