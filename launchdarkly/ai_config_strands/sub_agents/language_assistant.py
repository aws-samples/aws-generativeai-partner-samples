import os
import sys
from pathlib import Path
from strands import Agent, tool
from strands_tools import http_request
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
logger = get_agent_logger("language_assistant")

# Load dynamic prompt from AI Config
try:
    # Get agent role from environment
    agent_role = os.getenv("LANGUAGE_ASSISTANT_ROLE", "language-assistant")
    
    logger.info(f"Initializing language-assistant agent with role: {agent_role}")
    
    # Load AI Config prompt with fallback
    LANGUAGE_ASSISTANT_SYSTEM_PROMPT, language_ai_tracker, language_ai_config = load_ai_config_prompt(
        agent_role=agent_role,
        fallback_file_path="fallback_prompts/language_assistant_fallback_prompt.txt",
        ultimate_fallback="You are LanguageAssistant, a specialized language translation and learning assistant. Help users with accurate translations and language learning guidance with cultural context."
    )
    
    logger.info("Language-assistant dynamic prompt loaded successfully")
    
except Exception as e:
    logger.error(f"Critical error loading AI Config for language-assistant: {str(e)}")
    # Use ultimate fallback if AI Config fails completely
    LANGUAGE_ASSISTANT_SYSTEM_PROMPT = "You are LanguageAssistant, a specialized language translation and learning assistant. Help users with accurate translations and language learning guidance with cultural context."
    language_ai_tracker = None
    language_ai_config = None
    logger.warning("Using ultimate fallback prompt for language-assistant")


@tool
def language_assistant(query: str) -> str:
    """
    Process and respond to language translation and foreign language learning queries.
    
    Args:
        query: A request for translation or language learning assistance
        
    Returns:
        A translated text or language learning guidance with explanations
    """
    # Format the query with specific guidance for the language assistant
    formatted_query = f"Please address this translation or language learning request, providing cultural context and explanations where helpful: {query}"
    
    try:
        logger.info("Processing query - routing to Language Assistant")
        print("Routed to Language Assistant")
        
        # Create a Bedrock model instance
        logger.info("Loading model config: {}".format(language_ai_config.model.name))
        bedrock_model = BedrockModel(
            model_id= language_ai_config.model.name,
            temperature= language_ai_config.model.get_custom("temperature"),
            top_p= language_ai_config.model.get_custom("topP"),
        )

        # Create the language agent with dynamic prompt and http_request capability
        logger.debug("Creating language agent with dynamic prompt and http_request tool")
        language_agent = Agent(
            model=bedrock_model,
            system_prompt=LANGUAGE_ASSISTANT_SYSTEM_PROMPT,
            callback_handler=lambda **kwargs: event_loop_tracker(language_ai_tracker, logger, **kwargs),
            tools=[http_request],
        )
        
        logger.debug("Executing query with language agent")
        agent_response = language_agent(formatted_query)
        text_response = str(agent_response)

        if len(text_response) > 0:
            logger.info("Language query processed successfully")
            return text_response

        logger.warning("Language agent returned empty response")
        return "I apologize, but I couldn't process your language request. Please ensure you've specified the languages involved and the specific translation or learning need."
        
    except Exception as e:
        # Return specific error message for language processing
        logger.error(f"Error in language_assistant tool: {str(e)}")
        return f"Error processing your language query: {str(e)}"