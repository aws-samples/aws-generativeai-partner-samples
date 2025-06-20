import streamlit as st
import asyncio
import os
import time
from dotenv import load_dotenv
from strands import Agent, tool
from strands.tools.mcp import MCPClient
from strands.models import BedrockModel
from mcp import stdio_client, StdioServerParameters
from botocore.exceptions import ClientError

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Fraud Analytics Dashboard",
    page_icon="🔍",
    layout="wide"
)

# Constants
SYSTEM_PROMPT = """
# Fraud Analytics System Prompt
You are an analyst detecting fraud transactions based on data in tables in Snowflake database.
Thumb rule, for identifying fraud transactions is when transaction type is transfer. 
However, when asked for comprehensive analysis, you are an intelligent analyst and can analyze and report on fraud transactions based on your own knowledge and judgement.
Format your responses as clean, professional reports with clear sections and data-driven insights.
"""

## Available Snowflake Database

### 1. workshop_db

## Available Snowflake tables in workshop_db database

### 1. transaction
### 2. creditcards
### 3. cardholders
### 4. merchant


# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 2  # seconds

# Function to clean messages for Bedrock API
def clean_messages_for_bedrock(messages):
    cleaned_messages = []
    for msg in messages:
        # Skip messages with empty content
        if not msg.get("content"):
            continue
        
        # Ensure content is a string
        if isinstance(msg["content"], dict) or isinstance(msg["content"], list):
            msg["content"] = str(msg["content"])
        
        # Add to cleaned messages
        cleaned_messages.append(msg)
    
    return cleaned_messages

# Function to call agent with retry logic
def call_agent_with_retry(agent, prompt, messages=None, max_retries=MAX_RETRIES, initial_delay=INITIAL_RETRY_DELAY):
    retry_delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            if messages:
                return agent(prompt, messages=messages)
            else:
                return agent(prompt)
        except Exception as e:
            last_exception = e
            error_str = str(e).lower()
            
            # Check if it's a retryable error
            if ("modelstreamerrorexception" in error_str or 
                "throttling" in error_str or 
                "timeout" in error_str or 
                "unexpected error" in error_str):
                
                if attempt < max_retries - 1:
                    # Show a warning but don't fail yet
                    st.warning(f"Temporary service issue, retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
            
            # Either it's not a retryable error or we've exhausted retries
            raise last_exception
    
    # If we get here, all retries failed
    raise last_exception

# Initialize session state variables
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'agent' not in st.session_state:
    st.session_state.agent = None
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
if 'snowflake_mcp' not in st.session_state:
    st.session_state.snowflake_mcp = None

# Title and description
st.title("Fraud Analytics Dashboard")
st.markdown("""
This application helps you analyze fraudulent transactions using data from Snowflake.
Ask questions about transaction patterns, suspicious activities, or request specific fraud reports.
""")

# Sidebar
with st.sidebar:
    st.header("Settings")
    email_recipient = st.text_input("Email recipient for reports", value="")
    
    # Add a button to clear conversation history
    if st.button("Clear Conversation History"):
        st.session_state.messages = []
        st.success("Conversation history cleared!")
    
    # Add a button to initialize the agent
    if st.button("Initialize Agent"):
        with st.spinner("Initializing agent and connecting to Snowflake..."):
            try:
                # Get environment variables
                snowflake_mcp_server_script_path = os.getenv("SNOWFLAKE_MCP_SERVER_SCRIPT_PATH")
                
                if not snowflake_mcp_server_script_path:
                    st.error("SNOWFLAKE_MCP_SERVER_SCRIPT_PATH environment variable not set")
                else:
                    # Set up MCP client for Snowflake
                    snowflake_mcp = MCPClient(
                        lambda: stdio_client(
                            StdioServerParameters(
                                command="python",
                                args=[snowflake_mcp_server_script_path]
                            )
                        )
                    )
                    
                    # Define the send_email tool
                    @tool
                    def send_email(to_address: str, subject: str, body: str) -> str:
                        """Send a plain text email using Amazon SES via boto3."""
                        try:
                            import boto3
                            from botocore.exceptions import ClientError
                            
                            # Create a new SES client
                            ses_client = boto3.client(
                                'ses',
                                region_name=os.getenv('AWS_REGION', 'us-east-1'),
                                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
                            )
                            
                            # Format the text body for better readability
                            formatted_body = body.strip()
                            formatted_body = formatted_body.replace('\n\n\n', '\n\n')
                            formatted_body = formatted_body.replace('\n', '\n\n')
                            
                            # Prepare the email message
                            message = {
                                'Subject': {'Data': subject},
                                'Body': {'Text': {'Data': formatted_body}}
                            }
                            
                            # Send the email
                            response = ses_client.send_email(
                                Source=os.getenv('SENDER_EMAIL_ADDRESS'),
                                Destination={'ToAddresses': [to_address]},
                                Message=message,
                                ReplyToAddresses=[os.getenv('REPLY_TO_EMAIL_ADDRESSES', 
                                                          os.getenv('SENDER_EMAIL_ADDRESS'))]
                            )
                            
                            return f"✅ Email sent successfully to {to_address}! Message ID: {response['MessageId']}"
                                
                        except Exception as e:
                            return f"❌ Error sending email: {str(e)}"
                    
                    # Initialize the MCP client
                    snowflake_mcp.__enter__()
                    
                    # Get all tools
                    snowflake_tools = snowflake_mcp.list_tools_sync()
                    all_tools = snowflake_tools + [send_email]
                    
                    # Create the agent
                    MODEL_ID = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
                    model = BedrockModel(model_id=MODEL_ID, max_tokens=8000)
                    
                    # Store the agent in session state
                    st.session_state.agent = Agent(
                        system_prompt=SYSTEM_PROMPT,
                        tools=all_tools,
                        model=model
                    )
                    
                    # Store MCP client for cleanup
                    st.session_state.snowflake_mcp = snowflake_mcp
                    
                    st.session_state.initialized = True
                    st.success("Agent initialized successfully!")
            
            except Exception as e:
                st.error(f"Error initializing agent: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

# Chat interface
st.header("Fraud Analytics Chat")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input
if prompt := st.chat_input("Ask about fraud transactions..."):
    if not st.session_state.initialized:
        st.error("Please initialize the agent first by clicking the 'Initialize Agent' button in the sidebar.")
    else:
        # Only add non-empty messages
        if prompt.strip():
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Display user message
            with st.chat_message("user"):
                st.write(prompt)
            
            # Generate and display assistant response
            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    try:
                        # Clean the message history before sending to the agent
                        cleaned_messages = clean_messages_for_bedrock(st.session_state.messages[-10:])  # Only use last 10 messages to avoid context limits
                        
                        # Use the cleaned messages with the agent (with retry logic)
                        response = call_agent_with_retry(
                            st.session_state.agent, 
                            prompt, 
                            messages=cleaned_messages
                        )
                        
                        # Access the message content directly from the AgentResult object
                        if hasattr(response, 'message'):
                            response_content = response.message
                        else:
                            # Fallback to string representation if message attribute is not available
                            response_content = str(response)
                        
                        # Ensure response_content is a string
                        if not isinstance(response_content, str):
                            # If it's a dictionary with a specific structure
                            if isinstance(response_content, dict) and 'content' in response_content and isinstance(response_content['content'], list) and len(response_content['content']) > 0:
                                # Extract text from the first content item if it exists and has a 'text' field
                                if 'text' in response_content['content'][0]:
                                    response_content = response_content['content'][0]['text']
                                else:
                                    response_content = str(response_content)
                            else:
                                response_content = str(response_content)
                        
                        # Display the full response content
                        st.markdown(response_content)
                        
                        # Only add non-empty responses to the message history
                        if response_content.strip():
                            st.session_state.messages.append({"role": "assistant", "content": response_content})
                    except Exception as e:
                        error_msg = f"Error generating response: {str(e)}"
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})

# Cleanup on session end
def cleanup():
    if st.session_state.snowflake_mcp:
        try:
            st.session_state.snowflake_mcp.__exit__(None, None, None)
        except:
            pass

# Register the cleanup function
import atexit
atexit.register(cleanup)
