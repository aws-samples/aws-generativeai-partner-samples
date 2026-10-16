"""Register the custom market-intel tools in Elastic Agent Builder (create or update).

Every Agent Builder tool is served by the built-in MCP endpoint ({KIBANA_URL}/api/agent_builder/mcp),
so once this runs the tools are visible to Amazon Quick alongside the platform.core.* tools.
Usage: python 04_create_agent_tools.py [--delete]
"""
import argparse

from agent_tools import TOOLS, tool_body
from common import Kibana


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delete", action="store_true", help="remove the demo tools")
    args = ap.parse_args()

    kb = Kibana()
    major, minor = kb.version()
    legacy = (major, minor) < (9, 4)
    print(f"Kibana {major}.{minor} ({'legacy' if legacy else 'current'} parameter types)")
    existing = {t["id"] for t in kb.request("GET", "/api/agent_builder/tools").get("results", [])}

    for tool in TOOLS:
        tid = tool["id"]
        if args.delete:
            if tid in existing:
                kb.request("DELETE", f"/api/agent_builder/tools/{tid}")
                print(f"  deleted {tid}")
            continue
        body = tool_body(tool, legacy)
        if tid in existing:
            update = {k: v for k, v in body.items() if k not in ("id", "type")}
            kb.request("PUT", f"/api/agent_builder/tools/{tid}", update)
            print(f"  updated {tid}")
        else:
            kb.request("POST", "/api/agent_builder/tools", body)
            print(f"  created {tid}")


if __name__ == "__main__":
    main()
