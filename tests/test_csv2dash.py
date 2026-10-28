import csv, io, re, tempfile, unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
import csv2dash as c

ROOT = Path(__file__).resolve().parent.parent


def write_csv(rows, header=('date', 'sales', 'cost', 'region')):
    d = tempfile.mkdtemp(); p = Path(d, 'data.csv')
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    return p


class Numbers(unittest.TestCase):
    def test_compact(self):
        self.assertEqual([c.compact(v) for v in (0, 7, 12.4, 1500, 2_349_000, 5.2e9)], ['0', '7', '12', '1.5k', '2.3M', '5.2B'])
        self.assertEqual(c.compact(4200, money=True), '$4.2k')
        self.assertEqual(c.compact(None), '—')

    def test_pct_tiny(self):
        self.assertEqual(c.pct(0.0004), '<0.1%'); self.assertEqual(c.pct(0.123), '+12.3%'); self.assertEqual(c.pct(None), '—')

    def test_round_ticks(self):
        self.assertEqual(c.nice_ticks(2103), [0, 1000, 2000, 3000])
        self.assertEqual(c.nice_ticks(87), [0, 50, 100])
        self.assertEqual(c.nice_ticks(170), [0, 50, 100, 150, 200])
        self.assertEqual(c.nice_ticks(0), [0, 1])


class Deltas(unittest.TestCase):
    def test_tiny_base_reads_was_n_in_grey(self):
        self.assertEqual(c.delta(0, 1)[:2], ('was 1', c.GREY))

    def test_colour_follows_meaning(self):
        self.assertEqual(c.delta(120, 100)[1], c.GREEN)
        self.assertEqual(c.delta(80, 100)[1], c.RED)
        self.assertEqual(c.delta(80, 100, lower_better=True)[1], c.GREEN)   # cost going down is good
        self.assertEqual(c.delta(150, 100, neutral=True)[1], c.GREY)

    def test_no_previous(self):
        self.assertEqual(c.delta(10, None)[0], '—')


class Data(unittest.TestCase):
    def test_detects_columns_and_windows(self):
        p = write_csv([(f'2026-01-{d:02d}', d, 1, 'N' if d % 2 else 'S') for d in range(1, 21)])
        rows, num, cats = c.load(p)
        self.assertEqual((num, cats), (['sales', 'cost'], ['region']))
        cur, prev = c.windows(date(2026, 1, 20), 10)
        self.assertEqual((cur[0], cur[-1], prev[0], prev[-1]), (date(2026, 1, 11), date(2026, 1, 20), date(2026, 1, 1), date(2026, 1, 10)))

    def test_kpi_compares_same_length_periods(self):
        p = write_csv([(f'2026-01-{d:02d}', 10 if d <= 10 else 20, 1, 'N') for d in range(1, 21)])
        page, _ = c.build(p, days=10)
        self.assertIn('>$200<', page)         # current 10 days x 20 (sales is guessed as money)
        self.assertIn('+100.0%', page)        # vs 10 x 10

    def test_breakdown_sorted_with_share_bars(self):
        p = write_csv([('2026-01-01', 30, 1, 'A'), ('2026-01-01', 70, 1, 'B')])
        page, _ = c.build(p, days=1)
        self.assertRegex(page, r'<span>B</span><b>\$70</b><i style="width:70.0%"></i></li><li[^>]*><span>A</span>')

    def test_heatmap_tiers(self):
        vals = {date(2026, 1, d): float(d) for d in range(1, 29)}
        svg = c.heatmap(vals, date(2026, 1, 28), weeks=4)
        self.assertEqual(len(re.findall(r'<rect[^>]+><title>', svg)), (date(2026, 1, 28) - date(2026, 1, 5)).days + 8 - 7)
        for tier in c.TIERS[1:]: self.assertIn(tier, svg)

    def test_no_date_column(self):
        p = write_csv([('x', 1, 2, 'a')])
        with self.assertRaises(SystemExit): c.load(p)

    def test_html_is_escaped(self):
        p = write_csv([('2026-01-01', 1, 1, '<script>x</script>')])
        page, _ = c.build(p, days=1)
        self.assertNotIn('<script>', page)


class Demo(unittest.TestCase):
    def test_demo_is_wordless_and_one_file(self):
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()) as out:
            self.assertEqual(c.main(['--demo', '-o', f'{d}/shop.html']), 0)
            page = Path(d, 'shop.html').read_text(encoding='utf-8')
        self.assertIn('words audit: 0 sentence(s)', out.getvalue())
        self.assertNotRegex(page, r'<(script|link|img)\b')
        self.assertEqual(page.count('class="tile"'), 3)
        self.assertEqual(c.sentences(page), [])


if __name__ == '__main__':
    unittest.main()
