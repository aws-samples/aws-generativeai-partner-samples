"""Create the three demo indices: trades (tick data), companies (lookup), filings (semantic).

Usage: python 01_create_indices.py [--recreate] [--inference-id ID]
--recreate deletes and recreates only these three demo indices.
"""
import argparse

from common import COMPANIES, FILINGS, TRADES, es_client, is_serverless

TRADES_MAPPING = {
    "dynamic": "strict",
    "properties": {
        "time": {"type": "date"},
        "sym": {"type": "keyword"},
        "sector": {"type": "keyword"},
        "price": {"type": "double"},     # double, not float, so ES|QL returns clean cents
        "size": {"type": "integer"},
        "notional": {"type": "double"},  # price * size, enables VWAP = SUM(notional) / SUM(size)
        "side": {"type": "keyword"},     # buy | sell (aggressor side)
        "exchange": {"type": "keyword"},
        "is_block": {"type": "boolean"},  # size >= 10,000 shares
    },
}

COMPANIES_MAPPING = {
    "dynamic": "strict",
    "properties": {
        "sym": {"type": "keyword"},
        "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
        "sector": {"type": "keyword"},
        "industry": {"type": "keyword"},
        "hq": {"type": "keyword"},
        "shares_out_m": {"type": "double"},
        "eps_ttm": {"type": "double"},
        "revenue_ttm_bn": {"type": "double"},
        "ebitda_ttm_bn": {"type": "double"},
        "net_debt_bn": {"type": "double"},
        "dividend_yield_pct": {"type": "double"},
        "beta": {"type": "double"},
    },
}


def filings_mapping(inference_id: str | None) -> dict:
    content = {"type": "semantic_text"}
    if inference_id:
        content["inference_id"] = inference_id
    return {
        "dynamic": "strict",
        "properties": {
            "sym": {"type": "keyword"},
            "company": {"type": "keyword"},
            "sector": {"type": "keyword"},
            "form": {"type": "keyword"},
            "filed": {"type": "date"},
            "period": {"type": "date"},
            "section": {"type": "keyword"},
            "accession": {"type": "keyword"},
            "title": {"type": "text"},
            "content": content,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recreate", action="store_true", help="delete and recreate the demo indices")
    ap.add_argument("--inference-id", help="inference endpoint for semantic_text (default: cluster default)")
    args = ap.parse_args()

    es = es_client()
    serverless = is_serverless(es)
    print(f"Connected to {es.info()['version']['number']} ({'serverless' if serverless else 'hosted'})")

    specs = {
        TRADES: (TRADES_MAPPING, {} if serverless else {"number_of_shards": 1}),
        # index.mode=lookup lets ES|QL enrich trades with fundamentals via LOOKUP JOIN.
        COMPANIES: (COMPANIES_MAPPING, {"index.mode": "lookup"}),
        FILINGS: (filings_mapping(args.inference_id), {}),
    }
    for name, (mappings, settings) in specs.items():
        if es.indices.exists(index=name):
            if not args.recreate:
                print(f"  {name}: exists, skipping (use --recreate to rebuild)")
                continue
            es.indices.delete(index=name)
            print(f"  {name}: deleted")
        es.indices.create(index=name, mappings=mappings, settings=settings or None)
        print(f"  {name}: created")


if __name__ == "__main__":
    main()
