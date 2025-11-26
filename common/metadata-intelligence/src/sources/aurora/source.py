"""Aurora data source implementation."""

import time
from typing import Dict, Any
from datetime import datetime
from ..base import BaseDataSource
from ...orchestrator.models import (
    SourceMetadata, ExecutionResult, AgentRequest, QueryPlan, 
    SourceType
)
from .connection import AuroraConnection
import logging

logger = logging.getLogger(__name__)


class AuroraSource(BaseDataSource):
    """Aurora data source implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connection = AuroraConnection(config)
    
    async def initialize(self) -> bool:
        """Initialize Aurora connection."""
        try:
            await self.connection.initialize()
            logger.info("Aurora source initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Aurora source initialization failed: {str(e)}")
            return False
    
    async def get_metadata(self) -> SourceMetadata:
        """Get Aurora metadata with detailed schema information."""
        try:
            # Get table information
            tables = await self.connection.get_table_info()
            
            # Extract entity names (table names)
            entities = [f"{t['schemaname']}.{t['tablename']}" for t in tables]
            
            # Get detailed schema if available
            fields = []
            data_types = {}
            try:
                # Get column information for all tables
                column_query = """
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                ORDER BY table_name, ordinal_position
                """
                columns = await self.connection.execute_query(column_query)
                
                for col in columns:
                    field_name = f"{col['table_name']}.{col['column_name']}"
                    fields.append(col['column_name'])
                    data_types[field_name] = col['data_type']
            except Exception as e:
                logger.warning(f"Could not retrieve detailed column info: {str(e)}")
            
            return SourceMetadata(
                source_type=SourceType.AURORA,
                name="Aurora PostgreSQL",
                description="AWS Aurora PostgreSQL database for structured data queries",
                capabilities=[
                    "sql_queries",
                    "joins",
                    "aggregations", 
                    "transactions",
                    "analytical_queries"
                ],
                performance_score=0.8,
                data_freshness=datetime.now(),
                connection_status=await self.health_check(),
                entities=entities,
                fields=list(set(fields)),
                data_types=data_types,
                sample_queries=[
                    "SELECT * FROM customers",
                    "COUNT records by category",
                    "JOIN orders with customers",
                    "Analyze sales trends"
                ]
            )
        except Exception as e:
            logger.error(f"Failed to get Aurora metadata: {str(e)}")
            return SourceMetadata(
                source_type=SourceType.AURORA,
                name="Aurora PostgreSQL",
                description="AWS Aurora PostgreSQL database (connection failed)",
                capabilities=[],
                performance_score=0.0,
                data_freshness=datetime.now(),
                connection_status=False
            )
    
    async def execute_query(self, plan: QueryPlan) -> ExecutionResult:
        """Execute query against Aurora."""
        start_time = time.time()
        
        try:
            # Execute the translated query
            data = await self.connection.execute_query(plan.translated_query)
            
            execution_time = (time.time() - start_time) * 1000
            
            return ExecutionResult(
                success=True,
                source_type=SourceType.AURORA,
                data=data,
                metadata={
                    "query_type": "sql",
                    "rows_returned": len(data),
                    "original_query": plan.original_query,
                    "translated_query": plan.translated_query
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Aurora query execution failed: {str(e)}")
            
            return ExecutionResult(
                success=False,
                source_type=SourceType.AURORA,
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    async def health_check(self) -> bool:
        """Check Aurora health."""
        return await self.connection.health_check()
    
    async def close(self):
        """Close Aurora connection."""
        await self.connection.close()
