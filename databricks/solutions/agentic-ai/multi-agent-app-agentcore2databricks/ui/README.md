# Multi-Agent Financial Analyst — Web UI

React web console using AWS Cloudscape Design System for visualizing the hybrid multi-agent pipeline.

## Features

- Real-time agent execution flow visualization (WebSocket streaming)
- Shows data flowing across AWS (Bedrock Claude) and Databricks (Model Serving + MCP)
- Highlights input/output guardrails being applied
- Switch between Standard Agents and Strands SDK Agents
- 6 example queries for quick testing
- AWS Console look-and-feel via Cloudscape Design System

## Architecture

```
┌─────────────────────────────────────────────────┐
│  React UI (Cloudscape)                          │
│  - Query input + example queries                │
│  - Agent mode selector (Raw / Strands)          │
│  - Real-time flow visualization                 │
│  - Markdown result rendering                    │
└──────────────────────┬──────────────────────────┘
                       │ WebSocket
┌──────────────────────▼──────────────────────────┐
│  FastAPI Backend (Python)                        │
│  - WebSocket endpoint (/ws/query)               │
│  - Streams execution events to UI               │
│  - Reuses existing orchestrator code            │
└──────────────────────┬──────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   Bedrock       AgentCore       Databricks
   Claude        Gateway         Model Serving
   (Supervisor   (MCP routing    (Data Analyst
    Synthesizer)  + OAuth)        Validator)
```

## Quick Start

### 1. Start the Backend

```bash
# From the project root
.venv/bin/pip install fastapi uvicorn websockets
.venv/bin/python -m ui.backend.server
```

Backend runs at: http://localhost:8000

### 2. Start the Frontend

```bash
cd ui
npm install
npm start
```

Frontend runs at: http://localhost:3000

### 3. Use the UI

1. Select an example query or type your own
2. Choose agent mode (Standard or Strands)
3. Click "Run Analysis"
4. Watch the flow visualization as agents execute in real-time
5. View the final synthesized answer in the "Final Answer" tab

## WebSocket Event Types

The backend streams these events to the UI:

| Event Type | Description | Key Fields |
|------------|-------------|------------|
| `guardrail_input` | Input guardrail check | status, message |
| `supervisor` | Supervisor planning | status, agent, platform, subtasks |
| `agent_invoke` | Agent execution | status, agent, platform, route, result_preview |
| `guardrail_output` | Output guardrail check | status, message |
| `complete` | Pipeline finished | answer |
| `error` | Error occurred | message |

## Development

- Frontend: `ui/src/` (React + Cloudscape)
- Backend: `ui/backend/server.py` (FastAPI + WebSocket)
- The backend imports directly from `agentcore/` — no code duplication
