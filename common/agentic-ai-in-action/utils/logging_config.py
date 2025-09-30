#!/usr/bin/env python3
"""
Centralized Logging Configuration for Multi-Agent System

This module provides consistent logging configuration across all agents and utilities.
"""

import logging
import os

def setup_multi_agent_logging():
    """
    Setup logging configuration for the multi-agent system with clear agent identification.
    """
    # Get log level from environment or default to INFO
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Configure the root strands logger for detailed debugging
    logging.getLogger("strands").setLevel(logging.INFO)
    
    # Setup basic configuration with agent identification format
    logging.basicConfig(
        format="%(levelname)s | %(name)s | %(message)s", 
        handlers=[logging.StreamHandler()],
        level=getattr(logging, log_level, logging.INFO),
        force=True  # Override any existing configuration
    )

    # Supress boto logging noise
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING) 
    logging.getLogger("botocore.credentials").setLevel(logging.ERROR)
    logging.getLogger("botocore.utils").setLevel(logging.WARNING)

    # Set specific log levels for different components
    logging.getLogger("teacher_orchestrator").setLevel(logging.INFO)
    logging.getLogger("computer_science_assistant").setLevel(logging.INFO)
    logging.getLogger("math_assistant").setLevel(logging.INFO)
    logging.getLogger("language_assistant").setLevel(logging.INFO)
    logging.getLogger("english_assistant").setLevel(logging.INFO)
    logging.getLogger("general_assistant").setLevel(logging.INFO)
    logging.getLogger("ld_ai_config_utils").setLevel(logging.INFO)
    
    # Suppress overly verbose third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("ldclient").setLevel(logging.WARNING)
    
    # Log the configuration
    logger = logging.getLogger("logging_config")
    logger.info(f"Multi-agent logging configured with level: {log_level}")

def get_agent_logger(agent_name: str) -> logging.Logger:
    """
    Get a logger for a specific agent with consistent naming.
    
    Args:
        agent_name (str): Name of the agent (e.g., 'teacher_orchestrator', 'computer_science_assistant')
        
    Returns:
        logging.Logger: Configured logger for the agent
    """
    return logging.getLogger(agent_name)

# Initialize logging when module is imported
setup_multi_agent_logging()
