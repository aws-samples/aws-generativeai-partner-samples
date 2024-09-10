import boto3
from botocore.exceptions import ClientError

class BedrockSaaSClient:
    def __init__(self, customer_role_arn=None, external_id=None):
        self.customer_role_arn = customer_role_arn
        self.external_id = external_id
        self.sts_client = boto3.client('sts')

    def get_session_token(self, access_key, secret_key):
        sts_client = boto3.client(
            'sts',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )

        response = sts_client.get_session_token()

        return response['Credentials']
    
    def assume_role(self):
        response = self.sts_client.assume_role(
                RoleArn=self.customer_role_arn,
                RoleSessionName='BedrockSaaSSession',
                ExternalId = self.external_id
            )
        return response['Credentials']
    
    def invoke_bedrock_model(self, model_id, prompt, stream, credentials, message_list=None):
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken']
        )
    
        try:
            if not message_list:
                message_list = []
                initial_message = {
                    "role": "user",
                    "content": [
                        {"text": prompt}
                    ],
                }
                message_list.append(initial_message)
            if not stream:
                response = bedrock_runtime.converse(
                    modelId=model_id,
                    messages=message_list,
                    inferenceConfig={
                        "maxTokens": 2000,
                        "temperature": 0
                    },
                )
                return response, message_list
            else:
                response = bedrock_runtime.converse_stream(
                    modelId=model_id,
                    messages=message_list,
                    inferenceConfig={
                        "maxTokens": 2000,
                        "temperature": 0
                    },
                )
                return response, message_list
        except ClientError as e:
            return f"Error invoking Bedrock model: {e}"
