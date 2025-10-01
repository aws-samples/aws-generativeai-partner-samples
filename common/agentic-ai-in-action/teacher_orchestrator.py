#!/usr/bin/env python3
"""
# 📁 Teacher's Assistant Strands Agent

A specialized Strands agent that is the orchestrator to utilize sub-agents and tools at its disposal to answer a user query.

"""
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from utils.strands_to_openinference_mapping import StrandsToOpenInferenceProcessor
from arize.otel import register
from opentelemetry import trace
import grpc
import os
from dotenv import load_dotenv
load_dotenv()
from strands import Agent
from strands_tools import file_read, file_write, editor
from strands.models import BedrockModel

# Import custom handler for Strands
from utils.strands_utils import event_loop_tracker

# Import centralized logging configuration from utils
from utils.logging_config import get_agent_logger

# LaunchDarkly AI Config utilities from utils
from utils.ld_ai_config_utils import load_ai_agent_prompt

# Memory hook imports
from utils.conversation_memory_hook import ConversationMemoryHook
from utils.workflow_memory_hook import WorkflowMemoryHook
from utils.long_term_memory_hook import LongTermMemoryHook
from pymongo import MongoClient

# Agent imports from sub_agents package
from sub_agents import (
    english_assistant,
    language_assistant,
    math_assistant,
    computer_science_assistant,
    general_assistant
)
# Set Arize AI provider
provider = register(
    space_id=os.getenv("ARIZE_SPACE_ID"),
    api_key=os.getenv("ARIZE_API_KEY"),
    project_name="strands-agent-integration3",
    set_global_tracer_provider=True,
)

# Set additional span processor which uses custom mapping `StrandsToOpenInferenceProcessor`
provider.add_span_processor(StrandsToOpenInferenceProcessor(debug=False))
provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint=os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"],
            headers={
                "authorization": f"Bearer {os.getenv("ARIZE_API_KEY")}",
                "api_key": os.getenv("ARIZE_API_KEY"),
                "arize-space-id": os.getenv("ARIZE_SPACE_ID"),
                "arize-interface": "python",
                "user-agent": "arize-python",
            },
            compression=grpc.Compression.Gzip,
        )
    )
)
# set trace to use the custom Arize AI provider
user_tracer_provider = trace.set_tracer_provider(provider)

# Setup agent-specific logging
logger = get_agent_logger("teacher_orchestrator")

# Load dynamic prompt from AI Config
try:
    # Get agent role from environment
    agent_role = os.getenv("TEACHER_ORCHESTRATOR_ROLE", "teacher-orchestrator")
    agent_config_id = os.getenv("LD_AI_CONFIG_ID_TEACHER", "teacher-orchestrator")
    
    logger.info(f"Initializing teacher-orchestrator agent with role: {agent_role}")
    
    # Create sub_agents mapping
    sub_agents_mapping = {
        'english_assistant': english_assistant,
        'language_assistant': language_assistant,
        'math_assistant': math_assistant,
        'computer_science_assistant': computer_science_assistant,
        'general_assistant': general_assistant
    }
    
    # Load AI Config prompt with fallback
    TEACHER_SYSTEM_PROMPT, ai_tracker, ai_config, ai_tools = load_ai_agent_prompt(
        agent_role=agent_role,
        ai_config_id=agent_config_id,
        fallback_file_path="fallback_prompts/teacher_orchestrator_fallback_prompt.txt",
        ultimate_fallback="You are TeachAssist, an educational orchestrator. Route student queries to appropriate specialized agents.",
        sub_agents_mapping=sub_agents_mapping,
        logger=logger
    )
    
    logger.info("Teacher-orchestrator dynamic prompt loaded successfully")
    
except Exception as e:
    logger.error(f"Critical error loading AI Config for teacher-orchestrator: {str(e)}")
    raise RuntimeError(f"Failed to initialize AI Config: {str(e)}")

# Initialize Memory System
mongo_client = None
try:
    logger.info("Initializing memory system...")
    mongo_client = MongoClient(
        os.getenv("MONGODB_CONNECTION_STRING"),
        serverSelectionTimeoutMS=60000,  # 60 seconds - more time to find server
        connectTimeoutMS=30000,          # 30 seconds - more time for initial connection
        socketTimeoutMS=60000,           # 60 seconds - more time for operations
        retryWrites=True,                # Automatic retry on write failures
        retryReads=True,                 # Automatic retry on read failures
        maxPoolSize=10,                  # Smaller pool to reduce stale connections
        maxIdleTimeMS=30000,             # Close idle connections after 30s
        heartbeatFrequencyMS=10000,      # Check server health every 10s
    )
    conversation_hook = ConversationMemoryHook(
        mongo_client=mongo_client,
        database_name=os.getenv("MONGODB_DATABASE", "memory_demo"),
        collection_name=os.getenv("MONGODB_COLLECTION_CONVERSATION", "conversation_memory")
    )
    
    # Initialize workflow memory hook
    workflow_enabled = os.getenv("WORKFLOW_MEMORY_ENABLED", "false").lower() == "true"
    workflow_hook = WorkflowMemoryHook(
        mongo_client=mongo_client,
        database_name=os.getenv("MONGODB_DATABASE", "memory_demo"),
        collection_name=os.getenv("MONGODB_COLLECTION_WORKFLOW", "workflow_memory"),
        load_enabled=workflow_enabled
    ) if workflow_enabled else None
    
    # Initialize long-term memory hook
    long_term_enabled = os.getenv("LONG_TERM_MEMORY_ENABLED", "false").lower() == "true"
    long_term_hook = LongTermMemoryHook(
        mongo_client=mongo_client,
        database_name=os.getenv("MONGODB_DATABASE", "memory_demo"),
        collection_name=os.getenv("MONGODB_COLLECTION_LONG_TERM", "long_term_memory"),
        load_enabled=long_term_enabled
    ) if long_term_enabled else None
    logger.info("Memory system initialized successfully")
except Exception as e:
    logger.error(f"Error initializing memory system: {str(e)}")
    conversation_hook = None
    logger.warning("Continuing without memory functionality")

# Create a Bedrock model instance
logger.info("Loading model config: {}".format(ai_config.model.name))
bedrock_model = BedrockModel(
    model_id= ai_config.model.name,
    temperature= ai_config.model.get_custom("temperature"),
    top_p= ai_config.model.get_custom("topP"),
    streaming=False,
)

# Create agent with dynamic prompt from AI Config and memory hook
logger.info("Creating teacher-orchestrator agent with dynamic prompt and memory")

# Prepare hooks list
hooks = []
if conversation_hook:
    hooks.append(conversation_hook)
if workflow_hook:
    hooks.append(workflow_hook)
if long_term_hook:
    hooks.append(long_term_hook)

teacher_agent = Agent(
    model=bedrock_model,
    system_prompt=TEACHER_SYSTEM_PROMPT,
    hooks=hooks,  # Add memory hook
    callback_handler=lambda **kwargs: event_loop_tracker(ai_tracker, logger, **kwargs),
    tools=ai_tools,
    trace_attributes={
        "session.id": "abc-300",
        "user.id": "user-email-example@domain.com",
        "arize.tags": [
            "Agent-SDK",
            "Arize-Project",
            "OpenInference-Integration",
        ]
    }
)

logger.info("Teacher-orchestrator agent initialized and ready")

# Example usage
if __name__ == "__main__":
    print("\n📁 Teacher's Assistant Strands Agent 📁\n")
    print("Ask a question in any subject area, and I'll route it to the appropriate specialist.")
    print("Conversation Memory:", "✅ Enabled" if conversation_hook else "❌ Disabled")
    print("Workflow memory:", "✅ Enabled" if workflow_hook else "❌ Disabled")
    print("Long-term memory:", "✅ Enabled" if long_term_hook else "❌ Disabled")
    print("Type 'exit' to quit.")

    # Interactive loop
    while True:
        try:
            user_input = input("\n> ")
            if user_input.lower() == "exit":
                print("\nGoodbye! 👋")
                break

            response = teacher_agent(
                user_input, 
            )
            
            # Extract and print only the relevant content from the specialized agent's response
            content = str(response)
            print(content)
            
        except KeyboardInterrupt:
            print("\n\nExecution interrupted. Exiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            print("Please try asking a different question.")
    
    # Cleanup resources
    if mongo_client:
        mongo_client.close()
        logger.info("MongoDB client closed")