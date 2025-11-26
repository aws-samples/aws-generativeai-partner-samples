"""Orchestrator package for RIV Metadata AI with PLAN-AND-ACT pattern."""

from .agent import Orchestrator
from .models import (
    AgentRequest,
    AgentResponse,
    QueryPlan,
    ExecutionResult,
    ExecutionPlan,
    ExecutionStep,
    SourceType,
    SourceMetadata
)
from .planner import PlannerAgent
from .executor import ExecutorAgent
from .metadata_analyzer import MetadataAnalyzer

__all__ = [
    'Orchestrator',
    'AgentRequest',
    'AgentResponse',
    'QueryPlan',
    'ExecutionResult',
    'ExecutionPlan',
    'ExecutionStep',
    'SourceType',
    'SourceMetadata',
    'PlannerAgent',
    'ExecutorAgent',
    'MetadataAnalyzer'
]

__version__ = "0.2.0"
