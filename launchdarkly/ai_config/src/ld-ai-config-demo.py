import streamlit as st
import boto3
import ldclient
import os
import dotenv
import random
import json
import logging
from botocore.exceptions import ClientError
from ldclient import Context
from ldclient.config import Config
from ldai.client import LDAIClient, AIConfig, ModelConfig, LDMessage, ProviderConfig
from ldai.tracker import FeedbackKind

LAUNCHDARKLY_MAIN_LOGO = "images/launchdarkly_logo_white.png"
LAUNCHDARKLY_SMALL_LOGO = "images/launchdarkly_logo_white_small.png"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

dotenv.load_dotenv() # load environment vars

## Initialize session to store metrics
if 'LDtracker' not in st.session_state:
    logger.info("Initializing session state")
    st.session_state['LDtracker'] = {}

## Initialize LD client
ldclient.set_config(Config(os.getenv("LD_SERVER_KEY")))
aiclient = LDAIClient(ldclient.get())
ai_config_id = os.getenv("LD_AI_CONFIG_ID", default="test1")

## Initialize Bedrock Guardrail id
guardrail_id = os.getenv("BEDROCK_GUARDRAIL_ID")
guardrail_version = os.getenv("BEDROCK_GUARDRAIL_VERSION")

###############################################
##### LaunchDarkly User profile
###############################################
st.logo(LAUNCHDARKLY_MAIN_LOGO, icon_image=LAUNCHDARKLY_SMALL_LOGO)
with st.sidebar:
    st.title('LaunchDarkly AI Config Demo')
    st.subheader("Choose your user profile", divider="rainbow")

    userName = st.text_input("Your name", "John Doe")

    userRole = st.selectbox(
        "How would you like to be addressed?",
        ("King", "Queen", "Prince", "Princess", "Knight"),
        index=0,
        placeholder="Select role ...",
    )

    ageGroup = st.selectbox(
        "Enter your age group:",
        ("Kids", "Teens", "Adult"),
        index=2,
        placeholder="Select age group ...",
    )

    st.subheader("Choose your configuration", divider="rainbow")

    writingStyle = st.selectbox(
        "Which writting style do you preferred?",
        ("Shakespeare", "J. R.R. Tolkien", "J. K. Rowling"),
        index=0,
        placeholder="Select author ...",
    )

    language = st.selectbox(
        "Which language do you preferred?",
        ("English", "Spanish", "French"),
        index=0,
        placeholder="Select language ...",
    )

    st.subheader("Beta features", divider=True)

    userBetaModel = st.toggle("Activate beta model")

    st.divider()

    ## LaunchDarkly AI Config
    context = Context.builder("context-key-123abc") \
        .set("name", userName) \
        .set("role", userRole) \
        .set("style", writingStyle) \
        .set("age", ageGroup) \
        .set("beta_access", userBetaModel) \
        .build()

    variables = { 
        'var_writing_style': writingStyle,
        'var_language': language
    }

    fallback_value = AIConfig( # fallback config with default settings
        enabled=True,
        model=ModelConfig(
            name="anthropic.claude-v2:1",
            parameters={"temperature": 0.8},
        ),
        messages=[LDMessage(role="system", content="")],
        provider=ProviderConfig(name="bedrock"),
    )
    
    config, tracker = aiclient.config(ai_config_id, context, fallback_value, variables)
    logger.info("AI Config context updated")
    
    system_prompts = [json.loads(config.messages[0].content)] # Bedrock Converse API expect system prompts as list of dict
    inference_config = json.loads(config.messages[1].content) # Bedrock Converse API expect inference parameter as dict
    additional_model_fields = {"top_k": 200}
    
    if ageGroup in ["Kids", "Teens"]:
        guardrail_config = {
            "guardrailIdentifier": guardrail_id,
            "guardrailVersion": guardrail_version,
            "streamProcessingMode" : "async"
        }
    else:
        guardrail_config = None

    with st.expander("System prompt", expanded=False, icon=":material/input:"):
        st.text("This is the system prompt that is dynamically rendered based on user profile:")
        st.code(json.dumps(system_prompts, indent=2), language="json", wrap_lines=True)

    with st.expander("LaunchDarkly AI config data", expanded=False, icon=":material/settings:"):
        st.text("This is the context stored in AI Config for this particular user:")
        st.code(json.dumps(context.to_json_string(), indent=2), language="json", wrap_lines=True)
        st.text("This is the LLM configuration that is dynamically rendered based on user profile:")
        st.code(f"Model name: {config.model.name}")
        st.code(f"Model config: {config.model.to_dict()}")
        st.code(f"Provider: {config.provider}")
        st.code(f"Inference parameter: {inference_config}")
    
    with st.expander("Bedrock Guardrail status", expanded=False, icon=":material/privacy_tip:"):
        st.text("This is the guardrail that is dynamically activated based on user age group:")
        st.code(json.dumps(guardrail_config), language="json", wrap_lines=True)

    with st.expander("LaunchDarkly AI config tracker", expanded=False, icon=":material/monitoring:"):
        st.text("This is the tracker that is dynamically sent as telemetry to LaunchDarkly:")
        if 'LDtracker' in st.session_state:
            st.code(st.session_state['LDtracker'], language="json", wrap_lines=True)
            # st.code(old_tracker.get_summary().duration , language="json", wrap_lines=True)
            # st.code(old_tracker.get_summary().usage , language="json", wrap_lines=True)
        else:
            st.code("No tracker yet")

###############################################
##### LaunchDarkly Helper Function
###############################################

# Helper function to send feedback (thumbs up / down)
def ld_send_feedback(tracker):
    if st.session_state['LDfeedback'] is not None:
        if st.session_state['LDfeedback'] == True:
            tracker.track_feedback({"kind" : FeedbackKind.Positive})
        elif st.session_state['LDfeedback'] == False:
            tracker.track_feedback({"kind" : FeedbackKind.Negative})

# Helper function to send metrics
def ld_send_metric(tracker, metric_response):
    tracker.track_bedrock_converse_metrics(metric_response)
    tracker.track_success()
    ## write to session 
    st.session_state['LDtracker'] = metric_response
    logger.info("Tracker updated : {}".format(st.session_state['LDtracker']))


###############################################
##### Chat widget
###############################################

@st.cache_data
def get_welcome_message() -> str:
    return random.choice(
        [
            "Hello there! How can I assist you today?",
            "Hi there! Is there anything I can help you with?",
            "Do you need help?",
        ]
    )

@st.cache_resource
def get_bedrock_client():
    return boto3.client(service_name='bedrock-runtime', region_name=os.getenv("AWS_REGION"))

def get_history() -> str:
    history_list = [
        f"{record['role']}: {record['content']}" for record in st.session_state.messages
    ]
    return '\n\n'.join(history_list)

## https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-examples.html
def stream_conversation(bedrock_client,
                    model_id,
                    messages,
                    system_prompts,
                    inference_config,
                    additional_model_fields,
                    guardrail_config=None):
    """
    Sends messages to a model and streams the response.
    Args:
        bedrock_client: The Boto3 Bedrock runtime client.
        model_id (str): The model ID to use.
        messages (JSON) : The messages to send.
        system_prompts (JSON) : The system prompts to send.
        inference_config (JSON) : The inference configuration to use.
        additional_model_fields (JSON) : Additional model fields to use.
        guardrail_config (JSON) : Additional guardrail config
    Returns:
        Nothing.

    """

    logger.info("Streaming messages with model %s", model_id)

    params = {
        'modelId': model_id,
        'messages': messages,
        'system': system_prompts,
        'inferenceConfig': inference_config,
        'additionalModelRequestFields': additional_model_fields,
    }
    
    if guardrail_config:  # This will check if the dict is not empty
        params['guardrailConfig'] = guardrail_config
    
    response = bedrock_client.converse_stream(**params)
        
    return response.get('stream')

# Parse incoming stream block one by one, print it to the screen and collect other metadata / metrics
def parse_stream(stream, tracker):
    full_response = ""
    metric_response = {}
    metric_response["$metadata"] = {
        "httpStatusCode" : 200
    }
    
    for event in stream:
        if 'messageStart' in event:
            logger.info(f"Role: {event['messageStart']['role']}")

        if 'contentBlockDelta' in event:            
            message = event['contentBlockDelta']['delta']['text']
            # print(message, end="")
            full_response += message
            yield message # return output so chat can render it immediately

        if 'messageStop' in event:
            logger.info(f"Stop reason: {event['messageStop']['stopReason']}")

        if 'metadata' in event:
            metadata = event['metadata']
            if 'usage' in metadata:
                logger.info("Token usage")
                logger.info(f"Input tokens: {metadata['usage']['inputTokens']}")
                logger.info(f":Output tokens: {metadata['usage']['outputTokens']}")
                logger.info(f":Total tokens: {metadata['usage']['totalTokens']}")
                metric_response["usage"] = metadata['usage']
            if 'metrics' in event['metadata']:
                logger.info(f"Latency: {metadata['metrics']['latencyMs']} milliseconds")
                metric_response["metrics"] = {}
                metric_response["metrics"]["latencyMs"] = metadata['metrics']['latencyMs']
    
    # Add assistant response to chat history
    logger.info(f"Full response: {full_response}")
    st.session_state.messages.append(
        {"role": "Assistant", "content": full_response}
    )

    # Send metrics to tracker
    ld_send_metric(tracker, metric_response)

# Initialize bedrock client and pick model from AIConfig
bedrock_client = get_bedrock_client()
model_id = config.model.name

# Initialize welcome message
st.subheader("Hello {}, use the chat below to talk with your personal linguist expert".format(userName))
welcome_message = get_welcome_message()
with st.chat_message('assistant'):
    st.markdown(welcome_message)
    
# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("What's up?"):        
    # Display user message in chat message container
    with st.chat_message("Human"):
        st.markdown(prompt)

    # Add user message to chat history
    st.session_state.messages.append({"role": "Human", "content": prompt})

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        
        messages = [] # Bedrock Converse API expect message in list format
        message = {
            "role": "user",
            "content": [
                {"text": prompt}
            ]
        }
        messages.append(message)

        try:
            stream = stream_conversation(bedrock_client, model_id, messages, system_prompts, inference_config, additional_model_fields, guardrail_config)
            if stream:
                st.write_stream(parse_stream(stream, tracker))
        except ClientError as err:
            message = err.response['Error']['Message']
            logger.error("A client error occurred: %s", message)
            print("A client error occured: " + format(message))
        else:
            print(f"\nFinished streaming messages with model {model_id}.")

    logger.info(tracker.get_summary().usage)
    logger.info(tracker.get_summary().duration)

    # reset the thumb up/down feedback
    st.session_state['LDfeedback'] = None

    # render update
    st.rerun() 

# show the feedback button at the end of prompt response
if 'LDtracker' in st.session_state and st.session_state['LDtracker'] != {}:
    sentiment_mapping = [":material/thumb_down:", ":material/thumb_up:"]
    st.text("Rate the response :")

    # use the feedback widget and call back to send feedback to LD tracker object
    selected = st.feedback(options="thumbs", key="LDfeedback", on_change=ld_send_feedback(tracker))
    if selected is not None:
        st.markdown(f"You selected: {sentiment_mapping[selected]}")
