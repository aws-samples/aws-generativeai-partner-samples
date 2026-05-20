# Building a Cross-Platform Multi-Agent System with Amazon Bedrock AgentCore and Databricks

**A hands-on guide to hybrid agentic AI: orchestrating agents across AWS and Databricks to answer complex financial questions with governance, MCP protocol, and real-time observability.**

---

## The Problem: Intelligent Data Analysis Across Platform Boundaries

Enterprise data lives in lakehouses. AI reasoning lives in foundation model APIs. Governance lives in catalogs and access control layers. These three capabilities rarely exist in one place.

Financial analysts face a specific version of this problem daily. A question like "What is our risk exposure to the Technology sector across institutional accounts?" requires:

1. **Schema discovery** across multiple tables (positions, accounts, customers, sectors)
2. **SQL generation** that correctly joins 4 tables with the right filters
3. **Validation** that the results are consistent and complete
4. **Narrative synthesis** that executives can act on

No single AI model can do all of this. A model that generates SQL cannot execute it. A model that executes queries cannot govern who accesses what. A model in one cloud cannot natively access tools in another.

This guide shows how to solve this by building a **hybrid multi-agent system** where specialized agents on **Amazon Bedrock** and **Databricks** collaborate through **MCP protocol** via **AgentCore Gateway**, with full governance on both sides.

---

## The Solution: 4 Agents, 2 Platforms, 1 Protocol

The system uses 4 specialized agents, each running where it has optimal access to the capabilities it needs:

| Agent | Platform | Model | Role |
|-------|----------|-------|------|
| Supervisor | AWS Bedrock | Claude Sonnet 4.6 | Decomposes questions, plans execution order |
| Data Analyst | Databricks Model Serving | Llama 3.3 70B | Queries the lakehouse via managed MCP servers |
| Validator | Databricks Model Serving | Llama 3.3 70B | Cross-checks results for consistency |
| Synthesizer | AWS Bedrock | Claude Sonnet 4.6 | Generates executive-quality narrative answers |

Claude handles orchestration and synthesis because it excels at planning and narrative. Llama runs on Databricks because it has native MCP access to the SQL engine and Unity Catalog governance. The agents communicate through Amazon Bedrock AgentCore Gateway using MCP (Model Context Protocol), an open standard for connecting AI to tools.

**End-to-end pipeline timing: 60 seconds** from question to validated, sourced narrative with data lineage.

---

## Service Primer: The Building Blocks

### Amazon Bedrock

A fully managed service for accessing foundation models via API. We use the Converse API to call Claude Sonnet 4.6 for the Supervisor (question decomposition) and Synthesizer (narrative generation). Bedrock handles model hosting, scaling, and inference. We pay per token.

### Amazon Bedrock AgentCore Gateway

A managed MCP endpoint that aggregates tools from multiple backends into a single URL. It handles:

- **Tool discovery**: Exposes tools from registered targets via MCP `tools/list`
- **OAuth token exchange**: Acquires and refreshes Databricks tokens automatically
- **Request routing**: Routes MCP `tools/call` to the correct backend target
- **SigV4 authentication**: Secures inbound requests from our agents

Our agents connect to one Gateway URL. The Gateway manages all Databricks authentication behind the scenes.

### Databricks Model Serving

Hosts our Data Analyst and Validator agents as containerized REST endpoints. Each agent is a Python class (MLflow PythonModel) that uses Llama 3.3 70B for reasoning and Databricks Managed MCP servers for data access. Auto-scales to zero when idle.

### Databricks Managed MCP Servers

Workspace-hosted MCP endpoints that Databricks provides:

- **SQL MCP** (`/api/2.0/mcp/sql`): Execute SQL queries against Unity Catalog tables
- **UC Functions MCP** (`/api/2.0/mcp/functions/system/ai/python_exec`): Run arbitrary Python code

These are only accessible from within the workspace, which is why our data-plane agents run on Databricks, not AWS.

### Databricks Unity Catalog

The governance layer. Every query the Data Analyst executes is subject to Unity Catalog's table, column, and row-level security. The service principal has explicit grants on specific catalogs. If an agent tries to access unauthorized data, Unity Catalog blocks it, regardless of what the LLM requests.

---

## Architecture Walkthrough

```
User (Web UI)
    ↓ WebSocket
FastAPI Backend
    ↓
Bedrock Claude (Supervisor) — decomposes question into sub-tasks
    ↓ SigV4
AgentCore Gateway (MCP endpoint) — routes tool calls + manages OAuth
    ↓ OAuth M2M
Databricks Model Serving
    ├── Data Analyst (Llama 70B + SQL MCP) — queries lakehouse
    └── Validator (Llama 70B + SQL MCP + python_exec) — validates results
    ↓
Bedrock Claude (Synthesizer) — generates narrative answer
    ↓
User receives: summary, detailed analysis, lineage, confidence, follow-ups
```

**Data flow for a single question:**

1. User submits "What are the top 3 sectors by market value for institutional accounts?"
2. Input guardrails check for prompt injection and off-topic content
3. Supervisor (Claude) creates an execution plan: query data → validate → synthesize
4. Data Analyst is invoked via Gateway MCP. Gateway exchanges OAuth credentials with Databricks, routes the request to the serving endpoint. The agent uses Llama 70B to write SQL, executes it via SQL MCP, and returns results.
5. Validator is invoked via Gateway MCP. It runs cross-check queries and statistical tests.
6. Synthesizer (Claude) receives validated data and generates a narrative with lineage and confidence.
7. Output guardrails scan for PII before delivery.
8. Answer streams to the user via WebSocket.

**Authentication stack:**

- User → Backend: standard HTTP
- Backend → Gateway: AWS SigV4 (service name: `bedrock-agentcore`)
- Gateway → Databricks: OAuth Client Credentials (managed by Gateway credential provider)
- Databricks agents → MCP servers: workspace-internal OAuth (from env vars)

No static tokens anywhere in the system. All credentials are short-lived and auto-refreshing.

---

## Running the Application

### Prerequisites

- Python 3.11+, Node.js 18+
- Databricks workspace on AWS with admin access
- AWS account with Bedrock (Claude) and AgentCore permissions

### Setup (one-time, ~30 minutes)

```bash
git clone <repo-url> && cd hands-on-agentcore-dbx-01
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # Fill in credentials (see docs/databricks-setup-guide.md)
```

**Generate the financial dataset (11 tables, 23K rows):**
```bash
.venv/bin/python -m infrastructure.databricks.workspace_setup   # Validate connectivity
.venv/bin/python -m data.generate_synthetic                     # Load data
```

**Deploy agents to Databricks Model Serving:**
```bash
.venv/bin/python -m databricks_agents.deploy_agents   # ~5-10 min to provision
```

**Set up AgentCore Gateway:**
```bash
.venv/bin/python -m infrastructure.aws.agentcore_gateway_setup  # Creates Gateway + targets
```

### Run the pipeline

**CLI (Standard agents):**
```bash
.venv/bin/python -m agentcore.main "What are the top 3 sectors by market value?"
```

**CLI (Strands SDK, autonomous):**
```bash
.venv/bin/python -m agentcore.strands.main_strands "What is our Technology sector exposure?"
```

**Web UI with real-time visualization:**
```bash
.venv/bin/python -m ui.backend.server    # Terminal 1: Backend on :8000
cd ui && npm install && npm start         # Terminal 2: Frontend on :3000
```

The web UI (built with AWS Cloudscape Design System) shows each agent step as a clickable box in a horizontal workflow, with platform badges, status animations, and a detail panel. The final answer renders as formatted markdown with styled tables.

---

## Two Modes of Operation

The system supports two orchestration approaches:

**Standard Agents** (180 lines): The orchestrator explicitly controls execution order. It decomposes the question, calls each agent in dependency order, and assembles the result. Developers see exactly what happens at each step.

**Strands SDK Agents** (50 lines): A single Claude agent with access to Gateway MCP tools. Claude autonomously decides which tools to call, in what order, and how many times. The agent may call the Data Analyst multiple times or skip validation if confident. Produces richer output because Claude has full freedom to explore.

Both modes use the same infrastructure: same Gateway, same Databricks agents, same authentication. The difference is who controls the execution flow.

---

## Governance and Security

This system enforces governance at multiple layers:

**Input guardrails** block prompt injection ("ignore previous instructions") and off-topic requests ("write me a poem") before any agent executes. Cost of a blocked request: zero compute.

**Unity Catalog** governs all data access. The service principal has explicit grants on `finserv_catalog`. If we revoke `SELECT` on `risk.credit_risk_scores`, the Data Analyst's queries against that table fail with a permission error, regardless of what the LLM requests.

**Output guardrails** scan the Synthesizer's response for PII patterns (SSN, credit card, email) before delivery to the user.

**OAuth M2M** means no static tokens exist anywhere. Credentials rotate automatically. The Gateway's OAuth provider handles Databricks token lifecycle.

**Audit trail**: AgentCore traces every request. Databricks AI Gateway logs every MCP tool invocation. The complete chain is observable.

---

## Business Value

**For financial services teams**: Analysts get validated, sourced answers to complex multi-table questions in 60 seconds instead of 30 minutes of manual SQL, cross-checking, and report writing.

**For platform teams**: A reference architecture for cross-cloud agent collaboration. Deploy the pattern once; add new agents (fraud detection, compliance checks, market analysis) by writing one Python file and registering a Gateway target.

**For governance teams**: AI accessing data through governed channels with full lineage. Every query auditable. Every response checked for PII. Unity Catalog enforces the same access policies whether a human or an agent runs the query.

**Cost structure**: ~$0.01-0.03 per question for Bedrock Claude tokens. Databricks compute only when agents are invoked (scale-to-zero). Gateway is serverless with no idle cost. A complex 3-agent query costs less than $0.10 total.

---

## Key Technical Decisions and Trade-offs

**Why hybrid (not all-AWS or all-Databricks)?** Each platform has strengths that cannot be replicated on the other. Databricks MCP servers are workspace-internal; you cannot call them from outside. Claude's reasoning quality exceeds open models for orchestration tasks. Running data-plane agents next to the data eliminates network hops for SQL execution.

**Why MCP protocol?** It is an open standard for tool connectivity. AgentCore Gateway speaks MCP natively. Databricks exposes managed MCP servers. Using MCP means we avoid vendor-specific tool formats and can swap components without rewriting integration code.

**Why OAuth M2M instead of PATs?** PATs are static, long-lived, and create blast radius if leaked. OAuth M2M tokens expire in 1 hour and refresh automatically. The Databricks SDK handles the token lifecycle with zero application code.

**Why Llama 70B on Databricks (not Claude)?** At time of implementation, Claude was not available as a Databricks Foundation Model endpoint. The architecture is parameterized: changing `DATABRICKS_LLM_ENDPOINT` in `.env` and redeploying swaps the model without code changes.

---

## Conclusion

This reference architecture demonstrates that multi-agent AI systems do not need to live on a single platform. By combining Amazon Bedrock's reasoning capabilities with Databricks' governed data access, and connecting them through standard MCP protocol via AgentCore Gateway, we built a system where:

- Each agent runs where it has optimal capabilities
- All data access is governed and auditable
- Authentication is secure and automatic
- The system is observable in real-time
- Adding new agents takes 30 minutes, not weeks

The complete codebase is open and parameterized. Clone it, configure your credentials, and run a query against your own data in under an hour.

---

## Resources

- [Full codebase and documentation](.)
- [Databricks setup guide](docs/databricks-setup-guide.md)
- [Lessons learned (21 deployment pitfalls)](docs/lessons-learned.md)
- [Standard vs. Strands SDK comparison](docs/strands-sdk-comparison.md)
- [Demo script for presentations](docs/demo-script.md)
- [Knowledge base and FAQ](docs/knowledge-base.md)
