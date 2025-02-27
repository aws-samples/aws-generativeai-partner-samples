"""
UI module for the application.
Handles Streamlit UI elements and session state management.
"""
import streamlit as st
import uuid
import json
import re
import logging

# Get logger
logger = logging.getLogger(__name__)

def init_session_state():
    """Initialize the session state with default values."""
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.citations = []
    st.session_state.trace = {}

def setup_page(title, icon=None):
    """Set up the Streamlit page with title and icon."""
    st.set_page_config(page_title=title, page_icon=icon, layout="wide")
    st.title(title)
    if len(st.session_state.items()) == 0:
        init_session_state()

def display_sidebar_reset_button():
    """Display a reset button in the sidebar."""
    with st.sidebar:
        if st.button("Reset Session"):
            init_session_state()

def display_message_history():
    """Display the message history from session state."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)

def process_agent_response(response):
    """Process the agent response and format it for display."""
    output_text = response["output_text"]
    
    # Store citations in session state if available
    if "citations" in response:
        st.session_state.citations = response["citations"]
    else:
        st.session_state.citations = []

    # Store trace information in session state
    if "trace" in response:
        st.session_state.trace = response["trace"]

    # Check if the output is a JSON object with the instruction and result fields
    try:
        # When parsing the JSON, strict mode must be disabled to handle badly escaped newlines
        output_json = json.loads(output_text, strict=False)
        if "instruction" in output_json and "result" in output_json:
            output_text = output_json["result"]
    except json.JSONDecodeError as e:
        pass

    return output_text

def display_trace_information():
    """Display trace information in the sidebar."""
    trace_types_map = {
        "Pre-Processing": ["preGuardrailTrace", "preProcessingTrace"],
        "Orchestration": ["orchestrationTrace"],
        "Post-Processing": ["postProcessingTrace", "postGuardrailTrace"]
    }

    trace_info_types_map = {
        "preProcessingTrace": ["modelInvocationInput", "modelInvocationOutput"],
        "orchestrationTrace": ["invocationInput", "modelInvocationInput", "modelInvocationOutput", "observation", "rationale"],
        "postProcessingTrace": ["modelInvocationInput", "modelInvocationOutput", "observation"]
    }

    with st.sidebar:
        # Display citations if available
        if hasattr(st.session_state, 'citations') and st.session_state.citations:
            st.title("Citations")
            for i, citation in enumerate(st.session_state.citations):
                with st.expander(f"Citation {i+1}", expanded=False):
                    if "retrievedReferences" in citation:
                        for ref in citation["retrievedReferences"]:
                            if "location" in ref:
                                st.write(f"**Source:** {ref['location']['s3Location']['uri'] if 'uri' in ref['location']['s3Location'] else 'N/A'}")
                            if "content" in ref:
                                st.write(f"**Content:** {ref['content']['text'] if 'text' in ref['content'] else 'N/A'}")
                    else:
                        st.json(citation)
        
        # Display trace information
        st.title("Trace")

        # Show each trace type in separate sections
        step_num = 1
        for trace_type_header in trace_types_map:
            st.subheader(trace_type_header)
            
            has_trace = False
            for trace_type in trace_types_map[trace_type_header]:
                if trace_type in st.session_state.trace:
                    has_trace = True
                    trace_steps = process_trace_type(trace_type, st.session_state.trace[trace_type], trace_info_types_map)
                    step_num = display_trace_steps(trace_steps, step_num)
            
            if not has_trace:
                st.text("None")


def process_trace_type(trace_type, traces, trace_info_types_map):
    """Process traces of a specific type and organize them by trace ID."""
    trace_steps = {}
    
    for trace in traces:
        trace_id = extract_trace_id(trace_type, trace, trace_info_types_map)
        if trace_id:
            if trace_id not in trace_steps:
                trace_steps[trace_id] = [trace]
            else:
                trace_steps[trace_id].append(trace)
    
    return trace_steps

def extract_trace_id(trace_type, trace, trace_info_types_map):
    """Extract trace ID from a trace based on its type."""
    if trace_type in trace_info_types_map:
        trace_info_types = trace_info_types_map[trace_type]
        for trace_info_type in trace_info_types:
            if trace_info_type in trace:
                return trace[trace_info_type]["traceId"]
    elif "traceId" in trace:
        return trace["traceId"]
    return None

def display_trace_steps(trace_steps, step_num):
    """Display trace steps in the Streamlit UI."""
    for trace_id in trace_steps.keys():
        with st.expander(f"Trace Step {str(step_num)}", expanded=False):
            for trace in trace_steps[trace_id]:
                trace_str = json.dumps(trace, indent=2)
                st.code(trace_str, language="json", line_numbers=True, wrap_lines=True)
        step_num += 1
    
    return step_num