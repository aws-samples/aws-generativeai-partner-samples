"""Custom Elastic Agent Builder tools exposed to Amazon Quick through the Elastic MCP server.

These are the "context layer": vetted, parameterized ES|QL that encodes domain knowledge
(session hours, VWAP, open/close, anomaly baselines, valuation math) so the Quick agent
does not have to rediscover it from raw mappings on every question.

Session timing: trades are stored in UTC; the US session is 13:30-20:00 UTC in Sept 2026.
Opening/closing prices are the average trade price in the first/last five minutes.
"""

WINDOW = "time >= TO_DATETIME(?first_day) AND time < TO_DATETIME(?last_day) + 1 day"
OPEN_CLOSE = ('| EVAL minute_of_day = DATE_EXTRACT("minute_of_day", time)\n')
OPEN_AGG = "AVG(price) WHERE minute_of_day < 815"     # 13:30-13:35 UTC
CLOSE_AGG = "AVG(price) WHERE minute_of_day >= 1195"  # 19:55-20:00 UTC

P_FIRST = {"type": "date", "description": "First trading day, inclusive, as midnight UTC (e.g. 2026-09-01T00:00:00Z). Data covers 1-30 Sep 2026.",
           "optional": True, "defaultValue": "2026-09-01T00:00:00Z"}
P_LAST = {"type": "date", "description": "Last trading day, inclusive, as midnight UTC (e.g. 2026-09-30T00:00:00Z).",
          "optional": True, "defaultValue": "2026-09-30T00:00:00Z"}
P_SYM = {"type": "string", "description": "Ticker symbol in upper case, for example NVLT."}
P_DAY = {"type": "date", "description": "Trading day as midnight UTC (e.g. 2026-09-15T00:00:00Z)."}

TOOLS = [
    dict(
        id="mi_daily_bars",
        description="Daily OHLC bars for one ticker: open, high, low, close, VWAP, share volume, trade count, "
                    "buy/sell volume, and block trade count. Use for price trends, daily moves, and charts.",
        params={"sym": P_SYM, "first_day": P_FIRST, "last_day": P_LAST},
        query=f"""FROM trades
| WHERE sym == ?sym AND {WINDOW}
{OPEN_CLOSE}| STATS open = {OPEN_AGG}, high = MAX(price), low = MIN(price), close = {CLOSE_AGG},
        notional = SUM(notional), volume = SUM(size), trades = COUNT(*),
        buy_volume = SUM(size) WHERE side == "buy", blocks = COUNT(*) WHERE is_block
  BY day = DATE_TRUNC(1 day, time)
| EVAL vwap = ROUND(notional / volume, 2), open = ROUND(open, 2), close = ROUND(close, 2),
       change_pct = ROUND((close / open - 1) * 100, 2), buy_ratio = ROUND(buy_volume * 1.0 / volume, 3)
| KEEP day, open, high, low, close, change_pct, vwap, volume, trades, buy_ratio, blocks
| SORT day""",
    ),
    dict(
        id="mi_intraday_bars",
        description="15-minute intraday bars (UTC) for one ticker on one trading day: VWAP, high, low, volume, trades. "
                    "Use to pinpoint when news hit and to chart intraday price and volume.",
        params={"sym": P_SYM, "day": P_DAY},
        query="""FROM trades
| WHERE sym == ?sym AND time >= TO_DATETIME(?day) AND time < TO_DATETIME(?day) + 1 day
| STATS notional = SUM(notional), volume = SUM(size), high = MAX(price), low = MIN(price), trades = COUNT(*)
  BY bar = DATE_TRUNC(15 minutes, time)
| EVAL vwap = ROUND(notional / volume, 2)
| KEEP bar, vwap, high, low, volume, trades
| SORT bar""",
    ),
    dict(
        id="mi_price_performance",
        description="Open-to-close price return for every ticker over a date range, with sector and total volume. "
                    "Use for top gainers and losers, and for comparing tickers.",
        params={"first_day": P_FIRST, "last_day": P_LAST},
        query=f"""FROM trades
| WHERE {WINDOW}
{OPEN_CLOSE}| STATS start_open = AVG(price) WHERE time < TO_DATETIME(?first_day) + 1 day AND minute_of_day < 815,
        end_close = AVG(price) WHERE time >= TO_DATETIME(?last_day) AND minute_of_day >= 1195,
        volume = SUM(size)
  BY sym, sector
| EVAL return_pct = ROUND((end_close / start_open - 1) * 100, 2),
       start_open = ROUND(start_open, 2), end_close = ROUND(end_close, 2)
| SORT return_pct DESC""",
    ),
    dict(
        id="mi_sector_performance",
        description="Average, best, and worst ticker return by sector over a date range. Use for sector rotation questions.",
        params={"first_day": P_FIRST, "last_day": P_LAST},
        query=f"""FROM trades
| WHERE {WINDOW}
{OPEN_CLOSE}| STATS start_open = AVG(price) WHERE time < TO_DATETIME(?first_day) + 1 day AND minute_of_day < 815,
        end_close = AVG(price) WHERE time >= TO_DATETIME(?last_day) AND minute_of_day >= 1195,
        volume = SUM(size)
  BY sym, sector
| EVAL return_pct = (end_close / start_open - 1) * 100
| STATS avg_return_pct = ROUND(AVG(return_pct), 2), best_return_pct = ROUND(MAX(return_pct), 2),
        worst_return_pct = ROUND(MIN(return_pct), 2), volume = SUM(volume), tickers = COUNT(*)
  BY sector
| SORT avg_return_pct DESC""",
    ),
    dict(
        id="mi_volume_anomalies",
        description="Ticker-days whose share volume is unusually high versus that ticker's median daily volume in "
                    "the range. Use to find market-moving events, then check filings for the cause.",
        params={"first_day": P_FIRST, "last_day": P_LAST,
                "min_ratio": {"type": "float", "description": "Minimum volume / median volume ratio.",
                              "optional": True, "defaultValue": 2.0}},
        query=f"""FROM trades
| WHERE {WINDOW}
| STATS volume = SUM(size), notional = SUM(notional) BY sym, sector, day = DATE_TRUNC(1 day, time)
| INLINE STATS median_volume = MEDIAN(volume) BY sym
| EVAL volume_ratio = ROUND(volume / median_volume, 2), vwap = ROUND(notional / volume, 2)
| WHERE volume_ratio >= ?min_ratio
| KEEP day, sym, sector, volume, median_volume, volume_ratio, vwap
| SORT volume_ratio DESC
| LIMIT 25""",
    ),
    dict(
        id="mi_block_activity",
        description="Block trades (10,000+ shares) per ticker per day with buy/sell split. Use for unusual or "
                    "informed trading questions, for example heavy block buying before news.",
        params={"first_day": P_FIRST, "last_day": P_LAST,
                "min_blocks": {"type": "integer", "description": "Minimum number of blocks in a day.",
                               "optional": True, "defaultValue": 5}},
        query=f"""FROM trades
| WHERE is_block AND {WINDOW}
| STATS blocks = COUNT(*), buy_blocks = COUNT(*) WHERE side == "buy", block_shares = SUM(size),
        block_notional = SUM(notional)
  BY sym, day = DATE_TRUNC(1 day, time)
| WHERE blocks >= ?min_blocks
| EVAL buy_share = ROUND(buy_blocks * 1.0 / blocks, 2), block_notional_musd = ROUND(block_notional / 1000000, 1)
| KEEP day, sym, blocks, buy_blocks, buy_share, block_shares, block_notional_musd
| SORT blocks DESC
| LIMIT 25""",
    ),
    dict(
        id="mi_block_trades",
        description="List individual block trades (10,000+ shares) for one ticker, with time, price, size, side, venue.",
        params={"sym": P_SYM, "first_day": P_FIRST, "last_day": P_LAST},
        query=f"""FROM trades
| WHERE sym == ?sym AND is_block AND {WINDOW}
| KEEP time, sym, price, size, notional, side, exchange
| SORT time
| LIMIT 100""",
    ),
    dict(
        id="mi_valuation_snapshot",
        description="Valuation table for all tickers on one trading day: VWAP price joined with company fundamentals "
                    "to compute market cap, P/E, and EV/EBITDA. Use for valuation and peer comparisons.",
        params={"day": {**P_DAY, "optional": True, "defaultValue": "2026-09-30T00:00:00Z"}},
        query="""FROM trades
| WHERE time >= TO_DATETIME(?day) AND time < TO_DATETIME(?day) + 1 day
| STATS notional = SUM(notional), volume = SUM(size) BY sym
| EVAL price = notional / volume
| LOOKUP JOIN companies ON sym
| EVAL market_cap_bn = ROUND(price * shares_out_m / 1000, 1),
       pe = CASE(eps_ttm > 0, ROUND(price / eps_ttm, 1), null),
       ev_ebitda = CASE(ebitda_ttm_bn > 0, ROUND((price * shares_out_m / 1000 + net_debt_bn) / ebitda_ttm_bn, 1), null),
       price = ROUND(price, 2)
| KEEP sym, name, sector, industry, price, market_cap_bn, pe, ev_ebitda, dividend_yield_pct, beta
| SORT market_cap_bn DESC""",
    ),
    dict(
        id="mi_filings_search",
        type="index_search",
        description="Semantic search over SEC filing excerpts (10-K, 10-Q, 8-K) for all companies: risk factors, "
                    "results, guidance, and material events. Fields: sym, company, form, filed, section, title, content.",
        pattern="filings",
    ),
]


def tool_body(tool: dict, legacy_types: bool) -> dict:
    """Kibana Agent Builder API body. Stacks before 9.4 call the string type 'keyword'/'double'."""
    body = {"id": tool["id"], "type": tool.get("type", "esql"), "description": tool["description"],
            "tags": ["market-intel"]}
    if body["type"] == "index_search":
        body["configuration"] = {"pattern": tool["pattern"]}
        return body
    params = {}
    for name, p in tool["params"].items():
        p = dict(p)
        if legacy_types:
            p["type"] = {"string": "keyword", "float": "double"}.get(p["type"], p["type"])
        params[name] = p
    body["configuration"] = {"query": tool["query"], "params": params}
    return body
