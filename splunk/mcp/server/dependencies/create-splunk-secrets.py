import boto3
import json
from botocore.exceptions import ClientError

# Variables for Splunk Connection
secret_value = {}
secret_value['SplunkHost'] = "<Your Splunk Host IP or URL>"
secret_value['SplunkToken'] = "<Your Splunk Access Token>"

# Create a Secrets Manager client
secrets_client = boto3.client('secretsmanager')
# Create a new secret
try:
    create_secret_response = secrets_client.create_secret(
        Name='splunk-bedrock-secret',
        Description='This is an example secret',
        SecretString=json.dumps(secret_value)
    )
    print(f"Secret created: {create_secret_response['ARN']}")
    secret_arn = create_secret_response['ARN']
except ClientError as e:
    print(f"Error creating secret: {e.response['Error']['Code']}")

# Retrieve the secret value
try:
    get_secret_value_response = secrets_client.get_secret_value(
        SecretId='secret_arn'
    )
except ClientError as e:
    if e.response['Error']['Code'] == 'DecryptionFailureException':
        # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
        raise e
    elif e.response['Error']['Code'] == 'InternalServiceErrorException':
        # An error occurred on the server side.
        raise e
    elif e.response['Error']['Code'] == 'InvalidParameterException':
        # You provided an invalid value for a parameter.
        raise e
    elif e.response['Error']['Code'] == 'InvalidRequestException':
        # You provided a parameter value that is not valid for the current state of the resource.
        raise e
    elif e.response['Error']['Code'] == 'ResourceNotFoundException':
        # We can't find the resource that you asked for.
        raise e
else:
    # Decrypted secret value using the associated KMS CMK
    # Depending on whether the secret was a string or binary, one of these fields will be populated
    if 'SecretString' in get_secret_value_response:
        secret_value = get_secret_value_response['SecretString']
    else:
        secret_value = get_secret_value_response['SecretBinary']

    # Your code to use the secret value goes here
    print(f"Retrieved secret value: {secret_value}")

