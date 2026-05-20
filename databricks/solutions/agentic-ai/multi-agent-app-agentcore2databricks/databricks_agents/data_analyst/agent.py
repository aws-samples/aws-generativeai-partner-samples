"""
Data Analyst Agent — self-contained for Databricks Model Serving deployment.
All dependencies are inlined (no local imports).
"""

import json
import logging
import os
from typing import Any

import mlflow
from mlflow.pyfunc import PythonModel

logger = logging.getLogger(__name__)

CATALOG = os.environ.get("DATABRICKS_CATALOG", "finserv_catalog")

SYSTEM_PROMPT = f"""You are a Data Analyst agent for a financial services data lakehouse on Databricks.

You have access to the following catalog: {CATALOG}
Schemas: core, transactions, risk, reference

Your job is to:
1. Discover relevant tables and columns for the given analytical question
2. Write and execute Spark SQL to answer the question
3. Return structured results

Process:
- First, query INFORMATION_SCHEMA or use the SQL MCP to discover table structures
- Then write efficient SQL (always use fully qualified names: {CATALOG}.schema.table)
- Always include LIMIT (max 1000 rows for summaries, 100 for detailed data)
- Prefer aggregations (SUM, AVG, COUNT, GROUP BY) over raw row dumps
- For time comparisons, use explicit DATE filters
- After executing SQL, you may get a statement_id with PENDING status. Use poll_sql_result tool with that statement_id to get results.

Rules:
- Only SELECT queries (no DDL, no DML)
- Always include LIMIT clause
- Use table comments and column names to understand semantics
- If a query fails, analyze the error and retry with corrections

IMPORTANT: In your final response, always include:
1. The exact SQL query you executed
2. The tables you accessed (fully qualified names)
3. The results with specific numbers
4. A clear summary answering the question

Format your final answer like this:
SQL: <the query you ran>
Tables: <comma-separated table names>
Result: <the data/numbers>
Summary: <natural language answer with key data points>"""

MODEL_ENDPOINT = os.environ.get("DATABRICKS_LLM_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct")


class DataAnalystAgent(PythonModel):

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

    def predict(self, context, model_input: Any, params=None) -> dict:
        import pandas as pd

        if isinstance(model_input, pd.DataFrame):
            model_input = model_input.to_dict(orient="records")[0]

        messages = model_input.get("messages", [])
        question = messages[-1]["content"] if messages else str(model_input)

        answer = self._analyze(question)

        return {
            "choices": [
                {"message": {"role": "assistant", "content": answer}, "index": 0, "finish_reason": "stop"}
            ],
            "object": "chat.completion",
        }

    def _analyze(self, question: str) -> str:
        from databricks_openai import DatabricksOpenAI

        tools = self.sql_mcp.list_tools()
        client = DatabricksOpenAI(workspace_client=self.ws)
        openai_tools = self._mcp_tools_to_openai_format(tools)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        for _ in range(10):
            response = client.chat.completions.create(
                model=MODEL_ENDPOINT,
                messages=messages,
                tools=openai_tools if openai_tools else None,
            )

            choice = response.choices[0]

            if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                # Serialize without extra fields that Databricks endpoints reject
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

                    mcp_result = self.sql_mcp.call_tool(fn_name, fn_args)
                    result_str = self._extract_mcp_result(mcp_result)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_str,
                    })
            else:
                return choice.message.content or "No response generated."

        return "Agent reached maximum iterations."

    def _extract_mcp_result(self, result) -> str:
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


mlflow.models.set_model(DataAnalystAgent())
