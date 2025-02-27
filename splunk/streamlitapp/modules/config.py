"""
Configuration module for the application.
Handles environment variable loading and configuration settings.
"""
from dotenv import load_dotenv
import os
import logging
import logging.config
import yaml

def load_environment():
    """Load environment variables from .env file and set defaults."""
    # Attempt to load .env file from known locations
    file_dir_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(file_dir_path):
        print(f"Loading .env file from: {file_dir_path}")
        load_dotenv(dotenv_path=file_dir_path)
    else:
        print(f"Warning: .env file not found at {file_dir_path}")
    
    # Manually set environment variables to ensure they're available
    # This ensures the values are set regardless of .env file issues
    env_vars = {
        "LOG_LEVEL": "INFO",
        "BEDROCK_AGENT_ID": "changeme",
        "BEDROCK_AGENT_ALIAS_ID": "changeme",
        "BEDROCK_AGENT_TEST_UI_TITLE": "Agents for Amazon Bedrock Test UI",
        "BEDROCK_AGENT_TEST_UI_ICON": ""
    }
    
    # Only set if not already set from .env file
    for key, value in env_vars.items():
        if os.environ.get(key) is None:
            os.environ[key] = value
            print(f"Manually set {key}={value}")
        else:
            print(f"Environment variable already set: {key}={os.environ.get(key)}")

def setup_logging():
    """Configure logging using YAML file or basic config."""
    # Configure logging using YAML
    if os.path.exists("logging.yaml"):
        with open("logging.yaml", "r") as file:
            config = yaml.safe_load(file)
            logging.config.dictConfig(config)
    else:
        log_level = logging.getLevelNamesMapping()[(os.environ.get("LOG_LEVEL", "INFO"))]
        logging.basicConfig(level=log_level)

def get_config_values():
    """Return configuration values from environment variables."""
    return {
        "agent_id": os.environ.get("BEDROCK_AGENT_ID", "OLRUVU6WS4"),
        "agent_alias_id": os.environ.get("BEDROCK_AGENT_ALIAS_ID", "HYYQBZGPOI"),
        "ui_title": os.environ.get("BEDROCK_AGENT_TEST_UI_TITLE", "Agents for Amazon Bedrock Test UI"),
        "ui_icon": os.environ.get("BEDROCK_AGENT_TEST_UI_ICON")
    }

# Functions to verify environment variables are properly set
def print_debug_info():
    """Print debug information about environment variables."""
    print(f"BEDROCK_AGENT_ID={os.environ.get('BEDROCK_AGENT_ID')}")
    print(f"BEDROCK_AGENT_ALIAS_ID={os.environ.get('BEDROCK_AGENT_ALIAS_ID')}")
    print(f"LOG_LEVEL={os.environ.get('LOG_LEVEL')}")