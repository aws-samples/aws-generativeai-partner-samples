"""Credit Risk Agent Backend — FastAPI with Cognito JWT auth, async polling, 3LO+Okta support."""
import os
import json
import re
import time
import asyncio
import boto3
from botocore.config import Config as BotoConfig
import jwt
from uuid import uuid4
from collections import defaultdict
from jwt import PyJWKClient
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Credit Risk Agent API (3LO + Okta)")
app.add_middleware(CORSMiddleware, allow_origins=[os.environ.get("ALLOWED_ORIGIN", "http://localhost")],
                   allow_methods=["*"], allow_headers=["*"])
security = HTTPBearer()

REGION = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
AGENT_RUNTIME_ARN = os.environ.get("AGENT_RUNTIME_ARN", "")
USER_POOL_ID = os.environ.get("USER_POOL_ID", "")
USER_POOL_CLIENT_ID = os.environ.get("USER_POOL_CLIENT_ID", "")

JWKS_URL = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
ISSUER = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}"
_jwk_client = None

_sessions = defaultdict(lambda: {"messages": [], "customer_id": "", "last_active": 0})
MAX_HISTORY = 10
_jobs = {}

SCENARIOS = [
    {"id": "policy", "label": "1. Credit Policy Lookup",
     "prompt": "What is our maximum DTI ratio for personal loans?",
     "description": "AWS only — Bedrock KB (S3 policy PDFs)"},
    {"id": "accounts", "label": "2. Account Summary", "customer_id": "C-1042",
     "prompt": "Show account summary for customer C-1042 including all balances",
     "description": "Snowflake only — Cortex Analyst (text-to-SQL)"},
    {"id": "profile_search", "label": "3. Customer Profile Search",
     "prompt": "Find customers with high credit risk indicators",
     "description": "Snowflake only — Cortex Search (semantic discovery)"},
    {"id": "loan_eligibility", "label": "4. Loan Eligibility (Hero)", "customer_id": "C-1042",
     "prompt": "Is C-1042 eligible for a $50K personal loan? Check our credit policy for requirements, pull their profile, and get their account data to compute DTI.",
     "description": "KB + Cortex Search + Analyst — all 3 tools"},
    {"id": "pii", "label": "5. PII Redaction",
     "prompt": "My SSN is 123-45-6789. What is my credit score?",
     "description": "Bedrock Guardrail anonymizes SSN"},
]

CUSTOMERS = [
    {"id": "C-1042", "name": "Priya Sharma", "segment": "Gold", "score": 742},
    {"id": "C-2087", "name": "James Wilson", "segment": "Standard", "score": 658},
    {"id": "C-3156", "name": "Maria Garcia", "segment": "Premium", "score": 801},
]


def get_jwk_client():
    global _jwk_client
    if not _jwk_client:
        _jwk_client = PyJWKClient(JWKS_URL)
    return _jwk_client


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        signing_key = get_jwk_client().get_signing_key_from_jwt(credentials.credentials)
        decoded = jwt.decode(credentials.credentials, signing_key.key, algorithms=["RS256"],
                         issuer=ISSUER, options={"verify_aud": False})
        if USER_POOL_CLIENT_ID and decoded.get("client_id") != USER_POOL_CLIENT_ID:
            raise HTTPException(status_code=401, detail="Authentication failed")
        return decoded
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Authentication failed")


class ChatRequest(BaseModel):
    prompt: str
    customer_id: Optional[str] = None
    session_id: Optional[str] = "default"


class SsoAuthRequest(BaseModel):
    session_uri: str


@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/auth/config")
async def auth_config():
    return {"userPoolId": USER_POOL_ID, "clientId": USER_POOL_CLIENT_ID, "region": REGION}

@app.get("/api/scenarios")
async def get_scenarios(user=Depends(verify_token)):
    return SCENARIOS

@app.get("/api/customers")
async def get_customers(user=Depends(verify_token)):
    return CUSTOMERS


# --- 3LO: Store the user token used to initiate the auth flow ---
_pending_3lo_tokens = {}  # user_sub -> user_token

# --- 3LO: Cache Snowflake identity (user, role) per Cognito sub ---
_snowflake_identity = {}  # user_sub -> {"user": str, "role": str}


def _fetch_snowflake_identity(user_token: str) -> Optional[dict]:
    """Call Gateway sql-exec to get CURRENT_USER() / CURRENT_ROLE().
    Returns {"user": str, "role": str} or None on failure.
    """
    import urllib.request, urllib.error
    gw_url = os.environ.get("GATEWAY_URL", "")
    if not gw_url:
        print("[sf-identity] GATEWAY_URL not set")
        return None
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {
            "name": "SnowflakeMCPServer3LOOkta___sql-exec",
            "arguments": {"sql": "SELECT CURRENT_USER() AS u, CURRENT_ROLE() AS r"},
        },
    }).encode()
    req = urllib.request.Request(gw_url, data=payload, headers={
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Mcp-Protocol-Version": "2025-11-25",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as e:
        raw = e.read().decode() if e.fp else str(e)
        print(f"[sf-identity] HTTP {e.code}: {raw[:300]}")
        return None
    except Exception as e:
        print(f"[sf-identity] Gateway call failed: {type(e).__name__}: {e}")
        return None
    print(f"[sf-identity] Raw gateway response: {raw[:500]}")
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        return None
    # Extract text blocks from MCP result
    texts = []
    for c in body.get("result", {}).get("content", []):
        if c.get("type") == "text" and c.get("text"):
            texts.append(c["text"])
    # Snowflake sql-exec typically returns rows; try several shapes
    for t in texts:
        try:
            parsed = json.loads(t)
        except json.JSONDecodeError:
            continue
        # Shape A: Snowflake sql-exec native — {"result_set":{"data":[["MY_SF_USER","ANALYST_ROLE"]]}}
        if isinstance(parsed, dict) and "result_set" in parsed:
            data = parsed["result_set"].get("data") or []
            if data and isinstance(data[0], list) and len(data[0]) >= 2:
                return {"user": str(data[0][0]), "role": str(data[0][1])}
        # Shape B: list of dicts — [{"U": "MY_SF_USER", "R": "ANALYST_ROLE"}]
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
            row = parsed[0]
            keys = {k.upper(): v for k, v in row.items()}
            user_val = keys.get("U") or keys.get("USER") or keys.get("CURRENT_USER()")
            role_val = keys.get("R") or keys.get("ROLE") or keys.get("CURRENT_ROLE()")
            if user_val and role_val:
                return {"user": str(user_val), "role": str(role_val)}
        # Shape C: dict with "rows"/"data"/"result" — list of row-dicts or row-lists
        if isinstance(parsed, dict):
            rows = parsed.get("rows") or parsed.get("data") or parsed.get("result")
            if isinstance(rows, list) and rows:
                row = rows[0]
                if isinstance(row, dict):
                    keys = {k.upper(): v for k, v in row.items()}
                    user_val = keys.get("U") or keys.get("USER") or keys.get("CURRENT_USER()")
                    role_val = keys.get("R") or keys.get("ROLE") or keys.get("CURRENT_ROLE()")
                    if user_val and role_val:
                        return {"user": str(user_val), "role": str(role_val)}
                elif isinstance(row, list) and len(row) >= 2:
                    return {"user": str(row[0]), "role": str(row[1])}
    print(f"[sf-identity] Could not parse identity from texts: {texts}")
    return None


# --- 3LO: Get Okta auth URL by triggering a Gateway call ---
@app.get("/api/auth/sso-status")
async def sso_status(user=Depends(verify_token),
                     credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Return cached Snowflake identity for this user. If cache miss, try to fetch it."""
    user_sub = user.get("sub", "")
    identity = _snowflake_identity.get(user_sub)
    if not identity:
        # Cache miss — try to fetch (works if AgentCore Identity has a valid token for this user)
        identity = _fetch_snowflake_identity(credentials.credentials)
        if identity:
            _snowflake_identity[user_sub] = identity
    return {"connected": bool(identity), "identity": identity}


@app.get("/api/auth/sso-auth-url")
async def get_sso_auth_url(user=Depends(verify_token),
                           credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Trigger a Gateway tool call to get the 3LO auth URL (-32042 elicitation) — redirects to Okta."""
    import urllib.request, urllib.parse, urllib.error
    gw_url = os.environ.get("GATEWAY_URL", "")
    if not gw_url:
        raise HTTPException(status_code=500, detail="GATEWAY_URL not configured")

    user_token = credentials.credentials
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "SnowflakeMCPServer3LOOkta___credit-risk-analyst", "arguments": {"message": "test"}},
    }).encode()
    req = urllib.request.Request(gw_url, data=payload, headers={
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Mcp-Protocol-Version": "2025-11-25",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode() if e.fp else ""
        body = json.loads(raw) if raw else {}
    except Exception as e:
        print(f"[3LO auth-url] Gateway error: {type(e).__name__}: {e}")
        body = {}

    if "error" in body and body["error"].get("code") == -32042:
        elicitations = body["error"].get("data", {}).get("elicitations", [])
        if elicitations:
            # Store the token that initiated this flow
            _pending_3lo_tokens[user.get("sub", "")] = user_token
            return {"auth_url": elicitations[0]["url"]}
    # Already authenticated — fetch identity so header badge can show it
    user_sub = user.get("sub", "")
    if not _snowflake_identity.get(user_sub):
        identity = _fetch_snowflake_identity(user_token)
        if identity:
            _snowflake_identity[user_sub] = identity
    return {"auth_url": None, "message": "Already authenticated or no auth required",
            "identity": _snowflake_identity.get(user_sub)}


# --- 3LO: CompleteResourceTokenAuth endpoint ---
@app.post("/api/auth/complete-sso-auth")
async def complete_sso_auth(req: SsoAuthRequest, user=Depends(verify_token),
                            credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Complete the 3LO session binding after Okta consent redirect."""
    try:
        client = boto3.client("bedrock-agentcore", region_name=REGION,
                              config=BotoConfig(read_timeout=30, connect_timeout=10))
        user_sub = user.get("sub", "")
        # Use the SAME token that initiated the flow, fall back to current
        token_for_auth = _pending_3lo_tokens.pop(user_sub, None) or credentials.credentials
        print(f"[3LO] CompleteResourceTokenAuth: sub={user_sub}, session_uri={req.session_uri[:50]}..., using_stored_token={token_for_auth != credentials.credentials}")
        client.complete_resource_token_auth(
            sessionUri=req.session_uri,
            userIdentifier={"userToken": token_for_auth},
        )
        print(f"[3LO] CompleteResourceTokenAuth SUCCESS")

        # Fetch Snowflake identity via Gateway (uses the newly-cached token)
        identity = _fetch_snowflake_identity(token_for_auth)
        if identity:
            _snowflake_identity[user_sub] = identity
            print(f"[3LO] Snowflake identity cached: {identity}")
        return {"status": "ok", "message": "Snowflake authentication completed", "identity": identity}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"CompleteResourceTokenAuth failed: {str(e)}")


def _extract_elicitation_url(raw_response):
    """Check if agent response contains a -32042 URL elicitation error."""
    if not raw_response:
        return None
    text = str(raw_response)
    if "-32042" not in text and "elicitation" not in text.lower() and "oauth2/authorize" not in text:
        return None
    try:
        import re
        # Match AgentCore Identity OAuth authorize URL or Okta OAuth URL
        url_match = re.search(r'(https://[^\s"<>]+oauth2/authorize[^\s"<>]*)', text)
        if url_match:
            return url_match.group(1)
        url_match = re.search(r'(https://[^\s"<>]+\.okta\.com[^\s"<>]+/v1/authorize[^\s"<>]*)', text)
        if url_match:
            return url_match.group(1)
    except Exception:
        pass
    return None


def _invoke_agent_sync(full_prompt, customer_id, user_access_token=None):
    """Synchronous agent invocation — runs in thread pool.

    For 3LO: boto3 cannot pass Bearer tokens, so we use raw HTTPS when
    user_access_token is provided.  Runtime validates the JWT, generates a
    WorkloadAccessToken, and delivers it to the agent via payload headers.
    """
    payload = json.dumps({"prompt": full_prompt, "customer_id": customer_id, "user_token": user_access_token})

    if user_access_token and AGENT_RUNTIME_ARN:
        # 3LO path: HTTPS POST with Bearer token (boto3 doesn't support this)
        import urllib.request, urllib.parse, urllib.error
        escaped_arn = urllib.parse.quote(AGENT_RUNTIME_ARN, safe="")
        url = f"https://bedrock-agentcore.{REGION}.amazonaws.com/runtimes/{escaped_arn}/invocations?qualifier=DEFAULT"
        req = urllib.request.Request(url, data=payload.encode(), headers={
            "Authorization": f"Bearer {user_access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": f"3lo-{uuid4()}",
        })
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            raise Exception(f"Runtime HTTP {e.code}: {body[:500]}")
        return raw

    # Fallback: IAM SigV4 (no user identity — won't work for 3LO tools)
    client = boto3.client("bedrock-agentcore", region_name=REGION,
                          config=BotoConfig(read_timeout=300, connect_timeout=10))
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=AGENT_RUNTIME_ARN, payload=payload,
        runtimeSessionId=f"3lo-{uuid4()}",
        qualifier="DEFAULT", contentType="application/json", accept="application/json",
    )
    raw = resp["response"].read().decode("utf-8")
    if "text/event-stream" in resp.get("contentType", ""):
        texts = []
        for line in raw.split("\n"):
            if line.startswith("data: "):
                texts.append(line[6:])
        return "".join(texts)
    return raw


@app.post("/api/chat")
async def chat(req: ChatRequest, user=Depends(verify_token),
               credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Submit chat — returns job_id immediately, poll /api/chat/status for result."""
    # Capture the raw Cognito access token to pass through to Runtime for 3LO
    user_access_token = credentials.credentials

    session_id = req.session_id or str(uuid4())
    session = _sessions[session_id]
    session["last_active"] = time.time()
    if req.customer_id:
        session["customer_id"] = req.customer_id
    customer_id = req.customer_id or ""

    history_parts = [f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'][:500]}" for m in session["messages"][-MAX_HISTORY:]]
    full_prompt = ("CONVERSATION HISTORY:\n" + "\n".join(history_parts) + "\n\nNEW USER MESSAGE:\n" + req.prompt) if history_parts else req.prompt
    session["messages"].append({"role": "user", "content": req.prompt})

    detected_pii = [label for pat, label in [(r'\d{3}-\d{2}-\d{4}', 'SSN'), (r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}', 'Credit Card')] if re.search(pat, req.prompt)]

    job_id = str(uuid4())
    _jobs[job_id] = {"status": "running", "result": None, "created": time.time()}

    async def run_agent():
        start_time = time.time()
        try:
            # Wall-clock end-to-end timing (includes Runtime invoke overhead)
            _e2e_start = time.time()
            raw = await asyncio.to_thread(_invoke_agent_sync, full_prompt, customer_id, user_access_token)
            end_to_end_ms = int((time.time() - _e2e_start) * 1000)
            total_time = round(time.time() - start_time, 1)

            # --- 3LO: Check for URL elicitation (-32042) ---
            auth_url = _extract_elicitation_url(raw)
            if auth_url:
                _jobs[job_id] = {
                    "status": "sso_auth_required",
                    "result": {"auth_url": auth_url},
                    "created": time.time(),
                }
                return

            try:
                data = json.loads(raw)
                if isinstance(data, str):
                    data = json.loads(data)
                response_text = data.get("response", raw) if isinstance(data, dict) else raw
                tool_calls = data.get("tool_calls", []) if isinstance(data, dict) else []
                agent_elapsed_ms = data.get("agent_elapsed_ms") if isinstance(data, dict) else None
                reasoning_ms = data.get("reasoning_ms") if isinstance(data, dict) else None
            except (json.JSONDecodeError, AttributeError):
                response_text = raw
                tool_calls = []
                agent_elapsed_ms = None
                reasoning_ms = None

            # Overhead = end_to_end - sum(tool durations) - reasoning
            # Includes: Runtime invoke plumbing, network, JSON marshalling, etc.
            tool_total_ms = sum((tc.get("duration_ms") or 0) for tc in tool_calls)
            overhead_ms = None
            if end_to_end_ms is not None and reasoning_ms is not None:
                overhead_ms = max(0, end_to_end_ms - tool_total_ms - reasoning_ms)

            trace = [{"type": "agent", "total_time": total_time}]
            for tc in tool_calls:
                name = tc.get("tool", "")
                duration_ms = tc.get("duration_ms")
                if name == "knowledge_base_search":
                    trace.append({"type": "kb", "tool": name, "duration_ms": duration_ms,
                                  "detail": "Bedrock KB (S3 policy docs)"})
                elif name == "cortex_search":
                    trace.append({"type": "gateway", "tool": name, "duration_ms": duration_ms,
                                  "gateway": "SnowflakeMCPServer3LOOkta",
                                  "tools": ["customer-profile-search"], "detail": "Snowflake MCP Server → Cortex Search"})
                elif name == "cortex_analyst":
                    trace.append({"type": "gateway", "tool": name, "duration_ms": duration_ms,
                                  "gateway": "SnowflakeMCPServer3LOOkta",
                                  "tools": ["credit-risk-analyst"], "detail": "Snowflake MCP Server → Cortex Analyst"})

            session["messages"].append({"role": "assistant", "content": str(response_text)[:500]})
            guardrail_blocked = bool(detected_pii)
            guardrail_reason = f"PII Redacted: {', '.join(detected_pii)}" if detected_pii else ""
            if any(m in str(response_text) for m in ["[Assistant output redacted.]", "I cannot process this request"]):
                guardrail_blocked = True
                guardrail_reason = guardrail_reason or "Content Safety Policy"

            _jobs[job_id] = {"status": "done", "result": {
                "response": response_text, "tool_calls": tool_calls,
                "trace": trace, "session_id": session_id,
                "guardrail_blocked": guardrail_blocked, "guardrail_reason": guardrail_reason,
                "end_to_end_ms": end_to_end_ms,
                "agent_elapsed_ms": agent_elapsed_ms,
                "reasoning_ms": reasoning_ms,
                "overhead_ms": overhead_ms,
            }, "created": time.time()}
        except Exception as e:
            _jobs[job_id] = {"status": "error", "result": {
                "response": f"Agent error: {str(e)}", "tool_calls": [], "trace": [],
                "session_id": session_id, "guardrail_blocked": False, "guardrail_reason": "",
            }, "created": time.time()}

    asyncio.create_task(run_agent())

    stale = [k for k, v in _jobs.items() if time.time() - v["created"] > 600]
    for k in stale:
        del _jobs[k]

    return {"job_id": job_id, "status": "running"}


@app.get("/api/chat/status/{job_id}")
async def chat_status(job_id: str, user=Depends(verify_token)):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] == "running":
        return {"status": "running"}
    # 3LO: Return auth_url for sso_auth_required status
    if job["status"] == "sso_auth_required":
        return {"status": "sso_auth_required", "auth_url": job["result"]["auth_url"]}
    return {"status": job["status"], **job["result"]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
