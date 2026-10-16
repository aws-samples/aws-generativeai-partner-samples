"""Shared helpers: config loading, Elasticsearch/Kibana clients, small utilities."""
import json
import os
import sys
from pathlib import Path

import requests
from elasticsearch import Elasticsearch

ROOT = Path(__file__).resolve().parent.parent
TRADES, COMPANIES, FILINGS = "trades", "companies", "filings"


def load_env(path: Path = ROOT / ".env") -> None:
    """Minimal .env loader (KEY=VALUE per line); real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def env(name: str, required: bool = True) -> str | None:
    load_env()
    value = os.environ.get(name)
    if required and not value:
        sys.exit(f"Missing {name}. Set it in {ROOT / '.env'} (see .env.example) or export it.")
    return value


def es_client(api_key_var: str = "ELASTIC_ADMIN_API_KEY") -> Elasticsearch:
    return Elasticsearch(env("ELASTIC_URL"), api_key=env(api_key_var), request_timeout=300,
                         retry_on_timeout=True, max_retries=5)


def is_serverless(es: Elasticsearch) -> bool:
    return es.info()["version"].get("build_flavor") == "serverless"


class Kibana:
    """Thin wrapper over the Kibana HTTP API (Agent Builder lives here, not in Elasticsearch)."""

    def __init__(self, api_key_var: str = "ELASTIC_ADMIN_API_KEY"):
        self.base = env("KIBANA_URL").rstrip("/")
        self.headers = {
            "Authorization": f"ApiKey {env(api_key_var)}",
            "Content-Type": "application/json",
            "kbn-xsrf": "true",
        }

    def request(self, method: str, path: str, body: dict | None = None, ok=(200,)):
        r = requests.request(method, self.base + path, headers=self.headers,
                             data=json.dumps(body) if body is not None else None, timeout=120)
        if r.status_code not in ok:
            raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:800]}")
        return r.json() if r.text else {}

    def version(self) -> tuple[int, int]:
        v = self.request("GET", "/api/status")["version"]["number"]
        major, minor = v.split(".")[:2]
        return int(major), int(minor)


def esql(es: Elasticsearch, query: str, params: list | None = None) -> list[dict]:
    """Run ES|QL and return rows as dicts."""
    body = {"query": query}
    if params:
        body["params"] = params
    resp = es.esql.query(**body)
    cols = [c["name"] for c in resp["columns"]]
    return [dict(zip(cols, row)) for row in resp["values"]]


def print_table(rows: list[dict], max_rows: int = 25) -> None:
    if not rows:
        print("  (no rows)")
        return
    cols = list(rows[0])
    shown = rows[:max_rows]
    widths = {c: max(len(c), *(len(_fmt(r[c])) for r in shown)) for c in cols}
    print("  " + "  ".join(c.ljust(widths[c]) for c in cols))
    for r in shown:
        print("  " + "  ".join(_fmt(r[c]).ljust(widths[c]) for c in cols))
    if len(rows) > max_rows:
        print(f"  ... {len(rows) - max_rows} more rows")


def _fmt(v) -> str:
    return f"{v:,.2f}" if isinstance(v, float) else str(v)
