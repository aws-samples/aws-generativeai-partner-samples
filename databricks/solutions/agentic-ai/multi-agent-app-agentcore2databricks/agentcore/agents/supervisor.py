"""
Supervisor Agent — runs on AgentCore Runtime.

Decomposes user questions into sub-tasks, dispatches to Databricks-hosted agents
via Gateway, and routes results to the Synthesizer.
"""

import json
import logging

from agentcore.models.subtask import AgentType, ExecutionPlan, SubTask, SubTaskStatus

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Supervisor agent for a hybrid multi-agent financial analysis system.

Architecture:
- You run on AWS (AgentCore)
- Data Analyst agent runs on Databricks (has access to SQL and schema discovery)
- Validator agent runs on Databricks (has access to SQL and Python for statistical checks)
- Synthesizer agent runs on AWS (produces the final narrative)

Your job:
1. Receive a complex business question
2. Decompose it into ordered sub-tasks
3. Assign each sub-task to the appropriate agent
4. Independent data queries can run in parallel
5. Validation always depends on data queries completing
6. Synthesis is always the final step

Available tools:
- invoke_data_analyst: Send analytical sub-task to Databricks Data Analyst
- invoke_validator: Send results to Databricks Validator for cross-checking

Return a JSON execution plan:
{
  "subtasks": [
    {"id": "st-1", "task": "description", "agent": "data_analyst|validator|synthesizer", "depends_on": []}
  ]
}

Rules:
- Data Analyst handles schema discovery AND SQL execution (no separate schema step needed)
- Multiple Data Analyst tasks with no dependencies run in parallel
- Validator depends on ALL data queries completing
- Synthesizer depends on validation completing"""

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "subtasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "task": {"type": "string"},
                    "agent": {"type": "string", "enum": ["data_analyst", "validator", "synthesizer"]},
                    "depends_on": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "task", "agent", "depends_on"],
            },
        }
    },
    "required": ["subtasks"],
}


class SupervisorAgent:

    def create_default_plan(self, question: str, catalog: str = "finserv_catalog") -> ExecutionPlan:
        return ExecutionPlan(
            question=question,
            subtasks=[
                SubTask(
                    id="st-1",
                    task=f"Analyze the following question against the {catalog} lakehouse: {question}",
                    agent=AgentType.DATA_ANALYST,
                    depends_on=[],
                ),
                SubTask(
                    id="st-2",
                    task="Validate the query results for consistency and accuracy",
                    agent=AgentType.VALIDATOR,
                    depends_on=["st-1"],
                ),
                SubTask(
                    id="st-3",
                    task="Synthesize a narrative answer with lineage and confidence assessment",
                    agent=AgentType.SYNTHESIZER,
                    depends_on=["st-2"],
                ),
            ],
        )

    def parse_llm_plan(self, question: str, llm_output: dict) -> ExecutionPlan:
        subtasks = []
        for st in llm_output.get("subtasks", []):
            subtasks.append(
                SubTask(
                    id=st["id"],
                    task=st["task"],
                    agent=AgentType(st["agent"]),
                    depends_on=st.get("depends_on", []),
                )
            )
        return ExecutionPlan(question=question, subtasks=subtasks)

    def get_execution_waves(self, plan: ExecutionPlan) -> list[list[SubTask]]:
        waves = []
        completed: set[str] = set()
        remaining = {st.id for st in plan.subtasks}

        while remaining:
            wave = [
                st
                for st in plan.subtasks
                if st.id in remaining
                and all(dep in completed for dep in st.depends_on)
            ]
            if not wave:
                break
            waves.append(wave)
            for st in wave:
                remaining.discard(st.id)
                completed.add(st.id)

        return waves

    def mark_completed(self, plan: ExecutionPlan, subtask_id: str, result: dict) -> None:
        for st in plan.subtasks:
            if st.id == subtask_id:
                st.status = SubTaskStatus.COMPLETED
                st.result = result
                break

    def mark_failed(self, plan: ExecutionPlan, subtask_id: str, error: str) -> None:
        for st in plan.subtasks:
            if st.id == subtask_id:
                st.status = SubTaskStatus.FAILED
                st.error = error
                break

    def format_tool_input(self, subtask: SubTask, context: dict) -> str:
        parts = [f"Task: {subtask.task}"]
        if context:
            parts.append(f"\nContext from prior steps:\n{json.dumps(context, indent=2, default=str)}")
        return "\n".join(parts)
