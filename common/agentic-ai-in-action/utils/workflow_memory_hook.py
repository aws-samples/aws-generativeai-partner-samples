"""
Workflow Memory Hook for Strands Agent

Records complete conversation audit trail per session (messages + tool executions).
"""

import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from strands.hooks.events import AgentInitializedEvent, AfterInvocationEvent
from pymongo import MongoClient

from utils.base_memory_hook import BaseMemoryHook


class WorkflowMemoryHook(BaseMemoryHook):
    """Memory hook for complete conversation audit trail."""
    
    def __init__(self, mongo_client: MongoClient, database_name: str, collection_name: str, load_enabled: bool = True):
        super().__init__(mongo_client, database_name, collection_name)
        self.load_enabled = load_enabled
        self.logger.info(f"WorkflowMemoryHook - loading enabled: {load_enabled}")
    
    def on_agent_initialized(self, event: AgentInitializedEvent) -> None:
        """Load previous workflow steps when agent starts (if enabled)."""
        if not self.load_enabled:
            self.logger.info("🚫 Workflow memory loading disabled")
            return
            
        self.logger.info("🚀 Loading workflow history...")
        
        try:
            session_id = self._get_session_id(event.agent)
            workflow_steps = self._get_workflow_history(session_id)
            
            if workflow_steps:
                workflow_context = self._format_workflow_context(workflow_steps)
                event.agent.system_prompt += f"\n\n## Previous tool executions steps:\n{workflow_context}\n\nContinue the conversation with this context."
                self.logger.debug(f"📚 Workflow history loaded: \n{workflow_context[:self.max_context_size]}...(truncated)")
                self.logger.info(f"✅ Loaded {len(workflow_steps)} workflow steps for session {session_id}")
            else:
                self.logger.info(f"📭 No previous workflow steps found for session {session_id}")
                
        except Exception as e:
            self.logger.error(f"❌ Error loading workflow history: {str(e)}")
    
    def on_after_invocation(self, event: AfterInvocationEvent) -> None:
        """Record complete conversation step after agent invocation."""
        try:
            messages = event.agent.messages
            session_id = self._get_session_id(event.agent)
            user_id = self._get_user_id(event.agent)
            
            # Extract user query and agent response
            user_query = self._extract_user_query(messages)
            agent_response = self._extract_agent_response(messages)
            
            # Extract tool executions from message flow
            tools_executed = self._extract_tool_executions(messages)
            
            if user_query and agent_response:
                step_number = self._get_next_step_number(session_id)
                self._store_workflow_step(
                    session_id, user_id, step_number, 
                    user_query, agent_response, tools_executed, messages
                )
                self.logger.info(f"🔄 Stored workflow step {step_number} for session {session_id}")
            
        except Exception as e:
            self.logger.error(f"Error recording workflow step: {e}")
    
    def _get_workflow_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get recent workflow steps for a session, newest first, limited by max_interactions."""
        cursor = self.collection.find(
            {"session_id": session_id}
        ).sort("step_number", -1).limit(self.max_interactions)
        
        return list(cursor)
    
    def _get_next_step_number(self, session_id: str) -> int:
        """Get the next step number for the session."""
        last_step = self.collection.find_one(
            {"session_id": session_id},
            sort=[("step_number", -1)]
        )
        
        return (last_step.get("step_number", 0) + 1) if last_step else 1
    
    def _store_workflow_step(self, session_id: str, user_id: Optional[str], step_number: int,
                           user_query: str, agent_response: str, tools_executed: List[Dict],
                           all_messages: List[Dict]) -> None:
        """Store a complete workflow step."""
        workflow_record = {
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc),
            "step_number": step_number,
            "user_query": user_query,
            "agent_response": agent_response,
            "tools_executed": tools_executed,
            "metadata": {
                "total_messages": len(all_messages),
                "tool_count": len(tools_executed)
            }
        }
        
        result = self.collection.insert_one(workflow_record)
        self.logger.info(f"✅ Stored workflow step {result.inserted_id}")
    
    def _extract_user_query(self, messages: List[Dict]) -> Optional[str]:
        """Extract latest user query from messages."""
        for msg in reversed(messages):
            if msg['role'] == 'user':
                content = msg['content']
                if isinstance(content, list) and len(content) > 0:
                    if isinstance(content[0], dict) and 'text' in content[0]:
                        return content[0]['text']
        return None
    
    def _extract_agent_response(self, messages: List[Dict]) -> Optional[str]:
        """Extract final agent response from messages."""
        for msg in reversed(messages):
            if msg['role'] == 'assistant':
                content = msg['content']
                if isinstance(content, list) and len(content) > 0:
                    if isinstance(content[0], dict) and 'text' in content[0]:
                        return content[0]['text']
        return None
    
    def _extract_tool_executions(self, messages: List[Dict]) -> List[Dict[str, Any]]:
        """Extract tool executions from message flow."""
        tools_executed = []
        
        for i, msg in enumerate(messages):
            # Look for assistant messages with tool calls
            if msg['role'] == 'assistant':
                content = msg['content']
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and 'toolUse' in item:
                            tool_call = item['toolUse']
                            
                            # Find corresponding tool result
                            tool_result = self._find_tool_result(messages, i, tool_call.get('toolUseId'))
                            
                            tools_executed.append({
                                "tool_name": tool_call.get('name', 'unknown'),
                                "tool_call": tool_call,
                                "tool_result": tool_result,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })
        
        return tools_executed
    
    def _find_tool_result(self, messages: List[Dict], start_index: int, tool_use_id: str) -> Optional[Dict]:
        """Find tool result for a given tool use ID."""
        for msg in messages[start_index + 1:]:
            if msg['role'] == 'user':
                content = msg['content']
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and 'toolResult' in item:
                            tool_result = item['toolResult']
                            if tool_result.get('toolUseId') == tool_use_id:
                                return tool_result
        return None
    
    def _format_workflow_context(self, workflow_steps: List[Dict[str, Any]]) -> str:
        """Format workflow steps into context string."""
        context_parts = []
        
        for step in workflow_steps:  # Show last 5 steps
            step_num = step.get("step_number", "?")
            timestamp = step.get("timestamp", "").strftime("%H:%M") if step.get("timestamp") else ""
            query = step.get("user_query", "")[:200].replace("\n", " ")
            response = step.get("agent_response", "")[:200].replace("\n", " ")
            tools_executed = step.get("tools_executed", [])
            
            context_parts.append(f"Step {step_num} [{timestamp}]:")
            context_parts.append(f"  User: {query}")
            context_parts.append(f"  Agent: {response}")
            
            if tools_executed:
                context_parts.append(f"  Tools executed ({len(tools_executed)}):")
                for tool in tools_executed:
                    tool_name = tool.get("tool_name", "unknown")
                    tool_call = tool.get("tool_call", {})
                    tool_result = tool.get("tool_result", {})
                    
                    # Show tool call details
                    if tool_call:
                        input_params = tool_call.get("input", {})
                        context_parts.append(f"    - {tool_name}: {str(input_params)[:200]}...")
                    
                    # Show tool result summary
                    if tool_result:
                        context_parts.append(f"      → Status: {tool_result.get("status", "none")}")
                        result_content = tool_result.get("content", "")
                        if isinstance(result_content, list) and len(result_content) > 0:
                            if isinstance(result_content[0], dict) and "text" in result_content[0]:
                                result_text = result_content[0]["text"][:100].replace("\n", " ")
                                context_parts.append(f"      → Result: {result_text}...")
            else:
                context_parts.append("  No tools used")
        
        context = "\n".join(context_parts)
        
        if len(context) > self.max_context_size:
            context = context[:self.max_context_size] + "...[truncated]"
        
        return context
