"""Aurora-only SQL Agent using Strands framework."""

from typing import Dict, Any
from strands import Agent
from .models import AgentRequest, AgentResponse, QueryPlan, SourceType
from ..sources.aurora.source import AuroraSource
from ..sources.aurora.schema_provider import SchemaProvider
from ..sources.aurora.sql_generator import SQLGenerator
import logging

logger = logging.getLogger(__name__)


class AuroraAgent(Agent):
    """Aurora-only SQL Agent with Natural Language to SQL capability."""
    
    def __init__(self, aurora_config: Dict[str, Any]):
        super().__init__()
        self.aurora_source = AuroraSource(aurora_config)
        self.schema_provider = None
        self.sql_generator = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the Aurora agent and SQL generation components."""
        if not self._initialized:
            aurora_success = await self.aurora_source.initialize()
            if not aurora_success:
                raise RuntimeError("Failed to initialize Aurora source - check configuration and connectivity")
            
            # Initialize schema provider and SQL generator
            self.schema_provider = SchemaProvider(self.aurora_source.connection)
            self.sql_generator = SQLGenerator(self.schema_provider)
            
            logger.info("Aurora agent with natural language processing initialized successfully")
            self._initialized = True
    
    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """Process natural language query request and generate SQL."""
        await self.initialize()
        
        try:
            # Generate SQL from natural language query
            logger.info(f"Processing natural language query: '{request.user_query}'")
            sql_generation_result = await self.sql_generator.generate_sql(request.user_query)
            
            if not sql_generation_result["success"]:
                return AgentResponse(
                    request=request,
                    status="error",
                    message=f"Failed to generate SQL: {sql_generation_result.get('error', 'Unknown error')}"
                )
            
            generated_sql = sql_generation_result["sql"]
            
            # Validate the generated SQL
            validation_result = self.sql_generator.validate_sql_syntax(generated_sql)
            if not validation_result["valid"]:
                error_msg = f"Generated SQL validation failed: {', '.join(validation_result['errors'])}"
                logger.error(error_msg)
                return AgentResponse(
                    request=request,
                    status="error",
                    message=error_msg
                )
            
            # Create query plan with translation
            plan = QueryPlan(
                original_query=request.user_query,
                translated_query=generated_sql,
                explanation=f"Translated natural language query to SQL: {sql_generation_result.get('explanation', '')}",
                validation_passed=True
            )
            
            logger.info(f"Generated SQL: {generated_sql}")
            
            # Execute the generated SQL query
            result = await self.aurora_source.execute_query(plan)
            
            status = "success" if result.success else "failed"
            
            # Enhanced result message with translation details
            if result.success:
                message = {
                    "data": result.data,
                    "translation": {
                        "original_query": request.user_query,
                        "generated_sql": generated_sql,
                        "explanation": sql_generation_result.get("explanation", ""),
                        "confidence": sql_generation_result.get("confidence", 0.8)
                    },
                    "execution": {
                        "rows_returned": len(result.data) if result.data else 0,
                        "execution_time_ms": result.execution_time_ms
                    }
                }
            else:
                message = f"SQL execution error: {result.error_message}"
            
            return AgentResponse(
                request=request,
                plan=plan,
                result=result,
                status=status,
                message=str(message)
            )
        
        except Exception as e:
            logger.error(f"Aurora agent error: {str(e)}")
            return AgentResponse(
                request=request,
                status="error",
                message=f"Error: {str(e)}"
            )
