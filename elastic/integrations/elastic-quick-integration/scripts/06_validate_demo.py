"""Run every tool query and demo question against Elasticsearch and print the results.

Use it to confirm the data loaded correctly and to see the answers Quick should produce
during the demo (the numbers are deterministic for a given --seed in 02_load_data.py).
"""
from agent_tools import TOOLS
from common import FILINGS, es_client, esql, print_table

SAMPLE_ARGS = {
    "mi_daily_bars": {"sym": "NVLT"},
    "mi_intraday_bars": {"sym": "NVLT", "day": "2026-09-15"},
    "mi_block_trades": {"sym": "VTRX", "first_day": "2026-09-21", "last_day": "2026-09-23"},
}

# Ad-hoc ES|QL a Quick agent typically generates with platform.core.execute_esql (as in the blog).
ADHOC = {
    "Sample of 10 trades": "FROM trades | SORT time DESC | LIMIT 10",
    "Total volume for ORCH": 'FROM trades | WHERE sym == "ORCH" | STATS total_volume = SUM(size)',
    "Hourly volume for NVLT on 15 Sep": """FROM trades
| WHERE sym == "NVLT" AND time >= "2026-09-15" AND time < "2026-09-16"
| STATS volume = SUM(size) BY hour = DATE_TRUNC(1 hour, time) | SORT hour""",
    "Max price for VTRX on 24 Sep": """FROM trades
| WHERE sym == "VTRX" AND time >= "2026-09-24" AND time < "2026-09-25" | STATS max_price = MAX(price)""",
    "ORCH weekly volume around its 10-K": """FROM trades | WHERE sym == "ORCH"
| STATS volume = SUM(size) BY week = DATE_TRUNC(1 week, time) | SORT week""",
}


def tool_args(tool):
    args = {k: p.get("defaultValue") for k, p in tool["params"].items()}
    args.update(SAMPLE_ARGS.get(tool["id"], {}))
    return [{k: v} for k, v in args.items()]


def main():
    es = es_client()
    for tool in TOOLS:
        if tool.get("type") == "index_search":
            continue
        params = tool_args(tool)
        print(f"\n### {tool['id']} {params}")
        print_table(esql(es, tool["query"], params))
    for title, q in ADHOC.items():
        print(f"\n### {title}")
        print_table(esql(es, q))

    for question in ["Why did Novalight lower its revenue outlook?",
                     "Which companies are exposed to commercial real estate or office loans?",
                     "What new risks did Orchard Devices add in its annual report?"]:
        print(f"\n### filings semantic search: {question}")
        hits = es.search(index=FILINGS, size=3, query={"semantic": {"field": "content", "query": question}},
                         source=["sym", "form", "filed", "title"])["hits"]["hits"]
        for h in hits:
            s = h["_source"]
            print(f"  {h['_score']:.3f}  {s['sym']:5} {s['form']:5} {s['filed'][:10]}  {s['title']}")


if __name__ == "__main__":
    main()
