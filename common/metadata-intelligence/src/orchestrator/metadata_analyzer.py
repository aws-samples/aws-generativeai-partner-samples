"""Metadata-driven analyzer for intelligent source selection."""

from typing import List, Dict, Any, Tuple, Set, Optional
from .models import AgentRequest, SourceType, SourceMetadata
from ..sources.base import BaseDataSource
import logging
import re
import json
import boto3

logger = logging.getLogger(__name__)


class MetadataAnalyzer:
    """Analyzes queries using actual metadata and schema information for intelligent routing."""
    
    def __init__(self, aurora_source: BaseDataSource, opensearch_source: BaseDataSource, s3tables_source: Optional[BaseDataSource] = None):
        self.aurora_source = aurora_source
        self.opensearch_source = opensearch_source
        self.s3tables_source = s3tables_source
        self._metadata_cache: Dict[SourceType, SourceMetadata] = {}
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    async def _llm_route_decision(self, request: AgentRequest, aurora_meta: SourceMetadata, opensearch_meta: SourceMetadata, s3tables_meta: SourceMetadata = None) -> Tuple[SourceType, float]:
        """Use LLM to make routing decision based on metadata."""
        logger.info("Starting LLM-based routing decision")
        
        s3tables_info = ""
        if s3tables_meta:
            s3tables_info = f"""
S3 Tables (Object Metadata):
- Entities: {', '.join(s3tables_meta.entities)}
- Sample fields: {', '.join(s3tables_meta.fields[:20])}
- Capabilities: file metadata, object tags, image/document tracking
"""
        
        prompt = f"""Given a user query and metadata about data sources, determine which source is best suited to answer the query.

User Query: {request.user_query}

Aurora (SQL Database):
- Tables: {', '.join(aurora_meta.entities[:10])}
- Sample fields: {', '.join(aurora_meta.fields[:20])}
- Capabilities: structured queries, joins, aggregations

OpenSearch (Search Engine):
- Indices: {', '.join(opensearch_meta.entities)}
- Sample fields: {', '.join(opensearch_meta.fields[:20])}
- Capabilities: full-text search, log analysis, document search
{s3tables_info}
Respond with JSON only:
{{"source": "aurora" or "opensearch" or "s3tables", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""

        try:
            logger.info(f"Calling Bedrock with Nova Pro for routing decision")
            response = self.bedrock.invoke_model(
                modelId='us.amazon.nova-pro-v1:0',
                body=json.dumps({
                    "messages": [{"role": "user", "content": [{"text": prompt}]}],
                    "inferenceConfig": {"maxTokens": 200}
                })
            )
            
            result = json.loads(response['body'].read())
            content = result['output']['message']['content'][0]['text']
            logger.info(f"LLM response: {content}")
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group())
                source_str = decision['source'].lower()
                
                if source_str == 'aurora':
                    source_type = SourceType.AURORA
                elif source_str == 's3tables':
                    source_type = SourceType.S3TABLES
                else:
                    source_type = SourceType.OPENSEARCH
                    
                confidence = float(decision['confidence'])
                logger.info(f"LLM routing: {source_str} (confidence: {confidence:.2f}) - {decision['reasoning']}")
                return source_type, confidence
            else:
                logger.warning("No JSON found in LLM response")
        except Exception as e:
            logger.error(f"LLM routing failed: {e}", exc_info=True)
        
        # Fallback to metadata scoring
        logger.info("Falling back to metadata scoring")
        return None, 0.0
    
    async def _get_source_metadata(self, source: BaseDataSource) -> SourceMetadata:
        """Get and cache source metadata."""
        if source == self.aurora_source:
            source_type = SourceType.AURORA
        elif source == self.opensearch_source:
            source_type = SourceType.OPENSEARCH
        elif source == self.s3tables_source:
            source_type = SourceType.S3TABLES
        else:
            raise ValueError(f"Unknown source: {source}")
        
        if source_type not in self._metadata_cache:
            self._metadata_cache[source_type] = await source.get_metadata()
        
        return self._metadata_cache[source_type]
    
    async def select_best_source(self, request: AgentRequest) -> Tuple[SourceType, float]:
        """Select the best data source using LLM-based routing.
        
        Returns:
            Tuple of (SourceType, confidence_score)
        """
        # Get metadata from all sources
        aurora_meta = await self._get_source_metadata(self.aurora_source)
        opensearch_meta = await self._get_source_metadata(self.opensearch_source)
        s3tables_meta = await self._get_source_metadata(self.s3tables_source) if self.s3tables_source else None
        
        # Use LLM-based routing (only approach)
        source_type, confidence = await self._llm_route_decision(request, aurora_meta, opensearch_meta, s3tables_meta)
        
        if source_type:
            return source_type, confidence
        
        # If LLM routing fails completely, default to Aurora as a safe fallback
        logger.warning("LLM routing returned no result, defaulting to Aurora")
        return SourceType.AURORA, 0.5
