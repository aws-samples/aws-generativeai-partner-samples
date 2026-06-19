"""Credit Risk Agent Backend — FastAPI with Cognito JWT auth, async polling for long queries."""
import os
import json
import re
import time
import asyncio
import boto3
import jwt
from uuid import uuid4
from collections import defaultdict
from jwt import PyJWKClient
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="MCP 2LO Credit Risk Agent API")
# CORS: Only allow same-origin requests (frontend and backend share the same ALB).
# In production, replace with your specific domain.
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
                         issuer=ISSUER, options={"verify_aud": False})  # Cognito access tokens don't include aud claim
        # Verify the token was issued by our webapp client (access tokens use client_id, not aud)
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


def _invoke_agent_sync(full_prompt, customer_id):
    """Synchronous agent invocation — runs in thread pool."""
    from botocore.config import Config
    client = boto3.client("bedrock-agentcore", region_name=REGION,
                          config=Config(read_timeout=300, connect_timeout=10))
    payload = json.dumps({"prompt": full_prompt, "customer_id": customer_id})
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=AGENT_RUNTIME_ARN, payload=payload,
        runtimeSessionId=f"p2-{uuid4()}",
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
async def chat(req: ChatRequest, user=Depends(verify_token)):
    """Submit chat — returns job_id immediately, poll /api/chat/status for result."""
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
            raw = await asyncio.to_thread(_invoke_agent_sync, full_prompt, customer_id)
            total_time = round(time.time() - start_time, 1)
            try:
                data = json.loads(raw)
                if isinstance(data, str):
                    data = json.loads(data)
                response_text = data.get("response", raw) if isinstance(data, dict) else raw
                tool_calls = data.get("tool_calls", []) if isinstance(data, dict) else []
                timings = data.get("timings", {}) if isinstance(data, dict) else {}
            except (json.JSONDecodeError, AttributeError):
                response_text = raw
                tool_calls = []
                timings = {}

            trace = [{"type": "agent", "total_time": total_time, "timings": timings}]
            for tc in tool_calls:
                name = tc.get("tool", "")
                if name == "knowledge_base_search":
                    trace.append({"type": "kb", "tool": name, "detail": "Bedrock KB (S3 policy docs)"})
                elif name == "cortex_search":
                    trace.append({"type": "gateway", "tool": name, "gateway": "SnowflakeMCPServer",
                                  "tools": ["customer-profile-search"], "detail": "Snowflake MCP Server → Cortex Search"})
                elif name == "cortex_analyst":
                    trace.append({"type": "gateway", "tool": name, "gateway": "SnowflakeMCPServer",
                                  "tools": ["credit-risk-analyst", "sql-exec"], "detail": "Cortex Analyst + SQL Execution via Snowflake MCP Server"})

            session["messages"].append({"role": "assistant", "content": str(response_text)[:500]})
            guardrail_blocked = bool(detected_pii)
            guardrail_reason = f"PII Redacted: {', '.join(detected_pii)}" if detected_pii else ""
            if any(m in str(response_text) for m in ["[Assistant output redacted.]", "I cannot process this request"]):
                guardrail_blocked = True
                guardrail_reason = guardrail_reason or "Content Safety Policy"

            _jobs[job_id] = {"status": "done", "result": {
                "response": response_text, "tool_calls": tool_calls,
                "trace": trace,
                "end_to_end_ms": round((time.time() - start_time) * 1000),
                "session_id": session_id,
                "guardrail_blocked": guardrail_blocked, "guardrail_reason": guardrail_reason,
            }, "created": time.time()}
        except Exception as e:
            _jobs[job_id] = {"status": "error", "result": {
                "response": f"Agent error: {str(e)}", "tool_calls": [], "trace": [],
                "end_to_end_ms": round((time.time() - start_time) * 1000),
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
    return {"status": job["status"], **job["result"]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
