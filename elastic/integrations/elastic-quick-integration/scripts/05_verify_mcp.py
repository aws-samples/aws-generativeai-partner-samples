"""Verify the Elastic MCP server with the read-only key: list tools, then call two of them.

Use this path for automation or for an MCP gateway that authenticates with an API key.
"""
import json

import requests

from common import env

URL = env("KIBANA_URL").rstrip("/") + "/api/agent_builder/mcp"
HEADERS = {
    "Authorization": f"ApiKey {env('ELASTIC_API_KEY')}",
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "kbn-xsrf": "true",
}


def rpc(method: str, params: dict, rid: int = 1) -> dict:
    r = requests.post(URL, headers=HEADERS, timeout=120,
                      json={"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
    r.raise_for_status()
    if r.headers.get("content-type", "").startswith("text/event-stream"):
        data = [line[5:].strip() for line in r.text.splitlines() if line.startswith("data:")]
        return json.loads(data[-1])
    return r.json()


def call(name: str, arguments: dict):
    print(f"\n== tools/call {name} {arguments}")
    result = rpc("tools/call", {"name": name, "arguments": arguments}, 2)
    if "error" in result:
        print("  ERROR:", result["error"])
        return
    for part in result["result"]["content"]:
        print("  " + part.get("text", "")[:1500])


def main():
    tools = rpc("tools/list", {})["result"]["tools"]
    print(f"{len(tools)} tools available at {URL}:")
    for t in tools:
        print(f"  - {t['name']}: {t.get('description', '')[:90]}")
    call("mi_volume_anomalies", {"first_day": "2026-09-01T00:00:00Z", "last_day": "2026-09-30T00:00:00Z", "min_ratio": 3})
    call("mi_filings_search", {"nlQuery": "Why did Novalight cut its revenue outlook?"})


if __name__ == "__main__":
    main()
