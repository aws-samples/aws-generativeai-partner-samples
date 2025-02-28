"""
Main application module.
Streamlit web application for interacting with AWS Bedrock agents.
"""
import streamlit as st
import logging

# Import modules
from modules.config import load_environment, setup_logging, get_config_values, print_debug_info
from modules.ui import (
    init_session_state, setup_page, display_sidebar_reset_button, 
    display_message_history, process_agent_response, 
    display_trace_information
)
from modules.bedrock_client import BedrockClient

# Load environment variables and configure logging
load_environment()
setup_logging()
print_debug_info()

# Get logger
logger = logging.getLogger(__name__)

# Get configuration
config = get_config_values()

# Initialize Bedrock client
bedrock_client = BedrockClient()

# Set up the page
setup_page(config["ui_title"], config["ui_icon"])

# Display reset button in sidebar
display_sidebar_reset_button()

# Display message history
display_message_history()

# Chat input that invokes the agent
if prompt := st.chat_input():
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Get assistant response
    with st.chat_message("assistant"):
        with st.empty():
            with st.spinner():
                response = bedrock_client.invoke_agent(
                    config["agent_id"],
                    config["agent_alias_id"],
                    st.session_state.session_id,
                    prompt
                )
            
            # Process and display response
            output_text = process_agent_response(response)
            st.session_state.messages.append({"role": "assistant", "content": output_text})
            st.session_state.citations = response["citations"]
            st.session_state.trace = response["trace"]
            st.markdown(output_text, unsafe_allow_html=True)

# Display trace information and citations in sidebar
display_trace_information()
