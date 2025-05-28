"""
Bedrock client module for the application.
Provides an interface to interact with AWS Bedrock Agent Runtime.
"""
import boto3
from botocore.exceptions import ClientError
import logging

# Get logger
logger = logging.getLogger(__name__)

class BedrockClient:
    """Client for interacting with AWS Bedrock Agent Runtime."""
    
    def __init__(self):
        """Initialize the Bedrock client."""
        self.client = boto3.session.Session().client(service_name="bedrock-agent-runtime")
    
    def invoke_agent(self, agent_id, agent_alias_id, session_id, prompt):
        """
        Invoke a Bedrock agent with the given parameters.
        
        Args:
            agent_id (str): The ID of the agent to invoke
            agent_alias_id (str): The alias ID of the agent to invoke
            session_id (str): The session ID for this conversation
            prompt (str): The user input to send to the agent
            
        Returns:
            dict: The processed response containing output_text, citations, and trace information
        """
        try:
            # See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agent-runtime/client/invoke_agent.html
            response = self.client.invoke_agent(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                enableTrace=True,
                sessionId=session_id,
                inputText=prompt
            )

            output_text = ""
            citations = []
            trace = {}
            
            # Process streaming response and extract trace information
            has_guardrail_trace = False
            for event in response.get("completion"):
                # Combine the chunks to get the output text
                if "chunk" in event:
                    chunk = event["chunk"]
                    output_text += chunk["bytes"].decode()
                    if "attribution" in chunk:
                        citations += chunk["attribution"]["citations"]

                # Extract trace information from all events
                if "trace" in event:
                    for trace_type in ["guardrailTrace", "preProcessingTrace", "orchestrationTrace", "postProcessingTrace"]:
                        if trace_type in event["trace"]["trace"]:
                            mapped_trace_type = trace_type
                            if trace_type == "guardrailTrace":
                                if not has_guardrail_trace:
                                    has_guardrail_trace = True
                                    mapped_trace_type = "preGuardrailTrace"
                                else:
                                    mapped_trace_type = "postGuardrailTrace"
                            if mapped_trace_type not in trace:
                                trace[mapped_trace_type] = []
                            trace[mapped_trace_type].append(event["trace"]["trace"][trace_type])
            
            return {
                "output_text": output_text,
                "citations": citations,
                "trace": trace
            }
                
        except ClientError as e:
            error_message = f"Error invoking Bedrock agent: {e}"
            logger.error(error_message)
            return {
                "output_text": f"Error: {error_message}",
                "citations": [],
                "trace": {}
            }