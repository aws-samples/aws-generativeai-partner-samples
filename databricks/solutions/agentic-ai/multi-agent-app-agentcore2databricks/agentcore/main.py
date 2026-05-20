"""
Main entry point for the Multi-Agent Financial Analyst.

Orchestrates the hybrid pipeline via AgentCore Gateway:
  User → Supervisor (Bedrock Claude — plans sub-tasks)
       → AgentCore Gateway (MCP protocol, SigV4 auth)
           → Data Analyst (Databricks Model Serving — queries data via MCP)
           → Validator (Databricks Model Serving — validates results via MCP)
       → Synthesizer (Bedrock Claude — generates narrative answer)
       → Answer

Usage:
    .venv/bin/python -m agentcore.main "What is our risk exposure to Technology?"
    .venv/bin/python -m agentcore.main  # uses default example question
"""

import json
import logging
import sys

import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

from agentcore.agents.supervisor import SYSTEM_PROMPT as SUP_PROMPT, SupervisorAgent
from agentcore.agents.synthesizer import SynthesizerAgent
from agentcore.config.guardrails import check_input_guardrails, check_output_guardrails
from agentcore.config.settings import get_boto3_session, get_settings
from agentcore.models.subtask import AgentType, SubTaskStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def _build_gateway_tool_names(settings):
    """Build Gateway MCP tool names from endpoint names (format: databricks-{name}___invoke_{name_underscored})."""
    da_name = settings.serving.data_analyst_endpoint_name
    val_name = settings.serving.validator_endpoint_name
    return {
        AgentType.DATA_ANALYST: f"databricks-{da_name}___invoke_{da_name.replace('-', '_')}",
        AgentType.VALIDATOR: f"databricks-{val_name}___invoke_{val_name.replace('-', '_')}",
    }


class MultiAgentOrchestrator:
    def __init__(self):
        self.settings = get_settings()
        self.supervisor = SupervisorAgent()
        self.synthesizer = SynthesizerAgent()
        self._session = get_boto3_session(self.settings)
        self.bedrock = self._session.client("bedrock-runtime")
        self._credentials = self._session.get_credentials().get_frozen_credentials()
        self._gateway_url = (
            f"https://{self.settings.aws.agentcore_gateway_id}"
            f".gateway.bedrock-agentcore.{self.settings.aws.aws_region}.amazonaws.com/mcp"
        )
        self._gateway_tool_names = _build_gateway_tool_names(self.settings)

    def _invoke_bedrock(self, system_prompt: str, user_message: str) -> str:
        """Call Bedrock Claude for Supervisor/Synthesizer reasoning."""
        response = self.bedrock.converse(
            modelId=self.settings.aws.bedrock_model_id,
            messages=[{"role": "user", "content": [{"text": user_message}]}],
            system=[{"text": system_prompt}],
        )
        return response["output"]["message"]["content"][0]["text"]

    def _invoke_gateway_tool(self, tool_name: str, task_input: str) -> dict:
        """
        Invoke a Databricks agent via AgentCore Gateway MCP protocol.
        Uses SigV4 auth to the Gateway; Gateway handles OAuth to Databricks.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": {
                    "messages": [{"role": "user", "content": task_input}]
                },
            },
        }

        request = AWSRequest(
            method="POST",
            url=self._gateway_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        SigV4Auth(self._credentials, "bedrock-agentcore", self.settings.aws.aws_region).add_auth(request)

        resp = requests.post(
            self._gateway_url,
            data=json.dumps(payload),
            headers=dict(request.headers),
            timeout=600,
        )
        resp.raise_for_status()
        result = resp.json()

        if result.get("result", {}).get("isError"):
            error_text = result["result"]["content"][0]["text"]
            raise RuntimeError(f"Gateway tool error: {error_text}")

        content = result.get("result", {}).get("content", [{}])[0].get("text", "")
        try:
            parsed = json.loads(content)
            # Extract the agent's response from ChatCompletion format
            agent_content = parsed.get("choices", [{}])[0].get("message", {}).get("content", "")
            try:
                return json.loads(agent_content)
            except (json.JSONDecodeError, TypeError):
                return {"summary": agent_content}
        except (json.JSONDecodeError, TypeError):
            return {"summary": content}

    def decompose(self, question: str):
        logger.info("Supervisor (Bedrock Claude): Decomposing question...")
        prompt = (
            f"Decompose this financial analysis question into sub-tasks.\n\n"
            f"Question: {question}\n\n"
            f"Return JSON with the execution plan."
        )
        try:
            response_text = self._invoke_bedrock(SUP_PROMPT, prompt)
            # Extract JSON from response (LLM might wrap in markdown)
            json_str = response_text
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]
            plan_data = json.loads(json_str.strip())
            plan = self.supervisor.parse_llm_plan(question, plan_data)
            logger.info("  Plan: %d sub-tasks", len(plan.subtasks))
            return plan
        except Exception as e:
            logger.warning("  LLM decomposition failed (%s), using default plan", e)
            return self.supervisor.create_default_plan(question, catalog=self.settings.databricks.catalog)

    def run(self, question: str) -> str:
        # Input guardrail
        allowed, reason = check_input_guardrails(question)
        if not allowed:
            return reason

        logger.info("Gateway: %s", self._gateway_url)

        # Decompose
        plan = self.decompose(question)
        waves = self.supervisor.get_execution_waves(plan)
        logger.info("Executing %d sub-tasks in %d waves", len(plan.subtasks), len(waves))

        # Execute waves
        analyst_results: list[dict] = []
        validation_result: dict = {}

        for wave_idx, wave in enumerate(waves):
            logger.info("Wave %d: %d tasks", wave_idx + 1, len(wave))

            for subtask in wave:
                logger.info("  [%s] %s: %s", subtask.agent.value, subtask.id, subtask.task[:80])
                context = {
                    st.id: st.result
                    for st in plan.subtasks
                    if st.status == SubTaskStatus.COMPLETED and st.result
                }
                task_input = self.supervisor.format_tool_input(subtask, context)

                try:
                    if subtask.agent == AgentType.DATA_ANALYST:
                        tool_name = self._gateway_tool_names[AgentType.DATA_ANALYST]
                        logger.info("    → Gateway MCP: %s", tool_name)
                        result = self._invoke_gateway_tool(tool_name, task_input)
                        analyst_results.append(result)
                        self.supervisor.mark_completed(plan, subtask.id, result)

                    elif subtask.agent == AgentType.VALIDATOR:
                        tool_name = self._gateway_tool_names[AgentType.VALIDATOR]
                        logger.info("    → Gateway MCP: %s", tool_name)
                        result = self._invoke_gateway_tool(tool_name, task_input)
                        validation_result = result
                        self.supervisor.mark_completed(plan, subtask.id, result)

                    elif subtask.agent == AgentType.SYNTHESIZER:
                        logger.info("    → Bedrock Claude: Synthesizing narrative...")
                        synth_context = self.synthesizer.build_context(
                            question, analyst_results, validation_result
                        )
                        answer = self._invoke_bedrock(
                            self.synthesizer.system_prompt, synth_context
                        )
                        # Output guardrail
                        allowed, reason = check_output_guardrails(answer)
                        if not allowed:
                            answer = f"[Output filtered: {reason}]\n\nPlease rephrase your question."
                        self.supervisor.mark_completed(plan, subtask.id, {"answer": answer})
                        return answer

                except Exception as e:
                    logger.error("  Sub-task %s failed: %s", subtask.id, e)
                    self.supervisor.mark_failed(plan, subtask.id, str(e))

        return "Analysis could not be completed. Check logs for details."


def main():
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = (
            "What is our total risk exposure to the Technology sector across all "
            "institutional accounts, and how has it changed over the last quarter?"
        )

    orchestrator = MultiAgentOrchestrator()
    answer = orchestrator.run(question)

    print("\n" + "=" * 80)
    print(answer)
    print("=" * 80)


if __name__ == "__main__":
    main()
