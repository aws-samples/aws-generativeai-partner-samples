import os
import sys
from pathlib import Path
from strands import Agent, tool
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
logger = get_agent_logger("general_assistant")

# Load dynamic prompt from AI Config
try:
    # Get agent role from environment
    agent_role = os.getenv("GENERAL_ASSISTANT_ROLE", "general-assistant")
    
    logger.info(f"Initializing general-assistant agent with role: {agent_role}")
    
    # Load AI Config prompt with fallback
    GENERAL_ASSISTANT_SYSTEM_PROMPT, general_ai_tracker, general_ai_config = load_ai_config_prompt(
        agent_role=agent_role,
        fallback_file_path="fallback_prompts/general_assistant_fallback_prompt.txt",
        ultimate_fallback="You are GeneralAssist, a concise general knowledge assistant for topics outside specialized domains. Always acknowledge that you are not an expert in specific areas and provide brief, direct answers with disclaimers."
    )
    
    logger.info("General-assistant dynamic prompt loaded successfully")
    
except Exception as e:
    logger.error(f"Critical error loading AI Config for general-assistant: {str(e)}")
    # Use ultimate fallback if AI Config fails completely
    GENERAL_ASSISTANT_SYSTEM_PROMPT = "You are GeneralAssist, a concise general knowledge assistant for topics outside specialized domains. Always acknowledge that you are not an expert in specific areas and provide brief, direct answers with disclaimers."
    general_ai_tracker = None
    general_ai_config = None
    logger.warning("Using ultimate fallback prompt for general-assistant")


@tool
def general_assistant(query: str) -> str:
    """
    Handle general knowledge queries that fall outside specialized domains.
    Provides concise, accurate responses to non-specialized questions.
    
    Args:
        query: The user's general knowledge question
        
    Returns:
        A concise response to the general knowledge query
    """
    # Format the query for the agent
    formatted_query = f"Answer this general knowledge question concisely, remembering to start by acknowledging that you are not an expert in this specific area: {query}"
    
    try:
        logger.info("Processing query - routing to General Assistant")
        print("Routed to General Assistant")
        
        # Create a Bedrock model instance
        logger.info("Loading model config: {}".format(general_ai_config.model.name))
        bedrock_model = BedrockModel(
            model_id= general_ai_config.model.name,
            temperature= general_ai_config.model.get_custom("temperature"),
            top_p= general_ai_config.model.get_custom("topP"),
        )

        # Create the general agent with dynamic prompt and no specialized tools
        logger.debug("Creating general agent with dynamic prompt (no specialized tools)")
        general_agent = Agent(
            model=bedrock_model,
            system_prompt=GENERAL_ASSISTANT_SYSTEM_PROMPT,
            callback_handler=lambda **kwargs: event_loop_tracker(general_ai_tracker, logger, **kwargs),
            tools=[],  # No specialized tools needed for general knowledge
        )
        
        logger.debug("Executing query with general agent")
        agent_response = general_agent(formatted_query)
        text_response = str(agent_response)

        if len(text_response) > 0:
            logger.info("General query processed successfully")
            return text_response
        
        logger.warning("General agent returned empty response")
        return "Sorry, I couldn't provide an answer to your question."
        
    except Exception as e:
        # Return error message
        logger.error(f"Error in general_assistant tool: {str(e)}")
        return f"Error processing your question: {str(e)}"