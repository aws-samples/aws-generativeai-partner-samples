from enum import Enum

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AnalystResult(BaseModel):
    """Structured result from the Data Analyst agent on Databricks."""

    sql_queries: list[str] = Field(description="SQL queries that were executed")
    columns: list[str] = Field(default_factory=list, description="Column names in primary result")
    rows: list[list] = Field(default_factory=list, description="Result rows")
    row_count: int = Field(default=0)
    tables_accessed: list[str] = Field(default_factory=list)
    summary: str = Field(default="", description="Agent's natural language summary of findings")
    execution_time_ms: int = Field(default=0)


class ValidationResult(BaseModel):
    """Structured result from the Validator agent on Databricks."""

    is_valid: bool = Field(description="Whether results passed all validation checks")
    confidence: ConfidenceLevel
    checks_passed: list[str] = Field(default_factory=list)
    checks_failed: list[str] = Field(default_factory=list)
    notes: str = Field(default="")


class SynthesizedAnswer(BaseModel):
    """Final answer from the Synthesizer agent on AgentCore."""

    summary: str = Field(description="Executive summary (2-3 sentences)")
    detailed_narrative: str = Field(description="Full narrative with supporting data")
    lineage: list[str] = Field(description="Tables/columns that contributed to the answer")
    confidence: ConfidenceLevel
    follow_up_questions: list[str] = Field(default_factory=list)
    disclaimer: str = Field(
        default=(
            "This analysis is for informational purposes only and does not constitute "
            "financial advice. Consult a qualified financial advisor before making "
            "investment decisions."
        )
    )
