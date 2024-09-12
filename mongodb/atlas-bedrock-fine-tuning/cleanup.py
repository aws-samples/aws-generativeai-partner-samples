import boto3 
import time

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



account_id = sts_client.get_caller_identity()["Account"]
role_name = "AmazonBedrockCustomizationRole_FineTuning"
s3_bedrock_finetuning_access_policy="AmazonBedrockCustomizationPolicy_FineTuning"
customization_role = f"arn:aws:iam::{account_id}:role/{role_name}"


#detach policy
try:
    #detach policy from role
    iam.detach_role_policy(RoleName=role_name, PolicyArn=f"arn:aws:iam::{account_id}:policy/{s3_bedrock_finetuning_access_policy}")
    print(f"Detach Policy")
except Exception as e:
    print(e)
    print("Cleanup complete") 

#detach policy
try:
    #delete role
    iam.delete_role(RoleName=role_name)
    #sleep for 10 seconds to allow role to be deleted
    time.sleep(10)
    print(f"Deleted role {role_name}")
except Exception as e:
    print(e)
    print("Cleanup complete") 
    
#delete the policy
try:
    #delete policy
    iam.delete_policy(PolicyArn=f"arn:aws:iam::{account_id}:policy/{s3_bedrock_finetuning_access_policy}")
    print(f"Deleted policy")
except Exception as e:
    print(e)
    print("Cleanup complete") 

#delete all files in the s3 bucket 

try:
    #get list of objects in bucket
    objects = s3_client.list_objects(Bucket=bucket_name)
    #delete each object
    for obj in objects['Contents']:
        s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])
        print(f"Deleted {obj['Key']}")
        time.sleep(0.5)
    
    #delete the bucket
    s3_client.delete_bucket(Bucket=bucket_name)
    print(f"Deleted bucket {bucket_name}")
    print("Cleanup complete")

except Exception as e:
    print(e)
    print("Cleanup complete")

#delete provisioned model

provisioned_model_arn = 'arn:aws:bedrock:us-east-1:448407886166:provisioned-model/c6g3gpgbgav8' #replace with provisional model arn
bedrock.delete_provisioned_model_throughput(provisionedModelId=provisioned_model_arn)
print(f"Deleted provisioned model {provisioned_model_arn}")