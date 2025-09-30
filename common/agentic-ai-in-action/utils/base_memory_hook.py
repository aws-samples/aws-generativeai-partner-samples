"""
Base Memory Hook for Strands Agent

Provides common functionality for all memory hook implementations.
"""

import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import AgentInitializedEvent, AfterInvocationEvent
from pymongo import MongoClient
from pymongo.collection import Collection

from utils.logging_config import get_agent_logger


class BaseMemoryHook(HookProvider, ABC):
    """Abstract base class for memory hooks."""
    
    def __init__(self, mongo_client: MongoClient, database_name: str, collection_name: str):
        """
        Initialize base memory hook with MongoDB connection.
        
        Args:
            mongo_client: MongoClient instance
            database_name: MongoDB database name
            collection_name: MongoDB collection name
        """
        self.mongo_client = mongo_client
        self.db = mongo_client[database_name]
        self.collection: Collection = self.db[collection_name]
        self.logger = get_agent_logger(f"{self.__class__.__name__.lower()}")
        
        # Configuration from environment
        self.max_interactions = int(os.getenv("MAX_INTERACTIONS_PER_SESSION", "10"))
        self.max_context_size = int(os.getenv("MAX_MEMORY_CONTEXT_SIZE", "10000"))
        
        self.logger.info(f"{self.__class__.__name__} initialized - collection: {collection_name}")
    
    def register_hooks(self, registry: HookRegistry) -> None:
        """Register memory hooks with the agent."""
        registry.add_callback(AgentInitializedEvent, self.on_agent_initialized)
        registry.add_callback(AfterInvocationEvent, self.on_after_invocation)
        self.logger.info(f"{self.__class__.__name__} hooks registered")
    
    def _get_session_id(self, agent) -> str:
        """Get or generate session ID from agent state."""
        if hasattr(agent, 'trace_attributes') and agent.trace_attributes:
            session_id = agent.trace_attributes.get('session.id')
            if session_id:
                return session_id
        
        session_id = str(uuid.uuid4())
        self.logger.info(f"Generated new session_id: {session_id}")
        return session_id
    
    def _get_user_id(self, agent) -> Optional[str]:
        """Get user ID from agent trace attributes."""
        if hasattr(agent, 'trace_attributes') and agent.trace_attributes:
            return agent.trace_attributes.get('user.id')
        return None
    
    def _extract_message_content(self, message: Dict[str, Any]) -> Optional[str]:
        """Extract text content from message."""
        try:
            content = message.get("content")
            if isinstance(content, str):
                return content
            elif isinstance(content, list) and len(content) > 0:
                first_content = content[0]
                if isinstance(first_content, dict):
                    return first_content.get("text", "")
                return str(first_content)
            return str(content) if content else None
        except Exception as e:
            self.logger.error(f"Error extracting message content: {e}")
            return None
    
    @abstractmethod
    def on_agent_initialized(self, event: AgentInitializedEvent) -> None:
        """Handle agent initialization - must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def on_after_invocation(self, event: AfterInvocationEvent) -> None:
        """Handle after invocation - must be implemented by subclasses."""
        pass
