"""Verify the Elastic MCP server over OAuth (no API key), the same way Amazon Quick connects.

Spawns `npx mcp-remote` with a static OAuth client; on first run a browser opens for Elastic
Cloud login (authorization code + PKCE). Tokens are cached in ~/.mcp-auth for later runs.
Then sends initialize, tools/list, and two tools/call requests over stdio.

Usage: python 05b_verify_mcp_oauth.py   (needs ELASTIC_MCP_OAUTH_CLIENT_ID and KIBANA_URL)
"""
import json
import queue
import subprocess
import threading

from common import env

LOGIN_TIMEOUT = 300


def main():
    url = env("KIBANA_URL").rstrip("/").removesuffix(":443") + "/api/agent_builder/mcp"
    client = json.dumps({"client_id": env("ELASTIC_MCP_OAUTH_CLIENT_ID")})
    proc = subprocess.Popen(["npx", "-y", "mcp-remote", url, "--static-oauth-client-info", client],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    lines: queue.Queue = queue.Queue()
    threading.Thread(target=lambda: [lines.put(l) for l in proc.stdout], daemon=True).start()

    def send(method, params=None, rid=None):
        msg = {"jsonrpc": "2.0", "method": method, **({"params": params} if params is not None else {})}
        if rid is not None:
            msg["id"] = rid
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()
        while rid is not None:
            reply = json.loads(lines.get(timeout=LOGIN_TIMEOUT))
            if reply.get("id") == rid:
                return reply

    try:
        print(f"Connecting to {url} (complete the browser login if prompted)...")
        init = send("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                   "clientInfo": {"name": "quick-demo-verify", "version": "1.0"}}, 1)
        print("Server:", init["result"]["serverInfo"])
        send("notifications/initialized")
        tools = send("tools/list", {}, 2)["result"]["tools"]
        print(f"{len(tools)} tools; custom: {sorted(t['name'] for t in tools if t['name'].startswith('mi_'))}")
        for rid, (name, args) in enumerate([
            ("mi_volume_anomalies", {"first_day": "2026-09-01T00:00:00Z", "last_day": "2026-09-30T00:00:00Z",
                                     "min_ratio": 4}),
            ("mi_filings_search", {"nlQuery": "Why did Novalight cut its revenue outlook?"}),
        ], start=3):
            result = send("tools/call", {"name": name, "arguments": args}, rid)
            text = result.get("result", {}).get("content", [{}])[0].get("text", "") or json.dumps(result)
            print(f"\n== {name}: {text[:700]}")
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
