package com.exchance.app.widget;

import android.Manifest;
import android.app.Activity;
import android.appwidget.AppWidgetManager;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.BaseAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ListView;
import android.widget.TextView;
import android.widget.Toast;

import com.exchance.app.R;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * صفحه‌ی تنظیم ویجت: کاربر یک نماد انتخاب می‌کند و اگر بخواهد، حد بالا/پایین
 * برای هشدار می‌گذارد.
 *
 * <p>فهرست نمادها از خود API می‌آید (نه یک لیست جاوایی جدا)، پس هر نمادی که در
 * وب و اپ هست، اینجا هم هست. اول کش نشان داده می‌شود و بعد شبکه.
 */
public class WidgetConfigActivity extends Activity {

    private static final int REQUEST_NOTIFICATIONS = 71;

    private int widgetId = AppWidgetManager.INVALID_APPWIDGET_ID;
    private final List<Price> all = new ArrayList<>();
    private final RowAdapter adapter = new RowAdapter();
    private String selected = "";
    private TextView status;
    private EditText search;
    private EditText high;
    private EditText low;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // تا وقتی کاربر «ذخیره» نزده، ویجت اضافه نشود
        setResult(RESULT_CANCELED);
        setContentView(R.layout.ex_activity_widget_config);

        widgetId = getIntent().getIntExtra(AppWidgetManager.EXTRA_APPWIDGET_ID,
                AppWidgetManager.INVALID_APPWIDGET_ID);
        if (widgetId == AppWidgetManager.INVALID_APPWIDGET_ID) {
            finish();
            return;
        }

        ListView list = (ListView) findViewById(R.id.ex_config_list);
        status = (TextView) findViewById(R.id.ex_config_status);
        search = (EditText) findViewById(R.id.ex_config_search);
        high = (EditText) findViewById(R.id.ex_config_high);
        low = (EditText) findViewById(R.id.ex_config_low);

        list.setAdapter(adapter);
        list.setOnItemClickListener(new AdapterView.OnItemClickListener() {
            @Override
            public void onItemClick(AdapterView<?> parent, View view, int position, long id) {
                Price picked = adapter.getItem(position);
                selected = picked.code;
                status.setText(describe(picked));
                adapter.notifyDataSetChanged();   // تیک روی ردیف انتخاب‌شده
            }
        });

        selected = PriceStore.widgetCode(this, widgetId);
        double savedHigh = selected.isEmpty() ? 0d : PriceStore.alertHigh(this, selected);
        double savedLow = selected.isEmpty() ? 0d : PriceStore.alertLow(this, selected);
        if (savedHigh > 0) {
            high.setText(Money.price(savedHigh));
        }
        if (savedLow > 0) {
            low.setText(Money.price(savedLow));
        }

        search.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {
            }

            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
            }

            @Override
            public void afterTextChanged(Editable s) {
                applyFilter();
            }
        });

        ((Button) findViewById(R.id.ex_config_save)).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                save();
            }
        });

        List<Price> cached = PriceStore.cachedAll(this);
        if (!cached.isEmpty()) {
            all.addAll(cached);
            applyFilter();
            status.setText(getString(R.string.ex_config_pick));
        }
        loadSymbols();
    }

    // ------------------------------------------------------------- داده

    private void loadSymbols() {
        if (all.isEmpty()) {
            status.setText(R.string.ex_config_loading);
        }
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    final List<Price> fresh = PriceApi.fetch(WidgetConfigActivity.this);
                    if (fresh.isEmpty()) {
                        return;
                    }
                    PriceStore.savePrices(WidgetConfigActivity.this, fresh);
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            all.clear();
                            all.addAll(fresh);
                            applyFilter();
                            status.setText(getString(R.string.ex_config_pick));
                        }
                    });
                } catch (final Exception e) {
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            if (all.isEmpty()) {
                                status.setText(R.string.ex_config_offline);
                            }
                        }
                    });
                }
            }
        }, "ex-config-load").start();
    }

    private void applyFilter() {
        String query = search.getText().toString().trim().toLowerCase(Locale.ROOT);
        List<Price> rows = new ArrayList<>();
        for (Price p : all) {
            boolean hit = query.isEmpty()
                    || p.name.toLowerCase(Locale.ROOT).contains(query)
                    || p.code.toLowerCase(Locale.ROOT).contains(query)
                    || p.flag.contains(query);
            if (hit) {
                rows.add(p);
            }
        }
        adapter.set(rows);
    }

    private void save() {
        if (selected.isEmpty()) {
            Toast.makeText(this, R.string.ex_config_pick, Toast.LENGTH_SHORT).show();
            return;
        }
        double h = number(high);
        double l = number(low);
        PriceStore.setWidgetCode(this, widgetId, selected);
        PriceStore.setAlerts(this, selected, h, l);
        AlertScheduler.sync(this);

        if ((h > 0 || l > 0) && Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && !Notifier.canNotify(this)) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, REQUEST_NOTIFICATIONS);
            Toast.makeText(this, R.string.ex_notif_perm, Toast.LENGTH_LONG).show();
        }

        PriceWidgetProvider.refreshAsync(this);
        setResult(RESULT_OK, new Intent().putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, widgetId));
        finish();
    }

    private static double number(EditText field) {
        String raw = field.getText().toString().trim().replace(",", "").replace("٬", "");
        if (raw.isEmpty()) {
            return 0d;
        }
        try {
            return Double.parseDouble(raw);
        } catch (NumberFormatException e) {
            return 0d;
        }
    }

    private static String describe(Price p) {
        return (p.flag.isEmpty() ? "" : p.flag + "  ") + p.name
                + (p.hasValue() ? "   " + Money.price(p.value) + " " + p.unit : "");
    }

    /** ردیف‌های فهرست: خط اول پرچم و نام، خط دوم قیمت و تغییر. */
    private class RowAdapter extends BaseAdapter {

        private final List<Price> rows = new ArrayList<>();

        void set(List<Price> items) {
            rows.clear();
            rows.addAll(items);
            notifyDataSetChanged();
        }

        @Override
        public int getCount() {
            return rows.size();
        }

        @Override
        public Price getItem(int position) {
            return rows.get(position);
        }

        @Override
        public long getItemId(int position) {
            return getItem(position).code.hashCode();
        }

        @Override
        public View getView(int position, View convertView, ViewGroup parent) {
            View view = convertView != null
                    ? convertView
                    : getLayoutInflater().inflate(android.R.layout.simple_list_item_2, parent, false);
            Price p = getItem(position);
            TextView first = (TextView) view.findViewById(android.R.id.text1);
            TextView second = (TextView) view.findViewById(android.R.id.text2);
            first.setText((p.code.equals(selected) ? "✓ " : "")
                    + (p.flag.isEmpty() ? "" : p.flag + "   ") + p.name);
            second.setText(p.hasValue()
                    ? Money.price(p.value) + " " + p.unit + "   " + Money.change(p.change)
                    : "—");
            return view;
        }
    }
}
