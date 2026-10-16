# Demo script: a month-end market review in Amazon Quick

**Persona:** Maya, a portfolio analyst at an asset manager. It is 1 October 2026 and she has
30 minutes to prepare the September review for the investment committee. She doesn't write
ES|QL, and she doesn't need to.

**Runtime:** 10–12 minutes. Each step lists the prompt to type, the tool the agent should pick,
and the answer it should reach. The data is generated with a fixed seed, so these numbers come
out the same every time (checked with `scripts/06_validate_demo.py`).

All companies, tickers and filings are fictional.

---

## 1. Warm-up: what's in the data? (shows discovery)

> What data do you have access to, and what time period does it cover?

- **Tools:** `platform_core_list_indices`, `platform_core_get_index_mapping`
- **Expect:** three indices (`trades`, `companies`, `filings`); about 1.0M trades from 1 to 30 Sep 2026 across 24 tickers.
- **Say:** "The agent learns the data model itself. Nobody had to document the schema for the analyst."

## 2. What moved the market? (anomaly detection)

> What were the biggest market-moving events in September? Rank them by unusual volume.

- **Tool:** `mi_volume_anomalies`
- **Expect (top rows):**

| Day | Ticker | Volume vs. median |
|---|---|---|
| 24 Sep | VTRX | 7.2× |
| 23 Sep | VTRX | 5.7× |
| 18 Sep | ROVR | 4.9× |
| 22 Sep | VTRX | 4.6× |
| 15 Sep | NVLT | 4.4× |
| 9 Sep | HRBR | 4.4× |
| 3 Sep | CRTL | 3.2× |
| 29 Sep | LDGR | 2.7× |
| 22 Sep | ORCH | 2.1× |

- **Say:** "Behind this is a curated Agent Builder tool. The median-volume baseline is defined once in Elastic, and every agent reuses it. That's the context layer."

## 3. Why did Novalight fall? (structured data plus filings: agentic RAG)

> Why did Novalight drop on September 15? Show me when it happened during the day.

- **Tools:** `mi_intraday_bars` (NVLT, 2026-09-15), then `mi_filings_search`
- **Expect:**
  - Flat at about $377 until the 14:00 ET bar, then down to about $337: roughly −10.7% on the day.
  - Volume in the 14:15 ET bar was about 380K shares, around 5× the midday run rate.
  - **Cause:** the NVLT 8-K filed 15 Sep at 14:10 ET. A new export license requirement covers markets worth about 18% of data center revenue. Q3 revenue guidance falls by about $4B, and there may be up to $1.5B in charges.
- **Follow-up:**

  > Chart the intraday price and volume.

  This gives a line chart of VWAP and bars for volume.

## 4. Unusual trading before news (surveillance angle)

> Was there anything unusual in Vitrexa trading before its FDA news?

- **Tools:** `mi_filings_search` (finds the 8-K approval on 24 Sep, before the open), then `mi_block_activity` and `mi_block_trades`
- **Expect:**
  - **22 Sep:** 14 block trades, all buys, about $20.3M.
  - **23 Sep:** 23 blocks, 21 of them buys, about $30.1M.
  - On both days the blocks clustered between 14:30 and 16:00 ET. Volume was 4.6× and 5.7× normal.
  - The approval came on 24 Sep, two days before the PDUFA date (26 Sep, from the August 10-Q). The stock rose about 35% over the month ($38.08 to $51.48), and the 24 Sep high was $48.44.
- **Say:** "Two days of one-sided block buying right before a binary catalyst. That's exactly what a compliance or trading desk would want flagged."

## 5. Sector rotation (chart in chat)

> How did each sector perform in September? Show it as a bar chart.

- **Tool:** `mi_sector_performance`
- **Expect:**
  - Health Care led at +13.5% (driven by VTRX), followed by Industrials (+4.0%), Consumer Staples (+3.0%) and Utilities (+2.6%).
  - Financials (−4.1%) and Technology (−3.8%) were the weakest.
  - A defensive rotation, with tech dragged down by NVLT (−16.2%) and ORCH (−6.9%).

## 6. Annual report risk review (semantic search across filing versions)

> What new risks did Orchard Devices add in its latest 10-K compared with its prior 10-Q, and how did trading volume change that week?

- **Tools:** `mi_filings_search`, then `mi_daily_bars` or `platform_core_execute_esql` for weekly volume
- **Expect:**
  - **New in the 10-K (filed 22 Sep):**
    - Supply chain concentration: final assembly sits in one region, and about 70% of flagship displays come from two suppliers.
    - AI and digital markets regulation, plus an antitrust probe with fines of up to 10% of revenue.
  - **Prior 10-Q:** said only "no material changes".
  - **Volume:** about 6.7M shares in the week of 21 Sep, versus about 3.2M in early-September weeks (around 2×). The stock fell about 7% over the month.

## 7. Valuation context (ES|QL `LOOKUP JOIN`)

> Compare valuations for the technology names using September 30 prices.

- **Tool:** `mi_valuation_snapshot`
- **Expect:**

| Ticker | Market cap | P/E | EV/EBITDA |
|---|---|---|---|
| ORCH | $3.27T | 31.2 | 23.1 |
| NVLT | $842B | 35.1 | 15.8 |
| SKYF | $308B | 45.2 | 22.9 |
| HELX | $185B | 24.7 | 11.3 |

- **Say:** "Trade prices from one index are joined to fundamentals in another, at query time, inside Elastic."

## 8. Wrap-up: committee brief

> Write a one-page September market brief for the investment committee: key events, sector performance, names to watch, and risks. Cite filings.

- **Expect:** a synthesized brief that reuses the answers above, with filing citations (for example, "NVLT 8-K (2026-09-15), Item 7.01").
- **Optional:** use Quick to save it to a Space, or email it via an action.

---

### Questions for unscripted Q&A

| Question | Expected answer |
|---|---|
| "Total volume for ORCH in September?" | 19,836,666 shares |
| "Which regional bank warned on credit, and did it affect real estate names?" | HRBR 8-K on 9 Sep: CRE office provisions of $410–460M, stock −7.3% that day. KEYS (office REIT) fell 3.6% in sympathy. |
| "What did Rover Motors disclose, and how did the stock react?" | Recall of about 120K vehicles, 8-K filed after the close on 17 Sep. On 18 Sep the stock opened about 6% lower ($192.69 close to $181.17 open) on 4.9× volume. |
| "Show the hourly volume pattern for NVLT on Sep 15." | U-shaped, with a spike at 14:00 ET |
| "Which stocks have the highest P/E?" | ROVR 80.5, TERA 50.8, SKYF 45.2 |

### If something goes wrong live

- **Agent passes `2026-09-15` and the tool call errors:** say "use 2026-09-15T00:00:00Z". This is already in the persona instructions.
- **Agent writes its own ES|QL instead of using an `mi_*` tool:** that's still a valid demo. Expand the action to show the generated query.
