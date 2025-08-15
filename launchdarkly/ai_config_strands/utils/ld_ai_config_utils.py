#!/usr/bin/env python3
"""
LaunchDarkly AI Config Utilities

Shared utilities for loading AI configurations across multiple agents.
Provides centralized LaunchDarkly client management and AI Config loading.
"""

import os
import logging
import uuid
import dotenv
import ldclient
from ldclient import Context
from ldclient.config import Config
from ldai.client import LDAIClient, AIConfig, ModelConfig, LDMessage, ProviderConfig

# Import centralized logging configuration from same package
from .logging_config import get_agent_logger

# Setup logging for this utility module
logger = get_agent_logger("ld_ai_config_utils")

# Global clients (initialized once)
_ld_client = None
_ai_client = None
_clients_initialized = False

def initialize_launchdarkly_clients():
    """
    Initialize LaunchDarkly clients globally.
    This should be called once at application startup.
    """
    global _ld_client, _ai_client, _clients_initialized
    
    if _clients_initialized:
        logger.debug("LaunchDarkly clients already initialized")
        return _ld_client, _ai_client
    
    try:
        # Load environment variables
        dotenv.load_dotenv()
        
        # Get LaunchDarkly server key
        ld_server_key = os.getenv("LD_SERVER_KEY")
        if not ld_server_key:
            logger.error("LD_SERVER_KEY environment variable is required")
            raise ValueError("Missing required environment variable: LD_SERVER_KEY")
        
        # Initialize LaunchDarkly client
        ldclient.set_config(Config(ld_server_key))
        _ld_client = ldclient.get()
        logger.debug("LaunchDarkly client initialized successfully")
        
        # Initialize AI Config client
        _ai_client = LDAIClient(_ld_client)
        logger.debug("LaunchDarkly AI Config client initialized successfully")
        
        _clients_initialized = True
        return _ld_client, _ai_client
        
    except Exception as e:
        logger.error(f"Failed to initialize LaunchDarkly clients: {str(e)}")
        raise RuntimeError(f"LaunchDarkly client initialization failed: {str(e)}")

def create_agent_context(agent_role, additional_attributes=None):
    """
    Create a LaunchDarkly context for an agent with the specified role.
    
    Args:
        agent_role (str): The role of the agent (e.g., 'teacher-orchestrator', 'computer-science-assistant')
        additional_attributes (dict, optional): Additional context attributes to include
        
    Returns:
        Context: LaunchDarkly context object
    """
    try:
        # Generate unique context key with role identification
        context_key = f"agent-{agent_role}-{uuid.uuid4().hex[:8]}"
        
        # Build base context with agent role
        context_builder = Context.builder(context_key) \
            .set("role", agent_role) \
            .set("agent_type", "multi_agent_system")
        
        # Add additional attributes if provided
        if additional_attributes:
            for key, value in additional_attributes.items():
                context_builder.set(key, value)
        
        agent_context = context_builder.build()
        
        logger.info(f"Agent context created - Role: {agent_role}, Context Key: {context_key}")
        logger.debug(f"Full context: {agent_context.to_json_string()}")
        
        return agent_context
        
    except Exception as e:
        logger.error(f"Failed to create agent context for role {agent_role}: {str(e)}")
        raise RuntimeError(f"Agent context creation failed: {str(e)}")

def load_fallback_prompt_from_file(fallback_file_path, ultimate_fallback=None):
    """
    Load fallback prompt from a text file.
    
    Args:
        fallback_file_path (str): Path to the fallback prompt file
        ultimate_fallback (str, optional): Ultimate fallback text if file is missing
        
    Returns:
        str: The fallback prompt text
    """
    import os
    from pathlib import Path
    
    try:
        # Handle relative paths - make them relative to the project root
        if not os.path.isabs(fallback_file_path):
            # Get the project root directory (where this utils file is located)
            project_root = Path(__file__).parent.parent
            fallback_file_path = project_root / fallback_file_path
        
        with open(fallback_file_path, 'r', encoding='utf-8') as file:
            fallback_prompt = file.read().strip()
        logger.debug(f"Fallback prompt loaded from {fallback_file_path}")
        return fallback_prompt
    except FileNotFoundError:
        logger.error(f"Fallback prompt file not found: {fallback_file_path}")
        if ultimate_fallback:
            logger.info("Using ultimate fallback prompt")
            return ultimate_fallback
        else:
            raise
    except Exception as e:
        logger.error(f"Error loading fallback prompt from {fallback_file_path}: {str(e)}")
        if ultimate_fallback:
            logger.info("Using ultimate fallback prompt due to error")
            return ultimate_fallback
        else:
            raise

def load_ai_config_prompt(agent_role, ai_config_id=None, fallback_file_path=None, ultimate_fallback=None, additional_context=None):
    """
    Load system prompt from LaunchDarkly AI Config for a specific agent role.
    
    Args:
        agent_role (str): The role of the agent for context targeting
        ai_config_id (str, optional): AI Config ID to load. Defaults to env var LD_AI_CONFIG_ID
        fallback_file_path (str, optional): Path to fallback prompt file
        ultimate_fallback (str, optional): Ultimate fallback if all else fails
        additional_context (dict, optional): Additional context attributes
        
    Returns:
        tuple: (system_prompt, tracker, config) - The prompt, LaunchDarkly tracker, and full config
    """
    try:
        # Ensure clients are initialized
        ld_client, ai_client = initialize_launchdarkly_clients()
        
        # Get AI Config ID from parameter or environment
        if not ai_config_id:
            ai_config_id = os.getenv("LD_AI_CONFIG_ID", "multi-agent-llm-prompt-1")
        
        # Create agent context
        agent_context = create_agent_context(agent_role, additional_context)
        
        # Load fallback prompt
        fallback_prompt = None
        if fallback_file_path:
            fallback_prompt = load_fallback_prompt_from_file(fallback_file_path, ultimate_fallback)
        elif ultimate_fallback:
            fallback_prompt = ultimate_fallback
        else:
            fallback_prompt = f"You are a {agent_role.replace('-', ' ')} assistant. Help users with their queries."
        
        # Create fallback AI Config
        fallback_config = AIConfig(
            enabled=True,
            model=ModelConfig(
                name="anthropic.claude-v2:1",
                parameters={"temperature": 0.7, "max_tokens": 2000},
            ),
            messages=[LDMessage(role="system", content=fallback_prompt)],
            provider=ProviderConfig(name="bedrock"),
        )
        
        # Load AI Config with agent context
        logger.debug(f"Loading AI Config: {ai_config_id} with context role: {agent_role}")
        config, tracker = ai_client.config(ai_config_id, agent_context, fallback_config)
        
        # Extract system prompt from AI Config
        if config.messages and len(config.messages) > 0:
            system_prompt = config.messages[0].content
            logger.info(f"Successfully loaded system prompt from AI Config for {agent_role}")
            logger.debug(f"Loaded prompt preview: {system_prompt[:100]}...")
        else:
            logger.warning(f"No messages found in AI Config for {agent_role}, using fallback prompt")
            system_prompt = fallback_prompt
        
        return system_prompt, tracker, config
        
    except Exception as e:
        logger.error(f"Failed to load AI Config for {agent_role}: {str(e)}")
        logger.info(f"Falling back to default prompt for {agent_role}")
        
        # Return fallback prompt
        if fallback_file_path:
            try:
                fallback_prompt = load_fallback_prompt_from_file(fallback_file_path, ultimate_fallback)
            except:
                fallback_prompt = ultimate_fallback or f"You are a {agent_role.replace('-', ' ')} assistant."
        else:
            fallback_prompt = ultimate_fallback or f"You are a {agent_role.replace('-', ' ')} assistant."
        
        return fallback_prompt, None, None

def get_ai_clients():
    """
    Get the initialized LaunchDarkly clients.
    Initializes them if not already done.
    
    Returns:
        tuple: (ld_client, ai_client)
    """
    if not _clients_initialized:
        return initialize_launchdarkly_clients()
    return _ld_client, _ai_client
