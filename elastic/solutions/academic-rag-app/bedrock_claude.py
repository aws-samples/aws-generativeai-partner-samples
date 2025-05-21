import boto3
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from botocore.exceptions import ClientError

"""
Script to call Claude 3.7 Sonnet on Amazon Bedrock with a predefined prompt.
"""

def connect_to_aws():
    try:
        # Load environment variables from .env file in the script directory
        script_dir = Path(__file__).parent.absolute()
        print(script_dir)
        dotenv_path = os.path.join(script_dir, '.env')
        with open(dotenv_path, 'r') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        # Connect to Amazon Bedrock
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        print(aws_access_key_id)
        print(aws_secret_access_key)
        bedrock_client = boto3.client(
            service_name='bedrock-runtime',
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
    except Exception as e:
        print(f"An error occurred connecting to bedrock: {str(e)}")
    return bedrock_client

def invoke_model(user_prompt, context=None):
    bedrock_client = connect_to_aws()

    # Claude model settings
    model_id = 'us.anthropic.claude-3-5-haiku-20241022-v1:0'
    system_prompt = "You are Claude, a helpful AI assistant."
    max_tokens = 1000
    completion = ""

    try:
        # Prepare the request body
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}]
        })

        # Call the model
        response = bedrock_client.invoke_model(
            body=body,
            modelId=model_id
        )

        # Parse the response
        response_body = json.loads(response.get('body').read())

        # Print the response
        # print("\n--- Claude's Response ---")
        # print(response_body["content"][0]["text"])
        completion = response_body["content"][0]["text"]

    except ClientError as err:
        print(f"Error: {err.response['Error']['Message']}")
        completion = "I encountered an error accessing Amazon Bedrock. Please check your AWS credentials and try again."
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        completion = "I encountered an error generating a response. Please try again later."

    return completion


#+------------------------------------------------------+
#|                   Main Execution                     |
#+------------------------------------------------------+
def execute_llm(user_prompt):
    #print(f'\nUser prompt: {user_prompt}')
    llm_answer = invoke_model(user_prompt)
    print(f'\nLLM Answer: {llm_answer}')
    return llm_answer

