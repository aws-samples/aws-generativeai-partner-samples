import os
import boto3
from botocore.exceptions import ClientError
from typing import Dict, List, Tuple, Optional, Union

class BedrockSaaSClient:
    """
    A client for interacting with Amazon Bedrock in a SaaS context.

    This class provides methods for authentication and invoking Bedrock models
    using temporary credentials or assumed roles.

    Attributes:
        customer_role_arn (str): The ARN of the customer's IAM role to assume.
        external_id (str): The external ID for additional security when assuming a role.
        sts_client (boto3.client): The AWS Security Token Service (STS) client.
    """

    def __init__(self, customer_role_arn: Optional[str] = None, external_id: Optional[str] = None):
        """
        Initialize the BedrockSaaSClient.

        Args:
            customer_role_arn (str, optional): The ARN of the customer's IAM role to assume.
            external_id (str, optional): The external ID for additional security when assuming a role.
        """
        self.customer_role_arn = customer_role_arn
        self.external_id = external_id
        self.sts_client = boto3.client('sts')

    def get_session_token(self) -> Dict[str, str]:
        """
        Get temporary session credentials using AWS access key and secret key from environment variables.

        Returns:
            dict: A dictionary containing temporary credentials (AccessKeyId, SecretAccessKey, SessionToken).

        Raises:
            ValueError: If AWS credentials are not set in environment variables.
        """
        access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')

        if not access_key or not secret_key:
            raise ValueError("AWS credentials not found in environment variables.")

        sts_client = boto3.client(
            'sts',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )

        response = sts_client.get_session_token()

        return response['Credentials']
    
    def assume_role(self) -> Dict[str, str]:
        """
        Assume the specified IAM role using the customer's role ARN and external ID.

        Returns:
            dict: A dictionary containing temporary credentials for the assumed role.

        Raises:
            ValueError: If customer_role_arn is not set.
            ClientError: If there's an error assuming the role.
        """
        if not self.customer_role_arn:
            raise ValueError("customer_role_arn is not set.")

        try:
            response = self.sts_client.assume_role(
                    RoleArn=self.customer_role_arn,
                    RoleSessionName='BedrockSaaSSession',
                    ExternalId=self.external_id
                )
            return response['Credentials']
        except ClientError as e:
            raise ClientError(f"Error assuming role: {e}")
    
    def invoke_bedrock_model(self, 
                             model_id: str, 
                             prompt: str, 
                             stream: bool, 
                             credentials: Dict[str, str], 
                             message_list: Optional[List[Dict[str, Union[str, List[Dict[str, str]]]]]] = None,
                             max_tokens: int = 2000,
                             temperature: float = 0) -> Tuple[Union[Dict, object], List[Dict[str, Union[str, List[Dict[str, str]]]]]]:
        """
        Invoke a Bedrock model with the given parameters.

        Args:
            model_id (str): The ID of the Bedrock model to invoke.
            prompt (str): The input prompt for the model.
            stream (bool): Whether to stream the response or not.
            credentials (dict): The temporary credentials to use for the Bedrock client.
            message_list (list, optional): A list of previous messages for context.
            max_tokens (int, optional): The maximum number of tokens to generate. Defaults to 2000.
            temperature (float, optional): The sampling temperature. Defaults to 0.

        Returns:
            tuple: A tuple containing the model response and the updated message list.

        Raises:
            ClientError: If there's an error invoking the Bedrock model.
        """
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

            inference_config = {
                "maxTokens": max_tokens,
                "temperature": temperature
            }

            if not stream:
                response = bedrock_runtime.converse(
                    modelId=model_id,
                    messages=message_list,
                    inferenceConfig=inference_config,
                )
            else:
                response = bedrock_runtime.converse_stream(
                    modelId=model_id,
                    messages=message_list,
                    inferenceConfig=inference_config,
                )
            return response, message_list
        except ClientError as e:
            raise ClientError(f"Error invoking Bedrock model: {e}")
