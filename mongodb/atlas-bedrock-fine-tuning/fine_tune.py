import boto3 
import time
import pprint

bucket_name='fine-tune-embeddings-mongo'
session = boto3.session.Session()

#get region from session
region = session.region_name

#create necessary service clients
s3_client = boto3.client('s3', region_name = region)
bedrock = boto3.client(service_name="bedrock", region_name = region)
bedrock_runtime = boto3.client(service_name="bedrock-runtime", region_name = region )
sts_client = boto3.client('sts', region_name = region)
iam = boto3.client('iam', region_name=region)

s3_train_uri=f's3://{bucket_name}/train/dataset_train.jsonl'
s3_validation_uri=f's3://{bucket_name}/valid/dataset_valid.jsonl'
s3_test_uri=f's3://{bucket_name}/test/dataset_test.jsonl'

#create role for the customization job
account_id = sts_client.get_caller_identity()["Account"]
role_name = "AmazonBedrockCustomizationRole_FineTuning"
s3_bedrock_finetuning_access_policy="AmazonBedrockCustomizationPolicy_FineTuning"
customization_role = f"arn:aws:iam::{account_id}:role/{role_name}"
ROLE_DOC = f"""{{
    "Version": "2012-10-17",
    "Statement": [
        {{
            "Effect": "Allow",
            "Principal": {{
                "Service": "bedrock.amazonaws.com"
            }},
            "Action": "sts:AssumeRole",
            "Condition": {{
                "StringEquals": {{
                    "aws:SourceAccount": "{account_id}"
                }},
                "ArnEquals": {{
                    "aws:SourceArn": "arn:aws:bedrock:{region}:{account_id}:model-customization-job/*"
                }}
            }}
        }}
    ]
}}
"""
ACCESS_POLICY_DOC = f"""{{
    "Version": "2012-10-17",
    "Statement": [
        {{
            "Effect": "Allow",
            "Action": [
                "s3:AbortMultipartUpload",
                "s3:DeleteObject",
                "s3:PutObject",
                "s3:GetObject",
                "s3:GetBucketAcl",
                "s3:GetBucketNotification",
                "s3:ListBucket",
                "s3:PutBucketNotification"
            ],
            "Resource": [
                "arn:aws:s3:::{bucket_name}",
                "arn:aws:s3:::{bucket_name}/*"
            ]
        }}
    ]
}}"""

response_role = iam.create_role(
    RoleName=role_name,
    AssumeRolePolicyDocument=ROLE_DOC,
    Description="Role for Bedrock to access S3 for training",
)

response_policy = iam.create_policy(
    PolicyName=s3_bedrock_finetuning_access_policy,
    PolicyDocument=ACCESS_POLICY_DOC,
)
policy_arn = response_policy["Policy"]["Arn"]

iam.attach_role_policy(
    RoleName=role_name,
    PolicyArn=policy_arn,
)

#wait for role to be created
time.sleep(10)

finetune_role_arn = response_role["Role"]["Arn"]
pprint.pp(finetune_role_arn)

from datetime import datetime
ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

# Choose the foundation model you want to customize and provide ModelId(find more about model reference at https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-reference.html)
# using the titan embedding model for fine-tuning
base_model_id = "amazon.titan-text-express-v1:0:8k"

# Select the customization type of "FINE_TUNING".
customization_type = "FINE_TUNING"

# Create a customization job name
customization_job_name = f"amazon-titan-text-express-tuned-model-{ts}"

# Create a customized model name for your fine-tuned model
custom_model_name = f"amazon-titan-text-express-fine-tuned-{ts}"

# Define the hyperparameters for fine-tuning model
hyper_parameters = {
        "epochCount": "1",
        "batchSize": "1",
        "learningRate": "0.005"
    }

# Specify your data path for training, validation(optional) and output
training_data_config = {"s3Uri": s3_train_uri}

validation_data_config = {
        "validators": [{
            "s3Uri": s3_validation_uri
        }]
    }

output_data_config = {"s3Uri": f's3://{bucket_name}/outputs/output-{custom_model_name}'}

# Create the customization job
bedrock.create_model_customization_job(
    customizationType=customization_type,
    jobName=customization_job_name,
    customModelName=custom_model_name,
    baseModelIdentifier=base_model_id,
    hyperParameters=hyper_parameters,
    trainingDataConfig=training_data_config,
    validationDataConfig=validation_data_config,
    outputDataConfig=output_data_config,
    roleArn = finetune_role_arn
)

print("Fine tune job created. Navigate to console to view status.")