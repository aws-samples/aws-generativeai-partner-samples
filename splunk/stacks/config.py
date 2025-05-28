'''
Copyright (c) 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
This source code is subject to the terms found in the AWS Enterprise Customer Agreement.
NOTE: If deploying to production, set this to true.
 - If this is set to true, all properties from the Prod_Props class will be used
 - If this is set to false, all the properties from the Dev_Props class will be used
'''

import os

EMBEDDING_MODEL_IDs = ["amazon.titan-embed-text-v2:0"]
CHUNKING_STRATEGIES = {0:"Default chunking",1:"Fixed-size chunking", 2:"No chunking"}

class EnvSettings:
    # General params
    ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID", "") # Read account ID from environment variable
    ACCOUNT_REGION = "us-east-1" # TODO: Change this to your region
    RAG_PROJ_NAME = "e2e-rag" # TODO: Change this to any name of your choice

class KbConfig:
    KB_ROLE_NAME = f"{EnvSettings.RAG_PROJ_NAME}-kb-role"
    EMBEDDING_MODEL_ID = EMBEDDING_MODEL_IDs[0]
    CHUNKING_STRATEGY = CHUNKING_STRATEGIES[1] # TODO: Choose the Chunking option 0,1,2
    MAX_TOKENS = 512 # TODO: Change this value accordingly if you choose "FIXED_SIZE" chunk strategy
    OVERLAP_PERCENTAGE = 20 # TODO: Change this value accordingly

class DsConfig:
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", f"splunkrag{EnvSettings.ACCOUNT_ID}") # Get bucket name from environment or use default

class OpenSearchServerlessConfig:
    COLLECTION_NAME = f"{EnvSettings.RAG_PROJ_NAME}-kb-collection"
    INDEX_NAME = "splunk-sourcetypes"

class SplunkHelperConfig:
    INDEX_NAME = "splunk-sourcetypes"
    SECRET_ARN = os.getenv("SPLUNK_SECRET_NAME", f"arn:aws:secretsmanager:{EnvSettings.ACCOUNT_REGION}:{EnvSettings.ACCOUNT_ID}:secret:splunk-bedrock-secret-bPya16")
                 
