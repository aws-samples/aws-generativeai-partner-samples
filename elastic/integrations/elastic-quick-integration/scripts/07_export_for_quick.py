"""Export aggregated views to CSV for an Amazon Quick Sight dashboard (optional stretch).

Quick chat answers live questions through MCP; a dashboard needs a dataset. These CSVs are
small (a few thousand rows) and can be uploaded directly in Quick (Datasets > Upload a file)
or placed in S3. Output: build/quick_datasets/*.csv
"""
import csv

from agent_tools import TOOLS
from common import ROOT, es_client, esql
from filings_corpus import all_filings
from universe import COMPANIES, EVENTS

OUT = ROOT / "build" / "quick_datasets"
Q = {t["id"]: t["query"] for t in TOOLS if "query" in t}


def write(name: str, rows: list[dict]):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / f"{name}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"  {name}.csv: {len(rows)} rows")


def main():
    es = es_client()
    # Daily OHLCV for every ticker, with sector and fundamentals (one query, LOOKUP JOIN).
    write("daily_bars", esql(es, """FROM trades
| EVAL minute_of_day = DATE_EXTRACT("minute_of_day", time)
| STATS open = AVG(price) WHERE minute_of_day < 815, close = AVG(price) WHERE minute_of_day >= 1195,
        high = MAX(price), low = MIN(price), notional = SUM(notional), volume = SUM(size), trades = COUNT(*),
        buy_volume = SUM(size) WHERE side == "buy", blocks = COUNT(*) WHERE is_block
  BY sym, day = DATE_TRUNC(1 day, time)
| LOOKUP JOIN companies ON sym
| EVAL vwap = ROUND(notional / volume, 2), open = ROUND(open, 2), close = ROUND(close, 2),
       change_pct = ROUND((close / open - 1) * 100, 2), market_cap_bn = ROUND(close * shares_out_m / 1000, 1)
| KEEP day, sym, name, sector, industry, open, high, low, close, change_pct, vwap, volume, trades,
       buy_volume, blocks, market_cap_bn
| SORT sym, day
| LIMIT 10000"""))
    # One query per ticker: the full table (~13k rows) exceeds the ES|QL 10,000-row result cap.
    write("intraday_15m", [row for c in COMPANIES for row in esql(es, """FROM trades
| WHERE sym == ?sym
| STATS notional = SUM(notional), volume = SUM(size), high = MAX(price), low = MIN(price)
  BY sym, sector, bar = DATE_TRUNC(15 minutes, time)
| EVAL vwap = ROUND(notional / volume, 2)
| KEEP bar, sym, sector, vwap, high, low, volume
| SORT bar
| LIMIT 1000""", [{"sym": c["sym"]}])])
    write("valuation_2026_09_30", esql(es, Q["mi_valuation_snapshot"], [{"day": "2026-09-30"}]))
    write("venue_mix", esql(es, """FROM trades
| STATS volume = SUM(size), trades = COUNT(*) BY exchange, sector | SORT volume DESC"""))
    write("events", [{"day": e["day"], "time_et": e["time_et"], "sym": e["sym"], "label": e["label"]}
                     for e in EVENTS])
    write("filings", [{k: f[k] for k in ("filed", "sym", "company", "sector", "form", "section", "title")}
                      for f in all_filings()])
    write("companies", [{k: v for k, v in c.items() if k not in ("start_price", "liquidity")} for c in COMPANIES])
    print(f"Written to {OUT}")


if __name__ == "__main__":
    main()
