import boto3
from botocore.exceptions import ClientError
import json
import os
from paig_client import client as paig_shield_client
from paig_client.model import ConversationType
import requests
import shutil
import uuid

# Update the AWS Region and Bedrock model ID.
aws_region_name = "us-east-1"
aws_bedrock_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

# This is just to automate the testing of the PAIG integration. In a real-world scenario,
# this should be done in a secure way.
paig_url = "http://127.0.0.1:4545"
login_url = f"{paig_url}/account-service/api/login"
config_url = f"{paig_url}/governance-service/api/ai/application/1/config/json/download"
username = "admin"
password = "welcome1"

# We will use this user for testing purposes. In a real-world scenario, the user should be authenticated.
user = "test_user"

# Create a Bedrock Runtime client in the AWS Region you want to use.
client = boto3.client("bedrock-runtime", region_name=aws_region_name)

# Set the model ID, e.g., Titan Text Premier.
model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

def init_paig():
    # Initialize the PAIG client. This is default installation without LangChain or VectorDBs
    paig_shield_client.setup(frameworks=[])


# This is only for testing purposes. In a real-world scenario, the application config should be downloaded securely.
def download_and_upload_demo_app_config():
    session = requests.Session()
    login_payload = {
        "username": username,
        "password": password
    }
    login_response = session.post(login_url, data=json.dumps(login_payload))

    if login_response.status_code == 200:
        response = session.get(config_url)
        if response.status_code == 200:
            with open("privacera-shield-PAIG-Demo-config.json", "w") as file:
                file.write(response.text)
            destination_folder = "privacera"
            if not os.path.exists(destination_folder):
                os.makedirs(destination_folder)

            shutil.move("privacera-shield-PAIG-Demo-config.json", os.path.join(destination_folder, "privacera-shield-PAIG-Demo-config.json"))
            print("Application config file downloaded and moved to privacera folder successfully.")
        else:
            raise Exception(f"ERROR: Failed to download Application config file. Status code: {response.status_code}")
    else:
        raise  Exception("ERRRO: User authentication failed please check username and password")

# Utility function to invoke the model. This includes integration with PAIG
def invoke_llm(prompt):

    try:
        # Generate a random UUID which will be used to bind a prompt with a reply (not applicable in this example)
        privacera_thread_id = str(uuid.uuid4())
        with paig_shield_client.create_shield_context(username=user):
            # Validate prompt with Privacera Shield
            updated_prompt_data = paig_shield_client.check_access(
                text=prompt,
                conversation_type=ConversationType.PROMPT,
                thread_id=privacera_thread_id
            )
            updated_prompt_text = updated_prompt_data[0].response_text
            # Start a conversation with the user message.
            conversation = [
                {
                    "role": "user",
                    "content": [{"text": updated_prompt_text}],
                }
            ]

            # Send the message to the model, using a basic inference configuration.
            response = client.converse(
                modelId=aws_bedrock_model_id,
                messages=conversation,
                inferenceConfig={"maxTokens": 2000, "temperature": 0},
                additionalModelRequestFields={"top_k": 250}
            )


            llm_response_text = response["output"]["message"]["content"][0]["text"]

            updated_reply_data = paig_shield_client.check_access(
                text=llm_response_text,
                conversation_type=ConversationType.REPLY,
                thread_id=privacera_thread_id
            )
            updated_reply_text = updated_reply_data[0].response_text

            return updated_reply_text

    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        raise e


# Download the application config file and initialize the PAIG client
download_and_upload_demo_app_config()

# Initialize the PAIG client
init_paig()


user_prompts = ["Who was the first President of USA", "Where did the first President of USA was born",
                "What is 800-555-1212 phone number used for?", "That guy crossing the road is a moron"]

for user_message in user_prompts:
    print(f"User: {user_message}")
    PROMPT = f"""Use the following pieces of context to answer the question at the end. Keep it very short and simple.
            {user_message}
            ANSWER:
            """

    response = invoke_llm(PROMPT)
    print(f"PAIG: {response}")
    print("--------------------\n")

print(f"You can go to PAIG UI {paig_url}#/audits_security to see the logs and the results. The admin credentials are "
      f"{username}/{password}")