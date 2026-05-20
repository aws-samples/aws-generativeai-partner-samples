# Understanding the Databricks-Hosted Agents

## What Are These "Models"?

When you see `finserv_catalog.agents.data_analyst` and `finserv_catalog.agents.validator` in Unity Catalog, they are **not** trained ML models or fine-tuned LLMs. They are **agent programs** — Python code packaged as MLflow models and deployed to Model Serving containers.

Think of them as:
```
Agent Code (our Python class, packaged via MLflow)
  + calls → databricks-meta-llama-3-3-70b-instruct (foundation model, for reasoning)
  + calls → Databricks Managed MCP Servers (for data access)
```

---

## How the Agent is Composed

### Code Layer (what we wrote)
- `DataAnalystAgent` class extending `mlflow.pyfunc.PythonModel`
- System prompt instructing the LLM how to behave
- Tool integration with Databricks MCP servers
- Response formatting logic

### Foundation Model (what it calls for reasoning)
- `databricks-meta-llama-3-3-70b-instruct` — a pre-existing system endpoint
- Called at runtime via `DatabricksOpenAI` client
- Provides the "thinking" — SQL generation, tool selection, summarization
- Not contained in our model; referenced as an external endpoint

### Data Access (how it queries the lakehouse)
- Databricks SQL MCP Server — for executing SQL and schema discovery
- UC Functions MCP Server — for `system.ai.python_exec` and custom functions
- All governed by Unity Catalog permissions

---

## Where to See Details in the Databricks UI

### Model Registry (what's registered)
1. **Catalog** (left sidebar) → search for `finserv_catalog.agents.data_analyst`
2. Click the model → you'll see **Version 1**
3. Click the version → shows: creation time, source run, input/output signature

### MLflow Experiment & Run (the actual code and artifacts)
1. **Experiments** (left sidebar)
2. Find `/Users/<service-principal-id>/finserv-data-analyst`
3. Click the latest run
4. Go to the **Artifacts** tab — you'll see:
   - `agent.py` — **the actual agent code** (Python class with LLM + MCP logic)
   - `requirements.txt` — pip dependencies installed in the serving container
   - `MLmodel` — MLflow metadata (signature, flavors)
   - `conda.yaml` — environment specification

### Serving Endpoint (how it runs live)
1. **Serving** (left sidebar) → click `finserv-data-analyst`
2. **Overview** tab: entity name, model version, workload size, state
3. **Logs** tab: real-time container logs (useful for debugging)
4. **Metrics** tab: request latency, throughput, error rate

---

## Runtime Flow (what happens when a request arrives)

```
1. Request arrives
   POST /serving-endpoints/finserv-data-analyst/invocations
   Body: {"messages": [{"role": "user", "content": "What is our Tech sector exposure?"}]}

2. Container loads the agent
   agent.py → DataAnalystAgent.load_context()
   → Authenticates to workspace (OAuth M2M via environment variables)
   → Connects to SQL MCP Server

3. Agent processes the request
   DataAnalystAgent.predict() runs:
   → Sends user question + system prompt to databricks-meta-llama-3-3-70b-instruct
   → LLM responds with tool calls (e.g., "execute SQL: SELECT ...")
   → Agent executes the SQL via MCP Server
   → Results fed back to LLM
   → LLM generates final analysis
   → (Loop repeats if LLM needs more data)

4. Response returned
   {"choices": [{"message": {"role": "assistant", "content": "{...structured JSON...}"}}]}
```

---

## Key Distinction: Agent vs. Foundation Model

| | Our Agent (`data_analyst`) | Foundation Model (`llama-3-3-70b`) |
|---|---|---|
| **What it is** | Python program with logic and tools | Pre-trained LLM weights |
| **Where it lives** | `finserv_catalog.agents.data_analyst` (Unity Catalog) | `system.ai.llama_v3_3_70b_instruct` (system endpoint) |
| **Deployed as** | Model Serving endpoint (our code in a container) | System Foundation Model endpoint (Databricks-managed) |
| **Can be modified** | Yes — update code, redeploy | No — use as-is or fine-tune separately |
| **Has tools** | Yes — SQL MCP, python_exec | No — just text in/text out |
| **Knows our data** | Yes — via MCP + Unity Catalog | No — general purpose LLM |

The agent is the **orchestration layer** that gives the foundation model access to our specific data and tools, guided by our system prompt.

---

## Swapping the Foundation Model

To change which LLM the agents use (e.g., switch to Claude via an external model endpoint):

1. Edit the `MODEL_ENDPOINT` variable in the agent `.py` file
2. Redeploy via `.venv/bin/python -m databricks_agents.deploy_agents`

The agent code stays the same — only the model endpoint name changes. This is why we designed it to be parameterized.

---

## Related Files

| File | Purpose |
|------|---------|
| `databricks_agents/data_analyst/agent.py` | Data Analyst agent source code |
| `databricks_agents/validator/agent.py` | Validator agent source code |
| `databricks_agents/deploy_agents.py` | Deployment script (MLflow + Model Serving) |
| `docs/lessons-learned.md` | Troubleshooting deployment issues |
