"""Reproduce the README benchmark: build the demo dashboard from examples/shop.csv (4,410 rows), 3 runs of 20 builds."""
import sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import csv2dash as c

runs = []
for _ in range(3):
    t = time.perf_counter()
    for _ in range(20): c.build(ROOT / 'examples' / 'shop.csv', 'revenue', lower_better={'refunds'})
    runs.append((time.perf_counter() - t) / 20 * 1000)
print('ms per dashboard: ' + ', '.join(f'{r:.0f}' for r in runs))
