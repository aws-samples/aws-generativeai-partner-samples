"""
Long-term Memory Hook for Strands Agent

Stores user factual preferences triggered by specific keywords.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from strands.hooks.events import AgentInitializedEvent, AfterInvocationEvent
from pymongo import MongoClient

from utils.base_memory_hook import BaseMemoryHook


class LongTermMemoryHook(BaseMemoryHook):
    """Memory hook for keyword-triggered factual storage."""
    
    def __init__(self, mongo_client: MongoClient, database_name: str, collection_name: str, load_enabled: bool = True):
        super().__init__(mongo_client, database_name, collection_name)
        self.load_enabled = load_enabled
        
        # Trigger keywords for factual storage
        self.trigger_keywords = [
            "remember", "i prefer", "my preference is", "i like", "i don't like",
            "keep in mind", "note that", "for future reference", "i hate",
            "my favorite", "i love", "i dislike", "please remember",
            "make sure to", "always", "never forget"
        ]
        
        self.logger.info(f"LongTermMemoryHook - loading enabled: {load_enabled}")
    
    def on_agent_initialized(self, event: AgentInitializedEvent) -> None:
        """Load user facts when agent starts (if enabled)."""
        if not self.load_enabled:
            self.logger.info("🚫 Long-term memory loading disabled")
            return
            
        self.logger.info("🚀 Loading user facts...")
        
        try:
            user_id = self._get_user_id(event.agent)
            
            if user_id:
                user_facts = self._get_user_facts(user_id)
                
                if user_facts:
                    facts_context = self._format_facts_context(user_facts)
                    event.agent.system_prompt += f"\n\n## User facts to remember:\n{facts_context}\n\nKeep these preferences in mind during the conversation."
                    self.logger.info(f"✅ Loaded {len(user_facts)} facts for user {user_id}")
                else:
                    self.logger.info(f"📭 No facts found for user {user_id}")
            else:
                self.logger.info("📭 No user_id available for fact loading")
                
        except Exception as e:
            self.logger.error(f"❌ Error loading user facts: {str(e)}")
    
    def on_after_invocation(self, event: AfterInvocationEvent) -> None:
        """Store user facts when triggered by keywords."""
        try:
            messages = event.agent.messages
            user_query = self._extract_user_query(messages)
            
            if user_query:
                trigger_keyword = self._detect_trigger_keyword(user_query)
                
                if trigger_keyword:
                    session_id = self._get_session_id(event.agent)
                    user_id = self._get_user_id(event.agent)
                    
                    self._store_user_fact(session_id, user_id, user_query, trigger_keyword)
                    self.logger.info(f"🔄 Stored user fact triggered by '{trigger_keyword}'")
            
        except Exception as e:
            self.logger.error(f"Error in long-term memory storage: {e}")
    
    def _detect_trigger_keyword(self, user_query: str) -> Optional[str]:
        """Detect if user query contains trigger keywords."""
        query_lower = user_query.lower()
        
        for keyword in self.trigger_keywords:
            if keyword in query_lower:
                return keyword
        
        return None
    
    def _get_user_facts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all facts for a user in chronological order."""
        cursor = self.collection.find(
            {"user_id": user_id}
        ).sort("timestamp", 1)  # Oldest first
        
        return list(cursor)
    
    def _store_user_fact(self, session_id: str, user_id: Optional[str], user_query: str, trigger_keyword: str) -> None:
        """Store a user fact."""
        fact_record = {
            "unique_id": str(uuid.uuid4()),
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc),
            "user_query": user_query,
            "trigger_keyword": trigger_keyword
        }
        
        result = self.collection.insert_one(fact_record)
        self.logger.info(f"✅ Stored user fact {result.inserted_id}")
    
    def _extract_user_query(self, messages: List[Dict]) -> Optional[str]:
        """Extract latest user query from messages."""
        for msg in reversed(messages):
            if msg['role'] == 'user':
                content = msg['content']
                if isinstance(content, list) and len(content) > 0:
                    if isinstance(content[0], dict) and 'text' in content[0]:
                        return content[0]['text']
        return None
    
    def _format_facts_context(self, user_facts: List[Dict[str, Any]]) -> str:
        """Format user facts into context string."""
        context_parts = []
        
        for fact in user_facts[-10:]:  # Show last 10 facts
            timestamp = fact.get("timestamp", "").strftime("%m/%d") if fact.get("timestamp") else ""
            query = fact.get("user_query", "")
            trigger = fact.get("trigger_keyword", "")
            
            context_parts.append(f"[{timestamp}] {query} (keyword: {trigger})")
        
        context = "\n".join(context_parts)
        
        if len(context) > self.max_context_size:
            context = context[:self.max_context_size] + "...[truncated]"
        
        return context
