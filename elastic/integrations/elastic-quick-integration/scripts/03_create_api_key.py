"""Create a read-only API key for the Elastic MCP server (alternative to OAuth, for automation or gateways).

Scope: read on trades, companies, filings; inference for semantic_text search; Agent Builder read.
Elasticsearch does not let an API key mint a derived key with privileges, so this script must run
as a user: set ELASTIC_USERNAME / ELASTIC_PASSWORD. Without them it writes the request body to
build/api_key_request.json for you to run in Kibana Dev Tools (POST /_security/api_key).
"""
import json

from elasticsearch import Elasticsearch

from common import COMPANIES, FILINGS, ROOT, TRADES, env

BODY = {
    "name": "quick-mcp-market-intel-readonly",
    "expiration": "30d",
    "role_descriptors": {
        "quick-market-intel": {
            "cluster": ["monitor_inference"],
            "indices": [{"names": [TRADES, COMPANIES, FILINGS], "privileges": ["read", "view_index_metadata"]}],
            "applications": [{
                "application": "kibana-.kibana",
                "privileges": ["feature_agentBuilder.read", "feature_actions.read"],
                "resources": ["space:default"],
            }],
        }
    },
    "metadata": {"purpose": "Amazon Quick market intelligence demo"},
}


def main():
    user, password = env("ELASTIC_USERNAME", False), env("ELASTIC_PASSWORD", False)
    if not (user and password):
        out = ROOT / "build" / "api_key_request.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(BODY, indent=2))
        print(f"ELASTIC_USERNAME/ELASTIC_PASSWORD not set. Run this in Kibana Dev Tools:\n\n"
              f"POST /_security/api_key\n{json.dumps(BODY, indent=2)}\n\n(also saved to {out})")
        return
    es = Elasticsearch(env("ELASTIC_URL"), basic_auth=(user, password))
    resp = es.security.create_api_key(**BODY)
    print(f"Created API key id={resp['id']} (expires in 30 days).")
    print("Add this to .env as ELASTIC_API_KEY and store it in AWS Secrets Manager:")
    print(resp["encoded"])


if __name__ == "__main__":
    main()
