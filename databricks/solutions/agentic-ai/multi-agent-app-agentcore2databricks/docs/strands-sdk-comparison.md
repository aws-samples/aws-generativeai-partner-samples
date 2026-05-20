# Strands SDK vs Raw Implementation Comparison

This project includes two implementations of the same multi-agent pipeline:
1. **Raw version** (`agentcore/main.py`) — direct boto3 + requests + manual orchestration
2. **Strands SDK version** (`agentcore/strands/main_strands.py`) — using Strands Agents framework

Both produce the same result: a multi-agent financial analyst that routes through AgentCore Gateway to Databricks.

---

## Architecture (same for both)

```
User → Supervisor (Bedrock Claude)
         → AgentCore Gateway (MCP, SigV4)
             → Data Analyst (Databricks)
             → Validator (Databricks)
         → Synthesizer (Bedrock Claude)
         → Answer
```

---

## Side-by-Side Code Comparison

### Initializing the LLM

**Raw:**
```python
import boto3
session = get_boto3_session(settings)
bedrock = session.client("bedrock-runtime")

# Call LLM
response = bedrock.converse(
    modelId="us.anthropic.claude-sonnet-4-6",
    messages=[{"role": "user", "content": [{"text": prompt}]}],
    system=[{"text": system_prompt}],
)
text = response["output"]["message"]["content"][0]["text"]
```

**Strands:**
```python
from strands import Agent
from strands.models import BedrockModel

model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-6",
    region_name="us-west-2",
    boto_session=session,
)
agent = Agent(model=model, system_prompt=system_prompt)

# Call LLM
response = agent(prompt)
text = str(response)
```

---

### Connecting to AgentCore Gateway (MCP tools)

**Raw:**
```python
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

gateway_url = f"https://{gateway_id}.gateway.bedrock-agentcore.{region}.amazonaws.com/mcp"

# Manual MCP JSON-RPC call
payload = {
    "jsonrpc": "2.0",
    "id": "1",
    "method": "tools/call",
    "params": {
        "name": "databricks-finserv-data-analyst___invoke_finserv_data_analyst",
        "arguments": {"messages": [{"role": "user", "content": task}]},
    },
}

request = AWSRequest(method="POST", url=gateway_url, data=json.dumps(payload),
                     headers={"Content-Type": "application/json"})
SigV4Auth(credentials, "bedrock-agentcore", region).add_auth(request)

resp = requests.post(gateway_url, data=json.dumps(payload), headers=dict(request.headers))
result = resp.json()["result"]["content"][0]["text"]
```

**Strands:**
```python
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

gateway_url = f"https://{gateway_id}.gateway.bedrock-agentcore.{region}.amazonaws.com/mcp"
mcp_client = MCPClient(lambda: streamablehttp_client(gateway_url))

with mcp_client:
    tools = mcp_client.list_tools_sync()
    agent = Agent(model=model, system_prompt=system_prompt, tools=tools)
    response = agent("Query the customers table")  # Agent calls tools automatically
```

---

### Full Pipeline Orchestration

**Raw (agentcore/main.py):**
```python
class MultiAgentOrchestrator:
    def run(self, question):
        # 1. Supervisor decomposes (manual LLM call)
        plan = self.decompose(question)
        waves = self.supervisor.get_execution_waves(plan)

        # 2. Execute each wave manually
        for wave in waves:
            for subtask in wave:
                if subtask.agent == AgentType.DATA_ANALYST:
                    result = self._invoke_gateway_tool(tool_name, task_input)
                elif subtask.agent == AgentType.VALIDATOR:
                    result = self._invoke_gateway_tool(tool_name, task_input)
                elif subtask.agent == AgentType.SYNTHESIZER:
                    answer = self._invoke_bedrock(SYN_PROMPT, context)
                    return answer
```

**Strands (agentcore/strands/main_strands.py):**
```python
def run_pipeline(question):
    model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-6", boto_session=session)
    mcp_client = MCPClient(lambda: streamablehttp_client(gateway_url))

    with mcp_client:
        tools = mcp_client.list_tools_sync()
        supervisor = Agent(model=model, system_prompt=SUP_PROMPT, tools=tools)

        # ONE CALL — the agent handles decomposition + tool calling + synthesis
        response = supervisor(f"Analyze: {question}")
        return str(response)
```

---

## Key Differences

| Aspect | Raw | Strands SDK |
|--------|-----|-------------|
| **Lines of code** | ~180 (main.py) | ~50 (core logic) |
| **Tool calling** | Manual JSON-RPC + SigV4 signing | Automatic via MCPClient |
| **Multi-turn reasoning** | Manual wave execution loop | Agent handles internally |
| **Error handling** | Manual per-subtask try/except | Agent retries automatically |
| **Decomposition** | Separate LLM call + JSON parsing | Agent decides tool order itself |
| **Auth** | Manual SigV4Auth + credential management | Handled by MCPClient transport |
| **Dependencies** | boto3, requests, botocore | strands-agents, strands-agents-tools, mcp |

---

## When to Use Which

**Use Raw (agentcore/main.py) when:**
- You need full control over execution order
- You want to log/trace each step explicitly
- You need custom retry/timeout logic per agent
- Educational/demo purposes (shows exactly what's happening)
- You want to avoid additional SDK dependencies

**Use Strands SDK (agentcore/strands/main_strands.py) when:**
- Production deployment
- You want the LLM to decide tool calling order dynamically
- Cleaner, more maintainable code
- You want built-in tool error handling and retries
- Rapid prototyping of new agent patterns

---

## Running the Strands Version

```bash
# Install Strands SDK
.venv/bin/pip install strands-agents strands-agents-tools

# Run
.venv/bin/python -m agentcore.strands.main_strands "How many customers do we have?"
```

## Test Results (Verified Working)

The Strands version was tested end-to-end on 2026-05-19:

- **Question**: "How many customers are in the finserv_catalog.core.customers table?"
- **Result**: Comprehensive report with 500 customers confirmed, schema analysis, confidence scoring
- **Time**: ~2.5 minutes (includes two Databricks round-trips through Gateway)
- **Gateway calls**: 2 (Data Analyst + Validator, both via MCP protocol)
- **Key difference**: Claude autonomously decided the tool calling order — no manual wave/dependency management needed

The Strands agent produced a **significantly richer output** than the raw version because Claude had full control over the reasoning loop and could ask follow-up questions to the tools.

---

## File Layout

```
agentcore/
├── main.py                      # Raw version (production, working)
├── strands/
│   ├── __init__.py
│   └── main_strands.py          # Strands SDK version (same pipeline)
├── agents/
│   ├── supervisor.py            # System prompts (shared by both versions)
│   └── synthesizer.py           # System prompts (shared by both versions)
├── config/
│   ├── settings.py              # Shared settings (shared by both versions)
│   └── guardrails.py            # Shared guardrails (shared by both versions)
└── models/
    ├── subtask.py               # Used by raw version for execution planning
    └── responses.py             # Shared response models
```
