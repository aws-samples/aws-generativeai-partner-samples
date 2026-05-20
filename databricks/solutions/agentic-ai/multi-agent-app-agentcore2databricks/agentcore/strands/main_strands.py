"""
Multi-Agent Financial Analyst — Strands SDK Version.

This is the same pipeline as agentcore/main.py but implemented using the
Strands Agents SDK for cleaner agent orchestration and native MCP integration.

Architecture (same as non-Strands version):
  User → Supervisor Agent (Bedrock Claude + Gateway MCP tools)
       → Data Analyst (Databricks, via Gateway MCP)
       → Validator (Databricks, via Gateway MCP)
       → Synthesizer Agent (Bedrock Claude, text-only)
       → Answer

Usage:
    .venv/bin/python -m agentcore.strands.main_strands "What is our risk exposure?"
    .venv/bin/python -m agentcore.strands.main_strands

Requires:
    pip install strands-agents strands-agents-tools
"""

import json
import logging
import sys

from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

sys.path.insert(0, ".")
from agentcore.agents.supervisor import SYSTEM_PROMPT as SUP_PROMPT
from agentcore.agents.synthesizer import SYSTEM_PROMPT as SYN_PROMPT
from agentcore.config.guardrails import check_input_guardrails, check_output_guardrails
from agentcore.config.settings import get_boto3_session, get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def create_gateway_mcp_client(settings) -> MCPClient:
    """
    Create an MCP client connected to the AgentCore Gateway.
    The Gateway exposes Databricks agents as MCP tools.
    """
    gateway_url = (
        f"https://{settings.aws.agentcore_gateway_id}"
        f".gateway.bedrock-agentcore.{settings.aws.aws_region}.amazonaws.com/mcp"
    )

    # Strands MCPClient handles SigV4 auth automatically when
    # connecting to AgentCore Gateway endpoints
    return MCPClient(lambda: streamablehttp_client(gateway_url))


def create_supervisor_agent(model: BedrockModel, mcp_client: MCPClient) -> Agent:
    """
    Create the Supervisor agent with Bedrock Claude + Gateway MCP tools.
    Tool names are discovered dynamically from the Gateway.
    """
    tools = mcp_client.list_tools_sync()

    return Agent(
        model=model,
        system_prompt=SUP_PROMPT,
        tools=tools,
    )


def create_synthesizer_agent(model: BedrockModel) -> Agent:
    """
    Create the Synthesizer agent with Bedrock Claude (no tools needed).
    """
    return Agent(
        model=model,
        system_prompt=SYN_PROMPT,
    )


def run_pipeline(question: str) -> str:
    """
    Run the full multi-agent pipeline using Strands SDK.

    With Strands, the Supervisor agent handles tool calling automatically:
    - It reasons about the question
    - Decides which Gateway MCP tools to call
    - Calls them (Data Analyst, Validator)
    - Synthesizes the final answer

    This replaces the manual wave-based execution in the non-Strands version.
    """
    # Input guardrail
    allowed, reason = check_input_guardrails(question)
    if not allowed:
        return reason

    settings = get_settings()
    session = get_boto3_session(settings)

    # Create Bedrock model
    model = BedrockModel(
        model_id=settings.aws.bedrock_model_id,
        boto_session=session,
    )

    # Connect to AgentCore Gateway (exposes Databricks agents as MCP tools)
    mcp_client = create_gateway_mcp_client(settings)

    with mcp_client:
        # Create Supervisor with access to Gateway tools
        supervisor = create_supervisor_agent(model, mcp_client)

        # The Supervisor agent handles the full pipeline in one call:
        # - Analyzes the question
        # - Calls Data Analyst tool via Gateway → Databricks
        # - Calls Validator tool via Gateway → Databricks
        # - Produces final answer
        logger.info("Supervisor Agent (Strands + Bedrock Claude): Processing question...")
        logger.info("  Gateway: %s", mcp_client)
        logger.info("  Tools available: %d", len(mcp_client.list_tools_sync()))

        catalog = settings.databricks.catalog
        prompt = f"""Analyze this financial question by:
1. First, call the Data Analyst tool to query the {catalog} lakehouse
2. Then, call the Validator tool to validate the results
3. Finally, synthesize a comprehensive answer

Question: {question}

Use the available tools to get real data, then provide a narrative answer with:
- Executive summary (2-3 sentences)
- Detailed findings with numbers
- Data lineage (which tables were queried)
- Confidence level
- Follow-up questions"""

        response = supervisor(prompt)
        answer = str(response)

        # Output guardrail
        allowed, reason = check_output_guardrails(answer)
        if not allowed:
            return f"[Output filtered: {reason}]\n\nPlease rephrase your question."

        return answer


def run_two_agent_pipeline(question: str) -> str:
    """
    Alternative: Two-agent pipeline where Supervisor queries data,
    and a separate Synthesizer generates the narrative.

    This mirrors the non-Strands version more closely.
    """
    allowed, reason = check_input_guardrails(question)
    if not allowed:
        return reason

    settings = get_settings()
    session = get_boto3_session(settings)

    model = BedrockModel(
        model_id=settings.aws.bedrock_model_id,
        boto_session=session,
    )

    mcp_client = create_gateway_mcp_client(settings)

    with mcp_client:
        # Step 1: Supervisor queries data via Gateway tools
        supervisor = create_supervisor_agent(model, mcp_client)

        logger.info("Step 1: Supervisor querying data via Gateway MCP tools...")
        data_response = supervisor(
            f"Query the {settings.databricks.catalog} lakehouse to answer: {question}\n\n"
            f"Call the Data Analyst tool, then the Validator tool. "
            f"Return the raw results as JSON."
        )

        # Step 2: Synthesizer generates narrative (no tools needed)
        synthesizer = create_synthesizer_agent(model)

        logger.info("Step 2: Synthesizer generating narrative...")
        synth_prompt = (
            f"Original question: {question}\n\n"
            f"Data and validation results:\n{str(data_response)}\n\n"
            f"Generate a comprehensive financial analysis narrative."
        )
        final_response = synthesizer(synth_prompt)
        answer = str(final_response)

        allowed, reason = check_output_guardrails(answer)
        if not allowed:
            return f"[Output filtered: {reason}]"

        return answer


def main():
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        catalog = get_settings().databricks.catalog
        question = f"How many customers are in the {catalog}.core.customers table?"

    answer = run_pipeline(question)

    print("\n" + "=" * 80)
    print(answer)
    print("=" * 80)


if __name__ == "__main__":
    main()
