"""S3 Tables Agent using Strands framework."""

from typing import Dict, Any
from strands import Agent
from .models import AgentRequest, AgentResponse, QueryPlan, SourceType
from ..sources.s3tables.source import S3TablesSource
import logging

logger = logging.getLogger(__name__)


class S3TablesAgent(Agent):
    """S3 Tables Agent with natural language query capability for S3 metadata."""
    
    def __init__(self, s3tables_config: Dict[str, Any]):
        super().__init__()
        self.s3tables_source = S3TablesSource(s3tables_config)
        self._initialized = False
    
    async def initialize(self):
        """Initialize the S3 Tables agent."""
        if not self._initialized:
            s3tables_success = await self.s3tables_source.initialize()
            if not s3tables_success:
                raise RuntimeError("Failed to initialize S3 Tables source - check configuration and connectivity")
            
            logger.info("S3 Tables agent initialized successfully")
            self._initialized = True
    
    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """Process natural language query request for S3 metadata."""
        await self.initialize()
        
        try:
            logger.info(f"Processing S3 metadata query: '{request.user_query}'")
            
            # Translate to SQL for S3 Tables
            sql_query = self._translate_to_sql(request.user_query)
            
            # Create query plan
            plan = QueryPlan(
                original_query=request.user_query,
                translated_query=sql_query,
                explanation="Translated to S3 Tables SQL query",
                validation_passed=True
            )
            
            logger.info(f"S3 Tables SQL: {sql_query}")
            
            # Execute the query using the source
            result = await self.s3tables_source.execute_query(plan)
            
            status = "success" if result.success else "failed"
            
            # Enhanced result message
            if result.success:
                message = {
                    "data": result.data,
                    "translation": {
                        "original_query": request.user_query,
                        "sql_query": sql_query,
                        "query_type": "search"
                    },
                    "execution": {
                        "rows_returned": len(result.data) if result.data else 0,
                        "execution_time_ms": result.execution_time_ms
                    }
                }
            else:
                message = f"Query execution error: {result.error_message}"
            
            return AgentResponse(
                request=request,
                plan=plan,
                result=result,
                status=status,
                message=str(message)
            )
        
        except Exception as e:
            logger.error(f"S3 Tables agent error: {str(e)}")
            return AgentResponse(
                request=request,
                status="error",
                message=f"Error: {str(e)}"
            )
    
    def _translate_to_sql(self, query: str) -> str:
        """Translate natural language to SQL for S3 Tables metadata."""
        query_lower = query.lower()
        
        # Extract search terms
        search_terms = self._extract_search_terms(query_lower)
        
        # Build SQL query for S3 metadata table based on search terms
        if any(kw in query_lower for kw in ["count", "aggregate", "group", "sum"]):
            # Aggregation query
            sql = "SELECT storage_class, COUNT(*) as count FROM inventory GROUP BY storage_class LIMIT 10"
        else:
            # Search query
            if search_terms:
                conditions = " OR ".join([f"key LIKE '%{term}%'" for term in search_terms])
                sql = f"SELECT bucket, key, size, last_modified_date, storage_class FROM inventory WHERE {conditions} LIMIT 10"
            else:
                sql = "SELECT bucket, key, size, last_modified_date, storage_class FROM inventory LIMIT 10"
        
        return sql
    
    def _extract_search_terms(self, query: str) -> list:
        """Extract meaningful search terms from query."""
        stop_words = {"search", "find", "show", "get", "me", "all", "the", "for", "with", "from", "about", "list"}
        words = query.split()
        return [w for w in words if w not in stop_words and len(w) > 2]
