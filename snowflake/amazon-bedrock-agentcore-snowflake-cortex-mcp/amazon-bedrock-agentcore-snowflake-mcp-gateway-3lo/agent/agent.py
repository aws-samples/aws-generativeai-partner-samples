"""Credit Risk Agent — Bedrock KB + Snowflake MCP Server (3LO).

Three tools:
  - knowledge_base_search: Bedrock KB (RAG over S3 credit policy PDFs)
  - cortex_search: Snowflake Cortex Search via MCP Server (customer profiles)
  - cortex_analyst: Snowflake Cortex Analyst via MCP Server (SQL via Semantic View)

Auth: Cognito M2M (inbound to gateway) + Snowflake 3LO OAuth (outbound via AgentCore Identity).
Per-user Snowflake RBAC — each analyst authenticates with own credentials.
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

# Load gateway config
_gateway_config_path = os.path.join(os.path.dirname(__file__), "gateway_config.json")
if not os.path.exists(_gateway_config_path):
    _gateway_config_path = os.path.join(os.path.dirname(__file__), "..", "gateway_config.json")
GATEWAY_URL = os.environ.get("GATEWAY_URL", "")
TOKEN_ENDPOINT = os.environ.get("TOKEN_ENDPOINT", "")
CLIENT_ID = os.environ.get("CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "")
SCOPE = os.environ.get("SCOPE", "")
TARGET_NAME = os.environ.get("TARGET_NAME", "SnowflakeMCPServer3LO")

if os.path.exists(_gateway_config_path):
    with open(_gateway_config_path) as f:
        _gw = json.load(f)
    GATEWAY_URL = GATEWAY_URL or _gw.get("gateway_url", "")
    TARGET_NAME = _gw.get("target_name", TARGET_NAME)
    ci = _gw.get("client_info", {})
    TOKEN_ENDPOINT = TOKEN_ENDPOINT or ci.get("token_endpoint", "")
    CLIENT_ID = CLIENT_ID or ci.get("client_id", "")
    CLIENT_SECRET = CLIENT_SECRET or ci.get("client_secret", "")
    SCOPE = SCOPE or ci.get("scope", "")

# Load KB config
_kb_config_path = os.path.join(os.path.dirname(__file__), "kb_config.json")
if not os.path.exists(_kb_config_path):
    _kb_config_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "kb_config.json")

KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "")
if not KNOWLEDGE_BASE_ID and os.path.exists(_kb_config_path):
    with open(_kb_config_path) as f:
        KNOWLEDGE_BASE_ID = json.load(f).get("knowledge_base_id", "")

_bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)

# Module-level holder for the WorkloadAccessToken provided by Runtime.
# Set in invoke() from context.request_headers, read in _call_mcp_tool().
_current_workload_access_token = None
_user_jwt = None

# Per-invocation per-tool timing log (reset in invoke()).
# Each entry: {"tool": str, "duration_ms": int}
_tool_timings = []


def _get_gateway_token():
    """Return token for Gateway inbound auth.

    Priority: user's Cognito JWT (carries user identity for 3LO) > M2M token (fallback).
    """
    if _user_jwt:
        return _user_jwt
    if _current_workload_access_token:
        return _current_workload_access_token
    # Fallback: Cognito M2M token (won't carry user identity for 3LO)
    now = time.time()
    if _token_cache.get("token") and now < _token_cache.get("expires_at", 0) - 60:
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


_token_cache = {"token": "", "expires_at": 0}


def _call_mcp_tool(tool_name, arguments):
    """Call an MCP tool on the Snowflake MCP Server via AgentCore Gateway."""
    token = _get_gateway_token()
    # Log which token type we're using (first 20 chars only for security)
    token_type = "WorkloadAccessToken" if _current_workload_access_token else "M2M"
    print(f"[_call_mcp_tool] tool={tool_name} token_type={token_type} token_prefix={token[:20]}...")

    prefixed_name = f"{TARGET_NAME}___{tool_name}"
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": prefixed_name, "arguments": arguments},
    }).encode()
    req = urllib.request.Request(GATEWAY_URL, data=payload, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Mcp-Protocol-Version": "2025-11-25",
    })
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw_body = resp.read().decode()
            print(f"[_call_mcp_tool] response: {raw_body[:500]}")
            parsed = json.loads(raw_body)
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else str(e)
        return {"error": f"HTTP {e.code}: {body[:500]}"}

    # Check for -32042 URL elicitation (3LO — user needs to authenticate)
    if "error" in parsed and parsed["error"].get("code") == -32042:
        elicitations = parsed["error"].get("data", {}).get("elicitations", [])
        urls = [e.get("url") for e in elicitations if e.get("url")]
        return {"error": f"-32042: Snowflake authentication required", "elicitation_url": urls[0] if urls else "", "code": -32042}

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
    _t0 = time.time()
    try:
        resp = _bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={"text": question},
            retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": 5}},
        )
        chunks = []
        for r in resp.get("retrievalResults", []):
            text = r.get("content", {}).get("text", "")
            source = r.get("location", {}).get("s3Location", {}).get("uri", "")
            score = r.get("score", 0)
            if text:
                chunks.append({"text": text, "source": os.path.basename(source), "score": round(score, 3)})
        return json.dumps({"results": chunks}, default=str)
    finally:
        _tool_timings.append({"tool": "knowledge_base_search", "duration_ms": int((time.time() - _t0) * 1000)})


@tool
def cortex_search(question: str) -> str:
    """Search customer credit profiles using Snowflake Cortex Search.
    Use for: customer profiles, credit scores, employment, risk indicators, semantic discovery.
    Args:
        question: The search question about customer credit profiles.
    """
    _t0 = time.time()
    try:
        return json.dumps(_call_mcp_tool("customer-profile-search", {"query": question}), default=str)
    finally:
        _tool_timings.append({"tool": "cortex_search", "duration_ms": int((time.time() - _t0) * 1000)})


@tool
def cortex_analyst(question: str) -> str:
    """Query structured banking data using natural language. Generates SQL, executes it,
    and returns actual data rows. Covers accounts, balances, transactions, spending, cash flow.
    Args:
        question: The question about accounts, transactions, or financial data.
    """
    _t0 = time.time()
    try:
        # Step 1: Get SQL from Cortex Analyst
        result = _call_mcp_tool("credit-risk-analyst", {"message": question})
        if "error" in result:
            return json.dumps(result, default=str)

        # Step 2: Extract SQL and execute it via sql-exec
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
                return json.dumps({"interpretation": interpretation, "sql": sql, "data": exec_result}, default=str)
            return json.dumps({"interpretation": interpretation, "note": "No SQL generated"}, default=str)
        except (json.JSONDecodeError, TypeError):
            return json.dumps(result, default=str)
    finally:
        _tool_timings.append({"tool": "cortex_analyst", "duration_ms": int((time.time() - _t0) * 1000)})


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

IMPORTANT — AUTHENTICATION:
If a Snowflake tool returns an error containing "-32042" or "authentication required",
return the FULL error response including any URL. The frontend will handle the
Snowflake login redirect. Do NOT retry the tool call — just report the error as-is.

CRITICAL PERFORMANCE RULE:
When a query requires multiple tools, call ALL needed tools in a SINGLE response.
Do NOT call one tool, wait for results, then call the next.
For example, for loan eligibility, call knowledge_base_search AND cortex_search AND cortex_analyst
all at once in the same message, then synthesize all results together.
This is essential — sequential tool calls cause timeouts."""


@app.entrypoint
def invoke(payload, context=None):
    global _current_workload_access_token
    global _user_jwt

    if isinstance(payload, str):
        payload = json.loads(payload)

    # Extract tokens for Gateway auth.
    _current_workload_access_token = None
    _user_jwt = None
    # Reset per-invocation tool timings
    _tool_timings.clear()

    # Priority 1: User's Cognito JWT passed in payload (Runtime doesn't forward Authorization header)
    _user_jwt = payload.get("user_token")

    if context:
        from bedrock_agentcore.runtime.context import BedrockAgentCoreContext
        _current_workload_access_token = BedrockAgentCoreContext.get_workload_access_token()
        # Fallback: try Authorization header (in case Runtime starts forwarding it)
        if not _user_jwt:
            headers = getattr(context, "request_headers", None) or {}
            auth_header = headers.get("Authorization") or headers.get("authorization") or ""
            if auth_header.startswith("Bearer "):
                _user_jwt = auth_header[7:]
    print(f"[invoke] UserJWT: {bool(_user_jwt)}, WorkloadAccessToken: {bool(_current_workload_access_token)}")

    prompt = payload.get("prompt", "Hello")
    customer_id = payload.get("customer_id", "")
    if customer_id:
        prompt = f"[Customer ID: {customer_id}] {prompt}"

    model_kwargs = {"model_id": MODEL_ID}
    if GUARDRAIL_ID:
        model_kwargs["guardrail_id"] = GUARDRAIL_ID
        model_kwargs["guardrail_version"] = GUARDRAIL_VERSION
        model_kwargs["guardrail_trace"] = "enabled"

    agent = Agent(
        model=BedrockModel(**model_kwargs),
        system_prompt=SYSTEM_PROMPT,
        tools=[knowledge_base_search, cortex_search, cortex_analyst],
    )
    _agent_start = time.time()
    result = agent(prompt)
    _agent_elapsed_ms = int((time.time() - _agent_start) * 1000)

    # Attach per-call duration to each tool use by matching in order against _tool_timings.
    # Each @tool invocation appends one entry; if the model calls the same tool multiple times
    # we match by index of occurrence.
    tool_calls = []
    _per_tool_idx = {}
    for msg in agent.messages:
        if msg.get("role") == "assistant":
            for block in msg.get("content", []):
                if isinstance(block, dict) and block.get("toolUse"):
                    tu = block["toolUse"]
                    name = tu["name"]
                    # Find the Nth timing entry for this tool
                    occurrence = _per_tool_idx.get(name, 0)
                    _per_tool_idx[name] = occurrence + 1
                    duration_ms = None
                    matches = [t["duration_ms"] for t in _tool_timings if t["tool"] == name]
                    if occurrence < len(matches):
                        duration_ms = matches[occurrence]
                    tool_calls.append({"tool": name, "input": tu.get("input", {}), "duration_ms": duration_ms})

    response_text = ""
    if result.message.get("content"):
        for block in result.message["content"]:
            if isinstance(block, dict) and block.get("text"):
                response_text += block["text"]

    tool_total_ms = sum(t["duration_ms"] for t in _tool_timings)
    reasoning_ms = max(0, _agent_elapsed_ms - tool_total_ms)

    return json.dumps({
        "response": response_text,
        "tool_calls": tool_calls,
        "agent_elapsed_ms": _agent_elapsed_ms,
        "reasoning_ms": reasoning_ms,
    })


if __name__ == "__main__":
    app.run()
