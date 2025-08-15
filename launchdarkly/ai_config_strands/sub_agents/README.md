# Sub-Agents Directory

This directory contains all specialized assistant agents for the multi-agent educational system. Each agent is designed to handle specific domains of knowledge and is integrated with LaunchDarkly AI Config for dynamic prompt management.

## Available Agents

### 🖥️ `computer_science_assistant.py`
- **Domain**: Programming and Computer Science Education
- **Role**: `computer-science-assistant`
- **Tools**: `python_repl`, `shell`, `file_read`, `file_write`, `editor`
- **Capabilities**: Code execution, debugging, algorithm development, software design patterns

### 🧮 `math_assistant.py`
- **Domain**: Mathematics Education and Problem-Solving
- **Role**: `math-assistant`
- **Tools**: `calculator`
- **Capabilities**: Arithmetic, algebra, geometry, statistics, step-by-step solutions

### 🌍 `language_assistant.py`
- **Domain**: Language Translation and Learning
- **Role**: `language-assistant`
- **Tools**: `http_request`
- **Capabilities**: Translation, cultural context, pronunciation guidance, language patterns

### 📝 `english_assistant.py`
- **Domain**: English Language and Literature
- **Role**: `english-assistant`
- **Tools**: `editor`, `file_read`, `file_write`
- **Capabilities**: Grammar, writing assistance, literary analysis, style refinement

### 🌐 `general_assistant.py`
- **Domain**: General Knowledge (Non-specialized)
- **Role**: `general-assistant`
- **Tools**: None (general knowledge only)
- **Capabilities**: Basic information, simple explanations, general queries with disclaimers

## Architecture

All agents follow the same consistent architecture:

### 🔧 **LaunchDarkly AI Config Integration**
- Dynamic prompt loading from `multi-agent-llm-prompt-1`
- Role-based context targeting for personalized prompts
- Robust fallback mechanisms (AI Config → File → Ultimate fallback)

### 📊 **Logging System**
- Agent-specific loggers for clear identification
- Consistent logging format: `LEVEL | agent_name | message`
- Debug support for detailed troubleshooting

### 🛡️ **Error Handling**
- Graceful degradation when AI Config fails
- Comprehensive error logging with context
- Tool-specific error messages for better user experience

### 📁 **File Structure**
```
sub-agents/
├── __init__.py                     # Package initialization with imports
├── README.md                       # This documentation
├── computer_science_assistant.py   # CS education agent
├── math_assistant.py              # Mathematics agent
├── language_assistant.py          # Language/translation agent
├── english_assistant.py           # English/literature agent
└── general_assistant.py           # General knowledge agent
```

## Usage

### Import Individual Agents
```python
from sub_agents.computer_science_assistant import computer_science_assistant
from sub_agents.math_assistant import math_assistant
```

### Import All Agents
```python
from sub_agents import (
    computer_science_assistant,
    math_assistant,
    language_assistant,
    english_assistant,
    general_assistant
)
```

### Use with Teacher Orchestrator
The teacher orchestrator automatically imports and uses all sub-agents:
```python
# teacher_orchestrator.py
from sub_agents import (
    english_assistant,
    language_assistant,
    math_assistant,
    computer_science_assistant,
    general_assistant
)

teacher_agent = Agent(
    system_prompt=TEACHER_SYSTEM_PROMPT,
    tools=[math_assistant, language_assistant, english_assistant, 
           computer_science_assistant, general_assistant],
)
```

## Configuration

### Environment Variables
Each agent uses its own role-specific environment variable:
- `COMPUTER_SCIENCE_ASSISTANT_ROLE=computer-science-assistant`
- `MATH_ASSISTANT_ROLE=math-assistant`
- `LANGUAGE_ASSISTANT_ROLE=language-assistant`
- `ENGLISH_ASSISTANT_ROLE=english-assistant`
- `GENERAL_ASSISTANT_ROLE=general-assistant`

### Fallback Prompts
Each agent has a corresponding fallback prompt file in `../fallback_prompts/`:
- `computer_science_assistant_fallback_prompt.txt`
- `math_assistant_fallback_prompt.txt`
- `language_assistant_fallback_prompt.txt`
- `english_assistant_fallback_prompt.txt`
- `general_assistant_fallback_prompt.txt`

## Development

### Adding New Agents
1. Create new agent file in this directory
2. Follow the established architecture pattern
3. Add import to `__init__.py`
4. Create fallback prompt file
5. Add environment variable to `.env`
6. Update teacher orchestrator imports

### Testing Agents
Each agent can be tested independently:
```python
from sub_agents.math_assistant import math_assistant
result = math_assistant("What is 2 + 2?")
print(result)
```

## Logging Output Example
```
INFO | computer_science_assistant | Initializing computer-science-assistant agent with role: computer-science-assistant
INFO | ld_ai_config_utils | Loading AI Config: multi-agent-llm-prompt-1 with context role: computer-science-assistant
INFO | computer_science_assistant | Computer-science-assistant dynamic prompt loaded successfully
INFO | computer_science_assistant | Processing query - routing to Computer Science Assistant
INFO | computer_science_assistant | Computer science query processed successfully
```

This organized structure provides clear separation of concerns, easy maintenance, and scalable architecture for the multi-agent educational system.
