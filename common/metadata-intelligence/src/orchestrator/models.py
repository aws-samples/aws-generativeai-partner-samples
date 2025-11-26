"""Data models for the RIV Metadata AI Orchestrator."""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class SourceType(str, Enum):
    """Available data source types."""
    AURORA = "aurora"
    OPENSEARCH = "opensearch"
    S3TABLES = "s3tables"


class SourceMetadata(BaseModel):
    """Metadata about a data source."""
    source_type: SourceType
    name: str
    description: str
    capabilities: List[str]
    performance_score: float = Field(ge=0.0, le=1.0)
    data_freshness: datetime
    connection_status: bool = True
    # Enhanced schema information for intelligent routing
    entities: List[str] = Field(default_factory=list)  # Table names, index names, etc.
    fields: List[str] = Field(default_factory=list)   # Column names, document fields, etc.
    data_types: Dict[str, str] = Field(default_factory=dict)  # Field -> data type mapping
    relationships: List[Dict[str, str]] = Field(default_factory=list)  # Foreign keys, etc.
    sample_queries: List[str] = Field(default_factory=list)  # Example queries this source handles


class ExecutionStep(BaseModel):
    """Represents one step in an execution plan."""
    step_id: str
    step_number: int
    description: str
    source_type: SourceType
    query: str
    depends_on: List[str] = Field(default_factory=list)
    result: Optional['ExecutionResult'] = None
    observation: Optional[Dict[str, Any]] = None


class ExecutionPlan(BaseModel):
    """Multi-step or single-step execution plan."""
    original_query: str
    steps: List[ExecutionStep]
    strategy: str = "sequential"  # "sequential", "parallel", "adaptive"
    metadata: Optional[Dict[str, Any]] = None


class QueryPlan(BaseModel):
    """Represents a translated query for execution by a data source."""
    original_query: str
    translated_query: str
    explanation: str = ""
    validation_passed: bool = True


class ExecutionResult(BaseModel):
    """Result of query execution from any data source."""
    success: bool
    source_type: SourceType
    data: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None


class AgentRequest(BaseModel):
    """User request to the orchestrator."""
    user_query: str
    context: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    """Orchestrator response with plan and execution results."""
    request: AgentRequest
    plan: Optional[QueryPlan] = None
    result: Optional[ExecutionResult] = None
    status: str
    message: str
