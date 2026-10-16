package com.exchance.app.widget;

/** یک نماد با آخرین قیمت و تغییرش — همان چیزی که /api/market برمی‌گرداند. */
public class Price {

    public final String code;
    public final String name;
    public final String flag;
    public final String unit;
    public final double value;
    public final double change;
    public final double usd;

    public Price(String code, String name, String flag, String unit,
                 double value, double change, double usd) {
        this.code = code == null ? "" : code;
        this.name = name == null ? this.code : name;
        this.flag = flag == null ? "" : flag;
        this.unit = unit == null || unit.isEmpty() ? "تومان" : unit;
        this.value = value;
        this.change = Double.isFinite(change) ? change : 0d;
        this.usd = usd;
    }

    public boolean hasValue() {
        return Double.isFinite(value);
    }
}
