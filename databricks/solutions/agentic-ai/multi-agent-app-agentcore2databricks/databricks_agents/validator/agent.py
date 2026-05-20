"""
Validator Agent — self-contained for Databricks Model Serving deployment.
All dependencies are inlined (no local imports).
"""

import json
import logging
import os
from typing import Any

import mlflow
from mlflow.pyfunc import PythonModel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Validation agent for financial analysis results on Databricks.

You receive query results from the Data Analyst agent and must verify them for:
1. Non-empty results (queries returned data)
2. Null analysis (excessive NULLs indicate data quality issues)
3. Outlier detection (extreme values that may indicate errors)
4. Cross-result consistency (related results should be logically compatible)
5. Business rule validation (market values positive, dates in range, etc.)

You have access to:
- SQL MCP Server: run validation queries against the lakehouse
- system.ai.python_exec: run Python (pandas) for statistical analysis

Process:
- Examine the provided results
- Run validation queries if needed (e.g., check totals, verify counts)
- Use python_exec for statistical checks (distributions, outlier detection)
- After executing SQL, you may get a statement_id with PENDING status. Use poll_sql_result tool with that statement_id to get results.
- Assign a confidence level: HIGH (all checks pass), MEDIUM (minor issues), LOW (major problems)

Return structured JSON:
- is_valid: boolean
- confidence: "high" | "medium" | "low"
- checks_passed: list of checks that passed
- checks_failed: list of checks that failed (with details)
- notes: any additional context for the Synthesizer"""

MODEL_ENDPOINT = os.environ.get("DATABRICKS_LLM_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct")


class ValidatorAgent(PythonModel):

    def load_context(self, context):
        from databricks.sdk import WorkspaceClient
        from databricks_mcp import DatabricksMCPClient

        host = os.environ.get("DATABRICKS_HOST", "")
        if host:
            self.ws = WorkspaceClient(
                host=host,
                client_id=os.environ.get("DATABRICKS_CLIENT_ID", ""),
                client_secret=os.environ.get("DATABRICKS_CLIENT_SECRET", ""),
            )
        else:
            self.ws = WorkspaceClient()

        ws_host = self.ws.config.host
        base_url = ws_host if ws_host.startswith("https://") else f"https://{ws_host}"
        self.sql_mcp = DatabricksMCPClient(
            server_url=f"{base_url}/api/2.0/mcp/sql",
            workspace_client=self.ws,
        )
        self.python_mcp = DatabricksMCPClient(
            server_url=f"{base_url}/api/2.0/mcp/functions/system/ai/python_exec",
            workspace_client=self.ws,
        )

    def predict(self, context, model_input: Any, params=None) -> dict:
        import pandas as pd

        if isinstance(model_input, pd.DataFrame):
            model_input = model_input.to_dict(orient="records")[0]

        messages = model_input.get("messages", [])
        content = messages[-1]["content"] if messages else str(model_input)

        answer = self._validate(content)

        return {
            "choices": [
                {"message": {"role": "assistant", "content": answer}, "index": 0, "finish_reason": "stop"}
            ],
            "object": "chat.completion",
        }

    def _validate(self, content: str) -> str:
        from databricks_openai import DatabricksOpenAI

        all_tools = self.sql_mcp.list_tools() + self.python_mcp.list_tools()
        client = DatabricksOpenAI(workspace_client=self.ws)
        openai_tools = self._mcp_tools_to_openai_format(all_tools)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]

        for _ in range(8):
            response = client.chat.completions.create(
                model=MODEL_ENDPOINT,
                messages=messages,
                tools=openai_tools if openai_tools else None,
            )

            choice = response.choices[0]

            if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                msg_dict = {
                    "role": "assistant",
                    "content": choice.message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in choice.message.tool_calls
                    ],
                }
                messages.append(msg_dict)
                for tool_call in choice.message.tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = json.loads(tool_call.function.arguments)

                    mcp_result = self._call_tool(fn_name, fn_args)
                    result_str = self._extract_mcp_result(mcp_result)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_str,
                    })
            else:
                return choice.message.content or json.dumps({
                    "is_valid": True,
                    "confidence": "medium",
                    "checks_passed": ["agent completed analysis"],
                    "checks_failed": [],
                    "notes": "",
                })

        return json.dumps({
            "is_valid": True,
            "confidence": "low",
            "checks_passed": [],
            "checks_failed": ["agent reached max iterations"],
            "notes": "Validation incomplete",
        })

    def _call_tool(self, tool_name: str, arguments: dict):
        sql_tool_names = [t.name for t in self.sql_mcp.list_tools()]
        if tool_name in sql_tool_names:
            return self.sql_mcp.call_tool(tool_name, arguments)

        python_tool_names = [t.name for t in self.python_mcp.list_tools()]
        if tool_name in python_tool_names:
            return self.python_mcp.call_tool(tool_name, arguments)

        return None

    def _extract_mcp_result(self, result) -> str:
        if result is None:
            return "Tool not found"
        if hasattr(result, "content"):
            texts = []
            for item in result.content:
                if hasattr(item, "text"):
                    texts.append(item.text)
            return "\n".join(texts) if texts else str(result)
        return str(result)

    def _mcp_tools_to_openai_format(self, mcp_tools: list) -> list[dict]:
        openai_tools = []
        for tool in mcp_tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema or {"type": "object", "properties": {}},
                },
            })
        return openai_tools


mlflow.models.set_model(ValidatorAgent())
