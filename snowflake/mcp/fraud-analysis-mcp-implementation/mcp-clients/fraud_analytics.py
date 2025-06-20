import asyncio
import sys
import os
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional

# Import Strands SDK components
from strands import Agent, tool
from strands.tools.mcp import MCPClient
from strands.models import BedrockModel

from mcp import stdio_client, StdioServerParameters

# Constants
SYSTEM_PROMPT = """
# Fraud Analytics System Prompt
you are an analyst detecting fraud transactions based on data in tables in Snowflake database. Can you list fradulent transactions?
"""

## Available Snowflake Database
### 1. workshop_db

## Available tables in workshop_db
### 1. transaction
### 2. creditcards
### 3. cardholders
### 4. merchant

@tool
def send_email(to_address: str, subject: str, body: str) -> str:
    """Send a plain text email using Amazon SES via boto3.
    
    Args:
        to_address: Email address of the recipient
        subject: Subject line of the email
        body: Plain text content of the email
    
    Returns:
        Confirmation message with the email status
    """
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
        
        # Ensure sections are properly separated with blank lines
        formatted_body = formatted_body.replace('\n\n\n', '\n\n')  # Remove excessive blank lines
        formatted_body = formatted_body.replace('\n', '\n\n')  # Add proper spacing between lines
        
        # Prepare the email message (plain text only)
        message = {
            'Subject': {
                'Data': subject
            },
            'Body': {
                'Text': {
                    'Data': formatted_body
                }
            }
        }
        
        # Send the email
        response = ses_client.send_email(
            Source=os.getenv('SENDER_EMAIL_ADDRESS'),
            Destination={
                'ToAddresses': [to_address]
            },
            Message=message,
            ReplyToAddresses=[os.getenv('REPLY_TO_EMAIL_ADDRESSES', os.getenv('SENDER_EMAIL_ADDRESS'))]
        )
        
        return f"✅ Email sent successfully to {to_address}! Message ID: {response['MessageId']}"
            
    except ClientError as e:
        error_message = e.response['Error']['Message']
        return f"❌ Failed to send email: {error_message}"
    except Exception as e:
        return f"❌ Error sending email: {str(e)}"

async def main():
    load_dotenv()
        
    # Get environment variables
    # aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    # aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    # aws_region = os.getenv("AWS_REGION", "us-east-1")
    sender_email = os.getenv("SENDER_EMAIL_ADDRESS", "nidhigva+snow@amazon.com")
    reply_to_email = os.getenv("REPLY_TO_EMAIL_ADDRESSES", "nidhigva@amazon.com")
    # aws_ses_mcp_server_path = os.getenv("AWS_SES_MCP_SERVER_PATH")
    # weather_mcp_server_script_path = os.getenv("WEATHER_MCP_SERVER_SCRIPT_PATH")
    snowflake_mcp_server_script_path = os.getenv("SNOWFLAKE_MCP_SERVER_SCRIPT_PATH")
    
    # Set up MCP clients
    snowflake_mcp = MCPClient(
        lambda: stdio_client(
            StdioServerParameters(
                command="python",
                args=[snowflake_mcp_server_script_path]
            )
        )
    )
    
    # Define custom reservation tools
    custom_tool = [
        send_email
    ]
    MODEL_ID = "us.anthropic.claude-3-5-sonnet-20241022-v2:0" # Using Claude 3.5 Sonnet
    
    model = BedrockModel (
        model_id=MODEL_ID,
        max_tokens=8000
    )

    # Initialize the MCP clients
    try:
        with snowflake_mcp:
            #Get all the tools together here
            snowflake_tools = snowflake_mcp.list_tools_sync()
            all_tools = snowflake_tools + custom_tool

            # Create the agent
            agent = Agent(
                system_prompt=SYSTEM_PROMPT,
                tools=all_tools,
                model=model
            )
        
            # Define exit command checker
            def is_exit_command(user_input: str) -> bool:
                # Clean up input
                cleaned_input = user_input.lower().strip()
                
                # Direct commands
                exit_commands = {'quit', 'exit'}
                
                # Semantic variations
                semantic_phrases = {
                    'i am done', 
                    'i am finished',
                    "i'm done",
                    "i'm finished"
                }
                
                return cleaned_input in exit_commands or cleaned_input in semantic_phrases
            
            print("\nWelcome to the Fraud Analytics Assistant!")
            print("To exit, type 'quit', 'exit', 'I am done', or 'I am finished'")
            
            # Chat loop
            while True:
                try:
                    query = input("\nYou: ").strip()
                    if is_exit_command(query):
                        print("\nThank you for using the Fraud Analytics Assistant. Goodbye!")
                        break
                    
                    print("\nAssistant:", end=" ")
                    response = agent(query)
                    print(response)
                    quit
                        
                except Exception as e:
                    print(f"\nError: {str(e)}")
                    import traceback
                    traceback.print_exc()
    finally:
        # Clean up MCP clients
        print(" Thank You For Using Agentic AI capabilities from Amazon and Snowflake")


if __name__ == "__main__":
    asyncio.run(main())