"""OpenSearch client management."""

from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
import boto3
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class OpenSearchClient:
    """Manages connections to OpenSearch."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client: Optional[OpenSearch] = None
    
    async def initialize(self) -> bool:
        """Initialize OpenSearch Serverless client with AWS authentication."""
        try:
            session = boto3.Session()
            credentials = session.get_credentials()
            region = session.region_name or self.config.get('region', 'us-east-1')
            
            auth = AWSV4SignerAuth(credentials, region, 'aoss')
            
            host = self.config.get('host')
            if host and host.startswith('https://'):
                host = host.replace('https://', '')
            if host and host.startswith('http://'):
                host = host.replace('http://', '')
            
            self.client = OpenSearch(
                hosts=[{'host': host, 'port': 443}],
                http_auth=auth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30
            )
            
            self.client.ping()
            logger.info("OpenSearch Serverless client initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch Serverless client: {str(e)}")
            return False
    
    async def search(self, index: str, query: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a search query."""
        if not self.client:
            raise RuntimeError("OpenSearch client not initialized")
        
        return self.client.search(index=index, body=query)
    
    async def get_indices(self) -> List[str]:
        """Get list of available indices."""
        if not self.client:
            raise RuntimeError("OpenSearch client not initialized")
        
        try:
            indices = self.client.indices.get_alias()
            return list(indices.keys())
        except Exception as e:
            logger.error(f"Failed to get indices: {str(e)}")
            return []
    
    async def get_mapping(self, index: str) -> Dict[str, Any]:
        """Get mapping for an index."""
        if not self.client:
            raise RuntimeError("OpenSearch client not initialized")
        
        try:
            mapping = self.client.indices.get_mapping(index=index)
            if index in mapping:
                return mapping[index].get('mappings', {})
            return {}
        except Exception as e:
            logger.error(f"Failed to get mapping for {index}: {str(e)}")
            return {}
    
    async def health_check(self) -> bool:
        """Check OpenSearch health."""
        try:
            if not self.client:
                return False
            return self.client.ping()
        except Exception:
            return False
    
    async def close(self):
        """Close OpenSearch client."""
        if self.client:
            self.client.close()
            logger.info("OpenSearch client closed")
