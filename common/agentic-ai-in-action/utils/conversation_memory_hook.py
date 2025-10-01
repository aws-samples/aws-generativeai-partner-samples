"""
Conversation Memory Hook for Strands Agent

Handles Q&A pair storage and retrieval for session continuity.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from strands.hooks.events import AgentInitializedEvent, AfterInvocationEvent
from pymongo import MongoClient

from utils.base_memory_hook import BaseMemoryHook


class ConversationMemoryHook(BaseMemoryHook):
    """Memory hook for conversation Q&A pairs."""
    
    def __init__(self, mongo_client: MongoClient, database_name: str, collection_name: str):
        super().__init__(mongo_client, database_name, collection_name)
    
    def on_agent_initialized(self, event: AgentInitializedEvent) -> None:
        """Load conversation history when agent starts."""
        self.logger.info("🚀 Loading conversation history...")
        
        try:
            session_id = self._get_session_id(event.agent)
            memories = self._get_recent_conversations(session_id)
            
            if memories:
                memory_context = self._format_memory_context(memories)
                event.agent.system_prompt += f"\n\n## Recent conversation history:\n{memory_context}\n\nContinue the conversation naturally based on this context."
                self.logger.debug(f"📝 Memory context:\n{memory_context}")
                self.logger.info(f"✅ Loaded {len(memories)} memories for session {session_id}")
            else:
                self.logger.info(f"📭 No previous memories found for session {session_id}")
                
        except Exception as e:
            self.logger.error(f"❌ Error loading conversation history: {str(e)}")
    
    def on_after_invocation(self, event: AfterInvocationEvent) -> None:
        """Store conversation after agent invocation completes."""
        try:
            messages = event.agent.messages
            
            # Find latest user query and final assistant response
            user_query = None
            final_response = None
            
            # Get last user message that contains actual text (not tool results)
            for msg in reversed(messages):
                if msg['role'] == 'user' and user_query is None:
                    content = msg['content']
                    if isinstance(content, list) and len(content) > 0:
                        if isinstance(content[0], dict):
                            if 'text' in content[0]:
                                user_query = content[0]['text']
                                break
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
                self.logger.info(f"🔄 Stored Q&A pair for session {session_id}, user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error in AfterInvocationEvent: {e}")
    
    def _get_recent_conversations(self, session_id: str) -> List[Dict[str, Any]]:
        """Get recent conversations for a session."""
        cursor = self.collection.find(
            {"session_id": session_id}
        ).sort("timestamp", -1).limit(self.max_interactions)
        
        memories = list(cursor)
        return list(reversed(memories))
    
    def _store_memory_record(self, session_id: str, query: str, response: str, user_id: Optional[str] = None) -> None:
        """Store a conversation memory record."""
        memory_record = {
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc),
            "query": query,
            "response": response,
            "user_id": user_id,
            "routed_agent": None,
            "context": {},
            "embedding": None,
            "metadata": {}
        }
        
        result = self.collection.insert_one(memory_record)
        self.logger.info(f"✅ Stored memory record {result.inserted_id} for session {session_id}")
    
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
        
        if len(context) > self.max_context_size:
            context = context[:self.max_context_size] + "...[truncated]"
        
        return context
