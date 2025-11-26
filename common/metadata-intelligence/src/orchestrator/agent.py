"""RIV Metadata AI Orchestrator with PLAN-AND-ACT pattern."""

import asyncio
import os
from datetime import datetime
from .config import get_aurora_config, get_opensearch_config, get_s3tables_config
from typing import Optional, Dict, Any, List
from bedrock_agentcore import BedrockAgentCoreApp
from .models import AgentRequest, AgentResponse, ExecutionResult, ExecutionPlan, ExecutionStep, SourceType
from .metadata_analyzer import MetadataAnalyzer
from .planner import PlannerAgent
from .executor import ExecutorAgent
from ..sources.aurora.source import AuroraSource
from ..sources.opensearch.source import OpenSearchSource
from ..sources.s3tables.source import S3TablesSource
from .aurora_agent import AuroraAgent
from .opensearch_agent import OpenSearchAgent
from .s3tables_agent import S3TablesAgent
import logging

logger = logging.getLogger(__name__)
logger.info("=== ORCHESTRATOR WITH PLAN-AND-ACT PATTERN ===")


class Orchestrator:
    """RIV Metadata AI Orchestrator with PLAN-AND-ACT pattern."""
    
    def __init__(self, aurora_config: Dict[str, Any], opensearch_config: Dict[str, Any], s3tables_config: Dict[str, Any] = None, memory_config: Optional[Any] = None):
        # Initialize data sources (for metadata only)
        self.aurora_source = AuroraSource(aurora_config)
        self.opensearch_source = OpenSearchSource(opensearch_config)
        self.s3tables_source = S3TablesSource(s3tables_config) if s3tables_config else None
        
        # Initialize agent tools (for execution)
        self.aurora_agent = AuroraAgent(aurora_config)
        self.opensearch_agent = OpenSearchAgent(opensearch_config)
        self.s3tables_agent = S3TablesAgent(s3tables_config) if s3tables_config else None
        
        # Initialize metadata analyzer
        self.metadata_analyzer = MetadataAnalyzer(self.aurora_source, self.opensearch_source, self.s3tables_source)
        
        # Initialize PLAN-AND-ACT components with optional memory
        self.planner = PlannerAgent(self.metadata_analyzer, memory_config)
        self.executor = ExecutorAgent(self.aurora_agent, self.opensearch_agent, self.s3tables_agent)
        
        self._initialized = False
        
        # Log memory status
        if memory_config:
            logger.info(f"AgentCore Memory enabled - Memory ID: {getattr(memory_config, 'memory_id', 'unknown')}")
        else:
            logger.info("AgentCore Memory not configured - using session-only memory")
    
    async def initialize(self):
        """Initialize the orchestrator and its components."""
        if not self._initialized:
            # Initialize data sources (for metadata)
            aurora_success = await self.aurora_source.initialize()
            opensearch_success = await self.opensearch_source.initialize()
            
            # Initialize agent tools (for execution)
            await self.aurora_agent.initialize()
            await self.opensearch_agent.initialize()
            if self.s3tables_agent:
                await self.s3tables_agent.initialize()
            
            logger.info(f"Aurora source initialized: {aurora_success}")
            logger.info(f"OpenSearch source initialized: {opensearch_success}")
            logger.info("Aurora agent initialized")
            logger.info("OpenSearch agent initialized")
            if self.s3tables_agent:
                logger.info("S3 Tables agent initialized")
            logger.info("PLAN-AND-ACT components ready")
            
            self._initialized = True
    
    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """
        Process request using PLAN-AND-ACT pattern.
        
        Execution loop:
        1. Plan → 2. Execute step → 3. Observe → 4. Re-plan → repeat
        """
        await self.initialize()
        
        logger.info(f"=== PLAN-AND-ACT: Processing '{request.user_query}' ===")
        
        try:
            # PHASE 1: Initial Planning
            current_plan = await self.planner.create_initial_plan(request)
            logger.info(f"Initial plan: {len(current_plan.steps)} steps, strategy: {current_plan.strategy}")
            
            # Track execution
            completed_steps = []
            all_results = []
            context = {}
            max_iterations = 20  # Safety limit
            
            # PHASE 2: Execution Loop with Continuous Re-planning
            iteration = 0
            while current_plan.steps and iteration < max_iterations:
                iteration += 1
                
                # Execute NEXT step
                next_step = current_plan.steps[0]
                logger.info(f"=== Iteration {iteration}: Executing step {next_step.step_number} ===")
                
                result, observation = await self.executor.execute_step(
                    next_step,
                    context
                )
                
                # Update tracking
                next_step.result = result
                next_step.observation = observation
                completed_steps.append(next_step)
                all_results.append(result)
                
                # Update context for next steps
                if result.success and result.data:
                    context[f"step_{next_step.step_number}_data"] = result.data
                    context[f"step_{next_step.step_number}_row_count"] = len(result.data)
                    # Store sample of data for re-planning context
                    context[f"step_{next_step.step_number}_sample"] = result.data[:3] if len(result.data) > 3 else result.data
                
                # CRITICAL: Re-plan after EVERY step
                remaining_steps = current_plan.steps[1:]  # Remove executed step
                
                if remaining_steps or iteration == 1:  # Always re-plan after first step
                    logger.info(f"=== Re-planning based on observation ===")
                    current_plan = await self.planner.replan(
                        original_request=request,
                        completed_steps=completed_steps,
                        remaining_steps=remaining_steps,
                        latest_observation=observation
                    )
                    
                    # Check if Planner says we're done
                    if not current_plan.steps:
                        logger.info("✓ Planner determined goal is complete")
                        break
                else:
                    # No more steps and not first iteration - we're done
                    logger.info("✓ All steps completed")
                    break
            
            if iteration >= max_iterations:
                logger.warning(f"Reached maximum iterations ({max_iterations})")
            
            # PHASE 3: Aggregate Results
            final_result = self._aggregate_results(
                request,
                completed_steps,
                all_results
            )
            
            return AgentResponse(
                request=request,
                plan=None,  # ExecutionPlan, not QueryPlan
                result=final_result,
                status="success" if final_result.success else "failed",
                message=self._format_final_message(completed_steps, final_result)
            )
        
        except Exception as e:
            logger.error(f"PLAN-AND-ACT error: {str(e)}", exc_info=True)
            return AgentResponse(
                request=request,
                status="error",
                message=f"Orchestrator error: {str(e)}"
            )
    
    def _aggregate_results(
        self,
        request: AgentRequest,
        completed_steps: List[ExecutionStep],
        results: List[ExecutionResult]
    ) -> ExecutionResult:
        """Combine results from all steps."""
        if not results:
            return ExecutionResult(
                success=False,
                source_type=SourceType.AURORA,
                error_message="No steps executed"
            )
        
        # If single step, ensure it has proper metadata
        if len(results) == 1:
            result = results[0]
            # Ensure metadata exists with execution details
            if not result.metadata:
                result.metadata = {}
            result.metadata.update({
                "steps_executed": 1,
                "total_rows": len(result.data) if result.data else 0,
                "sources_used": [completed_steps[0].source_type.value],
                "execution_strategy": "plan_and_act"
            })
            return result
        
        # Multi-step: combine data
        combined_data = []
        total_time = 0
        sources_used = set()
        
        for i, result in enumerate(results):
            if result.success and result.data:
                # Add step context to each row
                for row in result.data:
                    row['_step_number'] = i + 1
                combined_data.extend(result.data)
            if result.execution_time_ms:
                total_time += result.execution_time_ms
            sources_used.add(completed_steps[i].source_type.value)
        
        return ExecutionResult(
            success=all(r.success for r in results),
            source_type=SourceType.AURORA,  # Mixed
            data=combined_data,
            metadata={
                "steps_executed": len(completed_steps),
                "total_rows": len(combined_data),
                "sources_used": list(sources_used),
                "execution_strategy": "plan_and_act"
            },
            execution_time_ms=total_time
        )
    
    def _format_final_message(
        self,
        completed_steps: List[ExecutionStep],
        final_result: ExecutionResult
    ) -> str:
        """Format final response message."""
        if not final_result.success:
            return f"Query execution failed: {final_result.error_message}"
        
        steps_summary = "\n".join([
            f"Step {step.step_number}: {step.description} "
            f"[{step.source_type.value}, {step.observation.get('row_count', 0)} rows]"
            for step in completed_steps
        ])
        
        return f"""Query completed successfully using PLAN-AND-ACT pattern.

Execution Summary:
{steps_summary}

Total Results: {len(final_result.data) if final_result.data else 0} rows
Total Time: {final_result.execution_time_ms}ms
Sources Used: {', '.join(final_result.metadata.get('sources_used', []))}"""
    
    async def get_source_metadata(self):
        """Get metadata from all available sources."""
        await self.initialize()
        
        aurora_metadata = await self.aurora_source.get_metadata()
        opensearch_metadata = await self.opensearch_source.get_metadata()
        
        return {
            "aurora": aurora_metadata.dict(),
            "opensearch": opensearch_metadata.dict()
        }
    
    async def health_check(self):
        """Check health of all data sources."""
        await self.initialize()
        
        return {
            "aurora": await self.aurora_source.health_check(),
            "opensearch": await self.opensearch_source.health_check()
        }
    
    async def close(self):
        """Close all data source connections."""
        await self.aurora_source.close()
        await self.opensearch_source.close()


# AgentCore Integration
app = BedrockAgentCoreApp()
orchestrator = None

async def get_orchestrator():
    """Get or initialize Orchestrator."""
    global orchestrator
    if orchestrator is None:
        # Aurora configuration from Secrets Manager
        aurora_cfg = get_aurora_config()
        aurora_config = {
            "cluster_arn": aurora_cfg["cluster_arn"],
            "secret_arn": aurora_cfg["credentials_secret_arn"],
            "database": aurora_cfg.get("database", "postgres"),
            "use_data_api": aurora_cfg.get("use_data_api", True),
            # Legacy connection parameters (fallback)
            "host": aurora_cfg.get("endpoint"),
            "port": aurora_cfg.get("port", 5432)
        }
        
        # OpenSearch configuration from Secrets Manager
        opensearch_cfg = get_opensearch_config()
        opensearch_config = {
            "host": opensearch_cfg["endpoint"],
            "region": os.getenv("AWS_REGION", "us-east-1"),
            "use_aws_auth": True  # Always use AWS auth for Serverless
        }
        
        # S3 Tables configuration
        # S3 Tables configuration from Secrets Manager
        s3tables_cfg = get_s3tables_config()
        s3tables_config = None
        if s3tables_cfg:
            s3tables_config = {
                "warehouse": s3tables_cfg["warehouse"],
                "region": s3tables_cfg.get("region", os.getenv("AWS_REGION", "us-east-1")),
                "namespace": s3tables_cfg["namespace"],
                "uri": s3tables_cfg.get("uri", f"https://s3tables.{s3tables_cfg.get('region', 'us-east-1')}.amazonaws.com/iceberg")
            }
            logger.info(f"S3 Tables config loaded from secret: {s3tables_config}")
        else:
            logger.warning("S3 Tables config not found in secret")
        
        # Configure AgentCore Memory if MEMORY_ID is set
        memory_config = None
        memory_id = os.getenv("AGENTCORE_MEMORY_ID")
        if memory_id:
            try:
                from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
                memory_config = AgentCoreMemoryConfig(
                    memory_id=memory_id,
                    session_id=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    actor_id=os.getenv("AGENTCORE_ACTOR_ID", "default_user")
                )
                logger.info(f"Memory config created for Memory ID: {memory_id}")
            except ImportError:
                logger.warning("bedrock-agentcore[strands-agents] not installed - memory will be disabled")
            except Exception as e:
                logger.warning(f"Failed to create memory config: {e}")
        
        orchestrator = Orchestrator(aurora_config, opensearch_config, s3tables_config, memory_config)
        await orchestrator.initialize()
    return orchestrator

@app.entrypoint
def invoke(payload):
    """AgentCore entry point."""
    try:
        user_query = payload.get("prompt", "Hello! How can I help you today?")
        context = payload.get("context", {})
        
        request = AgentRequest(user_query=user_query, context=context)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            agent = loop.run_until_complete(get_orchestrator())
            response = loop.run_until_complete(agent.process_request(request))
            
            # Build comprehensive response with data
            result = {
                "message": response.message,
                "status": response.status
            }
            
            # Include actual data and metadata if available
            if response.result:
                result["data"] = response.result.data
                result["metadata"] = response.result.metadata
                result["row_count"] = len(response.result.data) if response.result.data else 0
                result["execution_time_ms"] = response.result.execution_time_ms
                result["source_type"] = response.result.source_type.value if response.result.source_type else None
            
            return result
        finally:
            loop.close()
            
    except Exception as e:
        return {
            "message": f"Error: {str(e)}",
            "status": "error",
            "data": None,
            "metadata": None
        }

if __name__ == "__main__":
    app.run()
