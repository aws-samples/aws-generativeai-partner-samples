#!/usr/bin/env python3
"""
# 📁 Teacher's Assistant Strands Agent

A specialized Strands agent that is the orchestrator to utilize sub-agents and tools at its disposal to answer a user query.

## What This Example Shows

"""

import os
from strands import Agent
from strands_tools import file_read, file_write, editor
from strands.models import BedrockModel

# Import custom handler for Strands
from utils.strands_utils import event_loop_tracker

# Import centralized logging configuration from utils
from utils.logging_config import get_agent_logger

# LaunchDarkly AI Config utilities from utils
from utils.ld_ai_config_utils import load_ai_config_prompt

# Agent imports from sub_agents package
from sub_agents import (
    english_assistant,
    language_assistant,
    math_assistant,
    computer_science_assistant,
    general_assistant
)

# Setup agent-specific logging
logger = get_agent_logger("teacher_orchestrator")

# Load dynamic prompt from AI Config
try:
    # Get agent role from environment
    agent_role = os.getenv("TEACHER_ORCHESTRATOR_ROLE", "teacher-orchestrator")
    
    logger.info(f"Initializing teacher-orchestrator agent with role: {agent_role}")
    
    # Load AI Config prompt with fallback
    TEACHER_SYSTEM_PROMPT, ai_tracker, ai_config = load_ai_config_prompt(
        agent_role=agent_role,
        fallback_file_path="fallback_prompts/teacher_orchestrator_fallback_prompt.txt",
        ultimate_fallback="You are TeachAssist, an educational orchestrator. Route student queries to appropriate specialized agents."
    )
    
    logger.info("Teacher-orchestrator dynamic prompt loaded successfully")
    
except Exception as e:
    logger.error(f"Critical error loading AI Config for teacher-orchestrator: {str(e)}")
    raise RuntimeError(f"Failed to initialize AI Config: {str(e)}")

# Create a Bedrock model instance
logger.info("Loading model config: {}".format(ai_config.model.name))
bedrock_model = BedrockModel(
    model_id= ai_config.model.name,
    temperature= ai_config.model.get_custom("temperature"),
    top_p= ai_config.model.get_custom("topP"),
)

# Create agent with dynamic prompt from AI Config
logger.info("Creating teacher-orchestrator agent with dynamic prompt")

teacher_agent = Agent(
    model=bedrock_model,
    system_prompt=TEACHER_SYSTEM_PROMPT,
    callback_handler=lambda **kwargs: event_loop_tracker(ai_tracker, logger, **kwargs),
    tools=[math_assistant, language_assistant, english_assistant, computer_science_assistant, general_assistant],
)

logger.info("Teacher-orchestrator agent initialized and ready")

# Example usage
if __name__ == "__main__":
    print("\n📁 Teacher's Assistant Strands Agent 📁\n")
    print("Ask a question in any subject area, and I'll route it to the appropriate specialist.")
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