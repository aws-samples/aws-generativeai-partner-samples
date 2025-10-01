# Strands Multi-Agent Demo

A partner showcase demonstrating multi-agent educational system built with AWS Strands, featuring AI orchestration, memory management, and observability integrations.

## Overview

This example showcases a hub-and-spoke architecture where a teacher orchestrator routes student queries to specialized subject-matter expert agents while maintaining conversation context and providing monitoring through partner integrations.

## Architecture

### Core Components

- **`teacher_orchestrator.py`** - Main orchestrator agent that routes queries to specialized sub-agents
- **`sub_agents/`** - Collection of specialized AI agents for different subject domains
- **`utils/`** - Shared utilities and infrastructure components
- **`fallback_prompts/`** - Backup system prompts when AI configs are unavailable

### Multi-Agent System

- **Teacher Orchestrator** - Central router analyzing queries and delegating to appropriate specialists
- **English Assistant** - English language and literature specialist
- **Math Assistant** - Mathematics and problem-solving specialist
- **Computer Science Assistant** - Programming and CS concepts specialist
- **Language Assistant** - Foreign language learning specialist
- **General Assistant** - General knowledge and miscellaneous queries

### Memory Architecture

Three-tier memory system using MongoDB:

1. **Conversation Memory** - Short-term context within current session
2. **Workflow Memory** - Multi-step interaction patterns and tool usage
3. **Long-term Memory** - Persistent knowledge and user preferences

## Technology Stack

- **AWS Strands** - Agent framework for building AI agents
- **MongoDB Atlas** - Cloud database for memory storage
- **LaunchDarkly** - Feature flag and AI configuration management
- **Arize AI** - ML observability and monitoring platform
- **OpenTelemetry** - Distributed tracing and observability

## Features

- **Dynamic AI Configuration** - Runtime prompt and model management via LaunchDarkly
- **Observability Integration** - Arize AI integration with OpenTelemetry for monitoring
- **Fallback System** - Ensures reliability when AI configs are unavailable
- **Memory-Augmented Conversations** - Context-aware interactions across sessions
- **Subject-Matter Expertise** - Specialized agents for different academic domains

## Setup

### Prerequisites

- Python 3.x
- MongoDB Atlas account
- LaunchDarkly account
- Arize AI account
- AWS credentials for Bedrock

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy environment configuration:
   ```bash
   cp .env.example .env
   ```

4. Configure environment variables in `.env`:
   - LaunchDarkly server key and project key
   - MongoDB connection string
   - Arize AI space ID and API key
   - Agent role configurations

### Environment Variables

```bash
# LaunchDarkly Configuration
LD_SERVER_KEY=your-launchdarkly-server-key
LD_PROJECT_KEY=your-project-key

# AI Config IDs
LD_AI_CONFIG_ID_TEACHER=teacher-orchestrator
LD_AI_CONFIG_ID_ENGLISH=english-assistant
LD_AI_CONFIG_ID_COMPUTER_SCIENCE=computer-science-assistant
LD_AI_CONFIG_ID_MATH=math-assistant
LD_AI_CONFIG_ID_LANGUAGE=language-assistant
LD_AI_CONFIG_ID_GENERAL=general-assistant

# MongoDB Configuration
MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net/
MONGODB_DATABASE=memory_demo

# Memory Configuration
WORKFLOW_MEMORY_ENABLED=true
LONG_TERM_MEMORY_ENABLED=true

# Arize AI Configuration
ARIZE_SPACE_ID=your-arize-space-id
ARIZE_API_KEY=your-arize-api-key
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp.arize.com/v1
```

## Usage

Run the main orchestrator:

```bash
python teacher_orchestrator.py
```

The system will:
1. Initialize all specialized agents
2. Set up memory hooks and observability
3. Start the interactive session
4. Route queries to appropriate subject specialists
5. Maintain conversation context across interactions

## Project Structure

```
├── teacher_orchestrator.py          # Main orchestrator agent
├── sub_agents/                      # Specialized subject agents
│   ├── english_assistant.py
│   ├── math_assistant.py
│   ├── computer_science_assistant.py
│   ├── language_assistant.py
│   └── general_assistant.py
├── utils/                           # Shared utilities
│   ├── ld_ai_config_utils.py       # LaunchDarkly integration
│   ├── strands_to_openinference_mapping.py  # Arize AI processing
│   ├── logging_config.py           # Centralized logging
│   ├── base_memory_hook.py         # Memory base class
│   ├── conversation_memory_hook.py # Short-term memory
│   ├── workflow_memory_hook.py     # Multi-step tracking
│   └── long_term_memory_hook.py    # Persistent storage
├── fallback_prompts/               # Backup system prompts
└── requirements.txt                # Python dependencies
```
