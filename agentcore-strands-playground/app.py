import json
import os
import sys
import uuid
import urllib.parse
from typing import Dict, List

import boto3
import requests
import streamlit as st
from streamlit.logger import get_logger
from dotenv import load_dotenv
import yaml
from br_utils import get_bedrock_models

load_dotenv()

logger = get_logger(__name__)
logger.setLevel("INFO")

# Check if authentication should be enabled based on COGNITO_DISCOVERY_URL
# Priority: 1) .env file, 2) .bedrock_agentcore.yaml file
cognito_discovery_url = os.getenv('COGNITO_DISCOVERY_URL', '').strip()

# If not in .env, try to read from .bedrock_agentcore.yaml
# This is somewhat brittle, since it depends on the agent being in the "right" directory
if not cognito_discovery_url:
    try:
        yaml_path = 'agentcore_agent/.bedrock_agentcore.yaml'
        if os.path.exists(yaml_path):
            with open(yaml_path, 'r') as f:
                config = yaml.safe_load(f)
                # Navigate to the nested discoveryUrl in authorizer_configuration
                agents = config.get('agents', {})
                default_agent = config.get('default_agent', '')
                if default_agent and default_agent in agents:
                    agent_config = agents[default_agent]
                    auth_config = agent_config.get('authorizer_configuration', {})
                    jwt_config = auth_config.get('customJWTAuthorizer', {})
                    cognito_discovery_url = jwt_config.get('discoveryUrl', '').strip()
                    if cognito_discovery_url:
                        logger.info(f"Using COGNITO_DISCOVERY_URL from {yaml_path}: {cognito_discovery_url}")
                    else:
                        logger.info("No Cognito discovery url found.")
    except Exception as e:
        logger.warning(f"Could not read COGNITO_DISCOVERY_URL from YAML: {e}")

ENABLE_AUTH = bool(cognito_discovery_url)

# Check for --auth or --noauth command-line arguments to override
if '--auth' in sys.argv:
    ENABLE_AUTH = True
elif '--noauth' in sys.argv:
    ENABLE_AUTH = False

# Import authentication module OR set auth variables to None
if ENABLE_AUTH:
    from auth_utils import require_authentication
    logger.info(F"Using authentication: {cognito_discovery_url}")
else:
    st.session_state.authenticated = False
    st.session_state.access_token = None
    st.session_state.id_token = None
    st.session_state.refresh_token = None
    st.session_state.username = 'default_user'
    logger.info("Not using authentication.")

STRANDS_SYSTEM_PROMPT = os.getenv('STRANDS_SYSTEM_PROMPT', """You are a helpful assistant powered by Strands. Strands Agents is a simple-to-use, code-first framework for building agents - open source by AWS. The user has the ability to modify your set of built-in tools. Every time your tool set is changed, you can propose a new set of tasks that you can do.""")

# Tool descriptions for Strands built-in tools
tool_descriptions = {
    'agent_graph': 'Create and manage graphs of agents with different topologies and communication patterns',
    'calculator': 'Perform mathematical calculations with support for advanced operations',
    'cron': 'Manage crontab entries for scheduling tasks, with special support for Strands agent jobs',
    'current_time': 'Get the current time in various timezones',
    'editor': 'Editor tool designed to do changes iteratively on multiple files',
    'environment': 'Manage environment variables at runtime',
    'file_read': 'File reading tool with search capabilities, various reading modes, and document mode support',
    'file_write': 'Write content to a file with proper formatting and validation based on file type',
    'generate_image': 'Create images using Stable Diffusion models',
    'http_request': 'Make HTTP requests to external APIs with authentication support',
    'image_reader': 'Read and process image files for AI analysis',
    'journal': 'Create and manage daily journal entries with tasks and notes',
    'load_tool': 'Dynamically load Python tools at runtime',
    'memory': 'Store and retrieve data in Bedrock Knowledge Base',
    'nova_reels': 'Create high-quality videos using Amazon Nova Reel',
    'python_repl': 'Execute Python code in a REPL environment with PTY support and state persistence',
    'retrieve': 'Retrieves knowledge based on the provided text from Amazon Bedrock Knowledge Bases',
    'shell': 'Interactive shell with PTY support for real-time command execution and interaction',
    'slack': 'Comprehensive Slack integration for messaging, events, and interactions',
    'speak': 'Generate speech from text using say command or Amazon Polly',
    'stop': 'Stops the current event loop cycle by setting stop_event_loop flag',
    'swarm': 'Create and coordinate a swarm of AI agents for parallel processing and collective intelligence',
    'think': 'Process thoughts through multiple recursive cycles',
    'use_aws': 'Execute AWS service operations using boto3',
    'use_llm': 'Create isolated agent instances for specific tasks',
    'workflow': 'Advanced workflow orchestration system for parallel AI task execution',
    'websearch': 'search the web using DDG'
}

# Default selected tools
DEFAULT_TOOLS = ['calculator', 'current_time', 'use_aws', 'websearch']

# Page config
st.set_page_config(
    page_title="Bedrock AgentCore + Strands Playground",
    page_icon="static/gen-ai-dark.svg",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Remove Streamlit deployment components
st.markdown(
    """
      <style>
        .stAppDeployButton {display:none;}
        #MainMenu {visibility: hidden;}
      </style>
    """,
    unsafe_allow_html=True,
)

HUMAN_AVATAR = "static/user-profile.svg"
AI_AVATAR = "static/gen-ai-dark.svg"

#
# I have tried to put all AWS API calls into cached functions to reduce latency on Streamlit reruns
#

# uncomment caching before commit; for now we're cycling agents too frequently
#@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_agent_runtimes(region: str = "us-west-2") -> List[Dict]:
    """Fetch available agent runtimes from bedrock-agentcore-control"""
    try:
        client = boto3.client("bedrock-agentcore-control", region_name=region)
        response = client.list_agent_runtimes(maxResults=100)

        # Filter only READY agents and sort by name
        ready_agents = [
            agent
            for agent in response.get("agentRuntimes", [])
            if agent.get("status") == "READY"
        ]

        # Sort by most recent update time (newest first)
        ready_agents.sort(key=lambda x: x.get("lastUpdatedAt", ""), reverse=True)
        logger.debug(f"found ready agents: {ready_agents}")
        return ready_agents
    except Exception as e:
        st.error(f"Error fetching agent runtimes: {e}")
        return []

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_agent_runtime_versions(
    agent_runtime_id: str, region: str = "us-west-2"
) -> List[Dict]:
    """Fetch versions for a specific agent runtime"""
    try:
        client = boto3.client("bedrock-agentcore-control", region_name=region)
        response = client.list_agent_runtime_versions(agentRuntimeId=agent_runtime_id, maxResults=100)

        # Filter only READY versions
        ready_versions = [
            version
            for version in response.get("agentRuntimes", [])
            if version.get("status") == "READY"
        ]

        # Sort by most recent update time (newest first)
        ready_versions.sort(key=lambda x: x.get("lastUpdatedAt", ""), reverse=True)
        logger.debug(f"found agent versions: {ready_versions}")
        return ready_versions
    except Exception as e:
        st.error(f"Error fetching agent runtime versions: {e}")
        return []

@st.cache_data(ttl=300)  # Cache for 5 minutes
# TODO: instead of pulling all memories, look into .bedrock_agentcore.yaml and find the memory ID used by the agent
def fetch_memory(region: str) -> List[Dict]:
    """Fetch available memories from bedrock-agentcore-control"""
    try:
        client = boto3.client("bedrock-agentcore-control", region_name=region)
        response = client.list_memories(maxResults=100)
        #logger.info(response);
        # Filter only READY memories and sort by name
        ready_memories = []
        total_memories = response.get("memories", [])
        logger.info(f"Total memories retrieved: {len(total_memories)}")
        
        for memory in total_memories:
            memory_id = memory.get("id", "Unknown")
            memory_status = memory.get("status", "Unknown")
            #logger.info(f"Retrieved memory: {memory_id} (status: {memory_status})")
            
            if memory.get("status") == "ACTIVE":
                ready_memories.append(memory)
                #logger.info(f"Added Active memory: {memory_id}")
        
        #logger.info(f"Final ready_memories count: {len(ready_memories)}")

        # Sort by most recent update time (newest first)
        ready_memories.sort(key=lambda x: x.get("updatedAt", ""), reverse=True)
        logger.debug(F"Fetched memories: {ready_memories}")
        return ready_memories
    except Exception as e:
        st.error(f"Error fetching memories: {e}")
        return []

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_sessions(region: str, memory_id: str, actor_id: str) -> List[Dict]:
    """
    Fetch available sessions from bedrock-agentcore for a specific memory and actor.
    https://docs.aws.amazon.com/bedrock-agentcore/latest/APIReference/API_ListSessions.html
 """
    try:
        #logger.info("fetching sessions using boto3")
        client = boto3.client("bedrock-agentcore", region_name=region)
        
        # List sessions with pagination support
        sessions = []
        next_token = None
        max_iterations = 10  # Safety limit to prevent infinite loops
        
        for iteration in range(max_iterations):
            params = {
                "memoryId": memory_id,
                "actorId": actor_id,
                "maxResults": 100
            }            
            if next_token:
                params["nextToken"] = next_token
            response = client.list_sessions(**params)
            # Add sessions from this page
            session_summaries = response.get("sessionSummaries", [])
            sessions.extend(session_summaries)
            #logger.info(f"Page {iteration + 1}: Retrieved {len(session_summaries)} sessions (total: {len(sessions)})")
            # Check for more pages
            next_token = response.get("nextToken")
            if not next_token:
                break
    
        # Check if current session exists in the retrieved sessions
        session_ids_list = [s.get('sessionId') for s in sessions if isinstance(s, dict)]
        
        # If current session is not in the list, create an initialization event for AgentCore Memory
        # This is ugly. The only reason to create the event is so that when streamlit refreshes,
        # the session will be captured from the list_sessions() call
        # TBD: find a better way to get it into the dropdown
        if 'runtime_session_id' in st.session_state and st.session_state.runtime_session_id not in session_ids_list:
            try:
                from datetime import datetime, timezone
                
                # Extract session name for display
                session_name = st.session_state.runtime_session_id
                if '_' in session_name:
                    display_name = session_name.split('_')[0]
                    if display_name:
                        session_name = display_name
                
                #logger.info(f"Creating initialization event for new session: {st.session_state.runtime_session_id}")
                
                # Create minimal blob event to make session visible in list_sessions
                init_response = client.create_event(
                    memoryId=memory_id,
                    actorId=actor_id,
                    sessionId=st.session_state.runtime_session_id,
                    eventTimestamp=datetime.now(timezone.utc),
                    payload=[{'blob': 'session_init'}]
                )
                
                logger.info(f"Session initialization event created: {init_response.get('eventId')}")
                
                # Add the new session to the list so it appears in the dropdown
                sessions.append({
                    'sessionId': st.session_state.runtime_session_id,
                    'lastUpdatedDateTime': datetime.now(timezone.utc).isoformat(),
                    'eventCount': 1
                })
                
            except Exception as e:
                logger.error(f"Failed to create session initialization event: {e}")
        
        # Sort by most recent first (if lastUpdatedDateTime is available)
        sessions.sort(key=lambda x: x.get("lastUpdatedDateTime", ""), reverse=True)
        
        session_ids_log = [session.get("sessionId", "Unknown") for session in sessions]
        logger.info(f"Sessions retrieved for actor '{actor_id}': {session_ids_log}")
        return sessions
        
    except client.exceptions.ResourceNotFoundException as e:
        # Actor doesn't exist yet - this is normal for new users
        logger.info(f"Actor not found (will be created on first interaction): {actor_id}")
        return []
    except client.exceptions.ValidationException as e:
        st.error(f"Invalid parameters: {e}")
        logger.error(f"Validation error: {e}")
        return []
    except Exception as e:
        st.error(f"Error fetching sessions: {e}")
        logger.error(f"Error fetching sessions: {e}")
        return []

def get_token_usage(usage_data=None):
    """Extract token usage from usage_data dict or return zeros"""
    if usage_data and isinstance(usage_data, dict):
        return {
            'inputTokens': usage_data.get('inputTokens', 0),
            'outputTokens': usage_data.get('outputTokens', 0),
            'totalTokens': usage_data.get('totalTokens', 0)
        }
    return {'inputTokens': 0, 'outputTokens': 0, 'totalTokens': 0}

def return_metrics(mode: str, usage_data=None, error_msg: str = None, **kwargs):
    """
    Create a standardized metrics dictionary
    
    Args:
        mode: The mode string (e.g., 'AgentCore Runtime (requests + Bearer Token)')
        usage_data: Optional usage data dict to pass to get_token_usage()
        error_msg: Optional error message
        **kwargs: Additional key-value pairs to include in metrics (e.g., model_id, agent_arn, etc.)
    
    Returns:
        Dict with usage, mode, and any additional fields
    """
    metrics = {
        'usage': get_token_usage(usage_data),
        'mode': mode
    }
    
    # Add error if provided
    if error_msg:
        metrics['error'] = error_msg
    
    # Add any additional kwargs
    metrics.update(kwargs)
    
    return metrics
    
def invoke_agentcore_runtime_auth(message: str, agent_arn: str, region: str, access_token: str, session_id: str, username: str = None, memory_id: str = None) -> Dict:
    """
    Invoke AgentCore runtime using HTTP requests with bearer token authentication
    We need to use 'requests' because boto3 can't handle auth tokens (yet)
    """
    try:
        # URL encode the agent ARN
        escaped_agent_arn = urllib.parse.quote(agent_arn, safe='')
        
        # Construct the URL
        url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{escaped_agent_arn}/invocations?qualifier=DEFAULT"
        
        # Set up headers
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Amzn-Trace-Id": f"streamlit-session-{session_id[:8] if session_id else 'unknown'}",
            "Content-Type": "application/json",
        }
        # Add session ID header if provided
        if session_id:
            headers["X-Amzn-Bedrock-AgentCore-Runtime-Session-Id"] = session_id
        
        # Prepare payload
        payload_data = {"prompt": message}
        if session_id:
            payload_data["sessionId"] = session_id
        if username:
            payload_data["username"] = username
        
        # Add model_id to payload - get from session state or use STRANDS_MODEL_ID from .env
        model_id = st.session_state.get('selected_bedrock_model_id', os.getenv('STRANDS_MODEL_ID', 'us.amazon.nova-pro-v1:0'))
        if model_id:
            payload_data["model_id"] = model_id
        
        # Add memory_id to payload if provided
        if memory_id:
            payload_data["memory_id"] = memory_id
        
        # Add selected tools to payload
        selected_tools = st.session_state.get('selected_tools', DEFAULT_TOOLS)
        if selected_tools:
            payload_data["tools"] = selected_tools
        
        # Enable verbose logging for debugging (optional)
        # logging.basicConfig(level=logging.DEBUG)
        # logging.getLogger("urllib3.connectionpool").setLevel(logging.DEBUG)
        
        # Make the HTTP POST request
        invoke_response = requests.post(
            url,
            headers=headers,
            data=json.dumps(payload_data),
            timeout=300  # 5 minute timeout
        )
        
        # Handle response based on status code
        if invoke_response.status_code == 200:
            try:
                response_data = invoke_response.json()
                
                # Check if response_data is a string (double-encoded JSON)
                if isinstance(response_data, str):
                    try:
                        response_data = json.loads(response_data)
                    except json.JSONDecodeError:
                        # If it fails, treat as plain text
                        pass
                
                # Extract response text
                if isinstance(response_data, dict):
                    response_text = response_data.get('response', str(response_data))
                    
                    # Extract usage metrics if available
                    token_usage = get_token_usage(response_data.get('usage'))
                else:
                    response_text = str(response_data)
                    token_usage = get_token_usage()
                    response_data = {}  # Set to empty dict if not a dict
                
            except json.JSONDecodeError:
                # If response is not JSON, use the text as-is
                response_text = invoke_response.text
                token_usage = get_token_usage()
                response_data = {}  # Set to empty dict to prevent AttributeError
            
            # Include additional metrics if available (only if response_data is a dict)
            additional_metrics = response_data.get('metrics', {}) if isinstance(response_data, dict) else {}
            
            return {
                'success': True,
                'response': response_text,
                'metrics': return_metrics(
                    mode='AgentCore Runtime (requests + Bearer Token)',
                    usage_data=token_usage,
                    model_id=response_data.get('model_id', model_id),
                    agent_arn=agent_arn,
                    bearer_token_used=bool(access_token),
                    latency_ms=additional_metrics.get('latencyMs'),
                    additional_metrics=additional_metrics
                )
            }
            
        elif invoke_response.status_code >= 400:
            # Error response
            try:
                error_data = invoke_response.json()
                error_msg = json.dumps(error_data, indent=2)
            except json.JSONDecodeError:
                error_msg = invoke_response.text
            
            st.error(f"Error Response ({invoke_response.status_code}): {error_msg}")
            
            return {
                'success': False,
                'error': error_msg,
                'response': f"Sorry, I encountered an error ({invoke_response.status_code}): {error_msg}",
                'metrics': return_metrics(
                    mode='AgentCore Runtime (Error)',
                    error_msg=error_msg,
                    status_code=invoke_response.status_code
                )
            }
        else:
            # Unexpected status code
            error_msg = f"Unexpected status code: {invoke_response.status_code}"
            response_text = invoke_response.text[:500]
            
            st.error(f"{error_msg}\nResponse: {response_text}")
            
            return {
                'success': False,
                'error': error_msg,
                'response': f"Sorry, I encountered an unexpected error: {error_msg}",
                'metrics': return_metrics(
                    mode='AgentCore Runtime (Error)',
                    error_msg=error_msg,
                    status_code=invoke_response.status_code
                )
            }
        
    except requests.exceptions.Timeout:
        error_msg = "Request timed out after 5 minutes"
        st.error(f"Error invoking AgentCore runtime: {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'response': f"Sorry, the request timed out: {error_msg}",
            'metrics': return_metrics(
                mode='AgentCore Runtime (Timeout)',
                error_msg=error_msg
            )
        }
    except requests.exceptions.RequestException as e:
        error_msg = f"Request error: {str(e)}"
        st.error(f"Error invoking AgentCore runtime: {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'response': f"Sorry, I encountered a network error: {error_msg}",
            'metrics': return_metrics(
                mode='AgentCore Runtime (Network Error)',
                error_msg=error_msg
            )
        }
    except Exception as e:
        error_msg = str(e)
        st.error(f"Error invoking AgentCore runtime: {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'response': f"Sorry, I encountered an error: {error_msg}",
            'metrics': return_metrics(
                mode='AgentCore Runtime (Error)',
                error_msg=error_msg
            )
        }

def invoke_agentcore_runtime_no_auth(message: str, agent_arn: str, region: str, session_id: str, username: str = None, memory_id: str = None) -> Dict:
    """
    Invoke AgentCore runtime using boto3 without authentication token
    Uses standard AWS credentials (IAM role, profile, etc.)
    """
    try:
        # Initialize the Amazon Bedrock AgentCore client
        agent_core_client = boto3.client('bedrock-agentcore', region_name=region)
        
        # Prepare payload data
        payload_data = {"prompt": message}
        if session_id:
            payload_data["sessionId"] = session_id
        if username:
            payload_data["username"] = username
        
        # Add model_id to payload - get from session state or use STRANDS_MODEL_ID from .env
        model_id = st.session_state.get('selected_bedrock_model_id', os.getenv('STRANDS_MODEL_ID', 'us.amazon.nova-pro-v1:0'))
        if model_id:
            payload_data["model_id"] = model_id
        
        # Add memory_id to payload if provided
        if memory_id:
            payload_data["memory_id"] = memory_id
        
        # Add selected tools to payload
        selected_tools = st.session_state.get('selected_tools', DEFAULT_TOOLS)
        if selected_tools:
            payload_data["tools"] = selected_tools
        
        # Encode payload as JSON bytes
        payload = json.dumps(payload_data).encode()
        
        # Invoke the agent
        response = agent_core_client.invoke_agent_runtime(
            agentRuntimeArn=agent_arn,
            runtimeSessionId=session_id if session_id else str(uuid.uuid4()),
            payload=payload,
            qualifier="DEFAULT"
        )
        
        # Collect response chunks
        content = []
        for chunk in response.get("response", []):
            content.append(chunk.decode('utf-8'))
        
        # Parse the complete response
        response_text = ''.join(content)
        
        try:
            response_data = json.loads(response_text)
            
            # Check if response is double-encoded (string instead of dict)
            if isinstance(response_data, str):
                response_data = json.loads(response_data)
            
            # Extract response text
            if isinstance(response_data, dict):
                final_response = response_data.get('response', str(response_data))
                
                # Extract usage metrics if available
                token_usage = get_token_usage(response_data.get('usage'))
                
                # Include additional metrics if available
                additional_metrics = response_data.get('metrics', {})
            else:
                final_response = str(response_data)
                token_usage = get_token_usage()
                response_data = {}
                additional_metrics = {}
        except json.JSONDecodeError as e:
            # If response is not JSON, use the text as-is
            logger.error(f"JSON decode error: {e}")
            final_response = response_text
            token_usage = get_token_usage()
            response_data = {}
            additional_metrics = {}
        
        return {
            'success': True,
            'response': final_response,
            'metrics': return_metrics(
                mode='AgentCore Runtime (boto3 - No Auth Token)',
                usage_data=token_usage,
                model_id=response_data.get('model_id', model_id),
                agent_arn=agent_arn,
                bearer_token_used=False,
                latency_ms=additional_metrics.get('latencyMs'),
                additional_metrics=additional_metrics
            )
        }
        
    except agent_core_client.exceptions.ResourceNotFoundException as e:
        error_msg = f"Agent runtime not found: {str(e)}"
        st.error(f"Error invoking AgentCore runtime: {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'response': f"Sorry, the agent runtime was not found: {error_msg}",
            'metrics': return_metrics(
                mode='AgentCore Runtime (boto3 - Error)',
                error_msg=error_msg
            )
        }
    except agent_core_client.exceptions.ValidationException as e:
        error_msg = f"Invalid parameters: {str(e)}"
        st.error(f"Error invoking AgentCore runtime: {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'response': f"Sorry, invalid parameters: {error_msg}",
            'metrics': return_metrics(
                mode='AgentCore Runtime (boto3 - Error)',
                error_msg=error_msg
            )
        }
    except Exception as e:
        error_msg = str(e)
        st.error(f"Error invoking AgentCore runtime: {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'response': f"Sorry, I encountered an error: {error_msg}",
            'metrics': return_metrics(
                mode='AgentCore Runtime (boto3 - Error)',
                error_msg=error_msg
            )
        }


def render_metrics_panel():
    """Render the metrics summary panel"""
    st.subheader("📊 Metrics Summary")
    
    st.markdown("""
    <div style="margin-bottom: 10px; padding: 8px; background-color: #f0f2f6; border-radius: 4px;">
    </div>
    """, unsafe_allow_html=True)
    
    # Display metrics if available
    if 'last_metrics' in st.session_state:
        metrics = st.session_state.last_metrics
        
        # Check if metrics contain usage information
        if 'usage' in metrics and metrics['usage']:
            usage = metrics['usage']
            
            st.subheader("🎯 Token Usage")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Input Tokens", usage.get('inputTokens', 0))
            with col2:
                st.metric("Output Tokens", usage.get('outputTokens', 0))
            with col3:
                st.metric("Total Tokens", usage.get('totalTokens', 0))
        
        # Performance metrics
        if 'latency_ms' in metrics and metrics['latency_ms']:
            st.subheader("⚡ Performance")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Latency", f"{metrics['latency_ms']:.2f} ms")
            with col2:
                if 'additional_metrics' in metrics and metrics['additional_metrics']:
                    additional = metrics['additional_metrics']
                    if 'firstByteLatencyMs' in additional:
                        st.metric("First Byte", f"{additional['firstByteLatencyMs']:.2f} ms")
        
        # Error information if available
        if 'error' in metrics:
            st.subheader("⚠️ Error Details")
            st.error(metrics['error'])
            
    else:
        st.info("Metrics will appear after your first interaction with the AgentCore runtime.")

def render_tools_panel_content():
    """Render the tools panel content for use inside sidebar expander"""
    # Initialize selected tools in session state if not exists
    if 'selected_tools' not in st.session_state:
        st.session_state.selected_tools = DEFAULT_TOOLS.copy()
    
    st.markdown("**📋 Tool Selection**")
    st.info("💡 Select the tools you want the agent to have access to. Changes will be applied when you click Update Tools.")
    
    st.markdown("---")
    
    # Create checkboxes for each tool
    st.markdown("**🛠️ Available Tools:**")
    
    # Use a container with scroll for better UX
    tools_container = st.container(height=300)
    
    with tools_container:
        # Track selections in a temporary dict
        tool_selections = {}
        
        for tool_name, description in sorted(tool_descriptions.items()):
            is_selected = tool_name in st.session_state.selected_tools
            tool_selections[tool_name] = st.checkbox(
                f"**{tool_name}**",
                value=is_selected,
                key=f"tool_checkbox_{tool_name}",
                help=description
            )
    
    st.markdown("---")
    
    # Update and Reset buttons
    st.markdown("**⚙️ Actions**")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔄 Update Tools", use_container_width=True):
            # Update selected tools based on checkboxes
            new_selected_tools = [tool_name for tool_name, is_selected in tool_selections.items() if is_selected]
            
            #if len(new_selected_tools) == 0:
            #    st.warning("⚠️ Please select at least one tool")
            #else:
            st.session_state.selected_tools = new_selected_tools
            st.success(f"✅ Updated! {len(new_selected_tools)} tool(s) selected")
            st.rerun()
    
    with col2:
        if st.button("↻ Reset to Default", use_container_width=True):
            st.session_state.selected_tools = DEFAULT_TOOLS.copy()
            st.success("✅ Reset to default tools")
            st.rerun()
    
    st.markdown("---")
    
    # Show currently selected tools - styled like settings sidebar
    st.markdown("**📊 Current Status**")
    st.write(f"**Active Tools:** {len(st.session_state.selected_tools)}")
    if st.session_state.selected_tools:
        st.caption(", ".join(sorted(st.session_state.selected_tools)))
    else:
        st.caption("No tools selected")

def show_settings_sidebar(auth):
    """Show Settings sidebar with authentication info and all configuration options"""
    
    # Tools Configuration Section (collapsible)
    with st.sidebar.expander("🔧 Tools Configuration", expanded=False):
        render_tools_panel_content()
    
    st.sidebar.markdown("---")
    
    # Settings Section (collapsible)
    with st.sidebar.expander("⚙️ Settings", expanded=True):
        # Authentication section
        if ENABLE_AUTH:
            if auth.is_authenticated():
                st.markdown("**🔐 Authentication**")
                st.write(f"👤 **User:** {auth.get_username()}")
                st.write(f"� **Pool:** *{auth.pool_id}")
                
                if st.button("� Logoout", use_container_width=True):
                    auth.logout()
                    st.rerun()
                
                st.markdown("---")
        else:
                st.markdown("**🔐 Authentication**")
                st.write(f"👤 **User:** default_user")
                
                st.markdown("---")
    
        # Region selection
        st.markdown("**AWS Region**")
        default_region = os.getenv('AWS_REGION', 'us-west-2')
        regions = ["us-west-2", "us-west-2", "eu-west-1", "ap-southeast-1"]
        
        try:
            default_index = regions.index(default_region)
        except ValueError:
            regions.insert(0, default_region)
            default_index = 0
        
        region = st.selectbox(
            "Region",
            regions,
            index=default_index,
            help=f"Using {default_region} as default"
        )
        st.session_state.selected_region = region
        
        # Model selection - Bedrock models with tool use support
        st.markdown("**Bedrock Model (Tool Use)**")
        
        # Cache key for models based on region
        models_cache_key = f"bedrock_tool_models_{region}"
        if models_cache_key not in st.session_state or st.session_state.get('last_model_region') != region:
            with st.spinner("Loading Bedrock models..."):
                available_models = get_bedrock_models()
                st.session_state[models_cache_key] = available_models
                st.session_state.last_model_region = region
        else:
            available_models = st.session_state[models_cache_key]
        
        if available_models:
            # available_models is now a list of model ID strings
            model_options = available_models
            
            # Initialize selected model in session state - try to find STRANDS_MODEL_ID or use first option
            if 'selected_bedrock_model_id' not in st.session_state:
                # Get STRANDS_MODEL_ID from environment
                strands_model_id = os.getenv('STRANDS_MODEL_ID', 'us.amazon.nova-pro-v1:0')
                
                # Use STRANDS_MODEL_ID if available in the list, otherwise first option
                if strands_model_id in available_models:
                    st.session_state.selected_bedrock_model_id = strands_model_id
                else:
                    st.session_state.selected_bedrock_model_id = available_models[0]
            
            # Determine the index for the selectbox
            current_selection = st.session_state.get('selected_bedrock_model_id', available_models[0])
            try:
                current_index = available_models.index(current_selection) if current_selection in available_models else 0
            except ValueError:
                current_index = 0
            
            selected_model_id = st.selectbox(
                "Model",
                options=model_options,
                index=current_index,
                help="Select a Bedrock model"
            )
            
            st.session_state.selected_bedrock_model_id = selected_model_id
            
        else:
            st.warning("No tool-use capable models found in this region")
            st.session_state.selected_bedrock_model_id = None

        # Agent selection
        st.markdown("---")
        st.markdown("**🤖 Agent Selection**")
                
        # Initialize agent_arn in session state
        if 'selected_agent_arn' not in st.session_state:
            st.session_state.selected_agent_arn = ""
            
        # AgentCore selection logic - only fetch if needed
        if 'available_agents' not in st.session_state or st.session_state.get('last_region') != region:
            with st.spinner("Loading available agents..."):
                available_agents = fetch_agent_runtimes(region)
                st.session_state.available_agents = available_agents
                st.session_state.last_region = region
        else:
            available_agents = st.session_state.available_agents

        agent_arn = ""
        if available_agents:
            unique_agents = {}
            for agent in available_agents:
                name = agent.get("agentRuntimeName", "Unknown")
                runtime_id = agent.get("agentRuntimeId", "")
                if name not in unique_agents:
                    unique_agents[name] = runtime_id

            agent_names = list(unique_agents.keys())
            
            selected_agent_name = st.selectbox(
                "Agent Name",
                options=agent_names,
                help="Choose an agent to chat with",
            )

            if selected_agent_name and selected_agent_name in unique_agents:
                agent_runtime_id = unique_agents[selected_agent_name]
                
                # Only fetch versions if agent changed
                version_key = f"{agent_runtime_id}_{region}"
                if 'agent_versions' not in st.session_state or st.session_state.get('last_agent_key') != version_key:
                    with st.spinner("Loading versions..."):
                        agent_versions = fetch_agent_runtime_versions(agent_runtime_id, region)
                        st.session_state.agent_versions = agent_versions
                        st.session_state.last_agent_key = version_key
                else:
                    agent_versions = st.session_state.agent_versions

                if agent_versions:
                    version_options = []
                    version_arn_map = {}

                    for version in agent_versions:
                        version_num = version.get("agentRuntimeVersion", "Unknown")
                        arn = version.get("agentRuntimeArn", "")
                        updated = version.get("lastUpdatedAt", "")
                        description = version.get("description", "")

                        version_display = f"v{version_num}"
                        if updated:
                            try:
                                if hasattr(updated, "strftime"):
                                    updated_str = updated.strftime("%m/%d %H:%M")
                                    version_display += f" ({updated_str})"
                            except:
                                pass

                        version_options.append(version_display)
                        version_arn_map[version_display] = {
                            "arn": arn,
                            "description": description,
                        }

                    selected_version = st.selectbox(
                        "Version",
                        options=version_options,
                        help="Choose the version to use",
                    )

                    version_info = version_arn_map.get(selected_version, {})
                    agent_arn = version_info.get("arn", "")
                    st.session_state.selected_agent_arn = agent_arn
                    

        # Memory selection
        st.markdown("---")
        st.markdown("**🧠 Memory Configuration**")
        
        # Initialize memory_id in session state if not already there
        if 'selected_memory_id' not in st.session_state:
            st.session_state.selected_memory_id = ""
            
        # Memory selection logic - only fetch if needed
        if 'available_memories' not in st.session_state or st.session_state.get('last_memory_region') != region:
            with st.spinner("Loading available memories..."):
                available_memories = fetch_memory(region)
                memory_ids_log = [memory.get("id", "Unknown") for memory in available_memories]
                logger.info(f"Available memory: {memory_ids_log}")
                st.session_state.available_memories = available_memories
                st.session_state.last_memory_region = region
        else:
            available_memories = st.session_state.available_memories

        memory_id = ""
        if available_memories:
            memory_ids = [memory.get("id", "Unknown") for memory in available_memories]
            #logger.info(f"found memory: {memory_ids}")
            
            # Auto-select the first (most recent) memory if no memory is currently selected
            if not st.session_state.get('selected_memory_id') and memory_ids:
                st.session_state.selected_memory_id = memory_ids[0]
            
            # Set the index for the selectbox based on the selected memory
            current_selection = st.session_state.get('selected_memory_id', "")
            if current_selection in memory_ids:
                default_index = memory_ids.index(current_selection) + 1  # +1 because "None" is at index 0
            else:
                default_index = 1 if memory_ids else 0  # Select first memory if available, otherwise "None"
            
            selected_memory_id = st.selectbox(
                "Memory ID",
                options=["None"] + memory_ids,
                index=default_index,
                help="Choose a memory to use with the agent",
            )
            
            if selected_memory_id and selected_memory_id != "None":
                memory_id = selected_memory_id
                st.session_state.selected_memory_id = memory_id
            else:
                st.session_state.selected_memory_id = ""
        else:
            st.info("No memories found or none available")
            st.session_state.selected_memory_id = ""

        # Runtime Session ID - Simple configuration from streamlit-chat
        # sessions consist of an optional name followed by underscore followed by uuid,
        # since agentcore requires sessionId to be at least 32 characters
        # we extract the name from the beginning of the string to use in the dropdown
        # so users can give sessions human-readable names, while agentcore 
        # gets a name_uuid it can use for memory, session management, etc
        st.markdown("---")
        st.markdown("**🔗 Session Configuration**")

        # Fetch existing sessions (to populate dropdown)
        existing_sessions = fetch_sessions(region, st.session_state.selected_memory_id, st.session_state.get('username'))
        
        if not existing_sessions or not isinstance(existing_sessions, list):
            existing_sessions = [{"sessionId": "default_"+str(uuid.uuid4())}]
        
        # Initialize session ID in session state if there is none
        if "runtime_session_id" not in st.session_state:
            st.session_state.runtime_session_id = existing_sessions[0].get('sessionId', str(uuid.uuid4()))
            logger.info(f"Initialized with session: {st.session_state.runtime_session_id}")
        
        logger.info(f"Found {len(existing_sessions)} sessions")

        # Helper function to format session display name
        def format_session_display(session_id):
            """Extract display name from 'name_uuid' format. If no name before _, show full string."""
            if '_' in session_id:
                name_part = session_id.split('_')[0]
                if name_part:  # If there's a name before _
                    return name_part
            return session_id  # Return full string if no _ or no name before _
        
        # Session dropdown - select from existing sessions
        session_ids = []
        for session in existing_sessions:
            if isinstance(session, dict):
                session_ids.append(session.get('sessionId', 'Unknown'))
            else:
                logger.warning(f"Unexpected session format: {session}")
                session_ids.append(str(session))
        
        # Create display names for dropdown
        session_display_names = [format_session_display(sid) for sid in session_ids]
        
        # Find current session index
        try:
            current_index = session_ids.index(st.session_state.runtime_session_id)
        except ValueError:
            current_index = 0
        
        selected_display = st.selectbox(
            "Select Existing Session",
            options=session_display_names,
            index=current_index,
            help="Choose an existing session from the dropdown"
        )
        
        # Map display name back to full session ID
        selected_index = session_display_names.index(selected_display)
        selected_session = session_ids[selected_index]
        
        # Update session state when user selects from dropdown
        if selected_session != st.session_state.runtime_session_id:
            st.session_state.runtime_session_id = selected_session

        # New session input with button
        # Use session state to control the input value
        if 'new_session_input' not in st.session_state:
            st.session_state.new_session_input = ""
        
        new_session_name = st.text_input(
            "New Session Name",
            value=st.session_state.new_session_input,
            placeholder="Enter session name...",
            help="Type a session name and click 'New Session' to create",
            key="new_session_name_input"
        )

        if st.button("🔄 New Session", help="Create new session with the name above and clear chat"):
            if new_session_name.strip():
                # Format as name_uuid (using _ instead of # for AWS compliance)
                st.session_state.runtime_session_id = f"{new_session_name.strip()}_{str(uuid.uuid4())}"
            else:
                # Generate UUID only (no name prefix)
                st.session_state.runtime_session_id = str(uuid.uuid4())
            
            st.session_state.messages = []  # Clear chat messages when creating new session
            if 'last_metrics' in st.session_state:
                del st.session_state.last_metrics
            
            # Clear the input box for next time
            st.session_state.new_session_input = ""
            
            logger.info(f"Created new session: {st.session_state.runtime_session_id}")
            st.rerun()

        # System prompt configuration
        st.markdown("---")
        st.markdown("**📝 System Prompt**")
        system_prompt = st.text_area(
            "System Prompt",
            value=st.session_state.get('system_prompt', STRANDS_SYSTEM_PROMPT),
            height=100,
            help="Configure the agent's behavior"
        )
        st.session_state.system_prompt = system_prompt

        # Clear chat button
        st.markdown("---")
        if st.button("🗑️ Clear Chat", use_container_width=True):
            # TBD: clear AgentCore memory for this session if applicable
            st.session_state.messages = []
            if 'last_metrics' in st.session_state:
                del st.session_state.last_metrics
            st.rerun()


def main():
    if ENABLE_AUTH:
        auth = require_authentication()
    else:
        auth = None

    # Show Settings and Tools in sidebar
    show_settings_sidebar(auth)
    
    st.logo("static/agentcore-service-icon.png", size="large")
    st.title("Amazon Bedrock AgentCore Strands Playground")

    # Create two-column layout (removed tools column - now in sidebar)
    col1, col2 = st.columns([2, 1])

    # Panel 1: AgentCore Chat
    with col1:
        #st.header("AgentCore Chat")
        
        # Initialize chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Display chat messages
        chat_container = st.container(height=500)
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"], avatar=message.get("avatar", AI_AVATAR if message["role"] == "assistant" else HUMAN_AVATAR)):
                    st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input("Type your message here..."):
            # AgentCore mode implementation
            selected_agent_arn = st.session_state.get('selected_agent_arn', '')
            if selected_agent_arn:
                # Add user message to chat history
                st.session_state.messages.append(
                    {"role": "user", "content": prompt, "avatar": HUMAN_AVATAR}
                )
                
                # Generate assistant response using AgentCore Runtime
                # Show spinner outside chat to avoid duplication
                with st.spinner("Calling AgentCore Runtime..."):
                    # Get region from sidebar session state
                    region = st.session_state.get('selected_region', 'us-west-2')
                    
                    if ENABLE_AUTH:
                        agentcore_response = invoke_agentcore_runtime_auth(
                            message=prompt,
                            agent_arn=selected_agent_arn,
                            region=region,
                            access_token=st.session_state.access_token,
                            session_id=st.session_state.runtime_session_id,
                            username=st.session_state.get('username'),
                            memory_id=st.session_state.get('selected_memory_id')
                        )
                    else:
                        agentcore_response = invoke_agentcore_runtime_no_auth(
                            message=prompt,
                            agent_arn=selected_agent_arn,
                            region=region,
                            session_id=st.session_state.runtime_session_id,
                            username=st.session_state.get('username'),
                            memory_id=st.session_state.get('selected_memory_id')
                        )
                    logger.info(f"AgentCore Response - Success: {agentcore_response.get('success')}, Response Length: {len(agentcore_response.get('response', ''))}, Metrics: {agentcore_response.get('metrics')}")
                    logger.info(f"AgentCore Response Text: {agentcore_response.get('response', '')}")
                    if agentcore_response['success']:
                        response_text = agentcore_response['response']
                        # Store metrics for the metrics panel
                        st.session_state.last_metrics = agentcore_response['metrics']
                    else:
                        response_text = agentcore_response['response']
                        st.session_state.last_metrics = agentcore_response['metrics']

                # Add assistant response to chat history
                st.session_state.messages.append(
                    {"role": "assistant", "content": response_text, "avatar": AI_AVATAR}
                )
                
                # Rerun to display the new messages from session state
                st.rerun()
            else:
                if not selected_agent_arn:
                    st.warning("⚠️ Please select an AgentCore agent to continue.")
                else:
                    st.warning("⚠️ Authentication required. Please log in again.")
            
    # Panel 2: Metrics Summary
    with col2:
        render_metrics_panel()

if __name__ == "__main__":
    main()
