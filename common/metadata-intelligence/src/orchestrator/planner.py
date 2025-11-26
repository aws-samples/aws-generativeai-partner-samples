"""PLAN-AND-ACT Planner Agent for intelligent query planning."""

import json
import logging
from typing import List, Dict, Any, Optional
from strands import Agent
from .models import AgentRequest, ExecutionPlan, ExecutionStep, SourceType
from .metadata_analyzer import MetadataAnalyzer

logger = logging.getLogger(__name__)


class PlannerAgent(Agent):
    """
    PLAN-AND-ACT Planner Agent.
    
    Determines the "what" and "why" of query execution:
    - Creates initial full plan for goal achievement
    - Re-plans after each execution step based on observations
    - Uses MetadataAnalyzer for intelligent source selection
    - Supports AgentCore Memory for long-term learning
    """
    
    def __init__(self, metadata_analyzer: MetadataAnalyzer, memory_config: Optional[Any] = None):
        self.metadata_analyzer = metadata_analyzer
        
        # Initialize session manager for AgentCore Memory if configured
        session_manager = None
        if memory_config:
            try:
                from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
                session_manager = AgentCoreMemorySessionManager(
                    agentcore_memory_config=memory_config,
                    region_name=getattr(memory_config, 'region', 'us-east-1')
                )
                logger.info("AgentCore Memory enabled for PlannerAgent")
            except ImportError:
                logger.warning("bedrock-agentcore[strands-agents] not installed - memory disabled")
            except Exception as e:
                logger.warning(f"Failed to initialize memory: {e}")
        
        system_prompt = """You are a data query planner following the PLAN-AND-ACT methodology.

Your role is to determine the "what" and "why" of actions:
- WHAT data to retrieve (tables, indices, fields)
- WHY each step is needed (purpose, dependencies)
- HOW steps connect (data flow between steps)

You plan for two data sources:
1. Aurora: PostgreSQL database with structured data, supports SQL queries, joins, aggregations
2. OpenSearch: Search engine for logs, documents, full-text search capabilities

Create plans with clear high-level steps. Each step should specify:
- Which source to use (aurora or opensearch)
- What query to execute (in natural language - executor will translate)
- Why this step is needed
- What data dependencies exist

Always output valid JSON in this format:
{
  "steps": [
    {
      "step_number": 1,
      "description": "Brief description of what and why",
      "source": "aurora or opensearch",
      "query": "Natural language query",
      "depends_on_steps": []
    }
  ],
  "reasoning": "Overall plan reasoning"
}

You will be called after EVERY execution step to re-plan based on new observations."""
        
        super().__init__(
            name="planner",
            system_prompt=system_prompt,
            session_manager=session_manager
        )
    
    async def create_initial_plan(self, request: AgentRequest) -> ExecutionPlan:
        """Create initial full plan for the user query."""
        logger.info(f"Creating initial plan for: {request.user_query}")
        
        # Use MetadataAnalyzer for source intelligence
        primary_source, confidence = await self.metadata_analyzer.select_best_source(request)
        
        prompt = f"""Create a complete execution plan for this query:

Query: "{request.user_query}"

Recommended starting source: {primary_source.value} (confidence: {confidence:.2f})

Analyze the query and create a plan. For simple single-source queries, create a 1-step plan.
For complex queries requiring multiple sources or steps, create a multi-step plan.

Output JSON plan."""
        
        try:
            response = await self.invoke_async(prompt)
            plan_dict = self._extract_json_from_response(response)
            
            # Convert to ExecutionPlan
            steps = []
            for step_data in plan_dict.get("steps", []):
                source_type = SourceType.AURORA if step_data["source"].lower() == "aurora" else SourceType.OPENSEARCH
                
                step = ExecutionStep(
                    step_id=f"step_{step_data['step_number']}",
                    step_number=step_data["step_number"],
                    description=step_data["description"],
                    source_type=source_type,
                    query=step_data["query"],
                    depends_on=[f"step_{dep}" for dep in step_data.get("depends_on_steps", [])]
                )
                steps.append(step)
            
            plan = ExecutionPlan(
                original_query=request.user_query,
                steps=steps,
                strategy="plan_and_act",
                metadata={
                    "reasoning": plan_dict.get("reasoning", ""),
                    "initial_source_recommendation": primary_source.value,
                    "confidence": confidence
                }
            )
            
            logger.info(f"Initial plan created with {len(steps)} steps")
            return plan
            
        except Exception as e:
            logger.error(f"Error creating initial plan: {e}", exc_info=True)
            # Fallback to simple single-step plan
            return self._create_fallback_plan(request, primary_source)
    
    async def replan(
        self,
        original_request: AgentRequest,
        completed_steps: List[ExecutionStep],
        remaining_steps: List[ExecutionStep],
        latest_observation: Dict[str, Any]
    ) -> ExecutionPlan:
        """Re-plan based on latest observations - called after EVERY step."""
        logger.info(f"Re-planning after step {completed_steps[-1].step_number}")
        
        prompt = f"""Re-plan based on the latest execution results.

Original Query: "{original_request.user_query}"

Completed Steps:
{self._format_completed_steps(completed_steps)}

Latest Observation from Step {completed_steps[-1].step_number}:
- Source used: {latest_observation.get('source_used')}
- Success: {latest_observation.get('success')}
- Rows retrieved: {latest_observation.get('row_count', 0)}
- Execution time: {latest_observation.get('execution_time_ms', 0)}ms
{f"- Error: {latest_observation.get('error')}" if latest_observation.get('error') else ""}

Previous Remaining Steps:
{self._format_remaining_steps(remaining_steps)}

Based on what we now know from the execution:
1. Do we have enough data to complete the user's goal?
2. What steps (if any) still need to be done?
3. Should we adjust the approach based on the results?

If the goal is complete, return an empty steps array.
Otherwise, return the updated plan with remaining steps.

Output JSON plan."""
        
        try:
            response = await self.invoke_async(prompt)
            plan_dict = self._extract_json_from_response(response)
            
            # Convert to ExecutionPlan
            steps = []
            for step_data in plan_dict.get("steps", []):
                source_type = SourceType.AURORA if step_data["source"].lower() == "aurora" else SourceType.OPENSEARCH
                
                step = ExecutionStep(
                    step_id=f"step_{step_data['step_number']}",
                    step_number=step_data["step_number"],
                    description=step_data["description"],
                    source_type=source_type,
                    query=step_data["query"],
                    depends_on=[f"step_{dep}" for dep in step_data.get("depends_on_steps", [])]
                )
                steps.append(step)
            
            plan = ExecutionPlan(
                original_query=original_request.user_query,
                steps=steps,
                strategy="plan_and_act_replan",
                metadata={
                    "reasoning": plan_dict.get("reasoning", ""),
                    "replan_iteration": len(completed_steps)
                }
            )
            
            logger.info(f"Re-planned: {len(steps)} steps remaining")
            return plan
            
        except Exception as e:
            logger.error(f"Error re-planning: {e}", exc_info=True)
            # If re-planning fails, assume goal is complete
            return ExecutionPlan(
                original_query=original_request.user_query,
                steps=[],
                strategy="plan_and_act_complete",
                metadata={"error": str(e)}
            )
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        try:
            # Try to parse the entire response as JSON
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError("No valid JSON found in response")
    
    def _format_completed_steps(self, completed_steps: List[ExecutionStep]) -> str:
        """Format completed steps for prompt."""
        if not completed_steps:
            return "None"
        
        formatted = []
        for step in completed_steps:
            status = "✓ Success" if step.observation and step.observation.get("success") else "✗ Failed"
            row_count = step.observation.get("row_count", 0) if step.observation else 0
            formatted.append(
                f"Step {step.step_number}: {step.description} [{status}, {row_count} rows]\n"
                f"  Source: {step.source_type.value}, Query: {step.query}"
            )
        return "\n".join(formatted)
    
    def _format_remaining_steps(self, remaining_steps: List[ExecutionStep]) -> str:
        """Format remaining steps for prompt."""
        if not remaining_steps:
            return "None - this was the final step"
        
        formatted = []
        for step in remaining_steps:
            formatted.append(
                f"Step {step.step_number}: {step.description}\n"
                f"  Source: {step.source_type.value}, Query: {step.query}"
            )
        return "\n".join(formatted)
    
    def _create_fallback_plan(self, request: AgentRequest, source_type: SourceType) -> ExecutionPlan:
        """Create a simple fallback plan when LLM planning fails."""
        logger.warning("Using fallback plan")
        
        step = ExecutionStep(
            step_id="step_1",
            step_number=1,
            description=f"Execute query on {source_type.value}",
            source_type=source_type,
            query=request.user_query,
            depends_on=[]
        )
        
        return ExecutionPlan(
            original_query=request.user_query,
            steps=[step],
            strategy="fallback",
            metadata={"fallback": True}
        )
