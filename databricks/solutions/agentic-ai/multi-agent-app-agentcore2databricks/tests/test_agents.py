"""Unit tests for agent logic (no external dependencies)."""

from agentcore.agents.supervisor import SupervisorAgent
from agentcore.agents.synthesizer import SynthesizerAgent
from agentcore.models.subtask import AgentType, Platform, SubTaskStatus


class TestSupervisor:
    def setup_method(self):
        self.supervisor = SupervisorAgent()

    def test_default_plan_has_correct_agents(self):
        plan = self.supervisor.create_default_plan("What is our risk?")
        assert plan.question == "What is our risk?"
        assert len(plan.subtasks) == 3
        assert plan.subtasks[0].agent == AgentType.DATA_ANALYST
        assert plan.subtasks[1].agent == AgentType.VALIDATOR
        assert plan.subtasks[2].agent == AgentType.SYNTHESIZER

    def test_platform_assignment(self):
        plan = self.supervisor.create_default_plan("test")
        assert plan.subtasks[0].platform == Platform.DATABRICKS
        assert plan.subtasks[1].platform == Platform.DATABRICKS
        assert plan.subtasks[2].platform == Platform.AGENTCORE

    def test_execution_waves_respect_dependencies(self):
        plan = self.supervisor.create_default_plan("test")
        waves = self.supervisor.get_execution_waves(plan)
        assert len(waves) == 3
        assert waves[0][0].agent == AgentType.DATA_ANALYST
        assert waves[1][0].agent == AgentType.VALIDATOR
        assert waves[2][0].agent == AgentType.SYNTHESIZER

    def test_parallel_data_analyst_tasks(self):
        plan = self.supervisor.parse_llm_plan(
            "test",
            {
                "subtasks": [
                    {"id": "st-1", "task": "query A", "agent": "data_analyst", "depends_on": []},
                    {"id": "st-2", "task": "query B", "agent": "data_analyst", "depends_on": []},
                    {"id": "st-3", "task": "validate", "agent": "validator", "depends_on": ["st-1", "st-2"]},
                    {"id": "st-4", "task": "synthesize", "agent": "synthesizer", "depends_on": ["st-3"]},
                ]
            },
        )
        waves = self.supervisor.get_execution_waves(plan)
        assert len(waves[0]) == 2  # Both data_analyst tasks in parallel

    def test_mark_completed(self):
        plan = self.supervisor.create_default_plan("test")
        self.supervisor.mark_completed(plan, "st-1", {"data": "result"})
        assert plan.subtasks[0].status == SubTaskStatus.COMPLETED
        assert plan.subtasks[0].result == {"data": "result"}

    def test_mark_failed(self):
        plan = self.supervisor.create_default_plan("test")
        self.supervisor.mark_failed(plan, "st-1", "timeout")
        assert plan.subtasks[0].status == SubTaskStatus.FAILED
        assert plan.subtasks[0].error == "timeout"

    def test_format_tool_input_with_context(self):
        plan = self.supervisor.create_default_plan("test")
        plan.subtasks[0].status = SubTaskStatus.COMPLETED
        plan.subtasks[0].result = {"summary": "found 3 tables"}
        context = {"st-1": plan.subtasks[0].result}
        output = self.supervisor.format_tool_input(plan.subtasks[1], context)
        assert "found 3 tables" in output


class TestSynthesizer:
    def setup_method(self):
        self.synthesizer = SynthesizerAgent()

    def test_build_context(self):
        context = self.synthesizer.build_context(
            question="What is exposure?",
            analyst_results=[{
                "sql_queries": ["SELECT 1"],
                "tables_accessed": ["finserv_catalog.risk.portfolio_positions"],
                "summary": "Total exposure is $2.4B",
                "columns": ["sector", "total"],
                "rows": [["Technology", 2400000000]],
                "row_count": 1,
            }],
            validation_result={
                "is_valid": True,
                "confidence": "high",
                "checks_passed": ["non-empty"],
                "checks_failed": [],
                "notes": "",
            },
        )
        assert "What is exposure?" in context
        assert "$2.4B" in context
        assert "high" in context
