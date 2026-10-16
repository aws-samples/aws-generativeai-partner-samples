"""Minimal MCP stdio client over `npx mcp-remote` with a static OAuth client (same auth path as Quick)."""
import json
import queue
import subprocess
import threading

from common import env


class McpOAuthClient:
    def __init__(self, timeout: int = 300):
        self.url = env("KIBANA_URL").rstrip("/").removesuffix(":443") + "/api/agent_builder/mcp"
        client = json.dumps({"client_id": env("ELASTIC_MCP_OAUTH_CLIENT_ID")})
        self.timeout, self._id = timeout, 0
        self.proc = subprocess.Popen(["npx", "-y", "mcp-remote", self.url, "--static-oauth-client-info", client],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     text=True, bufsize=1)
        self._lines: queue.Queue = queue.Queue()
        threading.Thread(target=lambda: [self._lines.put(l) for l in self.proc.stdout], daemon=True).start()
        self.server_info = self.request("initialize", {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "quick-demo-tests", "version": "1.0"}})["serverInfo"]
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _send(self, msg: dict):
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def request(self, method: str, params: dict) -> dict:
        self._id += 1
        self._send({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params})
        while True:
            reply = json.loads(self._lines.get(timeout=self.timeout))
            if reply.get("id") == self._id:
                if "error" in reply:
                    raise RuntimeError(f"{method}: {reply['error']}")
                return reply["result"]

    def tools(self) -> list[dict]:
        return self.request("tools/list", {})["tools"]

    def call(self, name: str, arguments: dict) -> dict:
        """Returns the parsed Agent Builder payload ({"results": [...]}) from the tool's text content."""
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        text = result["content"][0]["text"]
        if result.get("isError"):
            raise RuntimeError(f"{name}: {text[:500]}")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"text": text}

    def close(self):
        self.proc.terminate()


def esql_rows(payload: dict) -> list[dict]:
    """Rows from the first esql_results block of an Agent Builder tool response."""
    for r in payload.get("results", []):
        if r.get("type") == "esql_results":
            cols = [c["name"] for c in r["data"]["columns"]]
            return [dict(zip(cols, v)) for v in r["data"]["values"]]
    raise AssertionError(f"no esql_results in response: {json.dumps(payload)[:400]}")
