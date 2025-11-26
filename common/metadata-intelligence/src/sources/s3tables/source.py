"""S3 Tables data source."""

import time
from typing import Dict, Any, List
from datetime import datetime
from ..base import BaseDataSource
from ...orchestrator.models import SourceMetadata, SourceType, QueryPlan, ExecutionResult
import boto3
import logging

logger = logging.getLogger(__name__)


class S3TablesSource(BaseDataSource):
    """S3 Tables data source for object metadata queries."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.warehouse = config.get('warehouse')
        self.region = config.get('region', 'us-east-1')
        self.namespace = config.get('namespace')
        self.s3_client = None
        self.s3tables_client = None
    
    async def initialize(self):
        """Initialize S3 Tables connection."""
        try:
            self.s3_client = boto3.client('s3', region_name=self.region)
            self.s3tables_client = boto3.client('s3tables', region_name=self.region)
            logger.info("S3 Tables source initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize S3 Tables source: {e}")
            return False
    
    async def close(self):
        """Close S3 Tables connection."""
        # boto3 clients don't need explicit closing
        pass
    
    async def health_check(self) -> bool:
        """Check S3 Tables health."""
        try:
            return self.s3_client is not None and self.s3tables_client is not None
        except Exception:
            return False
    
    async def execute_query(self, plan: QueryPlan) -> ExecutionResult:
        """Execute query against S3 Tables by listing objects with filters."""
        start_time = time.time()
        
        try:
            # Extract bucket name from warehouse ARN
            # Format: arn:aws:s3tables:region:account:bucket/bucket-name
            bucket_name = self.warehouse.split('/')[-1]
            
            # Get the actual S3 bucket name from namespace
            # Format: b_metaintel-source-20251124-122258 -> metaintel-source-20251124-122258
            s3_bucket = self.namespace.replace('b_', '').replace('_', '-')
            
            logger.info(f"Querying S3 bucket: {s3_bucket}")
            
            # List objects with car-images prefix
            response = self.s3_client.list_objects_v2(
                Bucket=s3_bucket,
                Prefix='car-images/',
                MaxKeys=5
            )
            
            # Convert to result format
            data = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    data.append({
                        'bucket': s3_bucket,
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'storage_class': obj.get('StorageClass', 'STANDARD')
                    })
            
            execution_time = (time.time() - start_time) * 1000
            logger.info(f"S3 query returned {len(data)} objects in {execution_time:.2f}ms")
            
            return ExecutionResult(
                success=True,
                source_type=SourceType.S3TABLES,
                data=data,
                metadata={
                    "query_type": "search",
                    "objects_returned": len(data),
                    "original_query": plan.original_query,
                    "translated_query": plan.translated_query
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"S3 query execution failed: {str(e)}", exc_info=True)
            
            return ExecutionResult(
                success=False,
                source_type=SourceType.S3TABLES,
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    async def get_metadata(self) -> SourceMetadata:
        """Get S3 Tables metadata."""
        return SourceMetadata(
            name="S3 Tables",
            source_type=SourceType.S3TABLES,
            connection_status=True,
            entities=["journal", "inventory"],
            fields=["bucket", "key", "size", "record_type", "object_tags", "user_metadata"],
            data_types={},
            capabilities=["s3_metadata", "object_metadata", "file_metadata", "tag_queries"],
            description="S3 Tables metadata for object tracking",
            performance_score=0.9,
            data_freshness=datetime.now()
        )
