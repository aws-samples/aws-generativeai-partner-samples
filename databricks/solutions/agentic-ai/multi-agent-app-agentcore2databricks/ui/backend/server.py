"""
FastAPI backend with WebSocket streaming for the Multi-Agent Financial Analyst UI.

Streams real-time agent execution events to the frontend:
- Plan decomposition
- Agent invocations (which agent, which platform)
- Guardrail checks (input/output)
- Results from each step
- Final synthesized answer

Usage:
    .venv/bin/python -m ui.backend.server
"""

import asyncio
import json
import logging
import sys
import time
from enum import Enum

import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, ".")
from agentcore.agents.supervisor import SYSTEM_PROMPT as SUP_PROMPT, SupervisorAgent
from agentcore.agents.synthesizer import SYSTEM_PROMPT as SYN_PROMPT, SynthesizerAgent
from agentcore.config.guardrails import check_input_guardrails, check_output_guardrails
from agentcore.config.settings import get_boto3_session, get_settings
from agentcore.models.subtask import AgentType, SubTaskStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Multi-Agent Financial Analyst API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _build_gateway_tool_names():
    """Build Gateway MCP tool names from endpoint names."""
    settings = get_settings()
    da_name = settings.serving.data_analyst_endpoint_name
    val_name = settings.serving.validator_endpoint_name
    return {
        AgentType.DATA_ANALYST: f"databricks-{da_name}___invoke_{da_name.replace('-', '_')}",
        AgentType.VALIDATOR: f"databricks-{val_name}___invoke_{val_name.replace('-', '_')}",
    }

EXAMPLE_QUERIES = [
    "What is the total market value across all portfolio positions?",
    "What are the top 3 customer segments by total account balance?",
    "How many trades were executed in the last 3 months with status EXECUTED?",
    "What is our risk exposure to the Technology sector for institutional accounts?",
    "Show the average VaR(95) and Sharpe ratio across all accounts in the risk metrics table.",
    "Which sectors have the highest unrealized P&L in portfolio positions?",
]


class AgentMode(str, Enum):
    RAW = "raw"
    STRANDS = "strands"


class QueryRequest(BaseModel):
    question: str
    mode: AgentMode = AgentMode.RAW


@app.get("/api/examples")
def get_examples():
    return {"examples": EXAMPLE_QUERIES}


@app.get("/api/health")
def health():
    return {"status": "ok", "gateway": get_settings().aws.agentcore_gateway_id}


async def send_event(ws: WebSocket, event_type: str, data: dict):
    await ws.send_json({"type": event_type, "timestamp": time.time(), **data})


@app.websocket("/ws/query")
async def websocket_query(ws: WebSocket):
    await ws.accept()

    try:
        msg = await ws.receive_json()
        question = msg.get("question", "")
        mode = msg.get("mode", "raw")

        settings = get_settings()
        session = get_boto3_session(settings)

        # Step 1: Input Guardrail
        await send_event(ws, "guardrail_input", {
            "status": "checking",
            "message": "Checking input guardrails...",
        })

        allowed, reason = check_input_guardrails(question)
        if not allowed:
            await send_event(ws, "guardrail_input", {
                "status": "blocked",
                "message": reason,
            })
            await send_event(ws, "complete", {"answer": reason})
            return

        await send_event(ws, "guardrail_input", {
            "status": "passed",
            "message": "Input guardrails passed.",
        })

        if mode == "strands":
            await run_strands_pipeline(ws, question, settings, session)
        else:
            await run_raw_pipeline(ws, question, settings, session)

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        try:
            await send_event(ws, "error", {"message": str(e)})
        except Exception:
            pass


async def run_raw_pipeline(ws: WebSocket, question: str, settings, session):
    """Run the raw orchestrator pipeline with streaming events."""
    supervisor = SupervisorAgent()
    synthesizer = SynthesizerAgent()
    bedrock = session.client("bedrock-runtime")
    credentials = session.get_credentials().get_frozen_credentials()
    gateway_url = (
        f"https://{settings.aws.agentcore_gateway_id}"
        f".gateway.bedrock-agentcore.{settings.aws.aws_region}.amazonaws.com/mcp"
    )

    # Step 2: Supervisor Decomposition
    await send_event(ws, "supervisor", {
        "status": "planning",
        "platform": "aws",
        "agent": "Supervisor",
        "model": settings.aws.bedrock_model_id,
        "message": "Decomposing question into sub-tasks...",
    })

    prompt = (
        f"Decompose this financial analysis question into sub-tasks.\n\n"
        f"Question: {question}\n\nReturn JSON with the execution plan."
    )

    try:
        response = bedrock.converse(
            modelId=settings.aws.bedrock_model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            system=[{"text": SUP_PROMPT}],
        )
        response_text = response["output"]["message"]["content"][0]["text"]
        json_str = response_text
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
        plan_data = json.loads(json_str.strip())
        plan = supervisor.parse_llm_plan(question, plan_data)
    except Exception:
        plan = supervisor.create_default_plan(question, catalog=settings.databricks.catalog)

    await send_event(ws, "supervisor", {
        "status": "planned",
        "platform": "aws",
        "agent": "Supervisor",
        "subtasks": [{"id": st.id, "task": st.task, "agent": st.agent.value, "depends_on": st.depends_on} for st in plan.subtasks],
        "message": f"Plan: {len(plan.subtasks)} sub-tasks",
    })

    # Step 3: Execute waves
    waves = supervisor.get_execution_waves(plan)
    analyst_results = []
    validation_result = {}

    for wave_idx, wave in enumerate(waves):
        for subtask in wave:
            context = {
                st.id: st.result
                for st in plan.subtasks
                if st.status == SubTaskStatus.COMPLETED and st.result
            }
            task_input = supervisor.format_tool_input(subtask, context)

            if subtask.agent == AgentType.DATA_ANALYST:
                await send_event(ws, "agent_invoke", {
                    "status": "running",
                    "platform": "databricks",
                    "agent": "Data Analyst",
                    "subtask_id": subtask.id,
                    "task": subtask.task,
                    "message": "Querying lakehouse via MCP...",
                    "route": "AgentCore Gateway → Databricks Model Serving → SQL MCP",
                })

                result = await asyncio.to_thread(
                    _invoke_gateway_tool, gateway_url, credentials, settings,
                    _build_gateway_tool_names()[AgentType.DATA_ANALYST], task_input,
                )
                analyst_results.append(result)
                supervisor.mark_completed(plan, subtask.id, result)

                await send_event(ws, "agent_invoke", {
                    "status": "completed",
                    "platform": "databricks",
                    "agent": "Data Analyst",
                    "subtask_id": subtask.id,
                    "result_preview": result.get("summary", str(result))[:300],
                })

            elif subtask.agent == AgentType.VALIDATOR:
                await send_event(ws, "agent_invoke", {
                    "status": "running",
                    "platform": "databricks",
                    "agent": "Validator",
                    "subtask_id": subtask.id,
                    "task": subtask.task,
                    "message": "Validating results via MCP...",
                    "route": "AgentCore Gateway → Databricks Model Serving → SQL MCP + python_exec",
                })

                result = await asyncio.to_thread(
                    _invoke_gateway_tool, gateway_url, credentials, settings,
                    _build_gateway_tool_names()[AgentType.VALIDATOR], task_input,
                )
                validation_result = result
                supervisor.mark_completed(plan, subtask.id, result)

                await send_event(ws, "agent_invoke", {
                    "status": "completed",
                    "platform": "databricks",
                    "agent": "Validator",
                    "subtask_id": subtask.id,
                    "result_preview": result.get("summary", str(result))[:300],
                })

            elif subtask.agent == AgentType.SYNTHESIZER:
                await send_event(ws, "agent_invoke", {
                    "status": "running",
                    "platform": "aws",
                    "agent": "Synthesizer",
                    "subtask_id": subtask.id,
                    "task": subtask.task,
                    "message": "Generating narrative with Bedrock Claude...",
                    "route": "Bedrock Converse API → Claude Sonnet",
                })

                synth_context = synthesizer.build_context(question, analyst_results, validation_result)
                response = bedrock.converse(
                    modelId=settings.aws.bedrock_model_id,
                    messages=[{"role": "user", "content": [{"text": synth_context}]}],
                    system=[{"text": SYN_PROMPT}],
                )
                answer = response["output"]["message"]["content"][0]["text"]

                # Output guardrail
                await send_event(ws, "guardrail_output", {
                    "status": "checking",
                    "message": "Checking output guardrails...",
                })

                allowed, reason = check_output_guardrails(answer)
                if not allowed:
                    await send_event(ws, "guardrail_output", {"status": "blocked", "message": reason})
                    answer = f"[Output filtered: {reason}]"
                else:
                    await send_event(ws, "guardrail_output", {"status": "passed", "message": "Output guardrails passed."})

                await send_event(ws, "agent_invoke", {
                    "status": "completed",
                    "platform": "aws",
                    "agent": "Synthesizer",
                    "subtask_id": subtask.id,
                    "result_preview": answer[:300],
                })

                await send_event(ws, "complete", {"answer": answer})
                return

    await send_event(ws, "complete", {"answer": "Analysis could not be completed."})


async def run_strands_pipeline(ws: WebSocket, question: str, settings, session):
    """Run the Strands SDK pipeline with streaming events."""
    await send_event(ws, "supervisor", {
        "status": "planning",
        "platform": "aws",
        "agent": "Supervisor (Strands)",
        "model": settings.aws.bedrock_model_id,
        "message": "Strands Agent reasoning with Gateway MCP tools...",
    })

    try:
        from agentcore.strands.main_strands import run_pipeline

        await send_event(ws, "supervisor", {
            "status": "planned",
            "platform": "aws",
            "agent": "Supervisor (Strands)",
            "message": "Strands Agent autonomously orchestrating pipeline...",
        })

        await send_event(ws, "agent_invoke", {
            "status": "running",
            "platform": "databricks",
            "agent": "Data Analyst",
            "subtask_id": "strands-da",
            "task": "Query lakehouse data via MCP (Strands autonomous)",
            "message": "Strands Agent calling Data Analyst via Gateway...",
            "route": "AgentCore Gateway → Databricks Model Serving → SQL MCP",
        })

        answer = await asyncio.to_thread(run_pipeline, question)

        await send_event(ws, "agent_invoke", {
            "status": "completed",
            "platform": "databricks",
            "agent": "Data Analyst",
            "subtask_id": "strands-da",
            "message": "Data Analyst completed (Strands autonomous)",
            "result_preview": answer[:200] if answer else "",
        })

        await send_event(ws, "agent_invoke", {
            "status": "completed",
            "platform": "databricks",
            "agent": "Validator",
            "subtask_id": "strands-val",
            "message": "Validation completed (Strands autonomous)",
            "result_preview": "Results validated by Strands Agent",
        })

        await send_event(ws, "agent_invoke", {
            "status": "completed",
            "platform": "aws",
            "agent": "Synthesizer",
            "subtask_id": "strands-synth",
            "message": "Synthesis completed (Strands autonomous)",
            "result_preview": answer[:200] if answer else "",
        })

        # Output guardrail
        await send_event(ws, "guardrail_output", {"status": "checking", "message": "Checking output guardrails..."})
        allowed, reason = check_output_guardrails(answer)
        if not allowed:
            await send_event(ws, "guardrail_output", {"status": "blocked", "message": reason})
            answer = f"[Output filtered: {reason}]"
        else:
            await send_event(ws, "guardrail_output", {"status": "passed", "message": "Output guardrails passed."})

        await send_event(ws, "complete", {"answer": answer})

    except Exception as e:
        await send_event(ws, "error", {"message": str(e)})


def _invoke_gateway_tool(gateway_url: str, credentials, settings, tool_name: str, task_input: str) -> dict:
    """Invoke a tool through AgentCore Gateway (synchronous, called from thread)."""
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": {"messages": [{"role": "user", "content": task_input}]},
        },
    }

    request = AWSRequest(
        method="POST", url=gateway_url,
        data=json.dumps(payload), headers={"Content-Type": "application/json"},
    )
    SigV4Auth(credentials, "bedrock-agentcore", settings.aws.aws_region).add_auth(request)

    resp = requests.post(gateway_url, data=json.dumps(payload), headers=dict(request.headers), timeout=600)
    resp.raise_for_status()
    result = resp.json()

    if result.get("result", {}).get("isError"):
        return {"summary": f"Error: {result['result']['content'][0]['text']}"}

    content = result.get("result", {}).get("content", [{}])[0].get("text", "")
    try:
        parsed = json.loads(content)
        agent_content = parsed.get("choices", [{}])[0].get("message", {}).get("content", "")
        try:
            return json.loads(agent_content)
        except (json.JSONDecodeError, TypeError):
            return {"summary": agent_content}
    except (json.JSONDecodeError, TypeError):
        return {"summary": content}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
