from enum import Enum

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    DATA_ANALYST = "data_analyst"
    VALIDATOR = "validator"
    SYNTHESIZER = "synthesizer"


class Platform(str, Enum):
    AGENTCORE = "agentcore"
    DATABRICKS = "databricks"


AGENT_PLATFORM_MAP = {
    AgentType.DATA_ANALYST: Platform.DATABRICKS,
    AgentType.VALIDATOR: Platform.DATABRICKS,
    AgentType.SYNTHESIZER: Platform.AGENTCORE,
}


class SubTaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SubTask(BaseModel):
    id: str = Field(description="Unique sub-task identifier (e.g., st-1)")
    task: str = Field(description="Natural language description of what to do")
    agent: AgentType = Field(description="Which agent handles this sub-task")
    depends_on: list[str] = Field(default_factory=list)
    status: SubTaskStatus = Field(default=SubTaskStatus.PENDING)
    result: dict | None = Field(default=None)
    error: str | None = Field(default=None)

    @property
    def platform(self) -> Platform:
        return AGENT_PLATFORM_MAP[self.agent]


class ExecutionPlan(BaseModel):
    question: str = Field(description="Original user question")
    subtasks: list[SubTask] = Field(description="Ordered list of sub-tasks")

    def ready_tasks(self) -> list[SubTask]:
        completed_ids = {st.id for st in self.subtasks if st.status == SubTaskStatus.COMPLETED}
        return [
            st
            for st in self.subtasks
            if st.status == SubTaskStatus.PENDING
            and all(dep in completed_ids for dep in st.depends_on)
        ]

    def all_completed(self) -> bool:
        return all(
            st.status in (SubTaskStatus.COMPLETED, SubTaskStatus.FAILED)
            for st in self.subtasks
        )
