"""
Utils Package

This package contains utility modules for the multi-agent educational system.

Available Utilities:
- ld_ai_config_utils: LaunchDarkly AI Config integration utilities
- logging_config: Centralized logging configuration

All utilities are designed to be shared across the multi-agent system components.
"""

# Import key utilities for easy access
from .ld_ai_config_utils import (
    initialize_launchdarkly_clients,
    create_agent_context,
    load_ai_config_prompt,
    load_ai_agent_prompt,
    get_ai_clients
)

from .logging_config import (
    setup_multi_agent_logging,
    get_agent_logger
)

from .strands_utils import (
    event_loop_tracker
)

__all__ = [
    'initialize_launchdarkly_clients',
    'create_agent_context', 
    'load_ai_config_prompt',
    'load_ai_agent_prompt',
    'get_ai_clients',
    'setup_multi_agent_logging',
    'get_agent_logger',
    'event_loop_tracker'
]
