"""
Teacher Memory Hook for Strands Agent

Provides conversational memory capabilities using MongoDB Atlas storage.
Implements simple query/response history for session continuity.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import AgentInitializedEvent, MessageAddedEvent, AfterInvocationEvent
from pymongo import MongoClient
from pymongo.collection import Collection

# Import centralized logging configuration from utils
from utils.logging_config import get_agent_logger


class TeacherMemoryHook(HookProvider):
    """Memory hook for teacher orchestrator agent using MongoDB Atlas."""
    
    def __init__(self, mongo_client: MongoClient, database_name: str, collection_name: str):
        """
        Initialize memory hook with MongoDB connection.
        
        Args:
            mongo_client: MongoClient instance
            database_name: MongoDB database name
            collection_name: MongoDB collection name
        """
        self.mongo_client = mongo_client
        self.db = mongo_client[database_name]
        self.collection: Collection = self.db[collection_name]
        self.logger = get_agent_logger("teacher_memory_hook")
        
        # Configuration from environment
        self.max_interactions = int(os.getenv("MAX_INTERACTIONS_PER_SESSION", "10"))
        self.max_context_size = int(os.getenv("MAX_MEMORY_CONTEXT_SIZE", "2000"))
        
        self.logger.info(f"TeacherMemoryHook initialized - max_interactions: {self.max_interactions}")
    
    def register_hooks(self, registry: HookRegistry) -> None:
        """Register memory hooks with the agent."""
        registry.add_callback(AgentInitializedEvent, self.on_agent_initialized)
        registry.add_callback(AfterInvocationEvent, self.on_after_invocation)
        self.logger.info("Memory hooks registered successfully")
    
    def on_agent_initialized(self, event: AgentInitializedEvent) -> None:
        """
        Load conversation history when agent starts.
        
        Args:
            event: AgentInitializedEvent containing agent context
        """
        self.logger.info("🚀 AgentInitializedEvent triggered - Loading conversation history...")
        
        try:
            # Get or generate session_id
            session_id = self._get_session_id(event.agent)
            self.logger.info(f"🔍 AgentInitialized: Using session_id: {session_id}")
            
            # Retrieve recent conversations
            memories = self._get_recent_conversations(session_id)
            
            if memories:
                # Format and inject memory context into system prompt
                memory_context = self._format_memory_context(memories)
                event.agent.system_prompt += f"\n\nRecent conversation history:\n{memory_context}\n\nContinue the conversation naturally based on this context."
                
                self.logger.info(f"✅ AgentInitialized: Loaded {len(memories)} memories for session {session_id}")
                self.logger.debug(f"📝 AgentInitialized: Memory context injected into system prompt")
            else:
                self.logger.info(f"📭 AgentInitialized: No previous memories found for session {session_id}")
                
        except Exception as e:
            self.logger.error(f"❌ AgentInitialized: Error loading conversation history: {str(e)}")
            # Continue without memory on error
    
    def on_after_invocation(self, event: AfterInvocationEvent) -> None:
        """Store conversation after agent invocation completes."""
        try:
            messages = event.agent.messages
            
            # Find the latest user query and final assistant response
            user_query = None
            final_response = None
            
            # Get last user message that contains actual text (not tool results)
            for msg in reversed(messages):
                if msg['role'] == 'user' and user_query is None:
                    content = msg['content']
                    if isinstance(content, list) and len(content) > 0:
                        # Check if it's a text message (not a tool result)
                        if isinstance(content[0], dict):
                            if 'text' in content[0]:
                                user_query = content[0]['text']
                                break
                            # Skip tool results (they have 'toolResult' key)
                            elif 'toolResult' in content[0]:
                                continue
            
            # Get last assistant message (final response)
            for msg in reversed(messages):
                if msg['role'] == 'assistant':
                    content = msg['content']
                    if isinstance(content, list) and len(content) > 0:
                        if isinstance(content[0], dict) and 'text' in content[0]:
                            final_response = content[0]['text']
                    break
            
            if user_query and final_response:
                session_id = self._get_session_id(event.agent)
                user_id = self._get_user_id(event.agent)
                self._store_memory_record(session_id, user_query, final_response, user_id)
                self.logger.info(f"🔄 AfterInvocation: Stored Q&A pair for session {session_id}, user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error in AfterInvocationEvent: {e}")
    
    def on_message_added(self, event: MessageAddedEvent) -> None:
        """
        Store conversation after message is added.
        
        Args:
            event: MessageAddedEvent containing agent and message context
        """
        self.logger.debug("💬 MessageAddedEvent triggered - Storing conversation...")
        
        try:
            # Get session_id from agent state
            session_id = self._get_session_id(event.agent)
            self.logger.debug(f"🔍 MessageAdded: Using session_id: {session_id}")
            
            # Get the latest messages
            messages = event.agent.messages
            self.logger.debug(f"📨 MessageAdded: Found {len(messages)} total messages")
            
            if len(messages) >= 2:  # Need at least user query and agent response
                # Extract last user message and agent response
                user_message = None
                agent_response = None
                
                # Find the last user and assistant messages
                for i, msg in enumerate(reversed(messages)):
                    role = msg.get("role", "unknown")
                    if role == "user" and user_message is None:
                        user_message = self._extract_message_content(msg)
                        self.logger.debug(f"🧑 MessageAdded: Found user message at position -{i+1}")
                    elif role == "assistant" and agent_response is None:
                        agent_response = self._extract_message_content(msg)
                        self.logger.debug(f"🤖 MessageAdded: Found assistant message at position -{i+1}")
                    
                    # Stop when we have both
                    if user_message and agent_response:
                        break
                
                if user_message and agent_response:
                    self.logger.info(f"💾 MessageAdded: Storing Q&A pair for session {session_id}")
                    self.logger.debug(f"❓ MessageAdded: Query: {user_message[:100]}...")
                    self.logger.debug(f"💡 MessageAdded: Response: {agent_response[:100]}...")
                    
                    # Store memory record
                    self._store_memory_record(session_id, user_message, agent_response)
                else:
                    self.logger.debug(f"⚠️ MessageAdded: Could not extract both user message and agent response")
                    self.logger.debug(f"🔍 MessageAdded: user_message found: {user_message is not None}, agent_response found: {agent_response is not None}")
            else:
                self.logger.debug(f"📝 MessageAdded: Not enough messages yet ({len(messages)} < 2), skipping storage")
            
        except Exception as e:
            self.logger.error(f"❌ MessageAdded: Error storing memory: {str(e)}")
            # Continue on error - don't break agent flow
    
    def _get_recent_conversations(self, session_id: str) -> List[Dict[str, Any]]:
        """Get recent conversations for a session."""
        cursor = self.collection.find(
            {"session_id": session_id}
        ).sort("timestamp", -1).limit(self.max_interactions)
        
        memories = list(cursor)
        # Reverse to get chronological order (oldest first)
        return list(reversed(memories))
    
    def _store_memory_record(self, session_id: str, query: str, response: str, user_id: Optional[str] = None) -> None:
        """Store a memory record."""
        memory_record = {
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc),
            "query": query,
            "response": response,
            # Store user_id from trace attributes
            "user_id": user_id,
            "routed_agent": None,
            "context": {},
            "embedding": None,
            "metadata": {}
        }
        
        result = self.collection.insert_one(memory_record)
        self.logger.info(f"✅ MongoDB: Stored memory record {result.inserted_id} for session {session_id}")
    
    def _format_memory_context(self, memories: List[Dict[str, Any]]) -> str:
        """Format memories into context string."""
        context_parts = []
        
        for memory in memories:
            timestamp = memory.get("timestamp", "").strftime("%H:%M") if memory.get("timestamp") else ""
            query = memory.get("query", "")
            response = memory.get("response", "")
            
            context_parts.append(f"[{timestamp}] Student: {query}")
            context_parts.append(f"[{timestamp}] Assistant: {response}")
        
        context = "\n".join(context_parts)
        
        # Truncate if too long
        if len(context) > self.max_context_size:
            context = context[:self.max_context_size] + "...[truncated]"
        
        return context
    
    def _get_session_id(self, agent) -> str:
        """Get or generate session ID from agent state."""
        # Try to get from agent state
        if hasattr(agent, 'state') and agent.state:
            session_id = agent.state.get('session_id')
            if session_id:
                return session_id
        
        # Try to get from trace attributes
        if hasattr(agent, 'trace_attributes') and agent.trace_attributes:
            session_id = agent.trace_attributes.get('session.id')
            if session_id:
                return session_id
        
        # Generate new session ID
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
                # Handle content as list of objects
                first_content = content[0]
                if isinstance(first_content, dict):
                    return first_content.get("text", "")
                return str(first_content)
            return str(content) if content else None
        except Exception as e:
            self.logger.error(f"Error extracting message content: {e}")
            return None
