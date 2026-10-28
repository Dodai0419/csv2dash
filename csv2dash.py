#!/usr/bin/env python3
"""csv2dash: turn a CSV with a date column into a clean, honest one-file HTML dashboard.

Applies the rules of abdiraimov-otabek/dashboard-design-skill (MIT): KPI tiles with a delta against the
previous period of the same length, "was N" instead of a red -100% on a tiny base, round axis ticks, the previous
period dashed grey, slim 3 px share bars, wordless (explanations live in tooltips). Adds the GitHub-style daily
grid of hassan-kamel/hermes-activity (MIT). Python stdlib only; the output needs no JavaScript.
"""
import argparse, csv, html, math, re, sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ACCENT, GREEN, RED, GREY, WARM = '#3e63dd', '#2f9e6b', '#d6453d', '#8b8d98', '#e5484d'
TIERS = ['#ebedf0', '#c6d3fa', '#8da4ef', '#5b7ce6', '#3e63dd']

# ---------- numbers ----------
def compact(v, money=False):
    if v is None: return '—'
    a, sign, pre = abs(v), '-' if v < 0 else '', '$' if money else ''
    for div, suf in ((1e9, 'B'), (1e6, 'M'), (1e3, 'k')):
        if a >= div:
            s = f'{a / div:.1f}'.rstrip('0').rstrip('.')
            return f'{sign}{pre}{s}{suf}'
    return f'{sign}{pre}{a:.0f}' if a >= 10 or a == int(a) else f'{sign}{pre}{a:.1f}'

def pct(p):
    if p is None: return '—'
    if 0 < abs(p) < 0.001: return '<0.1%'
    return f'{p * 100:+.1f}%'.replace('+0.0%', '0%')

def nice_ticks(hi, n=4):
    """Round ticks from 0 that cover hi: steps of 1, 2 or 5 x 10^k."""
    if hi <= 0: return [0, 1]
    raw = hi / n; mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 5, 10) if m * mag >= raw)
    return [i * step for i in range(int(math.ceil(hi / step - 1e-9)) + 1)]

def delta(cur, prev, lower_better=False, neutral=False):
    """-> (text, colour, tooltip). A base under 5 reads 'was N' in grey, never a red -100%."""
    if prev is None or cur is None: return '—', GREY, 'no previous period'
    if abs(prev) < 5: return f'was {compact(prev)}', GREY, f'previous period: {prev:g}'
    p = (cur - prev) / abs(prev)
    good = (p < 0) if lower_better else (p > 0)
    colour = GREY if neutral or abs(p) < 0.005 else (GREEN if good else RED)
    return pct(p), colour, f'previous period: {prev:,.2f}'.rstrip('0').rstrip('.')

# ---------- data ----------
def parse_date(s):
    m = re.match(r'\s*(\d{4})-(\d{1,2})-(\d{1,2})', s or '')
    return date(*map(int, m.groups())) if m else None

def to_num(s):
    try: return float(str(s).replace(',', '').replace('$', '').strip())
    except ValueError: return None

def load(path, date_col=None):
    rows = list(csv.DictReader(open(path, encoding='utf-8-sig', newline='')))
    if not rows: raise SystemExit(f'{path}: no rows')
    cols = list(rows[0])
    date_col = date_col or next((c for c in cols if sum(parse_date(r[c]) is not None for r in rows[:50]) >= min(len(rows), 50) * 0.9), None)
    if not date_col: raise SystemExit('no date column (YYYY-MM-DD) found; pass --date')
    others = [c for c in cols if c != date_col]
    numeric = [c for c in others if all(to_num(r[c]) is not None for r in rows[:200] if r[c].strip())]
    cats = [c for c in others if c not in numeric]
    data = [{**r, '_d': parse_date(r[date_col])} for r in rows]
    return [r for r in data if r['_d']], numeric, cats

def daily(rows, col):
    out = defaultdict(float)
    for r in rows: out[r['_d']] += to_num(r[col]) or 0
    return out

def windows(end, days):
    """Current window = last `days` days up to end; previous = the same length right before it."""
    cur = [end - timedelta(i) for i in range(days - 1, -1, -1)]
    return cur, [d - timedelta(days) for d in cur]

# ---------- svg ----------
def esc(s): return html.escape(str(s), quote=True)

def tile(name, value, d, money, selected=False, spark=None):
    text, colour, tip = d
    ring = f' style="background:#eef2fd;box-shadow:0 0 0 1px #c6d3fa"' if selected else ''
    return (f'<div class="tile"{ring}><div class="lbl">{esc(name)}</div><div class="big">{esc(compact(value, money))}</div>'
            f'<div class="d" style="color:{colour}" title="{esc(tip)}">{esc(text)}<span> vs prev</span></div>{spark or ""}</div>')

def sparkline(vals, w=200, h=36):
    hi = max(vals) or 1
    pts = ' '.join(f'{i * w / max(1, len(vals) - 1):.1f},{h - 2 - v / hi * (h - 4):.1f}' for i, v in enumerate(vals))
    return f'<svg class="sp" viewBox="0 0 {w} {h}" preserveAspectRatio="none"><polyline points="{pts}" fill="none" stroke="{GREY}" stroke-width="1.5"/></svg>'

def chart(cur_days, cur, prev, money, W=760, H=260):
    L, B, T, R = 52, 26, 12, 12
    vals = [cur.get(d, 0) for d in cur_days]; pvals = [prev.get(d - timedelta(len(cur_days)), 0) for d in cur_days]
    ticks = nice_ticks(max(vals + pvals + [0]))
    top = ticks[-1] or 1
    x = lambda i: L + i * (W - L - R) / max(1, len(cur_days) - 1)
    y = lambda v: T + (1 - v / top) * (H - T - B)
    g = [f'<line x1="{L}" x2="{W - R}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="#eceef2"/><text x="{L - 8}" y="{y(t) + 4:.1f}" text-anchor="end">{esc(compact(t, money))}</text>' for t in ticks]
    step = max(1, len(cur_days) // 6)
    g += [f'<text x="{x(i):.1f}" y="{H - 6}" text-anchor="{"start" if i == 0 else "end" if i == len(cur_days) - 1 else "middle"}">{d.strftime("%b %d").replace(" 0", " ")}</text>' for i, d in enumerate(cur_days) if i % step == 0]
    line = lambda vs: ' '.join(f'{x(i):.1f},{y(v):.1f}' for i, v in enumerate(vs))
    dots = ''.join(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="7" fill="transparent"><title>{d:%b %d}: {compact(v, money)} (prev {compact(pvals[i], money)})</title></circle>'
                   for i, (d, v) in enumerate(zip(cur_days, vals)))
    return (f'<svg class="chart" viewBox="0 0 {W} {H}">{"".join(g)}'
            f'<polyline points="{line(pvals)}" fill="none" stroke="#b9bbc6" stroke-width="2" stroke-dasharray="5 5"/>'
            f'<polyline points="{line(vals)}" fill="none" stroke="{ACCENT}" stroke-width="2.5" stroke-linejoin="round"/>{dots}</svg>')

def heatmap(day_vals, end, weeks=26, money=False):
    """GitHub-style grid: one column per week, Monday on top, five classed tiers (quantiles of non-zero days)."""
    start = end - timedelta(end.weekday() + 7 * (weeks - 1))
    nz = sorted(v for d, v in day_vals.items() if v > 0 and start <= d <= end)
    cuts = [nz[int(len(nz) * q)] for q in (0.25, 0.5, 0.75)] if nz else []
    def tier(v): return 0 if v <= 0 else 1 + sum(v > c for c in cuts)
    s, gap = 13, 3
    cells = []
    for i in range((end - start).days + 1):
        d = start + timedelta(i); v = day_vals.get(d, 0)
        cells.append(f'<rect x="{30 + (i // 7) * (s + gap)}" y="{16 + d.weekday() * (s + gap)}" width="{s}" height="{s}" rx="3" fill="{TIERS[tier(v)]}"><title>{d:%a %b %d}: {compact(v, money)}</title></rect>')
    months = [f'<text x="{30 + (i // 7) * (s + gap)}" y="10">{(start + timedelta(i)):%b}</text>' for i in range(0, (end - start).days + 1, 7)
              if (start + timedelta(i)).day <= 7]
    days = ''.join(f'<text x="0" y="{16 + k * (s + gap) + 10}">{n}</text>' for k, n in ((0, 'Mon'), (2, 'Wed'), (4, 'Fri')))
    legend = ''.join(f'<rect x="{30 + weeks * (s + gap) - 5 * (s + gap) + k * (s + gap)}" y="{16 + 7 * (s + gap) + 4}" width="{s}" height="{s}" rx="3" fill="{c}"/>' for k, c in enumerate(TIERS))
    W = 30 + weeks * (s + gap); H = 16 + 8 * (s + gap) + 8
    return f'<svg class="heat" viewBox="0 0 {W} {H}">{"".join(months)}{days}{"".join(cells)}{legend}</svg>'

def breakdown(rows, cat, col, cur_set, money, top=6):
    tot = defaultdict(float)
    for r in rows:
        if r['_d'] in cur_set: tot[r[cat] or '—'] += to_num(r[col]) or 0
    items = sorted(tot.items(), key=lambda kv: -kv[1]); whole = sum(tot.values()) or 1
    if len(items) > top: items = items[:top - 1] + [('Other', sum(v for _, v in items[top - 1:]))]
    li = ''.join(f'<li title="{esc(f"{v / whole:.1%} of {col}")}"><span>{esc(k)}</span><b>{esc(compact(v, money))}</b>'
                 f'<i style="width:{v / whole * 100:.1f}%"></i></li>' for k, v in items)
    return f'<div class="card"><h3>{esc(cat.replace("_", " ").title())}</h3><ul class="rank">{li}</ul></div>'

CSS = """*{box-sizing:border-box}body{margin:0;background:#f6f7f9;color:#1c2024;font:15px/1.4 -apple-system,"Segoe UI",Inter,Arial,sans-serif;font-variant-numeric:tabular-nums}
main{padding:28px;max-width:1800px;margin:auto}header{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-bottom:20px}h1{font-size:22px;margin:0 auto 0 0}
.pill{background:#fff;border:1px solid #e3e5ea;border-radius:999px;padding:5px 12px;font-size:13px;color:#555}.pill i{display:inline-block;width:7px;height:7px;border-radius:50%;background:#30a46c;margin-right:6px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:14px}
.tile,.card{background:#fff;border:1px solid #e3e5ea;border-radius:14px;padding:16px 18px}.lbl{color:#60646c;font-size:13px}.big{font-size:30px;font-weight:650;margin:2px 0}
.d{font-size:13px;font-weight:600}.d span{color:#8b8d98;font-weight:400}.sp{width:100%;height:36px;margin-top:8px}
.row{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:14px;margin-bottom:14px}.card h3{margin:0 0 10px;font-size:14px;color:#60646c;font-weight:600}
svg text{font-size:11px;fill:#8b8d98}.chart{width:100%;height:auto}.heat{width:100%;height:auto;max-width:900px}
.rank{list-style:none;margin:0;padding:0}.rank li{position:relative;display:flex;justify-content:space-between;padding:9px 0 11px}.rank li i{position:absolute;left:0;bottom:2px;height:3px;border-radius:3px;background:#8da4ef}
.rank li::after{content:"";position:absolute;left:0;right:0;bottom:2px;height:3px;border-radius:3px;background:#eef0f3;z-index:-1}.rank b{font-weight:600}
@media(min-width:1500px){.row.breaks{grid-template-columns:repeat(4,1fr)}}"""

def build(path, value=None, days=30, money=None, lower_better=(), neutral=(), title=None, date_col=None):
    rows, numeric, cats = load(path, date_col)
    if not numeric: raise SystemExit('no numeric column to chart')
    value = value or numeric[0]
    if value not in numeric: raise SystemExit(f'--value {value!r} is not a numeric column: {numeric}')
    money = set(money if money is not None else [c for c in numeric if re.search(r'revenue|sales|amount|price|cost|spend|usd|\$', c, re.I)])
    end = max(r['_d'] for r in rows)
    cur_days, prev_days = windows(end, days)
    per = {c: daily(rows, c) for c in numeric}
    tiles = []
    for c in numeric:
        cv, pv = sum(per[c].get(d, 0) for d in cur_days), sum(per[c].get(d, 0) for d in prev_days)
        has_prev = any(d in per[c] for d in prev_days)
        tiles.append(tile(c.replace('_', ' ').title(), cv, delta(cv, pv if has_prev else None, c in lower_better, c in neutral), c in money,
                          selected=c == value, spark=sparkline([per[c].get(d, 0) for d in cur_days])))
    cur_set = set(cur_days)
    rng = f'{cur_days[0]:%b %d} – {end:%b %d, %Y}'.replace(' 0', ' ')
    name = title or Path(path).stem.replace('_', ' ').replace('-', ' ').title()
    body = (f'<header><h1>{esc(name)}</h1><span class="pill">{esc(rng)}</span><span class="pill">{days} days</span>'
            f'<span class="pill" title="last row in the file"><i></i>{end:%b %d}</span></header>'
            f'<section class="tiles">{"".join(tiles)}</section>'
            f'<section class="row"><div class="card"><h3>{esc(value.replace("_", " ").title())} · daily</h3>{chart(cur_days, per[value], per[value], value in money)}</div>'
            f'<div class="card"><h3>{esc(value.replace("_", " ").title())} · 26 weeks</h3>{heatmap(per[value], end, money=value in money)}</div></section>'
            f'<section class="row breaks">{"".join(breakdown(rows, c, value, cur_set, value in money) for c in cats)}</section>')
    page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(name)}</title><style>{CSS}</style></head><body><main>{body}</main></body></html>')
    return page, {'rows': len(rows), 'numeric': numeric, 'categories': cats, 'value': value, 'range': rng}

def sentences(page):
    """Words audit from the skill's QA pass: visible text runs of 6+ words outside tooltips. Target: 0."""
    text = re.sub(r'<(title|style)>.*?</\1>', ' ', page, flags=re.S)
    return [t.strip() for t in re.findall(r'>([^<>]+)<', text) if len(re.findall(r'[A-Za-z]{2,}', t)) >= 6]

def main(argv=None):
    ap = argparse.ArgumentParser(description='Turn a CSV with a date column into a clean one-file HTML dashboard.')
    ap.add_argument('csv', nargs='?')
    ap.add_argument('-o', '--out', help='output .html (default: next to the CSV)')
    ap.add_argument('--value', help='numeric column for the chart, grid and breakdowns (default: the first)')
    ap.add_argument('--days', type=int, default=30, help='current period length; compared with the same length before it')
    ap.add_argument('--lower-better', default='', help='comma list of columns where down is good (cost, churn, refunds)')
    ap.add_argument('--neutral', default='', help='comma list of columns whose change is never coloured (spend, volume)')
    ap.add_argument('--money', help='comma list of money columns (default: guessed from names)')
    ap.add_argument('--date', help='date column (default: detected)')
    ap.add_argument('--title')
    ap.add_argument('--demo', action='store_true', help='build examples/shop.csv')
    a = ap.parse_args(argv)
    if a.demo:
        a.csv = a.csv or str(Path(__file__).with_name('examples') / 'shop.csv')
        a.lower_better = a.lower_better or 'refunds'; a.value = a.value or 'revenue'
    if not a.csv: ap.error('give a CSV or --demo')
    split = lambda s: {x.strip() for x in s.split(',') if x.strip()}
    page, info = build(a.csv, a.value, a.days, split(a.money) if a.money else None, split(a.lower_better), split(a.neutral), a.title, a.date)
    out = Path(a.out) if a.out else Path(a.csv).with_suffix('.html')
    out.write_text(page, encoding='utf-8')
    print(f'{out}  {info["rows"]} rows, {info["range"].replace("–", "-")}')
    print(f'  tiles: {", ".join(info["numeric"])}  |  chart + grid: {info["value"]}  |  breakdowns: {", ".join(info["categories"]) or "none"}')
    s = sentences(page)
    print(f'  words audit: {len(s)} sentence(s) on screen' + (': ' + ' / '.join(s[:3]) if s else ''))
    return 0

if __name__ == '__main__':
    sys.exit(main())
