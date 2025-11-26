"""Abstract base classes for data sources."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..orchestrator.models import SourceMetadata, ExecutionResult, AgentRequest, QueryPlan


class BaseDataSource(ABC):
    """Abstract base class for all data sources."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._metadata: Optional[SourceMetadata] = None
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the data source connection."""
        pass
    
    @abstractmethod
    async def get_metadata(self) -> SourceMetadata:
        """Get metadata about this data source."""
        pass
    
    @abstractmethod
    async def execute_query(self, plan: QueryPlan) -> ExecutionResult:
        """Execute a query against this data source."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the data source is healthy."""
        pass
    
    @abstractmethod
    async def close(self):
        """Close connections and cleanup resources."""
        pass
