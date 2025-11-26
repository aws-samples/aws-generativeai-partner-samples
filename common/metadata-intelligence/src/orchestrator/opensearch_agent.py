"""OpenSearch Agent using Strands framework."""

from typing import Dict, Any
from strands import Agent
from .models import AgentRequest, AgentResponse, QueryPlan, SourceType
from ..sources.opensearch.source import OpenSearchSource
import logging

logger = logging.getLogger(__name__)


class OpenSearchAgent(Agent):
    """OpenSearch Agent with natural language search capability."""
    
    def __init__(self, opensearch_config: Dict[str, Any]):
        super().__init__()
        self.opensearch_source = OpenSearchSource(opensearch_config)
        self._initialized = False
    
    async def initialize(self):
        """Initialize the OpenSearch agent."""
        if not self._initialized:
            opensearch_success = await self.opensearch_source.initialize()
            if not opensearch_success:
                raise RuntimeError("Failed to initialize OpenSearch source - check configuration and connectivity")
            
            logger.info("OpenSearch agent initialized successfully")
            self._initialized = True
    
    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """Process natural language search request."""
        await self.initialize()
        
        try:
            logger.info(f"Processing search query: '{request.user_query}'")
            
            # Translate to OpenSearch DSL
            opensearch_query = self._translate_to_opensearch(request.user_query)
            
            # Create query plan
            plan = QueryPlan(
                original_query=request.user_query,
                translated_query=opensearch_query,
                explanation="Translated to OpenSearch query",
                validation_passed=True
            )
            
            logger.info(f"OpenSearch query: {opensearch_query}")
            
            # Execute the search query
            result = await self.opensearch_source.execute_query(plan)
            
            status = "success" if result.success else "failed"
            
            # Enhanced result message
            if result.success:
                message = {
                    "data": result.data,
                    "translation": {
                        "original_query": request.user_query,
                        "opensearch_query": opensearch_query,
                        "query_type": "search"
                    },
                    "execution": {
                        "documents_returned": len(result.data) if result.data else 0,
                        "execution_time_ms": result.execution_time_ms
                    }
                }
            else:
                message = f"Search execution error: {result.error_message}"
            
            return AgentResponse(
                request=request,
                plan=plan,
                result=result,
                status=status,
                message=str(message)
            )
        
        except Exception as e:
            logger.error(f"OpenSearch agent error: {str(e)}")
            return AgentResponse(
                request=request,
                status="error",
                message=f"Error: {str(e)}"
            )
    
    def _translate_to_opensearch(self, query: str) -> str:
        """Translate natural language to OpenSearch DSL."""
        import json
        
        query_lower = query.lower()
        
        # Extract search terms
        search_terms = self._extract_search_terms(query_lower)
        
        # Build OpenSearch query based on query content
        if any(kw in query_lower for kw in ["count", "aggregate", "group"]):
            # Aggregation query
            opensearch_query = {
                "size": 0,
                "query": {"match_all": {}},
                "aggs": {
                    "results": {
                        "terms": {"field": "status", "size": 10}
                    }
                }
            }
        else:
            # Search query
            if search_terms:
                opensearch_query = {
                    "size": 10,
                    "query": {
                        "multi_match": {
                            "query": " ".join(search_terms),
                            "fields": ["*"]
                        }
                    }
                }
            else:
                opensearch_query = {
                    "size": 10,
                    "query": {"match_all": {}}
                }
        
        return json.dumps(opensearch_query)
    
    def _extract_search_terms(self, query: str) -> list:
        """Extract meaningful search terms from query."""
        # Remove common words
        stop_words = {"search", "find", "show", "get", "me", "all", "the", "for", "with", "from", "about"}
        words = query.split()
        return [w for w in words if w not in stop_words and len(w) > 2]
