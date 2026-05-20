"""
Prints AgentCore Runtime agent definitions for Supervisor and Synthesizer.

Usage:
    python -m infrastructure.aws.agentcore_agents_setup
"""

import json
import logging
import sys

sys.path.insert(0, ".")
from agentcore.agents.supervisor import SYSTEM_PROMPT as SUP_PROMPT
from agentcore.agents.synthesizer import SYSTEM_PROMPT as SYN_PROMPT
from agentcore.config.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    settings = get_settings()

    agents = [
        {
            "name": "finserv-supervisor",
            "description": "Orchestrates multi-agent financial analysis workflow",
            "model_id": settings.aws.bedrock_model_id,
            "system_prompt_length": len(SUP_PROMPT),
            "tools": ["invoke_data_analyst", "invoke_validator"],
            "platform": "AgentCore Runtime",
        },
        {
            "name": "finserv-synthesizer",
            "description": "Generates narrative answers from validated query results",
            "model_id": settings.aws.bedrock_model_id,
            "system_prompt_length": len(SYN_PROMPT),
            "tools": [],
            "platform": "AgentCore Runtime",
        },
    ]

    databricks_agents = [
        {
            "name": settings.serving.data_analyst_endpoint_name,
            "description": "Schema discovery + SQL execution via Managed MCP",
            "model_id": settings.databricks.llm_endpoint,
            "tools": ["SQL MCP Server", "UC Functions MCP (python_exec)"],
            "platform": "Databricks Model Serving",
            "endpoint": f"{settings.databricks.host}/serving-endpoints/{settings.serving.data_analyst_endpoint_name}/responses",
        },
        {
            "name": settings.serving.validator_endpoint_name,
            "description": "Result validation via SQL MCP + python_exec",
            "model_id": settings.databricks.llm_endpoint,
            "tools": ["SQL MCP Server", "UC Functions MCP (python_exec)"],
            "platform": "Databricks Model Serving",
            "endpoint": f"{settings.databricks.host}/serving-endpoints/{settings.serving.validator_endpoint_name}/responses",
        },
    ]

    print("=" * 70)
    print("MULTI-AGENT SYSTEM CONFIGURATION")
    print("=" * 70)
    print()
    print("─── AgentCore Agents (AWS) ───")
    for a in agents:
        print(f"  {a['name']}")
        print(f"    Model: {a['model_id']}")
        print(f"    Tools: {a['tools']}")
        print(f"    Prompt: {a['system_prompt_length']} chars")
        print()

    print("─── Databricks Agents (Model Serving) ───")
    for a in databricks_agents:
        print(f"  {a['name']}")
        print(f"    Model: {a['model_id']}")
        print(f"    Tools: {a['tools']}")
        print(f"    Endpoint: {a['endpoint']}")
        print()

    print("─── Integration Flow ───")
    print("  User → Supervisor (AgentCore)")
    print("       → invoke_data_analyst → Gateway → Databricks Data Analyst")
    print("       → invoke_validator → Gateway → Databricks Validator")
    print("       → Synthesizer (AgentCore)")
    print("       → Answer")


if __name__ == "__main__":
    main()
