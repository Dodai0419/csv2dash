"""Write examples/shop.csv: 210 days of a small online shop, seeded so the file never changes."""
import csv, math, random
from datetime import date, timedelta
from pathlib import Path

rnd = random.Random(7)
COUNTRIES = {'United States': 1.0, 'Germany': 0.45, 'Japan': 0.35, 'Brazil': 0.22, 'Korea': 0.18, 'France': 0.15, 'Canada': 0.12}
CHANNELS = {'Search': 0.5, 'Direct': 0.3, 'Social': 0.2}
start = date(2026, 3, 31)
with open(Path(__file__).with_name('shop.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['date', 'revenue', 'orders', 'refunds', 'country', 'channel'])
    for i in range(210):
        d = start + timedelta(i)
        trend = 1 + i / 260 + 0.18 * math.sin(i / 9)
        weekend = 0.7 if d.weekday() >= 5 else 1.0
        for c, cw in COUNTRIES.items():
            for ch, chw in CHANNELS.items():
                orders = max(0, round(rnd.gauss(6, 2) * cw * chw * trend * weekend))
                revenue = round(orders * rnd.uniform(28, 46), 2)
                refunds = sum(rnd.random() < 0.04 for _ in range(orders))
                w.writerow([d.isoformat(), revenue, orders, refunds, c, ch])
