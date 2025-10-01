import os
import sys
from pathlib import Path
from strands import Agent, tool
from strands_tools import python_repl, shell, file_read, file_write, editor
from strands.models import BedrockModel

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Import custom handler for Strands
from utils.strands_utils import event_loop_tracker

# Import centralized logging configuration from utils
from utils.logging_config import get_agent_logger

# LaunchDarkly AI Config utilities from utils
from utils.ld_ai_config_utils import load_ai_agent_prompt

# Setup agent-specific logging
logger = get_agent_logger("computer_science_assistant")

# Load dynamic prompt from AI Config
try:
    # Get agent role from environment
    agent_role = os.getenv("COMPUTER_SCIENCE_ASSISTANT_ROLE", "computer-science-assistant")
    agent_config_id = os.getenv("LD_AI_CONFIG_ID_COMPUTER_SCIENCE", "computer-science-assistant")
    
    logger.info(f"Initializing computer-science-assistant agent with role: {agent_role}")
    
    # Load AI Config prompt with fallback
    COMPUTER_SCIENCE_ASSISTANT_SYSTEM_PROMPT, ai_tracker, ai_config, ai_tools = load_ai_agent_prompt(
        agent_role=agent_role,
        ai_config_id=agent_config_id,
        fallback_file_path="fallback_prompts/computer_science_assistant_fallback_prompt.txt",
        ultimate_fallback="You are ComputerScienceExpert, a specialized assistant for computer science education and programming. Help users with programming and computer science concepts.",
        logger=logger
    )
    
    logger.info("Computer-science-assistant dynamic prompt loaded successfully")
    
except Exception as e:
    logger.error(f"Critical error loading AI Config for computer-science-assistant: {str(e)}")
    # Use ultimate fallback if AI Config fails completely
    COMPUTER_SCIENCE_ASSISTANT_SYSTEM_PROMPT = "You are ComputerScienceExpert, a specialized assistant for computer science education and programming. Help users with programming and computer science concepts."
    ai_tracker = None
    ai_config = None
    logger.warning("Using ultimate fallback prompt for computer-science-assistant")


@tool
def computer_science_assistant(query: str) -> str:
    """
    Process and respond to computer science and programming-related questions using a specialized agent with code execution capabilities.
    
    Args:
        query: The user's computer science or programming question
        
    Returns:
        A detailed response addressing computer science concepts or code execution results
    """
    # Format the query for the computer science agent with clear instructions
    formatted_query = f"Please address this computer science or programming question. When appropriate, provide executable code examples and explain the concepts thoroughly: {query}"
    
    try:
        logger.info("Processing query - routing to Computer Science Assistant")
        print("Routed to Computer Science Assistant")
        
        # Create a Bedrock model instance
        logger.info("Loading model config: {}".format(ai_config.model.name))
        bedrock_model = BedrockModel(
            model_id= ai_config.model.name,
            temperature= ai_config.model.get_custom("temperature"),
            top_p= ai_config.model.get_custom("topP"),
            streaming=False,
        )

        # Create the computer science agent with dynamic prompt and relevant tools
        logger.debug("Creating computer science agent with dynamic prompt and tools")
        cs_agent = Agent(
            model=bedrock_model,
            system_prompt=COMPUTER_SCIENCE_ASSISTANT_SYSTEM_PROMPT,
            callback_handler=lambda **kwargs: event_loop_tracker(ai_tracker, logger, **kwargs),
            tools=[python_repl, shell, file_read, file_write, editor],
        )
        
        logger.debug("Executing query with computer science agent")
        agent_response = cs_agent(formatted_query)
        text_response = str(agent_response)

        if len(text_response) > 0:
            logger.info("Computer science query processed successfully")
            return text_response
        
        logger.warning("Computer science agent returned empty response")
        return "I apologize, but I couldn't process your computer science question. Please try rephrasing or providing more specific details about what you're trying to learn or accomplish."
        
    except Exception as e:
        # Return specific error message for computer science processing
        logger.error(f"Error in computer_science_assistant tool: {str(e)}")
        return f"Error processing your computer science query: {str(e)}"