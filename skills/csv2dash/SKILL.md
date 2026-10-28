---
name: csv2dash
description: Turn a CSV with a date column into a clean one-file HTML dashboard (KPI tiles vs the previous period, daily chart, 26-week activity grid, ranked breakdowns). Use when the user wants to see, chart, summarise or share data from a CSV or spreadsheet export.
---

# csv2dash

## When to use
- The user has a CSV (sales, signups, usage, tickets, workouts, anything dated) and wants a dashboard, a chart or a quick look.
- The user asks "how are we doing" about data they can export to CSV.

## How
1. Make sure the CSV has a date column (`YYYY-MM-DD`), number columns, and optional text columns to break down by. One row per day or one row per event both work.
2. Pick the main metric and the ones where lower is better:
   `python csv2dash.py data.csv --value revenue --lower-better refunds,cost --days 30`
3. Read the printed line. `words audit: 0 sentence(s)` is the target; do not add sentences to the page.
4. Give the user the HTML path. Explanations are in hover tooltips on the page.

Options: `--days N` (period length), `--neutral spend` (never coloured), `--money a,b`, `--date col`, `--title`, `-o out.html`.
Python 3.8+ only. No packages to install.
