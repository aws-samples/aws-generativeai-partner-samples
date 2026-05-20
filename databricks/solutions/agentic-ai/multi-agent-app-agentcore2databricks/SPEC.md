# Multi-Agent Business Analyst for Financial Services

## Reference Architecture Specification

**Version**: 0.4
**Target Platforms**: Amazon Bedrock AgentCore (Gateway + Runtime) + Databricks (Agent Framework + Managed MCP Servers)
**Language**: Python
**Status**: Design Phase — Hybrid Multi-Agent Architecture (AgentCore + Databricks)

---

## 1. Problem Statement

Financial services teams need to answer complex, multi-dimensional business questions that span multiple datasets — portfolio risk exposure, transaction anomalies correlated with market events, customer lifetime value across product lines. Today this requires manual SQL authoring, domain expertise to identify the right tables, and significant effort to validate and synthesize results.

**This system provides**: A team of AI agents (orchestrated via Bedrock AgentCore) that collaboratively decompose, research, execute, validate, and synthesize answers to complex financial business questions — with full governance via Databricks Unity Catalog.

---

## 2. Architecture Overview

### 2.1 Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Agent Placement** | Hybrid — Supervisor + Synthesizer on AgentCore; Data Analyst + Validator on Databricks | Orchestration on AWS, data-plane agents near the data with native MCP access |
| **Databricks Agents** | Deployed via Model Serving (ResponsesAgent) | Exposes OpenAI-compatible REST endpoints callable from anywhere |
| **Data Access** | Databricks agents use Managed MCP Servers (SQL + UC Functions) internally | MCP tools are workspace-internal; agents on Databricks access them natively |
| **Cross-Platform Invocation** | AgentCore Gateway → Databricks Model Serving (OpenAPI target) | Gateway treats Databricks agents as OpenAPI tools; handles auth + routing |
| **Authentication** | OAuth/PAT for Databricks endpoints; IAM for AgentCore | Standard auth on both sides; Unity Catalog enforces data governance |

### 2.2 Hybrid Multi-Agent Architecture

```
┌──────────────────────── AWS ─────────────────────────────────────────────────┐
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │              AMAZON BEDROCK AGENTCORE RUNTIME                           │  │
│  │                                                                         │  │
│  │  ┌──────────────┐                           ┌──────────────┐           │  │
│  │  │  Supervisor  │ Decomposes question,       │ Synthesizer  │           │  │
│  │  │  Agent       │ manages plan, routes       │ Agent        │           │  │
│  │  │  (Claude)    │ to sub-agents              │ (Claude)     │           │  │
│  │  └──────┬───────┘                           └──────────────┘           │  │
│  │         │                                          ▲                    │  │
│  │  [Guardrails] [Memory] [Tracing]                   │ context            │  │
│  └─────────┼──────────────────────────────────────────┼────────────────────┘  │
│            │                                          │                        │
│  ┌─────────v──────────────────────────────────────────┼────────────────────┐  │
│  │              AMAZON BEDROCK AGENTCORE GATEWAY                            │  │
│  │                                                                          │  │
│  │  ┌─────────────────────────────────────┐                                │  │
│  │  │  OpenAPI Targets:                    │                                │  │
│  │  │  - databricks-data-analyst-agent     │  Routes tool calls to          │  │
│  │  │  - databricks-validator-agent        │  Databricks serving endpoints  │  │
│  │  └─────────────────────────────────────┘                                │  │
│  │  [OAuth Credential Mgmt] [Request Routing] [Response Mapping]           │  │
│  └──────────────────────────┬──────────────────────────────────────────────┘  │
│                              │                                                 │
└──────────────────────────────┼─────────────────────────────────────────────────┘
                               │ HTTPS (PAT/OAuth)
                               │ OpenAI-compatible REST API
                               │
┌──────────────────────────────┼───── Databricks on AWS ─────────────────────────┐
│                              ▼                                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │              DATABRICKS MODEL SERVING                                   │    │
│  │                                                                         │    │
│  │  ┌──────────────────────┐          ┌──────────────────────┐            │    │
│  │  │  Data Analyst Agent  │          │  Validator Agent     │            │    │
│  │  │  (ResponsesAgent)    │          │  (ResponsesAgent)    │            │    │
│  │  │                      │          │                      │            │    │
│  │  │  /serving-endpoints/ │          │  /serving-endpoints/ │            │    │
│  │  │  responses           │          │  responses           │            │    │
│  │  └──────────┬───────────┘          └──────────┬───────────┘            │    │
│  │             │                                  │                        │    │
│  └─────────────┼──────────────────────────────────┼────────────────────────┘    │
│                │ MCP (workspace-internal)          │                             │
│                ▼                                   ▼                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │              DATABRICKS MANAGED MCP SERVERS                              │   │
│  │                                                                          │   │
│  │  ┌──────────────────────┐          ┌──────────────────────────────┐     │   │
│  │  │  SQL MCP Server      │          │  UC Functions MCP Server     │     │   │
│  │  │  /api/2.0/mcp/sql    │          │  /api/2.0/mcp/functions/     │     │   │
│  │  │                      │          │  system/ai/python_exec       │     │   │
│  │  │  - Schema discovery  │          │  - Statistical validation    │     │   │
│  │  │  - SQL execution     │          │  - Custom UC functions       │     │   │
│  │  └──────────────────────┘          └──────────────────────────────┘     │   │
│  │                                                                          │   │
│  │  [Unity Catalog Governance] [AI Gateway Monitoring]                      │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  Delta Lake Tables (finserv_catalog) │ SQL Warehouse │ Unity Catalog     │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Cross-Platform Invocation Flow

```
1. User submits question to AgentCore (Supervisor)
       |
       v
2. Supervisor decomposes into sub-tasks, identifies target agents
       |
       v
3. Supervisor invokes Data Analyst (on Databricks) via AgentCore Gateway
   - Gateway has Databricks serving endpoint registered as OpenAPI target
   - Gateway attaches PAT/OAuth token from Secrets Manager
   - Request format: OpenAI-compatible /serving-endpoints/responses
       |
       v
4. Databricks Model Serving receives request
   - Data Analyst agent (ResponsesAgent) activates
   - Agent uses Managed MCP servers internally (SQL + UC Functions)
   - Unity Catalog governs data access
   - AI Gateway logs all tool invocations
       |
       v
5. Databricks agent returns structured response (JSON)
       |
       v
6. AgentCore Gateway maps response back to tool result
       |
       v
7. Supervisor receives result, routes to next agent (Validator or Synthesizer)
```

### 2.4 Authentication Architecture

```
┌─────────────────────────┐              ┌────────────────────────────────────┐
│  AWS Side               │              │  Databricks Side                   │
│                         │              │                                    │
│  IAM Role/User          │              │  Service Principal (SP)            │
│       │                 │              │  + PAT or OAuth M2M token          │
│       v                 │              │       │                            │
│  AgentCore Runtime      │              │       v                            │
│  (Supervisor +          │              │  Model Serving Endpoints           │
│   Synthesizer execute)  │              │  (Data Analyst + Validator)        │
│       │                 │              │       │                            │
│       v                 │              │       v                            │
│  AgentCore Gateway      │── HTTPS ────→│  Endpoint auth (PAT in header)    │
│  (OpenAPI target:       │   (Bearer)   │       │                            │
│   Databricks serving    │              │       v                            │
│   endpoints)            │              │  Agent uses MCP internally         │
│       │                 │              │  (SQL, UC Functions)               │
│       v                 │              │       │                            │
│  AWS Secrets Manager    │              │       v                            │
│  (stores DB PAT/OAuth)  │              │  Unity Catalog ACLs               │
└─────────────────────────┘              └────────────────────────────────────┘
```

**AgentCore Gateway OpenAPI Target Configuration**:
- Target type: OpenAPI
- Endpoint: `https://<workspace>.databricks.com/serving-endpoints/<agent-name>/responses`
- Auth method: Bearer token (PAT from Secrets Manager) or OAuth Client Credentials
- Request schema: OpenAI Responses API format
- Response mapping: Extract agent response content as tool result

**Databricks Side Setup**:
- Create a Service Principal with access to `finserv_catalog`
- Generate a PAT for the SP (or configure OAuth M2M)
- Deploy Data Analyst + Validator as Model Serving endpoints
- Grant CAN_QUERY on serving endpoints to the SP

---

## 3. Agent Definitions

### 3.0 Agent Placement Summary

| Agent | Runs On | Deployment | Invoked Via |
|-------|---------|-----------|-------------|
| Supervisor | **AgentCore Runtime** (AWS) | AgentCore agent definition | User → AgentCore API |
| Data Analyst | **Databricks Model Serving** | ResponsesAgent → MLflow → serving endpoint | AgentCore Gateway → OpenAPI target |
| Validator | **Databricks Model Serving** | ResponsesAgent → MLflow → serving endpoint | AgentCore Gateway → OpenAPI target |
| Synthesizer | **AgentCore Runtime** (AWS) | AgentCore agent definition | Supervisor → internal routing |

---

### 3.1 Supervisor Agent (Orchestrator) — *AgentCore*

**Runs on**: Amazon Bedrock AgentCore Runtime

**Role**: Receives the user question, decomposes it into a plan of sub-tasks, dispatches to specialist agents (both local and remote), and manages the overall workflow.

**Responsibilities**:
- Parse and understand the user's intent
- Decompose complex questions into ordered sub-tasks
- Invoke Databricks-hosted agents (Data Analyst, Validator) via Gateway as tools
- Invoke local Synthesizer agent with accumulated context
- Handle failures and retries
- Enforce timeout and cost budgets

**Tools Available** (registered in AgentCore Gateway):
| Tool | Target | Description |
|------|--------|-------------|
| `invoke_data_analyst` | Databricks Model Serving (OpenAPI) | Send analytical sub-task, receive query results |
| `invoke_validator` | Databricks Model Serving (OpenAPI) | Send results for validation, receive confidence assessment |

**Model**: Claude Sonnet (via Bedrock)

---

### 3.2 Data Analyst Agent — *Databricks*

**Runs on**: Databricks Model Serving (ResponsesAgent)

**Role**: Discovers relevant schema metadata AND executes analytical SQL queries. Has native access to Databricks Managed MCP servers from within the workspace.

**Rationale for running on Databricks**: The Managed MCP servers (SQL, UC Functions) are workspace-internal endpoints. Running this agent on Databricks gives it direct MCP access with full Unity Catalog governance and AI Gateway monitoring.

**Responsibilities**:
- Discover relevant tables via INFORMATION_SCHEMA or SQL MCP schema tools
- Generate and execute Spark SQL for analytical sub-questions
- Use `system.ai.python_exec` for complex computations when SQL isn't sufficient
- Iterate on queries if initial results are incomplete
- Return structured results (SQL used, columns, rows, tables accessed)

**MCP Tools** (accessed internally within Databricks workspace):

From **SQL MCP Server** (`/api/2.0/mcp/sql`):
- Schema introspection, query execution, table stats

From **UC Functions MCP Server** (`/api/2.0/mcp/functions/system/ai/python_exec`):
- Dynamic Python execution for data transformations

**Deployment**:
```python
# Built using Databricks Agent Framework
class DataAnalystAgent(ResponsesAgent):
    # Uses DatabricksMCPClient for SQL + UC Functions
    # Logged via MLflow, deployed to Model Serving
```

**Model**: Claude Sonnet (via Databricks Foundation Model APIs or external model endpoint)

**Endpoint**: `https://<workspace>/serving-endpoints/finserv-data-analyst/responses`

---

### 3.3 Validator Agent — *Databricks*

**Runs on**: Databricks Model Serving (ResponsesAgent)

**Role**: Cross-checks query results for consistency, reasonableness, and accuracy. Has MCP access for running validation queries and statistical checks.

**Rationale for running on Databricks**: Validation often requires running follow-up SQL queries and executing Python-based statistical checks — both available via workspace-internal MCP.

**Responsibilities**:
- Verify results against known constraints (totals sum correctly, values in expected ranges)
- Check for NULL/outlier anomalies
- Cross-reference between multiple result sets for consistency
- Run validation SQL queries via MCP if needed
- Execute statistical checks via `system.ai.python_exec`
- Return confidence level (HIGH/MEDIUM/LOW) with reasoning

**MCP Tools** (accessed internally):
- SQL MCP Server (validation queries)
- UC Functions: `system.ai.python_exec` (pandas-based statistical checks)
- Custom UC functions (e.g., `finserv_catalog.validation.check_bounds`)

**Deployment**:
```python
class ValidatorAgent(ResponsesAgent):
    # Uses DatabricksMCPClient for SQL + python_exec
    # Logged via MLflow, deployed to Model Serving
```

**Model**: Claude Sonnet (via Databricks Foundation Model APIs or external model endpoint)

**Endpoint**: `https://<workspace>/serving-endpoints/finserv-validator/responses`

---

### 3.4 Synthesizer Agent — *AgentCore*

**Runs on**: Amazon Bedrock AgentCore Runtime

**Role**: Assembles all validated sub-task results into a coherent narrative answer with supporting evidence and lineage.

**Rationale for running on AgentCore**: Pure text generation from context — no data access needed. Benefits from AgentCore's guardrails (PII filtering, financial advice disclaimer).

**Responsibilities**:
- Combine sub-task results into a unified narrative
- Generate executive summary + detailed breakdown
- Produce query lineage (which tables/columns → which conclusions)
- Assign overall confidence score
- Suggest follow-up questions
- Append financial advice disclaimer

**Tools Available**: None (text generation only — works from accumulated context)

**Model**: Claude Sonnet (via Bedrock)

---

## 4. Data Flow

```
1. User submits question → AgentCore Supervisor (AWS)
2. Supervisor decomposes into sub-tasks:
   [
     {"id": "st-1", "task": "Query current sector exposure for institutional accounts",
      "agent": "data_analyst", "platform": "databricks", "depends_on": []},
     {"id": "st-2", "task": "Query historical sector exposure (90 days ago)",
      "agent": "data_analyst", "platform": "databricks", "depends_on": []},
     {"id": "st-3", "task": "Validate consistency between current and historical results",
      "agent": "validator", "platform": "databricks", "depends_on": ["st-1", "st-2"]},
     {"id": "st-4", "task": "Synthesize final answer with lineage",
      "agent": "synthesizer", "platform": "agentcore", "depends_on": ["st-3"]}
   ]
3. Supervisor calls invoke_data_analyst tool (x2, in parallel) via Gateway
   → Gateway POSTs to Databricks Model Serving endpoint
   → Data Analyst agent runs on Databricks, uses MCP internally
   → Returns structured results
4. Supervisor calls invoke_validator tool via Gateway
   → Validator agent on Databricks cross-checks results via MCP
   → Returns confidence assessment
5. Supervisor invokes Synthesizer locally on AgentCore
   → Synthesizer generates narrative from accumulated context
6. Final answer returned to user
```

**Cross-platform call sequence** (example for st-1):
```
AgentCore Supervisor
  │
  ├─ Tool call: invoke_data_analyst(task="Query current sector exposure...")
  │       │
  │       ▼
  │   AgentCore Gateway (OpenAPI target)
  │       │
  │       ▼ POST https://<workspace>/serving-endpoints/finserv-data-analyst/responses
  │         Authorization: Bearer <PAT>
  │         Body: {"input": [{"role":"user","content":"<task + context>"}]}
  │       │
  │       ▼
  │   Databricks Model Serving → Data Analyst Agent activates
  │       │
  │       ├─ MCP call: SQL MCP → DESCRIBE finserv_catalog.risk.portfolio_positions
  │       ├─ MCP call: SQL MCP → SELECT sector, SUM(market_value)...
  │       │
  │       ▼
  │   Agent returns: {"output": [{"role":"assistant","content":"<structured result>"}]}
  │       │
  │       ▼
  │   Gateway maps response → tool result for Supervisor
  │
  ▼
Supervisor receives result, continues plan execution
```

---

## 5. Synthetic Dataset: Financial Services Schema

### 5.1 Catalog Structure

```
finserv_catalog
├── core
│   ├── customers
│   ├── accounts
│   └── products
├── transactions
│   ├── trades
│   ├── payments
│   └── transfers
├── risk
│   ├── portfolio_positions
│   ├── market_risk_metrics
│   └── credit_risk_scores
└── reference
    ├── market_sectors
    ├── instruments
    └── exchange_rates
```

### 5.2 Table Definitions

#### `core.customers`
| Column | Type | Description |
|--------|------|-------------|
| customer_id | STRING | Unique customer identifier |
| name | STRING | Customer legal name |
| segment | STRING | RETAIL, HNW, INSTITUTIONAL |
| onboarding_date | DATE | Account opening date |
| risk_tolerance | STRING | CONSERVATIVE, MODERATE, AGGRESSIVE |
| region | STRING | Geographic region |
| kyc_status | STRING | VERIFIED, PENDING, EXPIRED |

#### `core.accounts`
| Column | Type | Description |
|--------|------|-------------|
| account_id | STRING | Unique account identifier |
| customer_id | STRING | FK to customers |
| account_type | STRING | BROKERAGE, RETIREMENT, SAVINGS, MARGIN |
| currency | STRING | ISO 4217 currency code |
| opened_date | DATE | Account creation date |
| status | STRING | ACTIVE, DORMANT, CLOSED |
| balance | DECIMAL(18,2) | Current balance |

#### `core.products`
| Column | Type | Description |
|--------|------|-------------|
| product_id | STRING | Unique product identifier |
| product_name | STRING | Human-readable name |
| product_category | STRING | EQUITY, FIXED_INCOME, DERIVATIVE, FUND |
| risk_rating | INT | 1 (lowest) to 5 (highest) |
| inception_date | DATE | Product launch date |

#### `transactions.trades`
| Column | Type | Description |
|--------|------|-------------|
| trade_id | STRING | Unique trade identifier |
| account_id | STRING | FK to accounts |
| instrument_id | STRING | FK to instruments |
| trade_date | DATE | Execution date |
| trade_type | STRING | BUY, SELL, SHORT, COVER |
| quantity | DECIMAL(18,4) | Number of units |
| price | DECIMAL(18,4) | Price per unit |
| total_value | DECIMAL(18,2) | Total trade value |
| status | STRING | EXECUTED, PENDING, CANCELLED |

#### `transactions.payments`
| Column | Type | Description |
|--------|------|-------------|
| payment_id | STRING | Unique payment identifier |
| account_id | STRING | FK to accounts |
| payment_date | TIMESTAMP | Payment timestamp |
| amount | DECIMAL(18,2) | Payment amount |
| direction | STRING | INBOUND, OUTBOUND |
| payment_method | STRING | WIRE, ACH, CHECK |
| counterparty | STRING | External party name |

#### `risk.portfolio_positions`
| Column | Type | Description |
|--------|------|-------------|
| position_id | STRING | Unique position identifier |
| account_id | STRING | FK to accounts |
| instrument_id | STRING | FK to instruments |
| quantity | DECIMAL(18,4) | Current holding quantity |
| market_value | DECIMAL(18,2) | Current market value |
| cost_basis | DECIMAL(18,2) | Original purchase cost |
| unrealized_pnl | DECIMAL(18,2) | Unrealized profit/loss |
| as_of_date | DATE | Valuation date |
| sector | STRING | Market sector classification |

#### `risk.market_risk_metrics`
| Column | Type | Description |
|--------|------|-------------|
| metric_id | STRING | Unique metric identifier |
| account_id | STRING | FK to accounts |
| metric_date | DATE | Calculation date |
| var_95 | DECIMAL(18,2) | Value at Risk (95% confidence) |
| var_99 | DECIMAL(18,2) | Value at Risk (99% confidence) |
| beta | DECIMAL(8,4) | Portfolio beta |
| sharpe_ratio | DECIMAL(8,4) | Sharpe ratio |
| max_drawdown | DECIMAL(8,4) | Maximum drawdown percentage |
| concentration_score | DECIMAL(8,4) | Sector concentration (0-1) |

#### `risk.credit_risk_scores`
| Column | Type | Description |
|--------|------|-------------|
| score_id | STRING | Unique score identifier |
| customer_id | STRING | FK to customers |
| score_date | DATE | Score calculation date |
| credit_score | INT | Internal credit score (300-850) |
| default_probability | DECIMAL(8,6) | Probability of default |
| exposure_at_default | DECIMAL(18,2) | Estimated exposure at default |
| risk_grade | STRING | AAA through D |

#### `reference.market_sectors`
| Column | Type | Description |
|--------|------|-------------|
| sector_id | STRING | Unique sector identifier |
| sector_name | STRING | Sector display name |
| parent_sector | STRING | Parent sector (for hierarchy) |
| benchmark_index | STRING | Associated benchmark |

#### `reference.instruments`
| Column | Type | Description |
|--------|------|-------------|
| instrument_id | STRING | Unique instrument identifier |
| ticker | STRING | Market ticker symbol |
| instrument_name | STRING | Full name |
| instrument_type | STRING | STOCK, BOND, ETF, OPTION, FUTURE |
| sector_id | STRING | FK to market_sectors |
| currency | STRING | Trading currency |
| exchange | STRING | Trading exchange |

#### `reference.exchange_rates`
| Column | Type | Description |
|--------|------|-------------|
| rate_date | DATE | Rate effective date |
| from_currency | STRING | Source currency |
| to_currency | STRING | Target currency |
| rate | DECIMAL(12,6) | Exchange rate |

---

## 6. Technology Stack

### 6.1 AWS Side (AgentCore)

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Agent Orchestration | Amazon Bedrock AgentCore Runtime | Supervisor + Synthesizer execution, memory, guardrails |
| Tool Routing | Amazon Bedrock AgentCore Gateway | Routes tool calls to Databricks serving endpoints (OpenAPI targets) |
| LLM (AWS agents) | Claude Sonnet via Bedrock | Reasoning for Supervisor planning + Synthesizer narrative |
| Auth Secrets | AWS Secrets Manager | Stores Databricks PAT/OAuth credentials |
| Configuration | Pydantic + environment variables | Typed settings for both platforms |

### 6.2 Databricks Side

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Agent Hosting | Databricks Model Serving | Hosts Data Analyst + Validator as REST endpoints |
| Agent Framework | ResponsesAgent (Databricks Agent Framework) | Agent definition pattern with MCP tool access |
| LLM (DB agents) | Foundation Model APIs or External Model Endpoint | Claude/other model for agent reasoning |
| Data Access | Managed MCP Server — SQL | Schema discovery + SQL execution |
| Data Access | Managed MCP Server — UC Functions | `system.ai.python_exec` + custom functions |
| Governance | Unity Catalog + AI Gateway | Access control, audit logging, monitoring |
| Data Platform | Delta Lake + SQL Warehouse | Storage + query engine |
| Agent Logging | MLflow | Model versioning, experiment tracking, deployment |

### 6.3 Shared / Cross-Platform

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Data Generation | `databricks-sdk` + Faker | One-time synthetic dataset population |
| Agent Client (dev) | `databricks-mcp` + `databricks-openai` | Local testing of Databricks agents |
| Observability | AgentCore traces + AI Gateway logs | End-to-end tracing across platforms |

### 6.4 Integration Pattern: AgentCore Gateway → Databricks Model Serving

AgentCore Gateway registers Databricks serving endpoints as **OpenAPI targets**:

```yaml
# Gateway target definition (conceptual)
targets:
  - name: databricks-data-analyst
    type: openapi
    endpoint: https://<workspace>.databricks.com/serving-endpoints/finserv-data-analyst/responses
    auth:
      type: bearer
      secret_arn: arn:aws:secretsmanager:us-east-1:...:secret/databricks-pat
    operations:
      - name: invoke_data_analyst
        method: POST
        request_schema: {input: [{role: string, content: string}]}
        response_mapping: output[0].content → tool_result

  - name: databricks-validator
    type: openapi
    endpoint: https://<workspace>.databricks.com/serving-endpoints/finserv-validator/responses
    auth:
      type: bearer
      secret_arn: arn:aws:secretsmanager:us-east-1:...:secret/databricks-pat
    operations:
      - name: invoke_validator
        method: POST
        request_schema: {input: [{role: string, content: string}]}
        response_mapping: output[0].content → tool_result
```

**On the Databricks side**, agents are standard ResponsesAgent deployments:

```python
# Data Analyst Agent (runs on Databricks)
from databricks_mcp import DatabricksMCPClient
from databricks.sdk import WorkspaceClient

class DataAnalystAgent(ResponsesAgent):
    def __init__(self):
        ws = WorkspaceClient()
        self.sql_mcp = DatabricksMCPClient(
            server_url=f"https://{ws.config.host}/api/2.0/mcp/sql",
            workspace_client=ws,
        )
        self.python_mcp = DatabricksMCPClient(
            server_url=f"https://{ws.config.host}/api/2.0/mcp/functions/system/ai/python_exec",
            workspace_client=ws,
        )
```

---

## 7. Security and Governance

### 7.1 Access Control (OAuth + Unity Catalog)
- AgentCore Gateway authenticates to Databricks via **OAuth Client Credentials**
- OAuth app registered in Databricks with scopes: `sql`, `unity-catalog`
- Unity Catalog enforces table/column/row-level security on the OAuth identity
- All MCP tool calls are logged via **Databricks AI Gateway** (audit trail)
- OAuth client credentials stored in **AWS Secrets Manager**
- No tokens embedded in agent code

### 7.2 Credential Configuration
```
AWS Secrets Manager (or environment variables for local dev):
  DATABRICKS_HOST              = https://<workspace>.cloud.databricks.com
  DATABRICKS_OAUTH_CLIENT_ID   = <oauth-app-client-id>
  DATABRICKS_OAUTH_CLIENT_SECRET = <oauth-app-client-secret>
  DATABRICKS_WAREHOUSE_ID      = <sql-warehouse-id> (for data generation only)

AgentCore Gateway Target Configuration:
  - Target type: MCP Server
  - Endpoint: https://<workspace>.cloud.databricks.com/api/2.0/mcp/sql
  - Auth: OAuth Client Credentials
  - Scopes: sql, unity-catalog
```

### 7.3 Query Guardrails (Databricks-side)
- Managed MCP SQL server enforces workspace-level query policies
- Unity Catalog permissions limit accessible tables/columns
- AI Gateway provides monitoring, rate limiting, and audit logging
- PII masking via Unity Catalog dynamic views (pre-configured)

### 7.4 AgentCore Guardrails (AWS-side)
- Input guardrail: reject prompt injection attempts
- Output guardrail: no PII in synthesized responses
- Topic guardrail: stay within financial analysis domain
- Content filter: no generation of financial advice (disclaimer required)

### 7.5 Defense in Depth
Both platforms enforce governance independently:
- **AgentCore**: Controls what agents can do (guardrails, tool access)
- **Databricks**: Controls what data is accessible (Unity Catalog, AI Gateway)
- Even if an agent misbehaves, Databricks won't expose unauthorized data

---

## 8. Example Interaction

**User Question**: "What is our total risk exposure to the Technology sector across all institutional accounts, and how has it changed over the last quarter?"

**Supervisor Decomposition**:
1. Schema Explorer: Find tables related to portfolio positions, sector classification, and account types
2. SQL Analyst (parallel):
   - Query current Technology sector exposure for institutional accounts
   - Query Technology sector exposure as of 90 days ago for institutional accounts
3. Validator: Cross-check totals, verify sector classification consistency
4. Synthesizer: Compare current vs. historical, calculate change, generate narrative

**Expected Output**:
```
## Technology Sector Risk Exposure — Institutional Accounts

**Current Exposure**: $2.4B across 847 positions in 12 institutional accounts
**90-Day Prior**: $2.1B across 812 positions
**Change**: +$300M (+14.3%)

### Key Drivers
- Increased allocation to semiconductor equities (+$180M)
- New positions in AI/ML-focused ETFs (+$95M)
- Organic appreciation of existing holdings (+$25M)

### Risk Metrics
- Sector concentration score: 0.34 (moderate, up from 0.29)
- VaR(95) contribution from Tech sector: $48M daily

### Lineage
- Tables used: risk.portfolio_positions, reference.instruments, 
  reference.market_sectors, core.accounts, risk.market_risk_metrics
- Filters applied: segment = 'INSTITUTIONAL', sector = 'Technology'
- Time range: 2026-02-12 to 2026-05-12

**Confidence**: HIGH (all validation checks passed)
```

---

## 9. Project Structure (Planned)

```
hands-on-agentcore-dbx-01/
├── SPEC.md                              # This document
├── README.md                            # Quick-start guide (generated later)
├── pyproject.toml                       # Python project config
│
├── agentcore/                           # ── AWS SIDE (runs on AgentCore) ──
│   ├── agents/
│   │   ├── supervisor.py               # Supervisor agent definition (orchestrator)
│   │   └── synthesizer.py              # Synthesizer agent definition (narrative)
│   ├── gateway/
│   │   └── targets.py                  # OpenAPI target configs for Databricks endpoints
│   ├── config/
│   │   ├── settings.py                 # Pydantic settings (Gateway, Bedrock, secrets)
│   │   └── guardrails.py              # AgentCore guardrail definitions
│   ├── models/
│   │   ├── subtask.py                  # Sub-task + execution plan models
│   │   └── responses.py               # Response models (query result, validation, synthesis)
│   └── main.py                         # Entry point / CLI
│
├── databricks_agents/                   # ── DATABRICKS SIDE (deployed to Model Serving) ──
│   ├── data_analyst/
│   │   ├── agent.py                    # Data Analyst ResponsesAgent implementation
│   │   ├── prompts.py                  # System prompts for schema discovery + SQL
│   │   └── deploy.py                   # MLflow logging + Model Serving deployment
│   ├── validator/
│   │   ├── agent.py                    # Validator ResponsesAgent implementation
│   │   ├── prompts.py                  # System prompts for validation logic
│   │   └── deploy.py                   # MLflow logging + Model Serving deployment
│   └── shared/
│       ├── mcp_clients.py              # DatabricksMCPClient setup (SQL + UC Functions)
│       └── response_format.py          # Shared structured output schemas
│
├── data/
│   ├── generate_synthetic.py           # Synthetic dataset generator (databricks-sdk + Faker)
│   └── uc_functions.sql                # Custom UC function definitions for validation
│
├── infrastructure/
│   ├── aws/
│   │   ├── agentcore_gateway_setup.py  # Register OpenAPI targets in Gateway
│   │   ├── agentcore_agents_setup.py   # Register Supervisor + Synthesizer in Runtime
│   │   └── secrets_setup.py            # Store Databricks PAT in Secrets Manager
│   └── databricks/
│       ├── workspace_setup.py          # Service principal, catalog, permissions
│       ├── model_serving_setup.py      # Create/update serving endpoints
│       └── databricks.yml              # Databricks Asset Bundle config
│
├── tests/
│   ├── test_connectivity.py            # Verify Gateway → Databricks connectivity
│   ├── test_databricks_agents.py       # Test Databricks agents locally
│   ├── test_agentcore_agents.py        # Test AgentCore agents with mocked tools
│   └── test_e2e.py                     # End-to-end integration test
│
└── docs/
    └── architecture.md                 # Detailed diagrams + deployment guide
```

---

## 10. Implementation Phases

### Phase 1: Databricks Foundation
- Create synthetic dataset in Databricks (`finserv_catalog`)
- Register custom UC functions for validation helpers
- Set up Service Principal with appropriate catalog grants
- Verify Managed MCP server access (SQL + UC Functions) from workspace

### Phase 2: Databricks Agents
- Implement Data Analyst agent (ResponsesAgent + MCP clients)
- Implement Validator agent (ResponsesAgent + MCP clients)
- Log agents via MLflow, deploy to Model Serving endpoints
- Test agents locally and via serving endpoint curl calls

### Phase 3: AWS Infrastructure
- Store Databricks PAT in AWS Secrets Manager
- Register Databricks serving endpoints as OpenAPI targets in AgentCore Gateway
- Verify Gateway → Databricks connectivity (tool call → response)

### Phase 4: AgentCore Agents + Orchestration
- Implement Supervisor agent (decomposition + routing via Gateway tools)
- Implement Synthesizer agent (narrative generation)
- Wire full pipeline: Supervisor → Gateway → Databricks agents → Synthesizer
- Test parallel execution of Data Analyst sub-tasks

### Phase 5: Guardrails, Governance, and Polish
- Configure AgentCore guardrails (PII, topic, injection)
- Verify Unity Catalog enforcement (test with restricted permissions)
- Verify AI Gateway audit logs capture all MCP tool calls
- Implement lineage extraction from agent responses
- End-to-end integration tests with multiple question types
- Performance benchmarking (latency per agent, total E2E)
- Documentation and quick-start guide

---

## 11. Resolved Decisions

| # | Question | Decision | Version |
|---|----------|----------|---------|
| 1 | Where do agents run? | ~~All on AgentCore~~ → **Hybrid: Supervisor + Synthesizer on AgentCore, Data Analyst + Validator on Databricks** | v0.4 |
| 2 | Use Databricks AI Dev Kit? | ~~tools-core~~ → **Databricks Agent Framework (ResponsesAgent) + Managed MCP** | v0.4 |
| 3 | Authentication model? | PAT (or OAuth M2M) for cross-platform calls; Unity Catalog for data governance | v0.4 |
| 4 | Integration pattern? | **AgentCore Gateway → Databricks Model Serving (OpenAPI targets)** | v0.4 |
| 5 | Which MCP servers? | SQL + UC Functions (used internally by Databricks-hosted agents) | v0.4 |
| 6 | Agent design? | 4 agents: Supervisor, Data Analyst, Validator, Synthesizer | v0.4 |
| 7 | How does AgentCore invoke Databricks agents? | AgentCore Gateway with OpenAPI target (not Lambda, not direct HTTP) | v0.4 |

## 12. Remaining Open Questions

1. **LLM for Databricks agents**: Should Data Analyst + Validator use Claude via Databricks External Model Endpoint, or a Databricks Foundation Model (DBRX, Llama)?
2. **Streaming vs. synchronous**: Should Databricks serving endpoints return streaming responses, or complete responses? (Gateway compatibility)
3. **Cold start latency**: Model Serving scale-to-zero adds latency. Should we keep endpoints warm for demo?
4. **Agent response format**: Define exact JSON schema for Data Analyst → Supervisor result passing (structured output).
5. **Cost Controls**: What is an acceptable per-query cost budget for the SQL Warehouse?
6. **Error propagation**: How should Databricks agent failures surface to the Supervisor? (HTTP error codes vs. structured error in response body)

---

## 13. Success Criteria

### Cross-Platform Integration
- [ ] AgentCore Gateway successfully invokes Databricks Model Serving endpoints (OpenAPI target works)
- [ ] Databricks-hosted agents (Data Analyst, Validator) respond correctly to AgentCore tool calls
- [ ] PAT/OAuth authentication works end-to-end without manual intervention
- [ ] Round-trip latency for a single cross-platform tool call < 10 seconds

### Agent Functionality
- [ ] A complex multi-hop financial question produces a correct, validated answer
- [ ] At least two Data Analyst sub-tasks execute in parallel (demonstrating orchestration)
- [ ] Validator correctly identifies inconsistencies when introduced
- [ ] Synthesizer produces coherent narrative with accurate lineage

### Governance and Security
- [ ] Unity Catalog governance is respected (permission-denied tables produce auth errors)
- [ ] AgentCore guardrails block prompt injection and off-topic requests
- [ ] Databricks AI Gateway logs show all MCP tool invocations (audit trail)
- [ ] No credentials exposed in agent responses or logs

### Performance
- [ ] Total end-to-end latency < 60 seconds for a 3-subtask question
- [ ] Databricks serving endpoints respond within 15 seconds per invocation

### Demo Value
- [ ] Clearly demonstrates hybrid multi-agent pattern (agents on both platforms)
- [ ] Shows native MCP usage within Databricks agents
- [ ] Shows AgentCore orchestration + guardrails capabilities
- [ ] Both platforms' monitoring/observability visible (AgentCore traces + AI Gateway logs)
