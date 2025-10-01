import os
import sys
from pathlib import Path
from strands import Agent, tool
from strands_tools import file_read, file_write, editor
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
logger = get_agent_logger("english_assistant")

# Load dynamic prompt from AI Config
try:
    # Get agent role from environment
    agent_role = os.getenv("ENGLISH_ASSISTANT_ROLE", "english-assistant")
    agent_config_id = os.getenv("LD_AI_CONFIG_ID_ENGLISH", "english-assistant")
    
    logger.info(f"Initializing english-assistant agent with role: {agent_role}")
    
    # Load AI Config prompt with fallback
    ENGLISH_ASSISTANT_SYSTEM_PROMPT, ai_tracker, ai_config, ai_tools = load_ai_agent_prompt(
        agent_role=agent_role,
        ai_config_id=agent_config_id,
        fallback_file_path="fallback_prompts/english_assistant_fallback_prompt.txt",
        ultimate_fallback="You are English master, an advanced English education assistant. Help users with grammar, writing, literature analysis, and language learning with clear explanations and constructive feedback.",
        logger=logger
    )
    
    logger.info("English-assistant dynamic prompt loaded successfully")
    
except Exception as e:
    logger.error(f"Critical error loading AI Config for english-assistant: {str(e)}")
    # Use ultimate fallback if AI Config fails completely
    ENGLISH_ASSISTANT_SYSTEM_PROMPT = "You are English master, an advanced English education assistant. Help users with grammar, writing, literature analysis, and language learning with clear explanations and constructive feedback."
    ai_tracker = None
    ai_config = None
    logger.warning("Using ultimate fallback prompt for english-assistant")


@tool
def english_assistant(query: str) -> str:
    """
    Process and respond to English language, literature, and writing-related queries.
    
    Args:
        query: The user's English language or literature question
        
    Returns:
        A helpful response addressing English language or literature concepts
    """
    # Format the query with specific guidance for the English assistant
    formatted_query = f"Analyze and respond to this English language or literature question, providing clear explanations with examples where appropriate: {query}"
    
    try:
        logger.info("Processing query - routing to English Assistant")
        print("Routed to English Assistant")
        
        # Create a Bedrock model instance
        logger.info("Loading model config: {}".format(ai_config.model.name))
        bedrock_model = BedrockModel(
            model_id= ai_config.model.name,
            temperature= ai_config.model.get_custom("temperature"),
            top_p= ai_config.model.get_custom("topP"),
            streaming=False,
        )

        # Create the english agent with dynamic prompt and file manipulation tools
        logger.debug("Creating english agent with dynamic prompt and file tools")
        english_agent = Agent(
            model=bedrock_model,
            system_prompt=ENGLISH_ASSISTANT_SYSTEM_PROMPT,
            callback_handler=lambda **kwargs: event_loop_tracker(ai_tracker, logger, **kwargs),
            tools=[editor, file_read, file_write],
        )
        
        logger.debug("Executing query with english agent")
        agent_response = english_agent(formatted_query)
        text_response = str(agent_response)

        if len(text_response) > 0:
            logger.info("English query processed successfully")
            return text_response
        
        logger.warning("English agent returned empty response")
        return "I apologize, but I couldn't properly analyze your English language question. Could you please rephrase or provide more context?"
        
    except Exception as e:
        # Return specific error message for English queries
        logger.error(f"Error in english_assistant tool: {str(e)}")
        return f"Error processing your English language query: {str(e)}"