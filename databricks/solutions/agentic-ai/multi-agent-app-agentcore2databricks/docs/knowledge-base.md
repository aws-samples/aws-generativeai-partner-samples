# Knowledge Base: Multi-Agent Financial Analyst

A comprehensive guide for developers and architects learning from this codebase. Covers concepts, patterns, code explanations, and frequently asked questions.

---

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [How the Agents Work](#how-the-agents-work)
3. [MCP Protocol Explained](#mcp-protocol-explained)
4. [AgentCore Gateway Deep Dive](#agentcore-gateway-deep-dive)
5. [Databricks Agent Framework Patterns](#databricks-agent-framework-patterns)
6. [Authentication Flows](#authentication-flows)
7. [The Orchestration Loop](#the-orchestration-loop)
8. [Guardrails Implementation](#guardrails-implementation)
9. [FAQ](#faq)

---

## Core Concepts

### What is a "Multi-Agent System"?

A system where multiple specialized AI agents collaborate to complete a task that no single agent could handle well alone. Each agent has:
- A specific **role** (planning, querying, validating, writing)
- Access to specific **tools** (SQL, Python, APIs)
- A **model** (LLM) for reasoning

In our system, 4 agents work together:

```
User Question
    ↓
[Supervisor] — "What sub-questions do I need to answer?"
    ↓
[Data Analyst] — "Let me query the database for the numbers"
    ↓
[Validator] — "Are these numbers correct and consistent?"
    ↓
[Synthesizer] — "Here's a narrative report with confidence level"
    ↓
Final Answer
```

### What is "Hybrid" About This Architecture?

The agents run on **two different platforms**:

| Agent | Platform | Why There |
|-------|----------|-----------|
| Supervisor | AWS Bedrock | Claude is best at decomposition/planning |
| Data Analyst | Databricks | Native MCP access to lakehouse, Unity Catalog governance |
| Validator | Databricks | Needs MCP for validation queries + python_exec |
| Synthesizer | AWS Bedrock | Claude is best at narrative generation |

The "hybrid" part is the cross-platform collaboration — agents don't know or care where other agents run. They communicate through standard protocols.

### What is MCP (Model Context Protocol)?

MCP is an open protocol (by Anthropic) for connecting AI models to tools and data. Think of it as "USB for AI" — a standard way to plug capabilities into models.

Key MCP concepts:
- **Server**: Exposes tools (e.g., Databricks SQL MCP server exposes `execute_sql`)
- **Client**: Consumes tools (e.g., our agent calls `execute_sql`)
- **Tool**: A callable function with name, description, and input schema
- **Transport**: How client/server communicate (stdio, HTTPS/Streamable HTTP)

In our system:
```
AgentCore Gateway (MCP Server) ← Our agents connect here
    ↓ routes to
Databricks Managed MCP Servers (SQL, UC Functions) ← Where data actually lives
```

---

## How the Agents Work

### Supervisor Agent (AWS)

**File**: `agentcore/agents/supervisor.py`

The Supervisor receives a question and creates an execution plan:

```python
# The LLM generates a plan like this:
{
  "subtasks": [
    {"id": "st-1", "task": "Query portfolio positions by sector", "agent": "data_analyst", "depends_on": []},
    {"id": "st-2", "task": "Validate the sector totals", "agent": "validator", "depends_on": ["st-1"]},
    {"id": "st-3", "task": "Synthesize narrative answer", "agent": "synthesizer", "depends_on": ["st-2"]}
  ]
}
```

The `depends_on` field creates a dependency graph. Tasks with no dependencies run first; dependent tasks wait.

```python
def get_execution_waves(self, plan: ExecutionPlan) -> list[list[SubTask]]:
    """Group tasks into parallel execution waves."""
    waves = []
    completed: set[str] = set()
    remaining = {st.id for st in plan.subtasks}

    while remaining:
        # Find all tasks whose dependencies are satisfied
        wave = [
            st for st in plan.subtasks
            if st.id in remaining
            and all(dep in completed for dep in st.depends_on)
        ]
        waves.append(wave)
        for st in wave:
            remaining.discard(st.id)
            completed.add(st.id)

    return waves
```

If two data analyst tasks have no dependencies on each other, they run in the same wave (parallel).

### Data Analyst Agent (Databricks)

**File**: `databricks_agents/data_analyst/agent.py`

This agent runs inside a Databricks Model Serving container. Its reasoning loop:

```python
def _analyze(self, question: str) -> str:
    # 1. Get available SQL tools from MCP
    tools = self.sql_mcp.list_tools()
    
    # 2. Start conversation with LLM
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    
    # 3. Iterative tool-calling loop
    for _ in range(10):  # max iterations
        response = client.chat.completions.create(
            model=MODEL_ENDPOINT,   # from DATABRICKS_LLM_ENDPOINT env var
            messages=messages,
            tools=openai_tools,     # MCP tools in OpenAI format
        )
        
        choice = response.choices[0]
        
        if choice.finish_reason == "tool_calls":
            # LLM wants to call a tool (e.g., execute_sql)
            for tool_call in choice.message.tool_calls:
                # Execute via MCP
                result = self.sql_mcp.call_tool(tool_call.function.name, args)
                # Feed result back to LLM
                messages.append({"role": "tool", "content": result_text})
        else:
            # LLM has final answer
            return choice.message.content
```

The LLM decides what SQL to run, executes it via MCP, reads the results, and may run more queries until it has enough data to answer.

### Validator Agent (Databricks)

**File**: `databricks_agents/validator/agent.py`

Similar pattern to Data Analyst but with a validation-focused system prompt. It has access to two MCP servers:
- **SQL MCP**: Run validation queries (e.g., `SELECT COUNT(*) ...` to cross-check)
- **Python MCP** (`system.ai.python_exec`): Run statistical checks with pandas

### Synthesizer Agent (AWS)

**File**: `agentcore/agents/synthesizer.py`

The simplest agent — no tools, just text generation. It receives accumulated context from all prior agents and generates a structured narrative:

```python
def build_context(self, question, analyst_results, validation_result):
    """Build the prompt context from all prior results."""
    parts = [f"Original Question: {question}\n"]
    
    for result in analyst_results:
        parts.append(f"Findings: {result.get('summary', '')}")
        # ... SQL queries, tables accessed, etc.
    
    if validation_result:
        parts.append(f"Validation: {validation_result.get('summary', '')}")
    
    return "\n".join(parts)
```

---

## MCP Protocol Explained

### How MCP Tools Are Discovered

When the Gateway starts, or when an agent connects, tools are discovered via `tools/list`:

```json
// Request
{"jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": {}}

// Response
{
  "result": {
    "tools": [
      {
        "name": "databricks-finserv-data-analyst___invoke_finserv_data_analyst",
        "description": "Invoke the Data Analyst agent on Databricks",
        "inputSchema": {
          "type": "object",
          "required": ["messages"],
          "properties": {
            "messages": {
              "type": "array",
              "items": {"type": "object", "properties": {"role": {"type": "string"}, "content": {"type": "string"}}}
            }
          }
        }
      }
    ]
  }
}
```

### How MCP Tools Are Called

```json
// Request
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "tools/call",
  "params": {
    "name": "databricks-finserv-data-analyst___invoke_finserv_data_analyst",
    "arguments": {
      "messages": [{"role": "user", "content": "How many customers do we have?"}]
    }
  }
}

// Response
{
  "result": {
    "isError": false,
    "content": [
      {"type": "text", "text": "{\"choices\":[{\"message\":{\"content\":\"500 customers\"}}]}"}
    ]
  }
}
```

### MCP Tool Naming Convention

Tools in the Gateway are named: `<target-name>___<operationId>`

```
databricks-finserv-data-analyst___invoke_finserv_data_analyst
└── target name ──────────────┘   └── operationId from OpenAPI ─┘
```

This is auto-generated from the OpenAPI spec we registered:
```python
spec = {
    "paths": {
        "/serving-endpoints/finserv-data-analyst/invocations": {
            "post": {
                "operationId": "invoke_finserv_data_analyst",  # ← becomes tool suffix
                ...
            }
        }
    }
}
```

---

## AgentCore Gateway Deep Dive

### What the Gateway Does

```
Our Agent Code (SigV4 auth)
    ↓
AgentCore Gateway
    ├── Aggregates tools from all targets into one MCP endpoint
    ├── Handles OAuth token exchange with Databricks (automatic)
    ├── Routes tool calls to the correct target
    └── Returns results back via MCP protocol
    ↓
Databricks Model Serving (OAuth auth — Gateway manages this)
```

### Creating a Gateway (Python)

```python
import boto3

session = get_boto3_session(settings)
agentcore = session.client("bedrock-agentcore-control")

# Step 1: Create Gateway
gateway = agentcore.create_gateway(
    name="finserv-multi-agent-gateway",
    roleArn=role_arn,
    protocolType="MCP",
    authorizerType="NONE",
)
# Returns gatewayId like: "finserv-multi-agent-gateway-vabirxeraz"

# Step 2: Create OAuth provider for Databricks
agentcore.create_oauth2_credential_provider(
    name="databricks-finserv-oauth",
    credentialProviderVendor="CustomOauth2",  # Note: lowercase 'a' in Oauth
    oauth2ProviderConfigInput={
        "customOauth2ProviderConfig": {
            "oauthDiscovery": {
                "discoveryUrl": f"{workspace_url}/oidc/.well-known/openid-configuration"
            },
            "clientId": client_id,
            "clientSecret": client_secret,
        }
    },
)

# Step 3: Register target with OAuth
agentcore.create_gateway_target(
    gatewayIdentifier=gateway_id,  # MUST use gatewayId, NOT name
    name="databricks-finserv-data-analyst",
    targetConfiguration={"mcp": {"openApiSchema": {"inlinePayload": json.dumps(spec)}}},
    credentialProviderConfigurations=[{
        "credentialProviderType": "OAUTH",
        "credentialProvider": {
            "oauthCredentialProvider": {
                "providerArn": provider_arn,
                "grantType": "CLIENT_CREDENTIALS",
                "scopes": ["all-apis"],
            }
        }
    }],
)
```

### Calling Through the Gateway (SigV4)

```python
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests

gateway_url = f"https://{gateway_id}.gateway.bedrock-agentcore.{region}.amazonaws.com/mcp"

payload = {
    "jsonrpc": "2.0",
    "id": "1",
    "method": "tools/call",
    "params": {
        "name": "databricks-finserv-data-analyst___invoke_finserv_data_analyst",
        "arguments": {"messages": [{"role": "user", "content": question}]},
    },
}

# Sign with SigV4 (service name: "bedrock-agentcore")
request = AWSRequest(method="POST", url=gateway_url, data=json.dumps(payload),
                     headers={"Content-Type": "application/json"})
SigV4Auth(credentials, "bedrock-agentcore", region).add_auth(request)

resp = requests.post(gateway_url, data=json.dumps(payload), headers=dict(request.headers))
```

---

## Databricks Agent Framework Patterns

### Self-Contained Agent File

Databricks Model Serving requires agent files to be **completely self-contained** — no local imports. Everything must be in one file:

```python
# databricks_agents/data_analyst/agent.py

import json, os, logging
from typing import Any
import mlflow
from mlflow.pyfunc import PythonModel

# Inline the system prompt (can't import from another file)
CATALOG = os.environ.get("DATABRICKS_CATALOG", "finserv_catalog")
MODEL_ENDPOINT = os.environ.get("DATABRICKS_LLM_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct")
SYSTEM_PROMPT = f"""You are a Data Analyst for {CATALOG}..."""

class DataAnalystAgent(PythonModel):
    def load_context(self, context):
        # Called once when container starts
        from databricks.sdk import WorkspaceClient
        from databricks_mcp import DatabricksMCPClient
        
        self.ws = WorkspaceClient(
            host=os.environ["DATABRICKS_HOST"],
            client_id=os.environ["DATABRICKS_CLIENT_ID"],
            client_secret=os.environ["DATABRICKS_CLIENT_SECRET"],
        )
        # ... set up MCP clients

    def predict(self, context, model_input: Any, params=None) -> dict:
        # Called on each request
        messages = model_input.get("messages", [])
        question = messages[-1]["content"]
        answer = self._analyze(question)
        return {"choices": [{"message": {"role": "assistant", "content": answer}, "index": 0, "finish_reason": "stop"}], "object": "chat.completion"}

# REQUIRED: Tell MLflow which class is the model
mlflow.models.set_model(DataAnalystAgent())
```

### Deploying to Model Serving

```python
import mlflow
from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedEntityInput

# 1. Log model with ChatCompletion signature
mlflow.set_tracking_uri("databricks")
mlflow.set_registry_uri("databricks-uc")

from mlflow.models.rag_signatures import ChatCompletionRequest, ChatCompletionResponse
from mlflow.models.signature import ModelSignature
from mlflow.types.schema import convert_dataclass_to_schema

signature = ModelSignature(
    inputs=convert_dataclass_to_schema(ChatCompletionRequest),
    outputs=convert_dataclass_to_schema(ChatCompletionResponse),
)

with mlflow.start_run():
    mlflow.pyfunc.log_model(
        name="agent",
        python_model="path/to/agent.py",
        pip_requirements=[...],
        registered_model_name="catalog.schema.model_name",
        signature=signature,
    )

# 2. Create serving endpoint with env vars
ws.serving_endpoints.create(
    name="finserv-data-analyst",
    config=EndpointCoreConfigInput(
        name="finserv-data-analyst",
        served_entities=[
            ServedEntityInput(
                entity_name="catalog.schema.model_name",
                entity_version="1",
                scale_to_zero_enabled=True,
                workload_size="Small",
                environment_vars={
                    "DATABRICKS_HOST": "https://...",
                    "DATABRICKS_CLIENT_ID": "...",
                    "DATABRICKS_CLIENT_SECRET": "...",
                    "DATABRICKS_LLM_ENDPOINT": "databricks-meta-llama-3-3-70b-instruct",
                    "DATABRICKS_CATALOG": "finserv_catalog",
                },
            )
        ],
    ),
)
```

### MCP Client in Databricks Agents

```python
from databricks.sdk import WorkspaceClient
from databricks_mcp import DatabricksMCPClient

ws = WorkspaceClient(host=host, client_id=client_id, client_secret=client_secret)

# URL must not double the https://
base_url = ws.config.host if ws.config.host.startswith("https://") else f"https://{ws.config.host}"

sql_mcp = DatabricksMCPClient(
    server_url=f"{base_url}/api/2.0/mcp/sql",
    workspace_client=ws,
)

# List available tools
tools = sql_mcp.list_tools()  # Returns list of mcp.types.Tool objects
# Tool attributes: .name, .description, .inputSchema

# Call a tool
result = sql_mcp.call_tool("execute_sql", {"query": "SELECT COUNT(*) FROM ..."})
# Returns mcp.types.CallToolResult with .content[].text
```

---

## Authentication Flows

### OAuth M2M (Databricks)

No PATs. The SDK handles everything:

```python
# Set these env vars — the SDK auto-detects OAuth M2M:
# DATABRICKS_HOST=https://workspace.cloud.databricks.com
# DATABRICKS_CLIENT_ID=<application-id>
# DATABRICKS_CLIENT_SECRET=<oauth-secret>

from databricks.sdk import WorkspaceClient
ws = WorkspaceClient()  # Automatically uses OAuth M2M, refreshes tokens

# Under the hood:
# POST https://workspace/oidc/v1/token
# Body: grant_type=client_credentials&scope=all-apis
# Auth: Basic <client_id>:<client_secret>
# Returns: {"access_token": "eyJ...", "expires_in": 3600}
```

For the SQL connector (which doesn't auto-detect):
```python
from databricks.sdk import WorkspaceClient
from databricks import sql as databricks_sql

ws = WorkspaceClient(host=host, client_id=client_id, client_secret=client_secret)
headers = ws.config.authenticate()
token = headers["Authorization"].replace("Bearer ", "")

conn = databricks_sql.connect(
    server_hostname=host.replace("https://", ""),
    http_path=f"/sql/1.0/warehouses/{warehouse_id}",
    access_token=token,  # Short-lived OAuth token
)
```

### SigV4 (AWS → AgentCore Gateway)

```python
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

# Get credentials from explicit session (not default chain)
session = boto3.Session(
    aws_access_key_id=settings.aws.aws_access_key_id,
    aws_secret_access_key=settings.aws.aws_secret_access_key,
    region_name=settings.aws.aws_region,
)
credentials = session.get_credentials().get_frozen_credentials()

# Sign the request
request = AWSRequest(method="POST", url=gateway_url, data=body, headers=headers)
SigV4Auth(credentials, "bedrock-agentcore", region).add_auth(request)
# Service name is "bedrock-agentcore" (not "bedrock" or "execute-api")
```

### Why Explicit Credentials?

In our environment, `AWS_PROFILE=claude-code-DO-NOT-DELETE` is set by the Claude Code runtime, overriding the default credential chain. We bypass this by loading credentials from `.env` and creating an explicit `boto3.Session`:

```python
def get_boto3_session(settings):
    """Bypass environment variable credential chain overrides."""
    if settings.aws.aws_access_key_id:
        return boto3.Session(
            aws_access_key_id=settings.aws.aws_access_key_id,
            aws_secret_access_key=settings.aws.aws_secret_access_key,
            region_name=settings.aws.aws_region,
        )
    return boto3.Session(region_name=settings.aws.aws_region)
```

---

## The Orchestration Loop

### Standard Mode (`agentcore/main.py`)

```python
def run(self, question: str) -> str:
    # 1. Input guardrail
    allowed, reason = check_input_guardrails(question)
    if not allowed:
        return reason  # Blocked immediately

    # 2. Supervisor decomposes (Bedrock Claude)
    plan = self.decompose(question)
    waves = self.supervisor.get_execution_waves(plan)

    # 3. Execute wave by wave
    for wave in waves:
        for subtask in wave:
            if subtask.agent == AgentType.DATA_ANALYST:
                # Call through Gateway MCP → Databricks
                result = self._invoke_gateway_tool(tool_name, task_input)
            elif subtask.agent == AgentType.VALIDATOR:
                # Call through Gateway MCP → Databricks
                result = self._invoke_gateway_tool(tool_name, task_input)
            elif subtask.agent == AgentType.SYNTHESIZER:
                # Call Bedrock directly (no Gateway needed)
                answer = self._invoke_bedrock(SYN_PROMPT, context)
                # Output guardrail
                allowed, reason = check_output_guardrails(answer)
                return answer
```

### Strands SDK Mode (`agentcore/strands/main_strands.py`)

```python
def run_pipeline(question: str) -> str:
    model = BedrockModel(model_id=settings.aws.bedrock_model_id, boto_session=session)
    mcp_client = MCPClient(lambda: streamablehttp_client(gateway_url))

    with mcp_client:
        tools = mcp_client.list_tools_sync()
        agent = Agent(model=model, system_prompt=SUP_PROMPT, tools=tools)

        # ONE call — Claude decides everything autonomously
        response = agent(f"Analyze: {question}")
        return str(response)
```

The Strands SDK agent handles the entire loop internally — it calls tools, reads results, decides if it needs more data, and produces the final answer. No manual wave management.

---

## Guardrails Implementation

### Input Guardrails (`agentcore/config/guardrails.py`)

Pattern-based blocking before any agent executes:

```python
import re

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(previous|prior|all)\s+instructions",
    r"you\s+are\s+now",
    r"system\s+prompt",
    r"forget\s+(your|all)\s+instructions",
]

OFF_TOPIC_PATTERNS = [
    r"write\s+(me\s+)?(a\s+)?(poem|story|song|essay)",
    r"(hack|exploit|attack)\s+",
]

_injection_re = re.compile("|".join(PROMPT_INJECTION_PATTERNS), re.IGNORECASE)
_offtopic_re = re.compile("|".join(OFF_TOPIC_PATTERNS), re.IGNORECASE)

def check_input_guardrails(text: str) -> tuple[bool, str]:
    if _injection_re.search(text):
        return False, "Input blocked: potential prompt injection detected."
    if _offtopic_re.search(text):
        return False, "Input blocked: request is outside the financial analysis domain."
    return True, ""
```

### Output Guardrails

Regex-based PII detection on the final response:

```python
PII_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",           # SSN
    r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",  # Credit card
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
]

def check_output_guardrails(text: str) -> tuple[bool, str]:
    if _pii_re.search(text):
        return False, "Output blocked: potential PII detected in response."
    return True, ""
```

---

## FAQ

### General

**Q: Why not use a single LLM for everything?**
> Different LLMs have different strengths. Claude excels at reasoning, planning, and narrative generation. Llama 70B on Databricks has native access to MCP tools and executes within the governance boundary. Using both gives us the best of each world.

**Q: Why not run all agents on one platform?**
> The Data Analyst and Validator need workspace-internal MCP access (Databricks SQL MCP endpoints are only accessible from within the workspace). Running them on Databricks gives native, governed data access. The Supervisor and Synthesizer don't need data access — they just reason — so Bedrock is ideal.

**Q: What happens if an agent fails?**
> The orchestrator catches exceptions per sub-task and marks them as FAILED. If a critical agent fails (Data Analyst), downstream agents (Validator, Synthesizer) still attempt to run but with limited context. The Synthesizer will note the failure in its output.

**Q: Is this production-ready?**
> The architecture is production-grade (OAuth M2M, managed services, governance). For true production, you'd want: retry logic with exponential backoff, dead-letter queues for failed requests, model fallbacks, latency SLAs, and monitoring dashboards.

---

### Architecture

**Q: What is the AgentCore Gateway actually doing?**
> Three things: (1) aggregating tools from multiple targets into one MCP endpoint, (2) managing OAuth tokens for outbound calls (acquires, caches, refreshes Databricks tokens), and (3) routing MCP tool calls to the correct target based on tool name prefix.

**Q: Why not call Databricks directly (skip the Gateway)?**
> You can — our CLI mode did this initially. The Gateway adds: centralized credential management (you don't handle Databricks tokens in your code), unified MCP endpoint (agents connect to one URL regardless of how many backends), and a layer for future additions (rate limiting, logging, new targets) without code changes.

**Q: What's the difference between AgentCore Gateway and AgentCore Runtime?**
> **Gateway** = MCP tool routing (connects agents to tools/services). **Runtime** = Agent execution environment (runs your agent code). In our architecture, we use Gateway for routing to Databricks, and local Python for agent execution (rather than deploying to Runtime). Full production would use both.

**Q: Can I add more agents?**
> Yes. To add a new Databricks agent: (1) write `agent.py`, (2) deploy via MLflow, (3) register as Gateway target with OpenAPI spec. To add an AWS-side agent: add to the Supervisor's planning prompt and the orchestration loop. ~30 minutes each.

---

### Databricks-Specific

**Q: Why are agent files self-contained (no imports)?**
> Model Serving containers only receive the single file logged via MLflow. They don't have access to your project's directory structure. All dependencies must be in `pip_requirements` and all code in one file.

**Q: Why pass environment variables to serving endpoints?**
> Model Serving containers have no implicit workspace auth (unlike notebooks). The container is isolated — you must explicitly provide credentials. We pass `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`, `DATABRICKS_LLM_ENDPOINT`, and `DATABRICKS_CATALOG` via `ServedEntityInput.environment_vars`.

**Q: What's the `mlflow.models.set_model()` call at the end of agent files?**
> It tells MLflow "this is the model class to instantiate when the serving container starts." Without it, MLflow doesn't know which class to load from the file.

**Q: Why use `ChatCompletionRequest`/`ChatCompletionResponse` signature?**
> The Databricks Agent Framework (`databricks.agents.deploy()`) requires models to declare their input/output format. ChatCompletion is the standard format. Even though we use the SDK directly (not `agents.deploy`), the signature is still required for Unity Catalog model registration.

**Q: How does the SQL MCP server work?**
> Databricks exposes managed MCP servers at workspace-level URLs:
> - SQL: `https://<workspace>/api/2.0/mcp/sql` — executes SQL, returns results
> - UC Functions: `https://<workspace>/api/2.0/mcp/functions/system/ai/python_exec` — runs Python code
>
> These use workspace OAuth for auth. The `DatabricksMCPClient` wraps these endpoints with the MCP protocol (JSON-RPC over HTTPS).

**Q: SQL execution returns `PENDING` with a `statement_id` — why?**
> Long-running queries are asynchronous. The MCP server returns a `statement_id` immediately, and you must call `poll_sql_result` with that ID to get results. Our agent's system prompt instructs the LLM to use this polling pattern.

---

### AWS-Specific

**Q: Why `us.anthropic.claude-sonnet-4-6` and not `anthropic.claude-sonnet-4-6-20250514-v1:0`?**
> The `us.` prefix routes to US-based inference endpoints. The full version-stamped ID (`-20250514-v1:0`) wasn't available/valid in our region. The short form `us.anthropic.claude-sonnet-4-6` is the cross-region inference endpoint that works.

**Q: What IAM permissions are needed?**
> - `bedrock:InvokeModel` — for Bedrock Claude calls
> - `bedrock-agentcore:*` — for Gateway creation and management
> - `iam:CreateRole`, `iam:PassRole` — for Gateway service role
> - `secretsmanager:GetSecretValue` — Gateway role needs this for OAuth secrets

**Q: Why does the Gateway role need Secrets Manager access?**
> When you create an OAuth credential provider, AgentCore stores the client secret in Secrets Manager. The Gateway's IAM role must be able to read this secret to perform token exchange at request time.

**Q: What's SigV4 and why is it needed?**
> AWS Signature Version 4 is how AWS authenticates API calls. The Gateway is an AWS service — it requires SigV4-signed requests (like calling any other AWS API). The service name for signing is `bedrock-agentcore`.

---

### Strands SDK

**Q: What is Strands Agents SDK?**
> An open-source framework (by AWS) for building AI agents. It provides: `Agent` (reasoning loop), `BedrockModel` (LLM integration), and `MCPClient` (MCP tool consumption). It handles tool calling, retries, and multi-turn conversations automatically.

**Q: When should I use Strands vs Standard mode?**
> **Standard** when you need: deterministic execution order, per-step logging, custom retry logic, or explicit control over costs. **Strands** when you want: rapid prototyping, autonomous exploration, or simpler code (50 lines vs 180).

**Q: Does Strands use the same Gateway?**
> Yes. The `MCPClient` in Strands connects to the same Gateway URL. The difference is that Strands handles the `tools/list` → agent reasoning → `tools/call` loop internally, while Standard mode does it manually.

---

### Troubleshooting

**Q: "default auth: cannot configure default credentials" in serving logs**
> The serving container has no implicit auth. Add `environment_vars` with `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET` when creating the endpoint.

**Q: Double `https://` in MCP URL**
> `ws.config.host` already includes `https://`. Check before prepending:
> ```python
> base_url = ws.config.host if ws.config.host.startswith("https://") else f"https://{ws.config.host}"
> ```

**Q: "annotations" field error when calling Databricks LLM**
> The OpenAI response object has extra fields. Don't use `.model_dump()` when passing assistant messages back. Manually construct the message dict:
> ```python
> msg_dict = {
>     "role": "assistant",
>     "content": choice.message.content or "",
>     "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in choice.message.tool_calls],
> }
> ```

**Q: Gateway returns "internal error" in <1 second**
> The Gateway can't acquire an OAuth token. Check: (1) Gateway IAM role has `secretsmanager:GetSecretValue`, (2) Databricks OAuth discovery URL is accessible, (3) client credentials are valid.

**Q: Bedrock throttling ("Too many connections")**
> Rate limit hit. Wait 30 seconds and retry. In production, add exponential backoff. Happens more with concurrent Strands agents holding connections.

---

## Code Navigation Guide

If you want to understand a specific flow, start here:

| I want to understand... | Start at | Then follow to |
|-------------------------|----------|----------------|
| Full pipeline execution | `agentcore/main.py` → `run()` | `_invoke_gateway_tool()` → Gateway → Databricks |
| How agents are deployed | `databricks_agents/deploy_agents.py` → `main()` | `data_analyst/agent.py` |
| Gateway setup | `infrastructure/aws/agentcore_gateway_setup.py` | `agentcore/gateway/targets.py` |
| Configuration flow | `agentcore/config/settings.py` | `.env` → Pydantic → code |
| Guardrails | `agentcore/config/guardrails.py` | Used in `main.py` lines 120, 170 |
| UI streaming | `ui/backend/server.py` → `websocket_query()` | `run_raw_pipeline()` → `send_event()` |
| Strands alternative | `agentcore/strands/main_strands.py` | `run_pipeline()` |
| Data generation | `data/generate_synthetic.py` → `main()` | DDL templates + batch insert |
