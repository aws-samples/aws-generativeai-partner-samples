# LaunchDarkly AI Config Demo with Strands Agent SDK

This is a demo of how to use Strands Agent SDK to create multi-agent workflow with LaunchDarkly AI Config for dynamic prompt management. The system consists of a teacher orchestrator that intelligently routes student queries to specialized subject matter experts. This demo is inspired by sample implementation from [Strands Agent documentation](https://strandsagents.com/latest/documentation/docs/examples/python/agents_workflows/)

## 🏗️ Architecture Overview

For more in depth architecture details, please see [architecture](/launchdarkly/ai_config_strands/docs/architecture_diagrams.md)
```
┌─────────────────────────────────────────────────────────────┐
│                    Teacher Orchestrator                     │
│              (Routes queries to specialists)                │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Math      │ │  Computer   │ │  Language   │
│ Assistant   │ │   Science   │ │ Assistant   │
│             │ │ Assistant   │ │             │
└─────────────┘ └─────────────┘ └─────────────┘
        │             │             │
        ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  English    │ │   General   │ │ LaunchDarkly│
│ Assistant   │ │ Assistant   │ │ AI Config   │
│             │ │             │ │             │
└─────────────┘ └─────────────┘ └─────────────┘
```

## 📁 Project Structure

```
strands-multi-agent/
├── 📄 README.md                           # This file
├── 📄 .env                               # Environment configuration
├── 📄 .gitignore                         # Git ignore rules
├── 📄 requirements.txt                   # Python dependencies
├── 🎓 teacher_orchestrator.py            # Main orchestrator agent
│
├── 📁 utils/                             # Shared utilities
│   ├── 📄 __init__.py                    # Package initialization
│   ├── 📄 README.md                      # Utils documentation
│   ├── 🔧 ld_ai_config_utils.py         # LaunchDarkly utilities
│   └── 📊 logging_config.py             # Centralized logging
│
├── 📁 sub_agents/                        # Specialized agents
│   ├── 📄 __init__.py                    # Package initialization
│   ├── 📄 README.md                      # Sub-agents documentation
│   ├── 🖥️ computer_science_assistant.py  # Programming & CS
│   ├── 🧮 math_assistant.py              # Mathematics
│   ├── 🌍 language_assistant.py          # Translation & languages
│   ├── 📝 english_assistant.py           # Writing & literature
│   └── 🌐 general_assistant.py           # General knowledge
│
└── 📁 fallback_prompts/                  # Backup prompts
    ├── 📄 README.md                      # Fallback documentation
    ├── 📄 teacher_orchestrator_fallback_prompt.txt
    ├── 📄 computer_science_assistant_fallback_prompt.txt
    ├── 📄 math_assistant_fallback_prompt.txt
    ├── 📄 language_assistant_fallback_prompt.txt
    ├── 📄 english_assistant_fallback_prompt.txt
    └── 📄 general_assistant_fallback_prompt.txt
```

## 🚀 Features

### 🔄 **Dynamic Prompt Management**
- All agents load prompts from LaunchDarkly AI Config
- Zero-downtime prompt updates without code deployment
- A/B testing capabilities for different teaching approaches

### 🛡️ **Robust Fallback System**
- **Primary**: LaunchDarkly AI Config with role-based targeting
- **Secondary**: File-based fallback prompts
- **Tertiary**: Ultimate hardcoded fallbacks

### 🔧 **Specialized Callback Handler**
- Custom callback handler to instrument LLM telemtry back to LaunchDarkly AI Config
- Can be customized for other use-cases such as evaluating response quality

## 🎓 Available Agents

| Agent | Domain | Role | Tools | Capabilities |
|-------|--------|------|-------|-------------|
| 🎓 **Teacher Orchestrator** | Query Routing | `teacher-orchestrator` | All sub-agents | Intelligent routing to specialists |
| 🖥️ **Computer Science** | Programming & CS | `computer-science-assistant` | `python_repl`, `shell`, `file_read`, `file_write`, `editor` | Code execution, debugging, algorithms |
| 🧮 **Mathematics** | Math Education | `math-assistant` | `calculator` | Problem-solving, step-by-step solutions |
| 🌍 **Language** | Translation & Learning | `language-assistant` | `http_request` | Translation, cultural context |
| 📝 **English** | Writing & Literature | `english-assistant` | `editor`, `file_read`, `file_write` | Grammar, writing assistance, analysis |
| 🌐 **General** | General Knowledge | `general-assistant` | None | Basic information with disclaimers |

## ⚙️ Setup & Configuration

### 1. **Environment Setup**
```bash
# Clone the repository
git clone <repository-url>
cd launchdarkly/ai_config_strands

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. **LaunchDarkly Configuration**
Update `.env` file with your LaunchDarkly credentials:
```env
# LaunchDarkly Configuration
LD_SERVER_KEY=your-launchdarkly-server-key
LD_AI_CONFIG_ID=multi-agent-llm-prompt-1
LD_PROJECT_KEY=your-project-key

# Agent Roles - must match the segment context that you setup in LaunchDarkly AI Config
TEACHER_ORCHESTRATOR_ROLE=teacher-orchestrator
COMPUTER_SCIENCE_ASSISTANT_ROLE=computer-science-assistant
MATH_ASSISTANT_ROLE=math-assistant
LANGUAGE_ASSISTANT_ROLE=language-assistant
ENGLISH_ASSISTANT_ROLE=english-assistant
GENERAL_ASSISTANT_ROLE=general-assistant
```

### 3. **LaunchDarkly AI Config Setup**
Use the [bootstrap](./bootstrap/README.md) instruction to create the required AI Config in LaunchDarkly.

## 🎮 Usage

### **Basic Usage**
```python
from teacher_orchestrator import teacher_agent

# Ask a math question
response = teacher_agent("What is the derivative of x^2?")
print(response)

# Ask a programming question  
response = teacher_agent("How do I implement a binary search in Python?")
print(response)

# Ask a language question
response = teacher_agent("How do you say 'hello' in Spanish?")
print(response)
```

### **Direct Agent Usage**
```python
from sub_agents import math_assistant, computer_science_assistant

# Use specific agent directly
math_result = math_assistant("Solve: 2x + 5 = 15")
code_result = computer_science_assistant("Write a Python function to reverse a string")
```

### **Interactive Mode**
```python
# Run the teacher orchestrator interactively
python teacher_orchestrator.py
```

## 📊 Logging Output

The system provides clear, agent-specific logging:

```
INFO | logging_config | Multi-agent logging configured with level: INFO
INFO | teacher_orchestrator | Initializing teacher-orchestrator agent with role: teacher-orchestrator
INFO | ld_ai_config_utils | Loading AI Config: multi-agent-llm-prompt-1 with context role: teacher-orchestrator
INFO | teacher_orchestrator | Teacher-orchestrator dynamic prompt loaded successfully
INFO | math_assistant | Processing query - routing to Math Assistant
INFO | math_assistant | Math query processed successfully
```

## 📈 Monitoring & Analytics

Every agent it initialized with [callback_handler](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/streaming/callback-handlers/), which allowing you to create custom function as shown below:

```
teacher_agent = Agent(
    model=bedrock_model,
    system_prompt=TEACHER_SYSTEM_PROMPT,
    callback_handler=lambda **kwargs: event_loop_tracker(ai_tracker, logger, **kwargs),
    tools=[math_assistant, language_assistant, english_assistant, computer_science_assistant, general_assistant],
)
```

The function `event_loop_tracker` is responsible to unpack the Strands Agent [`EventLoopMetrics`](https://strandsagents.com/latest/documentation/docs/api-reference/telemetry/#strands.telemetry.metrics.EventLoopMetrics) and send it to LaunchDarkly:
```
def event_loop_tracker(tracker, logger, **kwargs):   
    # Track Metrics
    if kwargs.get("result", False):        
        logger.info(f"Metrics: {kwargs['result'].metrics}")
        tracker.track_success()
        tracker.track_duration(sum(kwargs['result'].metrics.cycle_durations))
        tracker.track_time_to_first_token(kwargs['result'].metrics.accumulated_metrics['latencyMs'])
        tokens = TokenUsage(
            total = kwargs['result'].metrics.accumulated_usage['totalTokens'],
            input = kwargs['result'].metrics.accumulated_usage['inputTokens'],
            output = kwargs['result'].metrics.accumulated_usage['outputTokens'],
        )
        tracker.track_tokens(tokens)
```

## 📚 Documentation

- **[Utils Documentation](utils/README.md)**: Shared utilities documentation
- **[Sub-Agents Documentation](sub_agents/README.md)**: Detailed agent information
- **[Fallback Prompts Documentation](fallback_prompts/README.md)**: Backup system details

## 📄 License

MIT-0
---

**Built with ❤️ using LaunchDarkly AI Config and Strands Agent SDK**