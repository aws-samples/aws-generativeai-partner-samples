import streamlit as st
import boto3
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up AWS Lambda client
lambda_client = boto3.client(
    'lambda',
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)

# Set up page configuration
st.set_page_config(
    page_title="Q Index MongoDB Atlas Integration",
    page_icon="🔍",
    layout="wide"
)

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'show_raw_data' not in st.session_state:
    st.session_state.show_raw_data = False
if 'conversation_id' not in st.session_state:
    st.session_state.conversation_id = None
if 'parent_message_id' not in st.session_state:
    st.session_state.parent_message_id = None

# Function to invoke Lambda
def invoke_lambda(query):
    try:
        # Prepare payload with only query and conversation context
        payload = {
            "query": query
        }
        
        # Add conversation context if available
        if st.session_state.conversation_id:
            payload["conversation_id"] = st.session_state.conversation_id
        
        if st.session_state.parent_message_id:
            payload["parent_message_id"] = st.session_state.parent_message_id
        
        response = lambda_client.invoke(
            FunctionName=os.getenv('LAMBDA_FUNCTION_NAME', 'QIndexMongoDBIntegration'),
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        return json.loads(response['Payload'].read())
    except Exception as e:
        st.error(f"Error invoking Lambda: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

# Sidebar
with st.sidebar:
    st.title("Settings")
    
    # Display options
    st.header("Display Options")
    show_raw_data = st.checkbox("Show Raw Data", value=st.session_state.show_raw_data)
    if show_raw_data != st.session_state.show_raw_data:
        st.session_state.show_raw_data = show_raw_data
    
    # Conversation context
    st.header("Conversation Context")
    st.text(f"Conversation ID: {st.session_state.conversation_id or 'None'}")
    
    # Clear chat history
    if st.button("Clear Chat History"):
        st.session_state.chat_history = []
        st.session_state.conversation_id = None
        st.session_state.parent_message_id = None
        st.rerun()

# Main content
st.title("Q Index MongoDB Atlas Integration")

# Display chat history
for message in st.session_state.chat_history:
    if message["role"] == "user":
        st.chat_message("user").write(message["content"])
    else:
        with st.chat_message("assistant"):
            # Display LLM response first
            if "llm_response" in message["content"]:
                st.markdown(message["content"]["llm_response"])
            
            # Show raw data if enabled
            if st.session_state.show_raw_data:
                with st.expander("View Raw Data"):
                    if "q_index_result" in message["content"]:
                        st.subheader("Q Index Results")
                        st.json(message["content"]["q_index_result"])
                    
                    if "mongodb_result" in message["content"]:
                        st.subheader("MongoDB Results")
                        st.json(message["content"]["mongodb_result"])
                    
                    if "conversation_id" in message["content"]:
                        st.subheader("Conversation Context")
                        st.text(f"Conversation ID: {message['content']['conversation_id']}")

# Chat input
query = st.chat_input("Ask a question about countries or travel destinations")

if query:
    # Add user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": query})
    
    # Show a spinner while processing
    with st.spinner("Processing your query..."):
        # Process query through Lambda
        response = invoke_lambda(query)
        
        if response["statusCode"] == 200:
            result = json.loads(response["body"])["result"]
            
            # Update conversation context
            if "conversation_id" in result:
                st.session_state.conversation_id = result["conversation_id"]
            
            if "parent_message_id" in result:
                st.session_state.parent_message_id = result["parent_message_id"]
            
            # Add assistant message to chat history
            st.session_state.chat_history.append({"role": "assistant", "content": result})
        else:
            error = json.loads(response["body"]).get("error", "Unknown error")
            # Add error message to chat history
            st.session_state.chat_history.append({"role": "assistant", "content": f"Sorry, I couldn't process your query: {error}"})
    
    # Rerun to update the UI
    st.rerun()
