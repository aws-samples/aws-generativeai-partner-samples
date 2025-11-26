"""PLAN-AND-ACT Executor Agent for step-by-step execution."""

import logging
from typing import Dict, Any, Tuple, Optional
from .models import AgentRequest, ExecutionStep, ExecutionResult, SourceType
from .aurora_agent import AuroraAgent
from .opensearch_agent import OpenSearchAgent
from .s3tables_agent import S3TablesAgent

logger = logging.getLogger(__name__)


class ExecutorAgent:
    """
    PLAN-AND-ACT Executor Agent.
    
    Translates high-level plan steps into immediate actions:
    - Executes ONE step at a time
    - Routes to appropriate agent (Aurora, OpenSearch, or S3 Tables)
    - Returns detailed observations for re-planning
    - Does NOT self-assess overall goal completion (that's Planner's job)
    """
    
    def __init__(self, aurora_agent: AuroraAgent, opensearch_agent: OpenSearchAgent, s3tables_agent: Optional[S3TablesAgent] = None):
        self.aurora_agent = aurora_agent
        self.opensearch_agent = opensearch_agent
        self.s3tables_agent = s3tables_agent
        logger.info("ExecutorAgent initialized")
    
    async def execute_step(
        self,
        step: ExecutionStep,
        context_from_previous_steps: Dict[str, Any]
    ) -> Tuple[ExecutionResult, Dict[str, Any]]:
        """
        Execute ONE step and return observation.
        
        Args:
            step: The execution step to perform
            context_from_previous_steps: Data and results from previous steps
            
        Returns:
            Tuple of (ExecutionResult, observation_dict)
        """
        logger.info(f"=== Executing Step {step.step_number}: {step.description} ===")
        logger.info(f"Source: {step.source_type.value}")
        logger.info(f"Query: {step.query}")
        
        # Select appropriate agent
        if step.source_type == SourceType.AURORA:
            agent = self.aurora_agent
        elif step.source_type == SourceType.S3TABLES:
            if not self.s3tables_agent:
                raise RuntimeError("S3 Tables agent not configured")
            agent = self.s3tables_agent
        else:
            agent = self.opensearch_agent
        
        # Create request with context
        request = AgentRequest(
            user_query=step.query,
            context={
                **context_from_previous_steps,
                "step_description": step.description,
                "step_number": step.step_number,
                "source_type": step.source_type.value
            }
        )
        
        # Execute through agent
        try:
            response = await agent.process_request(request)
            
            # Build observation for Planner
            observation = {
                "step_number": step.step_number,
                "step_id": step.step_id,
                "source_used": step.source_type.value,
                "success": response.status == "success",
                "data_retrieved": response.result.data if response.result else None,
                "row_count": len(response.result.data) if response.result and response.result.data else 0,
                "execution_time_ms": response.result.execution_time_ms if response.result else None,
                "error": response.result.error_message if response.result and not response.result.success else None,
                "metadata": response.result.metadata if response.result else None
            }
            
            # Log execution summary
            if observation["success"]:
                logger.info(f"✓ Step {step.step_number} completed: {observation['row_count']} rows in {observation['execution_time_ms']}ms")
            else:
                logger.error(f"✗ Step {step.step_number} failed: {observation['error']}")
            
            return response.result if response.result else self._create_error_result(step, "No result returned"), observation
            
        except Exception as e:
            logger.error(f"Error executing step {step.step_number}: {e}", exc_info=True)
            
            # Create error observation
            observation = {
                "step_number": step.step_number,
                "step_id": step.step_id,
                "source_used": step.source_type.value,
                "success": False,
                "data_retrieved": None,
                "row_count": 0,
                "execution_time_ms": None,
                "error": str(e),
                "metadata": None
            }
            
            return self._create_error_result(step, str(e)), observation
    
    def _create_error_result(self, step: ExecutionStep, error_message: str) -> ExecutionResult:
        """Create an error ExecutionResult."""
        return ExecutionResult(
            success=False,
            source_type=step.source_type,
            data=None,
            metadata={"step_number": step.step_number, "step_id": step.step_id},
            error_message=error_message,
            execution_time_ms=None
        )
