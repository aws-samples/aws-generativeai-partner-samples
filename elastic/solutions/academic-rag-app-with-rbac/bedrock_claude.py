import os
import json
import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def execute_llm(prompt):
    """
    Execute Claude model via Amazon Bedrock.
    
    Args:
        prompt: The prompt to send to Claude
        
    Returns:
        Claude's response as a string
    """
    try:
        # Get AWS region and model ID from environment variables
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        model_id = os.getenv("CLAUDE_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
        
        # Initialize Bedrock client
        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=aws_region
        )
        
        # Prepare request body for Claude
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        # Invoke Claude model
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response.get("body").read())
        return response_body["content"][0]["text"]
        
    except Exception as e:
        print(f"Error executing Claude model: {e}")
        return f"Error generating response: {str(e)}"