# Stretch goal: "September Market Review" dashboard in Amazon Quick Sight

There are two ways to show visuals in the demo:

1. **Charts in chat:** ask the agent to chart an answer (demo steps 3 and 5). This needs no setup and runs live over MCP.
2. **A Quick Sight dashboard** built from the CSVs that `scripts/07_export_for_quick.py` writes to `build/quick_datasets/`. Add it to a Quick Space with the chat agent so Maya can move between the dashboard and the conversation.

## Datasets

In Quick, go to **Datasets > Create dataset > Upload a file** and upload each CSV. Parse `day` and `bar` as dates.

| File | Rows | Grain |
|---|---|---|
| `daily_bars.csv` | 504 | ticker × day: OHLC, VWAP, volume, blocks, market cap, sector |
| `intraday_15m.csv` | 13,104 | ticker × 15-minute bar (UTC) |
| `valuation_2026_09_30.csv` | 24 | ticker: price, market cap, P/E, EV/EBITDA |
| `venue_mix.csv` | 70 | exchange × sector volume |
| `events.csv` | 9 | planted events (useful as reference lines) |
| `filings.csv` | 29 | filing metadata |

Add these calculated fields to `daily_bars`:

- `buy_ratio = buy_volume / volume`
- `rel_volume = volume / avgOver(volume, [sym], PRE_FILTER)`

## Sheet layout

| Position | Visual | Dataset | Configuration |
|---|---|---|---|
| Top row | 4 KPIs | daily_bars | Total shares traded (sum `volume`), total trades, block trades (sum `blocks`), tickers (distinct `sym`) |
| Row 2, left | Line chart: "Close by ticker" | daily_bars | X `day`, Y `close`, color `sym`. Add a `sym` filter control, defaulting to NVLT, VTRX, ORCH. |
| Row 2, right | Horizontal bar: "September return by sector" | daily_bars | Calculated `return_pct` = last close / first open − 1, grouped by `sector` |
| Row 3, left | Heat map: "Relative volume" | daily_bars | Rows `sym`, columns `day`, color `rel_volume`. The event days stand out at a glance. |
| Row 3, right | Combo chart: "Intraday price and volume" | intraday_15m | X `bar`, bars `volume`, line `vwap`. Add `sym` and day filter controls; default NVLT, 15 Sep. |
| Row 4, left | Scatter: "Valuation map" | valuation | X `pe`, Y `ev_ebitda`, size `market_cap_bn`, color `sector` |
| Row 4, right | Table: "Events and filings" | events | Day, time (ET), ticker, label |

## Q&A on the dashboard

Turn on Topics/Q&A for the `daily_bars` dataset so the business user can also ask questions of the dashboard in plain English, such as "which day had the highest NVLT volume". The live, cross-index reasoning (filings plus trades) remains with the MCP chat agent.
