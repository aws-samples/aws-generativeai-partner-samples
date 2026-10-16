"""End-to-end tests over the Elastic MCP server with OAuth, one per demo question.

Each test makes the tool calls the Quick agent is expected to make for a demo question and
checks the answer against the values in demo/demo-script.md. A pass here means anything that
goes wrong in Quick is on the agent side (tool choice or arguments), not in Elastic.

Usage: python 08_e2e_mcp_tests.py
"""
import json
import traceback

from mcp_client import McpOAuthClient, esql_rows

D = lambda day: f"2026-09-{day:02d}T00:00:00Z"  # noqa: E731  MCP date params need full ISO datetimes
MONTH = {"first_day": D(1), "last_day": D(30)}
TESTS = []


def test(question):
    def wrap(fn):
        TESTS.append((question, fn))
        return fn
    return wrap


def filings_hits(payload) -> list[str]:
    refs = []
    for r in payload.get("results", []):
        for res in r.get("data", {}).get("resources", []):
            refs.append(" ".join(res.get("content", {}).get("snippets", [])))
    return refs


@test("What data do you have access to, and what time period does it cover?")
def t_discovery(mcp):
    text = json.dumps(mcp.call("platform_core_list_indices", {}))
    assert all(i in text for i in ("trades", "companies", "filings")), "indices missing"
    rows = esql_rows(mcp.call("platform_core_execute_esql", {
        "query": "FROM trades | STATS trades = COUNT(*), first_trade = MIN(time), last_trade = MAX(time), tickers = COUNT_DISTINCT(sym)"}))
    r = rows[0]
    assert r["trades"] > 1_000_000 and r["tickers"] == 24, r
    assert r["first_trade"].startswith("2026-09-01") and r["last_trade"].startswith("2026-09-30"), r
    return f"{r['trades']:,} trades, {r['tickers']} tickers, {r['first_trade'][:10]} to {r['last_trade'][:10]}"


@test("What were the biggest market-moving events in September? Rank them by unusual volume.")
def t_anomalies(mcp):
    rows = esql_rows(mcp.call("mi_volume_anomalies", {**MONTH, "min_ratio": 2}))
    top = [(r["sym"], r["day"][:10]) for r in rows[:6]]
    assert top[0] == ("VTRX", "2026-09-24") and abs(rows[0]["volume_ratio"] - 7.23) < 0.01, rows[0]
    for want in [("ROVR", "2026-09-18"), ("NVLT", "2026-09-15"), ("HRBR", "2026-09-09")]:
        assert want in top, f"{want} not in top 6: {top}"
    return ", ".join(f"{r['sym']} {r['day'][5:10]} {r['volume_ratio']}x" for r in rows[:6])


@test("Why did Novalight drop on September 15? Show me when it happened during the day.")
def t_nvlt(mcp):
    bars = esql_rows(mcp.call("mi_intraday_bars", {"sym": "NVLT", "day": D(15)}))
    before = next(b for b in bars if b["bar"].startswith("2026-09-15T17:45"))
    after = next(b for b in bars if b["bar"].startswith("2026-09-15T18:15"))
    drop = after["vwap"] / before["vwap"] - 1
    assert drop < -0.09, f"drop {drop:.1%}"
    hits = filings_hits(mcp.call("mi_filings_search", {"nlQuery": "Why did Novalight lower its revenue outlook in September?"}))
    assert any("export" in h.lower() and "NVLT" in h for h in hits), "8-K not retrieved"
    return f"VWAP {before['vwap']} -> {after['vwap']} ({drop:.1%}) around 14:00-14:15 ET; export-license 8-K found"


@test("Was there anything unusual in Vitrexa trading before its FDA news?")
def t_vtrx(mcp):
    hits = filings_hits(mcp.call("mi_filings_search", {"nlQuery": "Vitrexa FDA approval VX-401"}))
    assert any("approved VX-401" in h for h in hits), "approval 8-K not retrieved"
    blocks = {r["day"][:10]: r for r in esql_rows(mcp.call("mi_block_activity", MONTH)) if r["sym"] == "VTRX"}
    b22, b23 = blocks["2026-09-22"], blocks["2026-09-23"]
    assert (b22["blocks"], b22["buy_blocks"], b23["blocks"], b23["buy_blocks"]) == (14, 14, 23, 21), (b22, b23)
    trades = esql_rows(mcp.call("mi_block_trades", {"sym": "VTRX", "first_day": D(22), "last_day": D(23)}))
    assert len(trades) >= 37, len(trades)
    return (f"22 Sep {b22['blocks']} blocks ({b22['buy_blocks']} buys, ${b22['block_notional_musd']}M); "
            f"23 Sep {b23['blocks']} ({b23['buy_blocks']} buys, ${b23['block_notional_musd']}M)")


@test("How did each sector perform in September? Show it as a bar chart.")
def t_sectors(mcp):
    rows = esql_rows(mcp.call("mi_sector_performance", MONTH))
    order = [r["sector"] for r in rows]
    assert order[0] == "Health Care" and set(order[-2:]) == {"Technology", "Financials"}, order
    return ", ".join(f"{r['sector']} {r['avg_return_pct']:+}%" for r in rows)


@test("What new risks did Orchard Devices add in its latest 10-K compared with its prior 10-Q, "
      "and how did trading volume change that week?")
def t_orch(mcp):
    hits = filings_hits(mcp.call("mi_filings_search", {"nlQuery": "Orchard Devices 10-K risk factors supply chain AI regulation"}))
    assert any("Form 10-K" in h and "ORCH" in h for h in hits), "10-K not retrieved"
    rows = esql_rows(mcp.call("platform_core_execute_esql", {
        "query": 'FROM trades | WHERE sym == "ORCH" | STATS volume = SUM(size) BY week = DATE_TRUNC(1 week, time) | SORT week'}))
    vol = {r["week"][:10]: r["volume"] for r in rows}
    ratio = vol["2026-09-21"] / vol["2026-08-31"]
    assert ratio > 1.8, vol
    return f"10-K found; week of 21 Sep {vol['2026-09-21']:,} shares vs {vol['2026-08-31']:,} ({ratio:.1f}x)"


@test("Compare valuations for the technology names using September 30 prices.")
def t_valuation(mcp):
    rows = {r["sym"]: r for r in esql_rows(mcp.call("mi_valuation_snapshot", {"day": D(30)}))}
    orch, nvlt = rows["ORCH"], rows["NVLT"]
    assert (orch["pe"], orch["ev_ebitda"], nvlt["pe"]) == (31.2, 23.1, 35.1), (orch, nvlt)
    return f"ORCH ${orch['market_cap_bn']:,}B P/E {orch['pe']}; NVLT ${nvlt['market_cap_bn']:,}B P/E {nvlt['pe']}"


@test("Total volume for ORCH in September?")
def t_total(mcp):
    rows = esql_rows(mcp.call("platform_core_execute_esql", {
        "query": 'FROM trades | WHERE sym == "ORCH" | STATS total_volume = SUM(size)'}))
    assert rows[0]["total_volume"] == 19_836_666, rows
    return f"{rows[0]['total_volume']:,} shares"


@test("Which regional bank warned on credit, and did it affect real estate names?")
def t_hrbr(mcp):
    hits = filings_hits(mcp.call("mi_filings_search", {"nlQuery": "bank provision for credit losses commercial real estate office loans"}))
    assert any("HRBR" in h for h in hits), "HRBR 8-K not retrieved"
    day = lambda s: next(r for r in esql_rows(mcp.call("mi_daily_bars", {"sym": s, "first_day": D(9), "last_day": D(9)})))  # noqa: E731
    h, k = day("HRBR"), day("KEYS")
    assert h["change_pct"] < -6 and k["change_pct"] < -2, (h, k)
    return f"HRBR {h['change_pct']}%, KEYS {k['change_pct']}% on 9 Sep"


def main():
    mcp = McpOAuthClient()
    print(f"Connected over OAuth to {mcp.url} ({mcp.server_info})")
    names = {t["name"] for t in mcp.tools()}
    missing = {"mi_volume_anomalies", "mi_filings_search", "platform_core_execute_esql"} - names
    assert not missing, f"tools missing: {missing}"
    passed = 0
    try:
        for i, (question, fn) in enumerate(TESTS, 1):
            try:
                detail = fn(mcp)
                passed += 1
                print(f"PASS {i}. {question}\n       -> {detail}")
            except Exception as e:  # report and continue
                print(f"FAIL {i}. {question}\n       -> {type(e).__name__}: {e}")
                traceback.print_exc(limit=1)
    finally:
        mcp.close()
    print(f"\n{passed}/{len(TESTS)} passed")
    raise SystemExit(0 if passed == len(TESTS) else 1)


if __name__ == "__main__":
    main()
