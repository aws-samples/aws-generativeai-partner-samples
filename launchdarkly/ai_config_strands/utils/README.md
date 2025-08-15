# Utils Directory

This directory contains shared utility modules for the multi-agent educational system. These utilities provide common functionality used across all agents and the orchestrator.

## Available Utilities

### 🚀 `ld_ai_config_utils.py`
**LaunchDarkly AI Config Integration Utilities**

Provides centralized LaunchDarkly AI Config functionality for dynamic prompt management.

#### Key Functions:
- `initialize_launchdarkly_clients()` - Global client initialization with singleton pattern
- `create_agent_context(agent_role, additional_attributes)` - Flexible context creation for different agent roles
- `load_fallback_prompt_from_file(file_path, ultimate_fallback)` - File-based fallback prompt loading with path resolution
- `load_ai_config_prompt(agent_role, fallback_file_path, ultimate_fallback)` - Complete AI Config loading with multi-tier fallback
- `get_ai_clients()` - Accessor for initialized LaunchDarkly clients

#### Features:
- **Global Client Management**: Singleton pattern prevents multiple client initializations
- **Context Flexibility**: Support for additional attributes per agent
- **Robust Fallbacks**: Three-tier fallback strategy (AI Config → File → Ultimate)
- **Path Resolution**: Handles relative paths from subdirectories
- **Error Handling**: Comprehensive error handling with detailed logging

### 📊 `logging_config.py`
**Centralized Logging Configuration**

Provides consistent logging setup across all agents and utilities.

#### Key Functions:
- `setup_multi_agent_logging()` - Initialize logging configuration for the entire system
- `get_agent_logger(agent_name)` - Get agent-specific logger with consistent naming

#### Features:
- **Consistent Format**: `LEVEL | agent_name | message` across all components
- **Agent Identification**: Clear identification of which agent generated each log
- **Environment Control**: Log level configurable via `LOG_LEVEL` environment variable
- **Third-party Suppression**: Reduces noise from verbose third-party libraries
- **Debug Support**: Optional detailed debugging for troubleshooting

## Architecture

### **Shared Infrastructure Pattern**
Both utilities follow a shared infrastructure pattern:
- **Centralized Configuration**: Single source of truth for system-wide settings
- **Reusable Components**: Functions designed for use across multiple agents
- **Error Resilience**: Comprehensive error handling with graceful degradation
- **Logging Integration**: All utilities use the centralized logging system

### **Import Pattern**
All agents and the orchestrator import from the utils package:
```python
# From root level (teacher_orchestrator.py)
from utils.logging_config import get_agent_logger
from utils.ld_ai_config_utils import load_ai_config_prompt

# From sub-agents (with path setup)
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from utils.logging_config import get_agent_logger
from utils.ld_ai_config_utils import load_ai_config_prompt
```

## Usage Examples

### **LaunchDarkly AI Config Integration**
```python
from utils.ld_ai_config_utils import load_ai_config_prompt

# Load dynamic prompt for an agent
system_prompt, tracker, config = load_ai_config_prompt(
    agent_role="math-assistant",
    fallback_file_path="fallback_prompts/math_assistant_fallback_prompt.txt",
    ultimate_fallback="You are a math assistant."
)
```

### **Logging Setup**
```python
from utils.logging_config import get_agent_logger

# Get agent-specific logger
logger = get_agent_logger("math_assistant")
logger.info("Math assistant initialized successfully")
```

### **Client Management**
```python
from utils.ld_ai_config_utils import get_ai_clients

# Get initialized LaunchDarkly clients
ld_client, ai_client = get_ai_clients()
```

## Configuration

### **Environment Variables**
The utilities respect these environment variables:
- `LD_SERVER_KEY` - LaunchDarkly server-side SDK key (required)
- `LD_AI_CONFIG_ID` - AI Config identifier (default: "multi-agent-llm-prompt-1")
- `LD_PROJECT_KEY` - LaunchDarkly project key (default: "default")
- `LOG_LEVEL` - Logging level (default: "INFO")

### **Fallback Strategy**
The AI Config utilities implement a robust three-tier fallback strategy:
1. **Primary**: LaunchDarkly AI Config with role-based targeting
2. **Secondary**: File-based fallback from `fallback_prompts/` directory
3. **Tertiary**: Ultimate hardcoded fallback provided by caller

## Error Handling

### **LaunchDarkly Errors**
- Network connectivity issues
- Invalid SDK keys or configuration
- AI Config loading failures
- Context creation errors

### **File System Errors**
- Missing fallback prompt files
- File permission issues
- Path resolution problems

### **Logging Errors**
- Logger initialization failures
- Log level configuration issues

All errors are handled gracefully with detailed logging and fallback mechanisms.

## Development

### **Adding New Utilities**
1. Create new utility file in this directory
2. Follow the established patterns for error handling and logging
3. Add imports to `__init__.py`
4. Update this README with documentation
5. Ensure compatibility with the existing import patterns

### **Testing Utilities**
```python
# Test LaunchDarkly integration
from utils.ld_ai_config_utils import initialize_launchdarkly_clients
ld_client, ai_client = initialize_launchdarkly_clients()

# Test logging
from utils.logging_config import get_agent_logger
logger = get_agent_logger("test_agent")
logger.info("Test message")
```

## File Structure
```
utils/
├── __init__.py                 # Package initialization with imports
├── README.md                   # This documentation
├── ld_ai_config_utils.py      # LaunchDarkly AI Config utilities
└── logging_config.py          # Centralized logging configuration
```

This organized utility structure provides a clean foundation for shared functionality across the multi-agent educational system.
