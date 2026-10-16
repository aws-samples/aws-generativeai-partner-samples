"""Generate and load synthetic market data: companies, ~1M trades for Sept 2026, and filings.

Prices follow a one-factor random walk (market beta + sector drift + noise) at minute
resolution, with intraday U-shaped volume and the planted events from universe.EVENTS.
A fixed seed makes every run produce the same numbers, so the demo script stays accurate.

Usage: python 02_load_data.py [--trades 1000000] [--seed 42] [--only trades,companies,filings]
"""
import argparse
import time as _time
from collections import deque
from datetime import date, datetime, timedelta, timezone

import numpy as np
from elasticsearch import helpers

from common import COMPANIES as COMPANIES_IDX, FILINGS, TRADES, es_client, is_serverless
from filings_corpus import all_filings
from universe import (COMPANIES, END, EVENTS, HOLIDAYS, SECTOR_DRIFT, SESSION_MINUTES, START,
                      UTC_OFFSET_HOURS)

EXCHANGES = np.array(["NASDAQ", "NYSE", "ARCA", "CBOE", "MEMX", "IEX", "TRF"])
EXCHANGE_P = np.array([0.28, 0.20, 0.10, 0.12, 0.06, 0.05, 0.19])
COMPANY_FIELDS = ["sym", "name", "sector", "industry", "hq", "shares_out_m", "eps_ttm",
                  "revenue_ttm_bn", "ebitda_ttm_bn", "net_debt_bn", "dividend_yield_pct", "beta"]


def trading_days() -> list[date]:
    d, days = START, []
    while d <= END:
        if d.weekday() < 5 and d not in HOLIDAYS:
            days.append(d)
        d += timedelta(days=1)
    return days


def minute_of(time_et: str) -> int:
    """Session minute (0 = 09:30 ET). Pre-market news returns -1 (applied as an opening gap)."""
    h, m = map(int, time_et.split(":"))
    return max(-1, (h * 60 + m) - (9 * 60 + 30))


def build_plan(days: list[date]):
    """Per (sym, day): volume multiplier, extra drift, intraday jumps, surges, planted blocks."""
    idx = {d.isoformat(): i for i, d in enumerate(days)}
    syms = [c["sym"] for c in COMPANIES]
    vol_mult = {(s, d): 1.0 for s in syms for d in idx}
    drift = {(s, d): 0.0 for s in syms for d in idx}
    jumps, surges, blocks = {}, {}, {}
    for ev in EVENTS:
        targets = syms if ev["sym"] == "*" else [ev["sym"]]
        start = idx[ev["day"]]
        minute = minute_of(ev["time_et"])
        for s in targets:
            for k, mult in enumerate(ev.get("day_vol", [])):
                if start + k < len(days):
                    key = (s, days[start + k].isoformat())
                    vol_mult[key] *= mult
            beta = next(c["beta"] for c in COMPANIES if c["sym"] == s) if ev["sym"] == "*" else 1.0
            jumps.setdefault((s, ev["day"]), []).append((minute, ev["jump"] * beta))
            surges.setdefault((s, ev["day"]), []).append((max(minute, 0), 3.0 if ev["sym"] == "*" else 6.0))
        for peer, move in ev.get("peers", {}).items():
            jumps.setdefault((peer, ev["day"]), []).append((minute, move))
            surges.setdefault((peer, ev["day"]), []).append((max(minute, 0), 2.0))
            vol_mult[(peer, ev["day"])] *= 1.6
        for d, extra in ev.get("drift", {}).items():
            drift[(ev["sym"], d)] += extra
        for d, n in ev.get("blocks", {}).items():
            blocks[(ev["sym"], d)] = n
    return vol_mult, drift, jumps, surges, blocks


def generate(n_target: int, seed: int):
    rng = np.random.default_rng(seed)
    days = trading_days()
    vol_mult, drift, jumps, surges, blocks = build_plan(days)
    market = rng.normal(0.0003, 0.008, len(days))
    minutes = np.arange(SESSION_MINUTES)
    u_shape = 1 + 1.8 * ((minutes - 195) / 195) ** 2

    weight = sum(c["liquidity"] * vol_mult[(c["sym"], d.isoformat())] for c in COMPANIES for d in days)
    base = n_target / weight

    for c in COMPANIES:
        sym, sector, beta = c["sym"], c["sector"], c["beta"]
        sigma = 0.032 if c["industry"] == "Biotechnology" else 0.011 * (0.6 + 0.4 * beta)
        log_px = np.log(c["start_price"])
        for di, d in enumerate(days):
            key = (sym, d.isoformat())
            day_ret = beta * market[di] + SECTOR_DRIFT[sector] + drift[key] + rng.normal(0, sigma * 0.6)
            steps = rng.normal(day_ret / SESSION_MINUTES, sigma * 0.5 / np.sqrt(SESSION_MINUTES), SESSION_MINUTES)
            gap = rng.normal(0, 0.003)
            for minute, move in jumps.get(key, []):
                if minute < 0:
                    gap += move
                else:
                    steps[minute] += move
            path = log_px + gap + np.cumsum(steps)
            log_px = path[-1]

            intensity = u_shape.copy()
            for m0, amp in surges.get(key, []):
                after = minutes >= m0
                intensity[after] += amp * np.exp(-(minutes[after] - m0) / 40)
            n = max(50, int(base * c["liquidity"] * vol_mult[key] * rng.lognormal(0, 0.12)))
            m = rng.choice(SESSION_MINUTES, size=n, p=intensity / intensity.sum())

            odd = rng.random(n) < 0.4
            size = np.where(odd, rng.integers(1, 100, n), 100 * np.minimum(rng.geometric(0.35, n), 50))
            big = rng.random(n) < 0.0005
            size = np.where(big, 100 * rng.integers(100, 400, n), size)
            minute_ret = np.diff(path, prepend=path[0])[m]
            side = np.where(rng.random(n) < 0.5 + np.clip(minute_ret * 300, -0.15, 0.15), "buy", "sell")

            k = blocks.get(key, 0)  # planted late-session block buys
            if k:
                m = np.concatenate([m, rng.integers(300, SESSION_MINUTES, k)])
                size = np.concatenate([size, 100 * rng.integers(150, 600, k)])
                side = np.concatenate([side, np.full(k, "buy")])
                n += k

            price = np.round(np.exp(path[m]) * (1 + rng.normal(0, 0.0003, n)), 2)
            exch = rng.choice(EXCHANGES, size=n, p=EXCHANGE_P)
            open_utc = datetime(d.year, d.month, d.day, 9 + UTC_OFFSET_HOURS, 30, tzinfo=timezone.utc)
            secs = m * 60 + rng.random(n) * 60
            order = np.argsort(secs)
            for i in order:
                ts = open_utc + timedelta(seconds=float(secs[i]))
                yield {
                    "_index": TRADES,
                    "_source": {
                        "time": ts.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                        "sym": sym, "sector": sector,
                        "price": float(price[i]), "size": int(size[i]),
                        "notional": round(float(price[i]) * int(size[i]), 2),
                        "side": str(side[i]), "exchange": str(exch[i]),
                        "is_block": bool(size[i] >= 10_000),
                    },
                }


def load_trades(es, n: int, seed: int, serverless: bool):
    if not serverless:
        es.indices.put_settings(index=TRADES, settings={"refresh_interval": "-1"})
    t0, done = _time.time(), 0
    try:
        for ok, info in helpers.parallel_bulk(es, generate(n, seed), thread_count=4, chunk_size=5000,
                                              raise_on_error=True):
            done += 1
            if done % 100_000 == 0:
                print(f"    {done:,} trades ({done / (_time.time() - t0):,.0f}/s)")
    finally:
        if not serverless:
            es.indices.put_settings(index=TRADES, settings={"refresh_interval": None})
    es.indices.refresh(index=TRADES)
    print(f"  trades: {es.count(index=TRADES)['count']:,} docs in {_time.time() - t0:,.0f}s")


def load_companies(es):
    actions = ({"_index": COMPANIES_IDX, "_id": c["sym"], "_source": {k: c[k] for k in COMPANY_FIELDS}}
               for c in COMPANIES)
    helpers.bulk(es, actions, refresh="wait_for")
    print(f"  companies: {es.count(index=COMPANIES_IDX)['count']} docs")


def load_filings(es):
    # semantic_text runs inference at ingest; small chunks avoid timeouts while ML capacity warms up.
    actions = ({"_index": FILINGS, "_id": f["accession"], "_source": f} for f in all_filings())
    deque(helpers.streaming_bulk(es.options(request_timeout=600), actions, chunk_size=5, max_retries=5,
                                 initial_backoff=10), maxlen=0)
    es.indices.refresh(index=FILINGS)
    print(f"  filings: {es.count(index=FILINGS)['count']} docs")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", type=int, default=1_000_000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--only", default="companies,filings,trades")
    args = ap.parse_args()
    only = set(args.only.split(","))

    es = es_client()
    serverless = is_serverless(es)
    for name in (COMPANIES_IDX, FILINGS, TRADES):
        if name in only and es.count(index=name)["count"]:
            raise SystemExit(f"{name} already has data. Run 01_create_indices.py --recreate first.")
    if "companies" in only:
        load_companies(es)
    if "filings" in only:
        load_filings(es)
    if "trades" in only:
        load_trades(es, args.trades, args.seed, serverless)


if __name__ == "__main__":
    main()
