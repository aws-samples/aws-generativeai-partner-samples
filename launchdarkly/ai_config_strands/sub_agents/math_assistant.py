import os
import sys
from pathlib import Path
from strands import Agent, tool
from strands_tools import calculator
from strands.models import BedrockModel

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Import custom handler for Strands
from utils.strands_utils import event_loop_tracker

# Import centralized logging configuration from utils
from utils.logging_config import get_agent_logger

# LaunchDarkly AI Config utilities from utils
from utils.ld_ai_config_utils import load_ai_config_prompt

# Setup agent-specific logging
logger = get_agent_logger("math_assistant")

# Load dynamic prompt from AI Config
try:
    # Get agent role from environment
    agent_role = os.getenv("MATH_ASSISTANT_ROLE", "math-assistant")
    
    logger.info(f"Initializing math-assistant agent with role: {agent_role}")
    
    # Load AI Config prompt with fallback
    MATH_ASSISTANT_SYSTEM_PROMPT, math_ai_tracker, math_ai_config = load_ai_config_prompt(
        agent_role=agent_role,
        fallback_file_path="fallback_prompts/math_assistant_fallback_prompt.txt",
        ultimate_fallback="You are math wizard, a specialized mathematics education assistant. Help users solve mathematical problems with clear explanations and step-by-step solutions."
    )
    
    logger.info("Math-assistant dynamic prompt loaded successfully")
    
except Exception as e:
    logger.error(f"Critical error loading AI Config for math-assistant: {str(e)}")
    # Use ultimate fallback if AI Config fails completely
    MATH_ASSISTANT_SYSTEM_PROMPT = "You are math wizard, a specialized mathematics education assistant. Help users solve mathematical problems with clear explanations and step-by-step solutions."
    math_ai_tracker = None
    math_ai_config = None
    logger.warning("Using ultimate fallback prompt for math-assistant")


@tool
def math_assistant(query: str) -> str:
    """
    Process and respond to math-related queries using a specialized math agent.
    
    Args:
        query: A mathematical question or problem from the user
        
    Returns:
        A detailed mathematical answer with explanations and steps
    """
    # Format the query for the math agent with clear instructions
    formatted_query = f"Please solve the following mathematical problem, showing all steps and explaining concepts clearly: {query}"
    
    try:
        logger.info("Processing query - routing to Math Assistant")
        print("Routed to Math Assistant")
        
        # Create a Bedrock model instance
        logger.info("Loading model config: {}".format(math_ai_config.model.name))
        bedrock_model = BedrockModel(
            model_id= math_ai_config.model.name,
            temperature= math_ai_config.model.get_custom("temperature"),
            top_p= math_ai_config.model.get_custom("topP"),
        )

        # Create the math agent with dynamic prompt and calculator capability
        logger.debug("Creating math agent with dynamic prompt and calculator tool")
        math_agent = Agent(
            system_prompt=MATH_ASSISTANT_SYSTEM_PROMPT,
            callback_handler=lambda **kwargs: event_loop_tracker(math_ai_tracker, logger, **kwargs),
            tools=[calculator],
        )
        
        logger.debug("Executing query with math agent")
        agent_response = math_agent(formatted_query)
        text_response = str(agent_response)

        if len(text_response) > 0:
            logger.info("Math query processed successfully")
            return text_response

        logger.warning("Math agent returned empty response")
        return "I apologize, but I couldn't solve this mathematical problem. Please check if your query is clearly stated or try rephrasing it."
        
    except Exception as e:
        # Return specific error message for math processing
        logger.error(f"Error in math_assistant tool: {str(e)}")
        return f"Error processing your mathematical query: {str(e)}"