"""OpenSearch data source implementation."""

import time
from typing import Dict, Any
from datetime import datetime
from ..base import BaseDataSource
from ...orchestrator.models import (
    SourceMetadata, ExecutionResult, AgentRequest, QueryPlan, 
    SourceType
)
from .client import OpenSearchClient
import logging

logger = logging.getLogger(__name__)


class OpenSearchSource(BaseDataSource):
    """OpenSearch data source implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = OpenSearchClient(config)
    
    async def initialize(self) -> bool:
        """Initialize OpenSearch client."""
        return await self.client.initialize()
    
    async def get_metadata(self) -> SourceMetadata:
        """Get OpenSearch metadata."""
        try:
            # Get basic index info for capabilities
            indices = await self.client.get_indices()
            
            # Extract entity names (index names)
            entities = indices if indices else []
            
            # Get field mappings if available
            fields = []
            data_types = {}
            
            try:
                if indices:
                    # Get mappings for first index as sample
                    mapping = await self.client.get_mapping(indices[0])
                    if mapping and "properties" in mapping:
                        for field_name, field_info in mapping["properties"].items():
                            fields.append(field_name)
                            data_types[field_name] = field_info.get("type", "unknown")
            except Exception as e:
                logger.warning(f"Could not retrieve field mappings: {str(e)}")
            
            return SourceMetadata(
                source_type=SourceType.OPENSEARCH,
                name="OpenSearch",
                description="OpenSearch cluster for full-text search and analytics",
                capabilities=[
                    "full_text_search",
                    "fuzzy_matching",
                    "aggregations",
                    "real_time_search",
                    "text_analytics"
                ],
                performance_score=0.8,
                data_freshness=datetime.now(),
                connection_status=await self.health_check(),
                entities=entities,
                fields=list(set(fields)),
                data_types=data_types,
                sample_queries=[
                    "Search for documents containing keyword",
                    "Find similar text",
                    "Match content patterns",
                    "Full text search"
                ]
            )
        except Exception as e:
            logger.error(f"Failed to get OpenSearch metadata: {str(e)}")
            return SourceMetadata(
                source_type=SourceType.OPENSEARCH,
                name="OpenSearch",
                description="OpenSearch cluster (connection failed)",
                capabilities=[],
                performance_score=0.0,
                data_freshness=datetime.now(),
                connection_status=False
            )
    
    async def execute_query(self, plan: QueryPlan) -> ExecutionResult:
        """Execute query against OpenSearch."""
        start_time = time.time()
        
        try:
            # Discover indices from metadata
            metadata = await self.get_metadata()
            available_indices = metadata.entities
            
            if not available_indices:
                raise ValueError("No indices available in OpenSearch")
            
            # Use all available indices for search (OpenSearch can handle multi-index searches efficiently)
            # In the future, could parse the query to determine specific indices
            indices_to_search = available_indices
            
            # Parse the translated query (should be OpenSearch DSL)
            if plan.translated_query.startswith('{'):
                # JSON query
                import json
                search_query = json.loads(plan.translated_query)
            else:
                # Simple text search
                search_query = {
                    "query": {
                        "multi_match": {
                            "query": plan.translated_query,
                            "fields": ["*"]
                        }
                    },
                    "size": 10
                }
            
            # Search across all selected indices
            all_data = []
            for index in indices_to_search:
                try:
                    result = await self.client.search(index, search_query)
                    hits = result.get("hits", {}).get("hits", [])
                    all_data.extend([hit.get("_source", {}) for hit in hits])
                except Exception as e:
                    logger.warning(f"Failed to search index {index}: {str(e)}")
            
            execution_time = (time.time() - start_time) * 1000
            
            return ExecutionResult(
                success=True,
                source_type=SourceType.OPENSEARCH,
                data=all_data,
                metadata={
                    "query_type": "search",
                    "indices_searched": indices_to_search,
                    "total_hits": len(all_data),
                    "original_query": plan.original_query,
                    "translated_query": plan.translated_query
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"OpenSearch query execution failed: {str(e)}")
            
            return ExecutionResult(
                success=False,
                source_type=SourceType.OPENSEARCH,
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    async def health_check(self) -> bool:
        """Check OpenSearch health."""
        return await self.client.health_check()
    
    async def close(self):
        """Close OpenSearch client."""
        await self.client.close()
