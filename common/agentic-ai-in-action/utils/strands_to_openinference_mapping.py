"""
Strands to OpenInference Converter for Arize AI

This module provides a span processor that converts Strands telemetry data
to OpenInference format for compatibility with Arize AI.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime

from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.trace import Span

logger = logging.getLogger(__name__)

class StrandsToOpenInferenceProcessor(SpanProcessor):
    """
    SpanProcessor that converts Strands telemetry attributes to OpenInference format
    for compatibility with Arize AI.
    """

    def __init__(self, debug: bool = False):
        """
        Initialize the processor.
        
        Args:
            debug: Whether to log debug information
        """
        super().__init__()
        self.debug = debug
        self.processed_spans = set()
        self.current_cycle_id = None
        self.span_hierarchy = {}
        # NEW: Store child outputs for bubbling up
        self.child_outputs = {}  # {parent_span_id: [child_outputs]}
        self.root_spans = set()  # Track top-level spans

    def on_start(self, span, parent_context=None):
        """Called when a span is started. Track span hierarchy."""
        span_id = span.get_span_context().span_id
        parent_id = None
        
        if parent_context and hasattr(parent_context, 'span_id'):
            parent_id = parent_context.span_id
        elif span.parent and hasattr(span.parent, 'span_id'):
            parent_id = span.parent.span_id
        
        # NEW: Track root spans (no parent)
        if parent_id is None:
            self.root_spans.add(span_id)
            
        self.span_hierarchy[span_id] = {
            'name': span.name,
            'span_id': span_id,
            'parent_id': parent_id,
            'start_time': datetime.now().isoformat()
        }

    def on_end(self, span: Span):
        """
        Called when a span ends. Transform the span attributes from Strands format
        to OpenInference format.
        """
        if not hasattr(span, '_attributes') or not span._attributes:
            return
        original_attrs = dict(span._attributes)
        span_id = span.get_span_context().span_id
        
        if span_id in self.span_hierarchy:
            self.span_hierarchy[span_id]['attributes'] = original_attrs
        
        try:
            if "event_loop.cycle_id" in original_attrs:
                self.current_cycle_id = original_attrs.get("event_loop.cycle_id")

            # Extract messages from events (new format)
            event_data = self._extract_events(span)
            
            # NEW: Collect output for bubbling up
            if span_id in self.span_hierarchy:
                parent_id = self.span_hierarchy[span_id]['parent_id']
                if parent_id:  # Has parent - collect output
                    output = self._extract_span_output(span, event_data)
                    if output:
                        if parent_id not in self.child_outputs:
                            self.child_outputs[parent_id] = []
                        self.child_outputs[parent_id].append({
                            'span_name': span.name,
                            'span_kind': self._determine_span_kind(span, original_attrs),
                            'output': output
                        })
            
            transformed_attrs = self._transform_attributes(original_attrs, span, event_data)
            span._attributes.clear()
            span._attributes.update(transformed_attrs)
            self.processed_spans.add(span_id)
            # self.processed_spans.add(span)
            
            # NEW: Cleanup after root span completes
            if span_id in self.root_spans:
                # Clean up child outputs for this root span
                self.child_outputs.pop(span_id, None)
                self.root_spans.discard(span_id)
            
            if self.debug:
                logger.info(f"Transformed span '{span.name}': {len(original_attrs)} -> {len(transformed_attrs)} attributes")
                
        except Exception as e:
            logger.error(f"Failed to transform span '{span.name}': {e}", exc_info=True)
            span._attributes.clear()
            span._attributes.update(original_attrs)

    def _extract_events(self, span: Span) -> Dict[str, Any]:
        """
        Extract messages and data from span events (new Strands SDK format).
        
        Returns:
            Dict containing extracted event data with keys:
            - input_messages: List of input messages
            - output_messages: List of output messages  
            - tool_data: Tool-related event data
        """
        event_data = {
            'input_messages': [],
            'output_messages': [],
            'tool_data': {}
        }
        
        if not hasattr(span, 'events') or not span.events:
            return event_data
            
        for event in span.events:
            event_name = event.name
            event_attrs = dict(event.attributes) if hasattr(event, 'attributes') and event.attributes else {}
            
            # Extract input messages (user, assistant, system)
            if event_name.endswith('.message') and not event_name.startswith('gen_ai.choice'):
                role = event_name.replace('gen_ai.', '').replace('.message', '')
                content = event_attrs.get('content', '')
                
                message = {
                    'role': role,
                    'content': self._deserialize_content(content)
                }
                
                # Add additional fields if present
                if 'id' in event_attrs:
                    message['id'] = event_attrs['id']
                    
                event_data['input_messages'].append(message)
            
            # Extract output messages (choices/responses)
            elif event_name == 'gen_ai.choice':
                content = event_attrs.get('message', '')
                finish_reason = event_attrs.get('finish_reason', 'stop')
                
                # Handle AgentResult stringification from latest SDK
                if isinstance(content, str) and content.startswith('AgentResult('):
                    # Try to extract actual content from stringified AgentResult
                    try:
                        # Simple extraction - look for content between quotes
                        import re
                        content_match = re.search(r"content='([^']*)'", content)
                        if content_match:
                            content = content_match.group(1)
                    except:
                        pass  # Keep original content if extraction fails
                
                message = {
                    'role': 'assistant',
                    'content': self._deserialize_content(content),
                    'finish_reason': finish_reason
                }
                
                # Handle tool results in choice events
                if 'tool.result' in event_attrs:
                    message['tool_result'] = self._deserialize_content(event_attrs['tool.result'])
                if 'id' in event_attrs:
                    message['id'] = event_attrs['id']
                    
                event_data['output_messages'].append(message)
            
            # Extract tool-specific data
            elif event_name == 'gen_ai.tool.message':
                # Latest SDK uses different structure for tool events
                tool_content = event_attrs.get('content', '')
                tool_id = event_attrs.get('id', '')
                tool_role = event_attrs.get('role', 'tool')
                
                event_data['tool_data'] = {
                    'content': self._deserialize_content(tool_content),
                    'id': tool_id,
                    'role': tool_role
                }
                
                # Also add as input message for consistency
                if tool_role == 'tool':
                    message = {
                        'role': tool_role,
                        'content': self._deserialize_content(tool_content),
                        'id': tool_id
                    }
                    event_data['input_messages'].append(message)
        
        return event_data

    def _deserialize_content(self, content: Any) -> Any:
        """Deserialize content from events, handling JSON strings."""
        if isinstance(content, str):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return content
        return content

    def _extract_text_content(self, content: Any) -> str:
        """Extract plain text from structured content formats."""
        if isinstance(content, list) and len(content) > 0:
            # Handle [{'text': 'content'}] format from latest SDK
            if isinstance(content[0], dict) and 'text' in content[0]:
                return content[0]['text']
        elif isinstance(content, dict) and 'text' in content:
            # Handle {'text': 'content'} format
            return content['text']
        
        # Return as string for any other format
        return str(content) if content is not None else ""

    def _extract_span_output(self, span: Span, event_data: Dict[str, Any]) -> Optional[str]:
        """Extract meaningful output from a span for bubbling up."""
        # Try assistant messages first
        if event_data['output_messages']:
            assistant_msgs = [msg for msg in event_data['output_messages'] 
                             if msg.get('role') == 'assistant']
            if assistant_msgs:
                return self._extract_text_content(assistant_msgs[0].get('content'))
        
        # Try tool results
        if event_data['tool_data'] and event_data['tool_data'].get('content'):
            return self._extract_text_content(event_data['tool_data']['content'])
        
        return None

    def _format_child_outputs(self, child_outputs: List[Dict]) -> str:
        """Format child outputs for the root span."""
        formatted = []
        for child in child_outputs:
            # Extract just the meaningful output content
            output = child['output']
            if output and output.strip():
                formatted.append(output.strip())
        return "\n\n".join(formatted)

    def _get_prompt_from_events_or_attrs(self, event_data: Dict[str, Any], attrs: Dict[str, Any]) -> Any:
        """Get prompt from events (new format) or attributes (old format)."""
        # Try events first (new format)
        if event_data['input_messages']:
            user_messages = [msg for msg in event_data['input_messages'] if msg.get('role') == 'user']
            if user_messages:
                content = user_messages[0].get('content')
                return self._extract_text_content(content)
        
        # Fall back to attributes (old format)
        return attrs.get("gen_ai.user.message") or attrs.get("gen_ai.prompt")

    def _get_completion_from_events_or_attrs(self, event_data: Dict[str, Any], attrs: Dict[str, Any]) -> Any:
        """Get completion from events (new format) or attributes (old format)."""
        # Try events first (new format)
        if event_data['output_messages']:
            assistant_messages = [msg for msg in event_data['output_messages'] if msg.get('role') == 'assistant']
            if assistant_messages:
                content = assistant_messages[0].get('content')
                
                # Handle AgentResult stringification from latest SDK
                if isinstance(content, str) and content.startswith('AgentResult('):
                    try:
                        import re
                        content_match = re.search(r"content='([^']*)'", content)
                        if content_match:
                            return content_match.group(1)
                    except:
                        pass  # Keep original content if extraction fails
                
                return self._extract_text_content(content)
        
        # Fall back to attributes (old format)
        return attrs.get("gen_ai.completion")

    def _transform_attributes(self, attrs: Dict[str, Any], span: Span, event_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Transform Strands attributes to OpenInference format.
        
        Args:
            attrs: Original span attributes
            span: The span being processed
            event_data: Extracted event data (new format) or None (old format)
        """
        if event_data is None:
            event_data = {'input_messages': [], 'output_messages': [], 'tool_data': {}}
            
        result = {}
        span_kind = self._determine_span_kind(span, attrs)
        result["openinference.span.kind"] = span_kind
        result["span.name"] = span.name  # Add span name for multiagent handler
        self._set_graph_node_attributes(span, attrs, result)
        
        # Try event data first (new format), fall back to attributes (old format)
        prompt = self._get_prompt_from_events_or_attrs(event_data, attrs)
        completion = self._get_completion_from_events_or_attrs(event_data, attrs)
        
        span_id = span.get_span_context().span_id
        
        # NEW: Add child outputs to root spans only
        if span_id in self.root_spans and span_id in self.child_outputs:
            child_outputs = self.child_outputs[span_id]
            result["child_outputs"] = self._format_child_outputs(child_outputs)
            result["child_outputs_count"] = len(child_outputs)
        
        model_id = attrs.get("gen_ai.request.model")
        agent_name = attrs.get("agent.name") or attrs.get("gen_ai.agent.name")

        if model_id:
            result["llm.model_name"] = model_id
            result["gen_ai.request.model"] = model_id
            
        if agent_name:
            result["llm.system"] = "strands-agents"
            result["llm.provider"] = "strands-agents"
        
        # Map operation name
        if operation_name := attrs.get("gen_ai.operation.name"):
            result["gen_ai.operation.name"] = operation_name
        
        if "tag.tags" in attrs:
            tags = attrs.get("tag.tags")
            if isinstance(tags, list):
                for tag in tags:
                    if isinstance(tag, str):
                        result[f"tag.{tag}"] = str(tag)
            elif isinstance(tags, str):
                result[f"tag.{tags}"] = str(tags)
        
        # Handle different span types
        if span_kind == "LLM":
            self._handle_chain_and_llm_span(attrs, result, prompt, completion, event_data)
        elif span_kind == "TOOL":
            self._handle_tool_span(attrs, result, event_data)
        elif span_kind == "AGENT":
            # Check if it's a multiagent span (invoke_ prefix)
            if span.name.startswith("invoke_") and not span.name.startswith("invoke_agent"):
                self._handle_multiagent_span(attrs, result, prompt, event_data)
            else:
                self._handle_agent_span(attrs, result, prompt, event_data)
        elif span_kind == "CHAIN":
            self._handle_chain_and_llm_span(attrs, result, prompt, completion, event_data)
        
        # Handle token usage
        self._map_token_usage(attrs, result)
        
        important_attrs = [
            "session.id", "user.id", "llm.prompt_template.template",
            "llm.prompt_template.version", "llm.prompt_template.variables",
            "gen_ai.event.start_time", "gen_ai.event.end_time", "gen_ai.operation.name"
        ]
        
        for key in important_attrs:
            if key in attrs:
                result[key] = attrs[key]
        
        self._add_metadata(attrs, result)    
        return result
    
    def _determine_span_kind(self, span: Span, attrs: Dict[str, Any]) -> str:
        """Determine the OpenInference span kind."""
        span_name = span.name
        
        # Updated patterns for latest Strands Agent implementation
        if span_name == "chat":
            return "LLM"
        elif span_name.startswith("execute_tool"):
            return "TOOL"
        elif span_name.startswith("invoke_agent"):
            return "AGENT"
        elif span_name == "execute_event_loop_cycle":
            return "CHAIN"
        elif span_name.startswith("invoke_"):  # multiagent spans
            return "AGENT"
        # Backward compatibility with 0.1.9
        elif "Model invoke" in span_name:
            return "LLM"
        elif span_name.startswith("Tool:"):
            return "TOOL"
        elif attrs.get("agent.name") or attrs.get("gen_ai.agent.name"):
            return "AGENT"
        elif "Cycle" in span_name:
            return "CHAIN"
        return "CHAIN"
    
    def _set_graph_node_attributes(self, span: Span, attrs: Dict[str, Any], result: Dict[str, Any]):
        """
        Set graph node attributes for Arize visualization.
        Hierarchy: Agent -> Cycles -> (LLMs and/or Tools)
        """
        span_name = span.name
        span_kind = result["openinference.span.kind"]        
        span_id = span.get_span_context().span_id
        
        # Get parent information from span hierarchy
        span_info = self.span_hierarchy.get(span_id, {})
        parent_id = span_info.get('parent_id')
        parent_info = self.span_hierarchy.get(parent_id, {}) if parent_id else {}
        parent_name = parent_info.get('name', '')
        
        if span_kind == "AGENT":
            result["graph.node.id"] = "strands_agent"
        
        # Handle both new and old cycle patterns
        if span_kind == "CHAIN":
            if span_name == "execute_event_loop_cycle":
                # Extract cycle ID from attributes for new format
                cycle_id = attrs.get("event_loop.cycle_id", span_id)
                result["graph.node.id"] = f"cycle_{cycle_id}"
                result["graph.node.parent_id"] = "strands_agent"
            elif "Cycle " in span_name:
                # Old format: "Cycle {id}"
                cycle_id = span_name.replace("Cycle ", "").strip()
                result["graph.node.id"] = f"cycle_{cycle_id}"
                result["graph.node.parent_id"] = "strands_agent"
        
        if span_kind == "LLM":
            result["graph.node.id"] = f"llm_{span_id}"
            # Check for both new and old parent patterns
            if parent_name == "execute_event_loop_cycle":
                parent_cycle_id = parent_info.get('attributes', {}).get("event_loop.cycle_id", parent_id)
                result["graph.node.parent_id"] = f"cycle_{parent_cycle_id}"
            elif parent_name.startswith("Cycle"):
                cycle_id = parent_name.replace("Cycle ", "").strip()
                result["graph.node.parent_id"] = f"cycle_{cycle_id}"
            else:
                result["graph.node.parent_id"] = "strands_agent"
        
        if span_kind == "TOOL":
            # Handle both new and old tool name extraction
            if span_name.startswith("execute_tool "):
                tool_name = span_name.replace("execute_tool ", "").strip()
            elif span_name.startswith("Tool: "):
                tool_name = span_name.replace("Tool: ", "").strip()
            else:
                tool_name = attrs.get("gen_ai.tool.name") or attrs.get("tool.name", "unknown")
            
            tool_id = attrs.get("gen_ai.tool.call.id") or attrs.get("tool.id", span_id)
            result["graph.node.id"] = f"tool_{tool_name}_{tool_id}"
            
            # Check for both new and old parent patterns
            if parent_name == "execute_event_loop_cycle":
                parent_cycle_id = parent_info.get('attributes', {}).get("event_loop.cycle_id", parent_id)
                result["graph.node.parent_id"] = f"cycle_{parent_cycle_id}"
            elif parent_name.startswith("Cycle "):
                cycle_id = parent_name.replace("Cycle ", "").strip()
                result["graph.node.parent_id"] = f"cycle_{cycle_id}"
            else:
                result["graph.node.parent_id"] = "strands_agent"

        if self.debug:
            logger.info(f"span_name: {span_name}")
            logger.info(f"span_kind: {span_kind}")
            logger.info(f"span_id: {span_id}")
            logger.info(f"span_info: {span_info}")
            logger.info(f"parent_id: {parent_id}")
            logger.info(f"parent_info: {parent_info}")
            logger.info(f"parent_name: {parent_name}")
            logger.info("==========================")
            logger.info(f"Span: {span_name} || (ID: {span_id})")
            logger.info(f"  Parent: {parent_name} || (ID: {parent_id})")
            logger.info(f"  Graph Node: {result.get('graph.node.id')} -> Parent: {result.get('graph.node.parent_id')}")

    def _handle_chain_and_llm_span(self, attrs: Dict[str, Any], result: Dict[str, Any], prompt: Any, completion: Any, event_data: Dict[str, Any] = None):
        """Handle LLM-specific attributes."""
        if event_data is None:
            event_data = {'input_messages': [], 'output_messages': [], 'tool_data': {}}
            
        if prompt:
            self._map_messages(prompt, result, is_input=True)
        
        if completion:
            self._map_messages(completion, result, is_input=False)
        
        self._add_input_output_values(attrs, result, prompt, completion)
        self._map_invocation_parameters(attrs, result)
    
    def _handle_tool_span(self, attrs: Dict[str, Any], result: Dict[str, Any], event_data: Dict[str, Any] = None):
        """Handle tool-specific attributes."""
        if event_data is None:
            event_data = {'input_messages': [], 'output_messages': [], 'tool_data': {}}
            
        # Use new attribute names first, fall back to old ones
        if tool_name := (attrs.get("gen_ai.tool.name") or attrs.get("tool.name")):
            result["tool.name"] = tool_name
        
        if tool_id := (attrs.get("gen_ai.tool.call.id") or attrs.get("tool.id")):
            result["tool.id"] = tool_id
        
        if tool_status := attrs.get("tool.status"):
            result["tool.status"] = str(tool_status)
        
        if tool_description := attrs.get("tool.description"):
            result["tool.description"] = tool_description
        
        # Extract tool parameters from events first, then attributes
        tool_params = None
        if event_data['tool_data'].get('content'):
            tool_params = event_data['tool_data']['content']
        else:
            tool_params = attrs.get("tool.parameters")
            
        if tool_params:
            result["tool.parameters"] = self._serialize_value(tool_params)
            tool_call = {
                "tool_call.id": attrs.get("gen_ai.tool.call.id") or attrs.get("tool.id", ""),
                "tool_call.function.name": attrs.get("gen_ai.tool.name") or attrs.get("tool.name", ""),
                "tool_call.function.arguments": self._serialize_value(tool_params)
            }
            
            input_message = {
                "message.role": "assistant",
                "message.tool_calls": [tool_call]
            }
            result["llm.input_messages"] = json.dumps([input_message], separators=(",", ":"))
            result["llm.input_messages.0.message.role"] = "assistant"
            result["tool_call.id"] = tool_call["tool_call.id"]
            result["tool_call.function.name"] = tool_call["tool_call.function.name"]
            result["tool_call.function.arguments"] = tool_call["tool_call.function.arguments"]
        
            for key, value in tool_call.items():
                result[f"llm.input_messages.0.message.tool_calls.0.{key}"] = value
        
        # Extract tool result from events first, then attributes
        tool_result = None
        if event_data['output_messages']:
            for msg in event_data['output_messages']:
                if msg.get('tool_result'):
                    tool_result = msg['tool_result']
                    break
        if not tool_result:
            tool_result = attrs.get("tool.result")
            
        if tool_result:
            result["tool.result"] = self._serialize_value(tool_result)
            tool_result_content = tool_result
            if isinstance(tool_result, dict):
                tool_result_content = tool_result.get("content", tool_result)
                if "error" in tool_result:
                    result["tool.error"] = self._serialize_value(tool_result.get("error"))

            output_message = {
                "message.role": "tool",
                "message.content": self._serialize_value(tool_result_content),
                "message.tool_call_id": attrs.get("gen_ai.tool.call.id") or attrs.get("tool.id", "")
            }

            if tool_name := (attrs.get("gen_ai.tool.name") or attrs.get("tool.name")):
                output_message["message.name"] = tool_name
            result["llm.output_messages"] = json.dumps([output_message], separators=(",", ":"))
            result["llm.output_messages.0.message.role"] = "tool"
            result["llm.output_messages.0.message.content"] = self._serialize_value(tool_result_content)
            result["llm.output_messages.0.message.tool_call_id"] = output_message["message.tool_call_id"]
            
            if tool_name:
                result["llm.output_messages.0.message.name"] = tool_name

        if start_time := attrs.get("gen_ai.event.start_time"):
            result["tool.start_time"] = start_time
        
        if end_time := attrs.get("gen_ai.event.end_time"):
            result["tool.end_time"] = end_time

        tool_metadata = {}
        for key, value in attrs.items():
            if key.startswith("tool.") and key not in ["tool.name", "tool.id", "tool.parameters", "tool.result", "tool.status"]:
                tool_metadata[key] = self._serialize_value(value)
        
        if tool_metadata:
            result["tool.metadata"] = json.dumps(tool_metadata, separators=(",", ":"))
    
    def _handle_agent_span(self, attrs: Dict[str, Any], result: Dict[str, Any], prompt: Any, event_data: Dict[str, Any] = None):
        """Handle agent-specific attributes."""
        if event_data is None:
            event_data = {'input_messages': [], 'output_messages': [], 'tool_data': {}}
            
        result["llm.system"] = "strands-agents"
        result["llm.provider"] = "strands-agents"
        
        # Use new attribute names first, fall back to old ones
        if tools := (attrs.get("gen_ai.agent.tools") or attrs.get("agent.tools")):
            self._map_tools(tools, result)
        
        if prompt:
            input_message = {
                "message.role": "user",
                "message.content": str(prompt)
            }
            result["llm.input_messages"] = json.dumps([input_message], separators=(",", ":"))
            result["input.value"] = str(prompt)
            result["llm.input_messages.0.message.role"] = "user"
            result["llm.input_messages.0.message.content"] = str(prompt)

        self._add_input_output_values(attrs, result, prompt)

    def _handle_multiagent_span(self, attrs: Dict[str, Any], result: Dict[str, Any], prompt: Any, event_data: Dict[str, Any] = None):
        """Handle multiagent/swarm-specific attributes."""
        if event_data is None:
            event_data = {'input_messages': [], 'output_messages': [], 'tool_data': {}}
            
        result["llm.system"] = "strands-agents"
        result["llm.provider"] = "strands-agents"
        
        # Extract instance name from span name (invoke_{instance})
        span_name = result.get("span.name", "")
        if span_name.startswith("invoke_"):
            instance_name = span_name.replace("invoke_", "")
            result["agent.instance"] = instance_name
        
        # Handle agent name from attributes
        if agent_name := (attrs.get("gen_ai.agent.name") or attrs.get("agent.name")):
            result["agent.name"] = agent_name
        
        if prompt:
            input_message = {
                "message.role": "user",
                "message.content": str(prompt)
            }
            result["llm.input_messages"] = json.dumps([input_message], separators=(",", ":"))
            result["input.value"] = str(prompt)
            result["llm.input_messages.0.message.role"] = "user"
            result["llm.input_messages.0.message.content"] = str(prompt)

        self._add_input_output_values(attrs, result, prompt)
    
    def _map_messages(self, messages_data: Any, result: Dict[str, Any], is_input: bool):
        """Map Strands messages to OpenInference message format."""
        key_prefix = "llm.input_messages" if is_input else "llm.output_messages"
        
        if isinstance(messages_data, str):
            try:
                messages_data = json.loads(messages_data)
            except json.JSONDecodeError:
                messages_data = [{"role": "user" if is_input else "assistant", "content": messages_data}]
        
        messages_list = self._normalize_messages(messages_data)
        result[key_prefix] = json.dumps(messages_list, separators=(",", ":"))

        for idx, msg in enumerate(messages_list):
            if not isinstance(msg, dict):
                continue
                
            for sub_key, sub_val in msg.items():
                clean_key = sub_key.replace("message.", "") if sub_key.startswith("message.") else sub_key
                dotted_key = f"{key_prefix}.{idx}.message.{clean_key}"
                
                if clean_key == "tool_calls" and isinstance(sub_val, list):
                    # Handle tool calls with proper structure
                    for tool_idx, tool_call in enumerate(sub_val):
                        if isinstance(tool_call, dict):
                            for tool_key, tool_val in tool_call.items():
                                tool_dotted_key = f"{key_prefix}.{idx}.message.tool_calls.{tool_idx}.{tool_key}"
                                result[tool_dotted_key] = self._serialize_value(tool_val)
                else:
                    result[dotted_key] = self._serialize_value(sub_val)
    
    def _normalize_messages(self, data: Any) -> List[Dict[str, Any]]:
        """Normalize messages data to a consistent list format."""
        if isinstance(data, list):
            return [self._normalize_message(m) for m in data]
        
        if isinstance(data, dict) and all(isinstance(k, str) and k.isdigit() for k in data.keys()):
            ordered = sorted(data.items(), key=lambda kv: int(kv[0]))
            return [self._normalize_message(v) for _, v in ordered]
        
        if isinstance(data, dict):
            return [self._normalize_message(data)]
        
        return [{"message.role": "user", "message.content": str(data)}]
    
    def _normalize_message(self, msg: Any) -> Dict[str, Any]:
        """Normalize a single message to OpenInference format."""
        if not isinstance(msg, dict):
            return {"message.role": "user", "message.content": str(msg)}
        
        result = {}
        for key in ["role", "content", "name", "tool_call_id", "finish_reason"]:
            if key in msg:
                result[f"message.{key}"] = msg[key]
        
        if "toolUse" in msg and isinstance(msg["toolUse"], list):
            tool_calls = []
            for tool_use in msg["toolUse"]:
                tool_calls.append({
                    "tool_call.id": tool_use.get("toolUseId", ""),
                    "tool_call.function.name": tool_use.get("name", ""),
                    "tool_call.function.arguments": json.dumps(tool_use.get("input", {}))
                })
            result["message.tool_calls"] = tool_calls
        
        return result
    
    def _map_tools(self, tools_data: Any, result: Dict[str, Any]):
        """Map tools from Strands to OpenInference format."""
        if isinstance(tools_data, str):
            try:
                tools_data = json.loads(tools_data)
            except json.JSONDecodeError:
                return
        
        if not isinstance(tools_data, list):
            return
        
        openinf_tools = []
        for tool in tools_data:
            if isinstance(tool, dict):
                openinf_tool = {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                }
                
                if "parameters" in tool:
                    openinf_tool["parameters"] = tool["parameters"]
                elif "input_schema" in tool:
                    openinf_tool["parameters"] = tool["input_schema"]
                
                openinf_tools.append(openinf_tool)
        
        if openinf_tools:
            for idx, tool in enumerate(openinf_tools):
                for key, value in tool.items():
                    dotted_key = f"llm.tools.{idx}.{key}"
                    result[dotted_key] = self._serialize_value(value)
    
    def _map_token_usage(self, attrs: Dict[str, Any], result: Dict[str, Any]):
        """Map token usage metrics."""
        token_mappings = [
            # Original mappings
            ("gen_ai.usage.prompt_tokens", "llm.token_count.prompt"),
            ("gen_ai.usage.completion_tokens", "llm.token_count.completion"),
            ("gen_ai.usage.total_tokens", "llm.token_count.total"),
            # New duplicate mappings (latest SDK)
            ("gen_ai.usage.input_tokens", "llm.token_count.prompt"),
            ("gen_ai.usage.output_tokens", "llm.token_count.completion"),
            # New cache-related mappings
            ("gen_ai.usage.cache_read_input_tokens", "llm.token_count.cache_read"),
            ("gen_ai.usage.cache_write_input_tokens", "llm.token_count.cache_write"),
        ]
        
        for strands_key, openinf_key in token_mappings:
            if value := attrs.get(strands_key):
                result[openinf_key] = value
    
    def _map_invocation_parameters(self, attrs: Dict[str, Any], result: Dict[str, Any]):
        """Map invocation parameters."""
        params = {}
        
        param_mappings = {
            "max_tokens": "max_tokens",
            "temperature": "temperature",
            "top_p": "top_p",
        }
        
        for key, param_key in param_mappings.items():
            if key in attrs:
                params[param_key] = attrs[key]
        
        if params:
            result["llm.invocation_parameters"] = json.dumps(params, separators=(",", ":"))
    
    def _add_input_output_values(self, attrs: Dict[str, Any], result: Dict[str, Any], prompt: Any = None, completion: Any = None):
        """Add input.value and output.value for Arize compatibility."""
        span_kind = result.get("openinference.span.kind")
        model_name = result.get("llm.model_name") or attrs.get("gen_ai.request.model") or "unknown"
        invocation_params = {}
        if "llm.invocation_parameters" in result:
            try:
                invocation_params = json.loads(result["llm.invocation_parameters"])
            except:
                pass
        
        if span_kind == "LLM":
            if "llm.input_messages" in result:
                try:
                    input_messages = json.loads(result["llm.input_messages"])
                    if input_messages:
                        input_structure = {
                            "messages": input_messages,
                            "model": model_name
                        }
                        if max_tokens := invocation_params.get("max_tokens"):
                            input_structure["max_tokens"] = max_tokens
                        
                        result["input.value"] = json.dumps(input_structure, separators=(",", ":"))
                        result["input.mime_type"] = "application/json"
                except:
                    if prompt_content := result.get("llm.input_messages.0.message.content"):
                        result["input.value"] = prompt_content
                        result["input.mime_type"] = "application/json"

            if "llm.output_messages" in result:
                try:
                    output_messages = json.loads(result["llm.output_messages"])
                    if output_messages and len(output_messages) > 0:
                        first_msg = output_messages[0]
                        content = first_msg.get("message.content", "")
                        role = first_msg.get("message.role", "assistant")
                        finish_reason = first_msg.get("message.finish_reason", "stop")
                        output_structure = {
                            "id": attrs.get("gen_ai.response.id"),
                            "choices": [{
                                "finish_reason": finish_reason,
                                "index": 0,
                                "logprobs": None,
                                "message": {
                                    "content": content,
                                    "role": role,
                                    "refusal": None,
                                    "annotations": []
                                }
                            }],
                            "model": model_name,
                            "usage": {
                                "completion_tokens": result.get("llm.token_count.completion"),
                                "prompt_tokens": result.get("llm.token_count.prompt"),
                                "total_tokens": result.get("llm.token_count.total")
                            }
                        }
                        
                        result["output.value"] = json.dumps(output_structure, separators=(",", ":"))
                        result["output.mime_type"] = "application/json"
                except:
                    if completion_content := result.get("llm.output_messages.0.message.content"):
                        result["output.value"] = completion_content
                        result["output.mime_type"] = "application/json"
                    
        elif span_kind == "AGENT":
            # Use extracted prompt and completion from events/attributes
            if prompt:
                result["input.value"] = str(prompt)
                result["input.mime_type"] = "text/plain"
            elif prompt_attr := attrs.get("gen_ai.prompt"):
                result["input.value"] = str(prompt_attr)
                result["input.mime_type"] = "text/plain"

            if completion:
                result["output.value"] = str(completion)
                result["output.mime_type"] = "text/plain"
            elif completion_attr := attrs.get("gen_ai.completion"):
                result["output.value"] = str(completion_attr)
                result["output.mime_type"] = "text/plain"
            elif child_outputs := result.get("child_outputs"):
                result["output.value"] = str(child_outputs)
                result["output.mime_type"] = "text/plain"

        elif span_kind == "TOOL":
            if tool_params := attrs.get("tool.parameters"):
                if isinstance(tool_params, str):
                    result["input.value"] = tool_params
                else:
                    result["input.value"] = json.dumps(tool_params, separators=(",", ":"))
                result["input.mime_type"] = "application/json"
            
            if tool_result := attrs.get("tool.result"):
                if isinstance(tool_result, str):
                    result["output.value"] = tool_result
                else:
                    result["output.value"] = json.dumps(tool_result, separators=(",", ":"))
                result["output.mime_type"] = "application/json"
                
        elif span_kind == "CHAIN":
            if prompt := attrs.get("gen_ai.prompt"):
                if isinstance(prompt, str):
                    result["input.value"] = prompt
                else:
                    result["input.value"] = json.dumps(prompt, separators=(",", ":"))
                result["input.mime_type"] = "text/plain" if isinstance(prompt, str) else "application/json"
            
            if completion := attrs.get("gen_ai.completion"):
                if isinstance(completion, str):
                    result["output.value"] = completion  
                else:
                    result["output.value"] = json.dumps(completion, separators=(",", ":"))
                result["output.mime_type"] = "text/plain" if isinstance(completion, str) else "application/json"
    
    def _add_metadata(self, attrs: Dict[str, Any], result: Dict[str, Any]):
        """Add remaining attributes to metadata."""
        metadata = {}
        skip_keys = {"gen_ai.prompt", "gen_ai.completion", "agent.tools", "gen_ai.agent.tools", "span.name"}
        
        for key, value in attrs.items():
            if key not in skip_keys and key not in result:
                metadata[key] = self._serialize_value(value)
        
        if metadata:
            result["metadata"] = json.dumps(metadata, separators=(",", ":"))
    
    def _serialize_value(self, value: Any) -> Any:
        """Ensure a value is serializable."""
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        
        try:
            return json.dumps(value, separators=(",", ":"))
        except (TypeError, OverflowError):
            return str(value)

    def shutdown(self):
        """Called when the processor is shutdown."""
        pass

    def force_flush(self, timeout_millis=None):
        """Called to force flush."""
        return True