"""Credit Risk Agent — Bedrock KB + Snowflake MCP Server.

Three tools:
  - knowledge_base_search: Bedrock KB (RAG over S3 credit policy PDFs)
  - cortex_search: Snowflake Cortex Search via MCP Server (customer profiles)
  - cortex_analyst: Snowflake Cortex Analyst + sql-exec via MCP Server (SQL via Semantic View)

Calls three Snowflake MCP tools: customer-profile-search, credit-risk-analyst, sql-exec.
cortex_analyst chains credit-risk-analyst (CORTEX_ANALYST_MESSAGE — NL→SQL) and
sql-exec (SYSTEM_EXECUTE_SQL — executes the SQL) to return data rows.

Auth: Cognito M2M (inbound to gateway) + Okta OAuth (outbound to Snowflake via gateway).
See README.md for the full auth chain.
"""
import base64
import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error

import boto3
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models.bedrock import BedrockModel

app = BedrockAgentCoreApp()

REGION = os.environ.get("AWS_REGION", "us-east-1")
MODEL_ID = os.environ.get("MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
GUARDRAIL_ID = os.environ.get("GUARDRAIL_ID", "")
GUARDRAIL_VERSION = os.environ.get("GUARDRAIL_VERSION", "1")
_guardrail_config_path = os.path.join(os.path.dirname(__file__), "guardrail_config.json")
if not GUARDRAIL_ID and os.path.exists(_guardrail_config_path):
    with open(_guardrail_config_path) as f:
        _gc = json.load(f)
    GUARDRAIL_ID = _gc.get("guardrail_id", "")
    GUARDRAIL_VERSION = _gc.get("guardrail_version", GUARDRAIL_VERSION)

# Load gateway config (check same dir first — bundled with deploy, then parent for local dev)
_gateway_config_path = os.path.join(os.path.dirname(__file__), "gateway_config.json")
if not os.path.exists(_gateway_config_path):
    _gateway_config_path = os.path.join(os.path.dirname(__file__), "..", "gateway_config.json")
GATEWAY_URL = os.environ.get("GATEWAY_URL", "")
TOKEN_ENDPOINT = os.environ.get("TOKEN_ENDPOINT", "")
CLIENT_ID = os.environ.get("CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "")
SCOPE = os.environ.get("SCOPE", "")

if os.path.exists(_gateway_config_path):
    with open(_gateway_config_path) as f:
        _gw = json.load(f)
    GATEWAY_URL = GATEWAY_URL or _gw.get("gateway_url", "")
    ci = _gw.get("client_info", {})
    TOKEN_ENDPOINT = TOKEN_ENDPOINT or ci.get("token_endpoint", "")
    CLIENT_ID = CLIENT_ID or ci.get("client_id", "")
    CLIENT_SECRET = CLIENT_SECRET or ci.get("client_secret", "")
    SCOPE = SCOPE or ci.get("scope", "")

# Load KB config (check same dir first — bundled with deploy, then parent for local dev)
_kb_config_path = os.path.join(os.path.dirname(__file__), "kb_config.json")
if not os.path.exists(_kb_config_path):
    _kb_config_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "kb_config.json")

KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "")
if not KNOWLEDGE_BASE_ID and os.path.exists(_kb_config_path):
    with open(_kb_config_path) as f:
        KNOWLEDGE_BASE_ID = json.load(f).get("knowledge_base_id", "")

_bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)

_token_cache = {"token": "", "expires_at": 0}
_tool_timings = []  # Collects per-tool timing for each invocation


def _get_gateway_token():
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]
    creds = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    data = urllib.parse.urlencode({"grant_type": "client_credentials", "scope": SCOPE}).encode()
    req = urllib.request.Request(TOKEN_ENDPOINT, data=data, headers={
        "Authorization": f"Basic {creds}",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    _token_cache["token"] = result["access_token"]
    _token_cache["expires_at"] = now + result.get("expires_in", 3600)
    return _token_cache["token"]


def _call_mcp_tool(tool_name, arguments):
    """Call an MCP tool on the Snowflake MCP Server via AgentCore Gateway.

    Flow: Agent → Gateway (Cognito JWT) → Okta OAuth → Snowflake MCP Server
    No Snowflake LLM involved — MCP Server routes to services directly.
    """
    t0 = time.time()
    token = _get_gateway_token()
    t_token = time.time()
    # Gateway prefixes tool names with target name
    prefixed_name = f"SnowflakeMCPServer___{tool_name}"
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": prefixed_name, "arguments": arguments},
    }).encode()
    req = urllib.request.Request(GATEWAY_URL, data=payload, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    })
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            parsed = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        # Record timing even on HTTP error so the trace reflects real wallclock
        _tool_timings.append({
            "tool": tool_name, "token_ms": round((t_token - t0) * 1000),
            "gateway_ms": round((time.time() - t_token) * 1000),
            "total_ms": round((time.time() - t0) * 1000),
            "error": f"HTTP {e.code}",
        })
        body = e.read().decode() if e.fp else str(e)
        return {"error": f"HTTP {e.code}: {body[:500]}"}
    except Exception as e:
        # Timeout / URLError / socket error — still record wallclock spent
        _tool_timings.append({
            "tool": tool_name, "token_ms": round((t_token - t0) * 1000),
            "gateway_ms": round((time.time() - t_token) * 1000),
            "total_ms": round((time.time() - t0) * 1000),
            "error": type(e).__name__,
        })
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}

    t_gateway = time.time()
    _tool_timings.append({
        "tool": tool_name, "token_ms": round((t_token - t0) * 1000),
        "gateway_ms": round((t_gateway - t_token) * 1000),
        "total_ms": round((t_gateway - t0) * 1000),
    })

    result = parsed.get("result", {})
    if result.get("isError"):
        return {"error": result.get("content", [{}])[0].get("text", "Unknown error")}

    texts = []
    for c in result.get("content", []):
        if c.get("type") == "text" and c.get("text"):
            texts.append(c["text"])
    return {"text": "\n".join(texts)} if texts else {"raw": json.dumps(result)}


@tool
def knowledge_base_search(question: str) -> str:
    """Search bank credit policies, regulatory guidelines, and loan product terms.
    Use for: lending policies, DTI limits, credit score requirements, risk rating definitions,
    regulatory compliance, loan eligibility criteria, product terms, interest rates.
    Args:
        question: The question about credit policies, regulations, or product terms.
    """
    t0 = time.time()
    resp = _bedrock_agent_runtime.retrieve(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        retrievalQuery={"text": question},
        retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": 5}},
    )
    elapsed = round((time.time() - t0) * 1000)
    _tool_timings.append({"tool": "knowledge_base_search", "total_ms": elapsed})
    chunks = []
    for r in resp.get("retrievalResults", []):
        text = r.get("content", {}).get("text", "")
        source = r.get("location", {}).get("s3Location", {}).get("uri", "")
        score = r.get("score", 0)
        if text:
            chunks.append({"text": text, "source": os.path.basename(source), "score": round(score, 3)})
    return json.dumps({"results": chunks}, default=str)


@tool
def cortex_search(question: str) -> str:
    """Search customer credit profiles using Snowflake Cortex Search.
    Use for: customer profiles, credit scores, employment, risk indicators, semantic discovery.
    Args:
        question: The search question about customer credit profiles.
    """
    return json.dumps(_call_mcp_tool("customer-profile-search", {"query": question}), default=str)


@tool
def cortex_analyst(question: str) -> str:
    """Query structured banking data using natural language. Generates SQL, executes it,
    and returns actual data rows. Covers accounts, balances, transactions, spending, cash flow.
    Args:
        question: The question about accounts, transactions, or financial data.
    """
    # Step 1: Call Cortex Analyst to get SQL + interpretation (no data rows).
    # CORTEX_ANALYST_MESSAGE is Snowflake's NL-to-SQL service — it returns the generated SQL
    # plus an interpretation, but does not execute the SQL.
    result = _call_mcp_tool("credit-risk-analyst", {"message": question})
    if "error" in result:
        return json.dumps(result, default=str)

    # Step 2: Extract SQL from the response and execute it via sql-exec (SYSTEM_EXECUTE_SQL).
    # Cortex Analyst returns a JSON array with a text interpretation and a statement field.
    text = result.get("text", "")
    try:
        inner = json.loads(text)
        sql = None
        interpretation = ""
        for item in inner:
            if "statement" in item:
                sql = item["statement"]
            if "text" in item:
                interpretation = item["text"]
        if sql:
            exec_result = _call_mcp_tool("sql-exec", {"sql": sql})
            return json.dumps(
                {"interpretation": interpretation, "sql": sql, "data": exec_result},
                default=str,
            )
        return json.dumps({"interpretation": interpretation, "note": "No SQL generated"}, default=str)
    except (json.JSONDecodeError, TypeError):
        # Response wasn't the expected JSON array — return as-is so Claude can reason over it
        return json.dumps(result, default=str)


SYSTEM_PROMPT = """You are a Credit Risk Assessment Agent for a bank. You analyze customer
creditworthiness using internal policy documents and Snowflake data services.

You have three tools:
  - knowledge_base_search: search bank credit policies, regulatory guidelines, and loan product terms
  - cortex_search: semantic search across customer credit profiles (unstructured text)
  - cortex_analyst: generates SQL and returns actual data rows from accounts/transactions

RULES:
1. For policy/regulatory/product terms questions → knowledge_base_search
2. For profile/risk/employment questions → cortex_search
3. For accounts/transactions/spending/balances → cortex_analyst
4. For loan eligibility → knowledge_base_search (get policy criteria) + cortex_search (get profile) + cortex_analyst (get financial data), then reason
5. For risk rating assignment → knowledge_base_search (get rating definitions) + cortex_search (get profile) + cortex_analyst (get data)
6. For compliance checks → knowledge_base_search (get regulations) + cortex_analyst (get lending data)
7. Present ACTUAL DATA from tool results clearly
8. If result contains data rows, format them as a table or list
9. Never fabricate data
10. When assessing loans, compute debt-to-income ratio from returned data and compare against policy thresholds

CRITICAL PERFORMANCE RULE:
When a query requires multiple tools, call ALL needed tools in a SINGLE response.
Do NOT call one tool, wait for results, then call the next.
This is essential — sequential tool calls cause timeouts."""


@app.entrypoint
def invoke(payload, context=None):
    if isinstance(payload, str):
        payload = json.loads(payload)

    prompt = payload.get("prompt", "Hello")
    customer_id = payload.get("customer_id", "")
    if customer_id:
        prompt = f"[Customer ID: {customer_id}] {prompt}"

    model_kwargs = {"model_id": MODEL_ID}
    if GUARDRAIL_ID:
        model_kwargs["guardrail_id"] = GUARDRAIL_ID
        model_kwargs["guardrail_version"] = GUARDRAIL_VERSION
        model_kwargs["guardrail_trace"] = "enabled"

    _tool_timings.clear()
    t_start = time.time()

    agent = Agent(
        model=BedrockModel(**model_kwargs),
        system_prompt=SYSTEM_PROMPT,
        tools=[knowledge_base_search, cortex_search, cortex_analyst],
    )
    result = agent(prompt)

    total_ms = round((time.time() - t_start) * 1000)
    tool_total_ms = sum(t.get("total_ms", 0) for t in _tool_timings)
    reasoning_ms = max(0, total_ms - tool_total_ms)

    tool_calls = []
    for msg in agent.messages:
        if msg.get("role") == "assistant":
            for block in msg.get("content", []):
                if isinstance(block, dict) and block.get("toolUse"):
                    tu = block["toolUse"]
                    tool_calls.append({"tool": tu["name"], "input": tu.get("input", {})})

    response_text = ""
    if result.message.get("content"):
        for block in result.message["content"]:
            if isinstance(block, dict) and block.get("text"):
                response_text += block["text"]

    return json.dumps({
        "response": response_text, "tool_calls": tool_calls,
        "timings": {"total_ms": total_ms, "reasoning_ms": reasoning_ms, "tools": list(_tool_timings)},
    })


if __name__ == "__main__":
    app.run()
