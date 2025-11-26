# RIV Metadata AI - Intelligent Multi-Source Orchestrator with PLAN-AND-ACT

A sophisticated AI-powered orchestrator implementing the **PLAN-AND-ACT pattern** with metadata-driven routing and continuous re-planning, designed for deployment on AWS Bedrock AgentCore runtime service.

## Overview

RIV Metadata AI uses the PLAN-AND-ACT methodology to intelligently execute queries across multiple data sources (Aurora PostgreSQL and OpenSearch). The system continuously re-plans after each execution step, adapting to actual results for maximum accuracy and flexibility.

### 🚀 PLAN-AND-ACT Pattern

Based on research from "PLAN-AND-ACT: Improving Planning of Agents for Long-Horizon Tasks" (Erdogan et al. 2025), our implementation features:

- **Continuous Re-planning**: Plan is updated after EVERY execution step
- **Adaptive Execution**: Adjusts strategy based on actual observations
- **Goal-Oriented**: Planner determines when goal is complete
- **Metadata-Driven**: Uses schema introspection for intelligent routing

## Key Features

### 🎯 **LLM-Powered Routing**
- **Intelligent Source Selection**: Uses AWS Bedrock Nova Pro to analyze queries and select optimal data source
- **Schema-Aware**: Considers actual database tables, columns, and indices from all sources
- **Context-Rich Decisions**: LLM evaluates capabilities, entities, and fields for accurate routing
- **High Confidence**: AI-powered routing eliminates manual keyword matching

### 🤖 **Agent-as-a-Tool Pattern**
- **Specialized Agents**: Aurora agent with Bedrock-powered natural language to SQL translation
- **Modular Architecture**: Easy to add new specialized agent tools
- **Standalone Testing**: Each agent can be tested independently

### 🔄 **Multi-Source Support**
- **Aurora PostgreSQL**: Structured relational data with SQL queries
- **OpenSearch**: Full-text search and document retrieval
- **S3 Tables**: S3 object metadata for file and image tracking
- **Extensible**: Framework supports adding additional data sources

### 💡 **Natural Language Processing**
- **Bedrock Integration**: AI-powered SQL generation from natural language
- **Schema-Aware**: Understands your specific table structures
- **Query Validation**: Validates generated SQL before execution
- **Translation Details**: Provides explanation of query translation

## Architecture

### PLAN-AND-ACT Execution Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator (PLAN-AND-ACT)                  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  EXECUTION LOOP                            │ │
│  │                                                            │ │
│  │  ┌──────────┐     ┌──────────┐     ┌──────────┐         │ │
│  │  │ Planner  │────▶│ Executor │────▶│ Observe  │         │ │
│  │  │  Agent   │     │  Agent   │     │ Results  │         │ │
│  │  │(Nova Pro)│     │          │     │          │         │ │
│  │  └──────────┘     └──────────┘     └──────────┘         │ │
│  │       ▲                                    │              │ │
│  │       │         Re-plan after              │              │ │
│  │       └────────────EVERY step──────────────┘              │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │         MetadataAnalyzer (LLM-Based Routing)               │ │
│  │  • Bedrock Nova Pro routing • Schema-aware decisions       │ │
│  │  • Multi-source intelligence • Confidence scoring          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                    │
│          ┌──────────────────┴────────────────────────┐           │
│          ↓                   ↓                        ↓           │
│   ┌──────────────┐    ┌──────────────┐      ┌──────────────┐   │
│   │ Aurora Agent │    │  OpenSearch  │      │  S3 Tables   │   │
│   │              │    │    Agent     │      │    Agent     │   │
│   │ • NL→SQL     │    │ • Search DSL │      │ • S3 Queries │   │
│   │ • Schema     │    │ • Full-text  │      │ • Object     │   │
│   │ • Bedrock    │    │ • Documents  │      │   Metadata   │   │
│   └──────────────┘    └──────────────┘      └──────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Component Overview

**PlannerAgent** (`planner.py`)
- Creates initial full plan using MetadataAnalyzer + Bedrock Nova Pro
- Re-plans after EVERY execution step based on observations
- Determines when goal is complete
- Handles multi-step and cross-source queries

**ExecutorAgent** (`executor.py`)
- Executes ONE step at a time
- Routes to Aurora or OpenSearch agents
- Returns detailed observations for re-planning
- Does not self-assess goal completion

**MetadataAnalyzer** (`metadata_analyzer.py`)
- Provides intelligent source recommendations
- Schema introspection and entity matching
- LLM-enhanced routing decisions
- Confidence scoring for transparency

## PLAN-AND-ACT Execution Flow

### Simple Single-Source Query

```
User Query: "Show me all customers from Aurora"

Step 1: Initial Planning
  Planner analyzes query and metadata
  → Creates 1-step plan: Query Aurora customers table
  
Step 2: Execute
  Executor runs: SELECT * FROM customers
  → Observation: 150 rows retrieved in 80ms
  
Step 3: Re-plan
  Planner sees goal achieved
  → Returns empty steps array (complete)
  
Result: 150 customer records ✓
```

### Complex Multi-Source Query

```
User Query: "Get top 10 products from Aurora and their reviews from OpenSearch"

Iteration 1:
  Plan: Query all products from Aurora
  Execute: SELECT * FROM products ORDER BY sales DESC
  Observe: 500 products found
  Re-plan: Filter to top 10 only

Iteration 2:
  Plan: Get top 10 best-selling products  
  Execute: SELECT * FROM products ORDER BY sales DESC LIMIT 10
  Observe: 10 products with IDs [101, 203, 405...]
  Re-plan: Search OpenSearch for reviews using product IDs

Iteration 3:
  Plan: Search reviews for product IDs
  Execute: OpenSearch query with product_id filter
  Observe: 87 reviews found across all products
  Re-plan: Goal complete (empty steps)

Result: 10 products + 87 reviews aggregated ✓
Total time: 450ms across 3 steps
Sources used: Aurora, OpenSearch
```

### Adaptive Re-planning Example

```
User Query: "Show recent orders"

Iteration 1:
  Plan: Query orders table
  Execute: SELECT * FROM orders WHERE order_date > NOW() - INTERVAL '7 days'
  Observe: 0 rows (no recent orders)
  Re-plan: Expand timeframe to 30 days

Iteration 2:
  Plan: Query orders with wider timeframe
  Execute: SELECT * FROM orders WHERE order_date > NOW() - INTERVAL '30 days'
  Observe: 42 orders found
  Re-plan: Goal achieved

Result: 42 orders from last 30 days ✓
```

## Long-Term Memory (Optional)

The agent supports **AWS Bedrock AgentCore Memory** for learning across conversations. Memory is optional and controlled by environment variables.

### What Gets Remembered

**User Preferences:**
- Preferred data sources (Aurora vs OpenSearch)
- Common query patterns
- Output format preferences

**Semantic Facts:**
- Table and field mappings learned from queries
- Relationships between tables
- Business rules and patterns

**Session Summaries:**
- High-level summaries of multi-step query sessions
- Key decisions and results from past interactions

### Setup Instructions

#### Step 1: Create Memory Resource (One-Time)

Use the AWS CLI to create the memory resource with all three built-in strategies:

```bash
# Set your region
export AWS_REGION=us-east-1

# Create memory with all strategies
aws bedrock-agentcore-control create-memory \
    --name "RIVMetadataAIMemory" \
    --description "Long-term memory for RIV Metadata AI Agent" \
    --strategies '[
        {
            "summaryMemoryStrategy": {
                "name": "SessionSummarizer",
                "description": "Summarizes conversation sessions",
                "namespaces": ["/summaries/{actorId}/{sessionId}"]
            }
        },
        {
            "userPreferenceMemoryStrategy": {
                "name": "PreferenceLearner",
                "description": "Learns user preferences",
                "namespaces": ["/preferences/{actorId}"]
            }
        },
        {
            "semanticMemoryStrategy": {
                "name": "FactExtractor",
                "description": "Extracts factual information",
                "namespaces": ["/facts/{actorId}"]
            }
        }
    ]' \
    --region $AWS_REGION
```

**Save the Memory ID** from the output and wait for status to become `ACTIVE` (2-3 minutes):

```bash
aws bedrock-agentcore-control get-memory \
    --memory-id mem-abc123def456 \
    --region $AWS_REGION
```

#### Step 2: Configure Environment Variables

Add to your environment:

```bash
# Required: Your memory resource ID
export AGENTCORE_MEMORY_ID=mem-abc123def456

# Optional: Actor/User ID (defaults to "default_user")
export AGENTCORE_ACTOR_ID=user_12345
```

#### Step 3: Deploy

The agent will automatically enable memory when `AGENTCORE_MEMORY_ID` is set:

```bash
./deploy.sh
```

### How Memory Works

```
User Query
    ↓
Orchestrator
    ↓
PlannerAgent (with AgentCore Memory Session Manager)
    ↓
AWS Bedrock AgentCore Memory
    ├── Short-term: Conversation history
    └── Long-term: 3 strategies
        ├── Preferences: Query patterns
        ├── Semantic: Table/field facts
        └── Summary: Session summaries
    ↓
Query Planning (informed by memory)
```

**Memory is automatic:**
- ✅ Conversations stored automatically
- ✅ Insights extracted asynchronously
- ✅ Relevant memory retrieved on each query
- ✅ Agent learns and improves over time

### Disabling Memory

To disable memory, unset the environment variable:

```bash
unset AGENTCORE_MEMORY_ID
```

The agent will continue working with session-only memory.

### Verify Memory

```bash
# Check memory status
aws bedrock-agentcore-control get-memory \
    --memory-id $AGENTCORE_MEMORY_ID \
    --region $AWS_REGION

# List memory records
aws bedrock-agentcore-control list-memory-records \
    --memory-id $AGENTCORE_MEMORY_ID \
    --namespace "/preferences/user_12345" \
    --max-results 10 \
    --region $AWS_REGION
```

## How It Works

### 1. LLM-Powered Source Selection

**RIV Approach (LLM-Based Routing):**
```python
# LLM analyzes query with full context
user_query = "Show me all customers"

# LLM receives metadata from all sources:
aurora_metadata = {
    "entities": ["customers", "orders", "products"],
    "fields": ["customer_id", "customer_name", "order_date"],
    "capabilities": ["sql_queries", "joins", "aggregations"]
}

opensearch_metadata = {
    "entities": ["web_logs"],
    "fields": ["timestamp", "ip", "method", "url"],
    "capabilities": ["full_text_search", "log_analysis"]
}

s3tables_metadata = {
    "entities": ["journal", "inventory"],
    "fields": ["bucket", "key", "size", "object_tags"],
    "capabilities": ["s3_metadata", "object_metadata"]
}

# LLM Decision (Bedrock Nova Pro):
{
    "source": "aurora",
    "confidence": 0.95,
    "reasoning": "Query asks for customers table which exists in Aurora"
}
```

### 2. Agent Tool Execution Flow

```
User Query: "Show customers who ordered last month"
                    ↓
      [Metadata Analyzer Introspects Schema]
                    ↓
      Aurora has "customers" table ✓
      Aurora has "orders" table ✓
      Confidence: 0.85 → Route to Aurora
                    ↓
      [Aurora Agent Tool Receives Request]
                    ↓
      Schema Provider → Get table structures
      SQL Generator (Bedrock) → Generate SQL:
        SELECT c.* FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        WHERE o.order_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
                    ↓
      Validate SQL → Execute → Return Results
```

## Project Structure

```
src/
├── orchestrator/
│   ├── __init__.py
│   ├── agent.py                 # Main orchestrator with PLAN-AND-ACT
│   ├── planner.py               # PlannerAgent - creates and re-plans
│   ├── executor.py              # ExecutorAgent - executes steps
│   ├── metadata_analyzer.py    # MetadataAnalyzer - intelligent routing
│   ├── aurora_agent.py          # Specialized Aurora agent (NL to SQL)
│   ├── opensearch_agent.py      # Specialized OpenSearch agent
│   ├── models.py                # Pydantic models (ExecutionPlan, etc.)
│   ├── database.py              # Database utilities
│   └── ui.py                    # Streamlit interface
│
├── sources/
│   ├── base.py                  # Abstract base for data sources
│   ├── aurora/
│   │   ├── __init__.py
│   │   ├── source.py            # Aurora data source with metadata
│   │   ├── connection.py        # Aurora connection management
│   │   ├── schema_provider.py  # Schema introspection
│   │   └── sql_generator.py    # Bedrock-powered SQL generation
│   │
│   └── opensearch/
│       ├── __init__.py
│       ├── source.py            # OpenSearch data source
│       └── client.py            # OpenSearch client wrapper
│
cdk/
├── app.py                       # CDK app entry point
└── aurora_opensearch_stack.py   # Infrastructure as code

scripts/
└── deploy.sh                    # Deployment script

.bedrock_agentcore.yaml          # AgentCore configuration
```

### Key Files

**PLAN-AND-ACT Core:**
- `orchestrator/planner.py` - Creates plans, re-plans after each step
- `orchestrator/executor.py` - Executes one step at a time
- `orchestrator/metadata_analyzer.py` - Intelligent source selection

**Agents:**
- `orchestrator/aurora_agent.py` - Natural language to SQL translation
- `orchestrator/opensearch_agent.py` - Search query execution

**Data Sources:**
- `sources/aurora/` - Aurora PostgreSQL integration
- `sources/opensearch/` - OpenSearch Serverless integration

## Quick Start

### Prerequisites

```bash
# Python 3.11+
pip install -e .

# AWS credentials configured
aws configure

# Environment variables
export AURORA_CLUSTER_ARN="arn:aws:rds:region:account:cluster:cluster-name"
export AURORA_SECRET_ARN="arn:aws:secretsmanager:region:account:secret:secret-name"
export OPENSEARCH_ENDPOINT="https://collection-id.region.aoss.amazonaws.com"
```

### Local Development

1. **Run Main Orchestrator:**
   ```bash
   python -m src.orchestrator.agent
   ```

2. **Test Aurora Agent Standalone:**
   ```bash
   python -m src.orchestrator.aurora_agent
   ```

3. **Run with Streamlit UI:**
   ```bash
   streamlit run src/orchestrator/ui.py
   ```

4. **Test AgentCore Integration:**
   ```bash
   python test_agentcore.py
   ```

### AWS Deployment

Deploy complete infrastructure with CDK:

```bash
./deploy.sh
```

This creates:
- Aurora PostgreSQL Serverless v2 cluster with Data API
- OpenSearch Serverless collection
- AgentCore deployment with auto-scaling
- Necessary IAM roles and security groups

## Usage Examples

### Natural Language Queries (Aurora)

```python
# Query gets routed to Aurora agent tool automatically
queries = [
    "Show me all customers",
    "Count orders by month",
    "Find customers who ordered in the last week",
    "What are the top selling products?"
]

# Agent automatically:
# 1. Routes to Aurora (high schema match confidence)
# 2. Generates SQL using Bedrock LLM
# 3. Validates syntax
# 4. Executes query
# 5. Returns results with translation details
```

### Search Queries (OpenSearch)

```python
# Query gets routed to OpenSearch automatically
queries = [
    "Search for documents about machine learning",
    "Find similar content to this article",
    "Full text search for customer feedback"
]

# Orchestrator:
# 1. Routes to OpenSearch (low Aurora schema match)
# 2. Translates to OpenSearch DSL
# 3. Executes search
# 4. Returns document results
```

### Metadata Queries

```python
# Get source metadata
metadata = await orchestrator.get_source_metadata()

# Returns:
{
    "aurora": {
        "entities": ["customers", "orders", "products"],
        "fields": ["customer_id", "order_date", "product_name"],
        "data_types": {"customers.customer_id": "integer"},
        "capabilities": ["sql_queries", "joins", "aggregations"]
    },
    "opensearch": {
        "entities": ["documents", "logs"],
        "fields": ["content", "timestamp", "category"],
        "capabilities": ["full_text_search", "fuzzy_matching"]
    },
    "s3tables": {
        "entities": ["journal", "inventory"],
        "fields": ["bucket", "key", "size", "object_tags"],
        "capabilities": ["s3_metadata", "object_metadata", "file_metadata"]
    }
}
```

## Routing Intelligence

### LLM-Based Routing Decision

The system uses AWS Bedrock Nova Pro to make intelligent routing decisions based on:
- **Query Intent**: What the user is trying to accomplish
- **Source Capabilities**: What each data source can do
- **Schema Information**: Available entities and fields in each source
- **Context**: Previous query patterns and results

### Example Routing Decision

```
Query: "Show customer orders"

LLM receives metadata:
  Aurora: tables=[customers, orders], fields=[customer_id, order_date]
  OpenSearch: indices=[web_logs], fields=[timestamp, ip, method]
  S3 Tables: entities=[journal, inventory], fields=[bucket, key, size]

LLM Decision:
{
  "source": "aurora",
  "confidence": 0.95,
  "reasoning": "Query asks for customer orders which are structured data 
                in Aurora's customers and orders tables. Aurora supports 
                joins and relational queries needed for this request."
}

Decision: Route to Aurora Agent ✓
```

### Fallback Behavior

If LLM routing fails:
- System defaults to Aurora as safe fallback
- Logs warning for monitoring
- Confidence set to 0.5 (moderate)

## Configuration

### AgentCore Configuration (.bedrock_agentcore.yaml)

```yaml
runtime: python:3.11
handler: src.orchestrator.agent:invoke
auto_scaling:
  min_replicas: 1
  max_replicas: 3
resources:
  memory: 2048Mi
  cpu: 1000m
secrets:
  - aurora-agent-config
```

### Environment Variables

**Aurora Configuration:**
- `AURORA_CLUSTER_ARN`: Aurora cluster ARN for Data API
- `AURORA_SECRET_ARN`: Secrets Manager ARN for credentials
- `AURORA_ENDPOINT`: Database endpoint (fallback)

**OpenSearch Configuration:**
- `OPENSEARCH_ENDPOINT`: OpenSearch Serverless endpoint
- `AWS_REGION`: AWS region for services

## Testing

### Unit Tests
```bash
pytest tests/
```

### Integration Tests
```bash
# Test orchestrator routing
python -m pytest tests/test_orchestrator.py

# Test Aurora agent standalone
python -m pytest tests/test_aurora_agent.py

# Test metadata analyzer
python -m pytest tests/test_metadata_analyzer.py
```

### Manual Testing
```bash
# Test with sample queries
curl -X POST http://localhost:8080/invoke \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Show me all customers"}'
```

## Advanced Features

### Custom Agent Tools

Add new specialized agents:

```python
class CustomAgentTool(Agent):
    async def process_request(self, request: AgentRequest) -> AgentResponse:
        # Custom processing logic
        pass

# Register in orchestrator
orchestrator.custom_agent_tool = CustomAgentTool(config)
```

### Metadata Caching

Metadata is cached for performance:
```python
# Force metadata refresh
await orchestrator.metadata_analyzer._metadata_cache.clear()
await orchestrator.get_source_metadata()
```

### Custom Routing Logic

Extend MetadataAnalyzer for custom LLM prompts:
```python
class CustomMetadataAnalyzer(MetadataAnalyzer):
    async def _llm_route_decision(self, request, aurora_meta, opensearch_meta, s3tables_meta):
        # Custom LLM prompt for routing
        # Modify the prompt to include additional context
        return source_type, confidence
```

## Security

- ✅ SQL injection prevention through query validation
- ✅ Read-only operations enforced
- ✅ AWS IAM role-based access control
- ✅ Secrets Manager for credential management
- ✅ VPC isolation for database connections
- ✅ Resource limits and monitoring

## Performance

- **Metadata Caching**: Schema introspection cached per source
- **Connection Pooling**: Reuses database connections
- **Async Operations**: Non-blocking I/O throughout
- **Auto-scaling**: AgentCore scales 1-3 replicas based on load

## Contributing

1. Follow agent-as-a-tool pattern for new features
2. Add comprehensive metadata support for new sources
3. Include confidence scoring for routing decisions
4. Add unit tests with >80% coverage
5. Update documentation for API changes

## Troubleshooting

### Common Issues

**"Connection pool not initialized"**
- Ensure Aurora cluster ARN and secret ARN are set
- Check IAM permissions for RDS Data API
- Verify cluster is in "available" state

**Routing issues**
- Check metadata is properly populated: `await get_source_metadata()`
- Verify LLM has access to accurate schema information
- Review CloudWatch logs for LLM routing decisions

**Agent tool initialization fails**
- Verify all required configuration parameters
- Check network connectivity to data sources
- Review CloudWatch logs for detailed errors

## License

Copyright © 2024 Amazon Web Services

## Support

For issues and questions:
- GitHub Issues: [repository/issues]
- Internal Wiki: [link to documentation]
- Team Contact: [team distribution list]
