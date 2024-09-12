import boto3

session = boto3.session.Session()

#get region from session
region = session.region_name
bedrock = boto3.client(service_name="bedrock", region_name = region)

# retrieve the modelArn of the fine-tuned model using model name
custom_model_name = 'titan-text-lite-v1-fine-tuned-2024-07-23-16-12-46' # replace with your custom model name, get the custom model-name from the Bedrock console


fine_tune_job = bedrock.get_custom_model(modelIdentifier=custom_model_name)
custom_model_id = fine_tune_job['modelArn']


# Create the provision throughput job and retrieve the provisioned model id. This takes between 15 to 30 mins
provisioned_model_arn = bedrock.create_provisioned_model_throughput(
     modelUnits=1,
    # create a name for your provisioned throughput model
     provisionedModelName='prov-model-v1', 
     modelId=custom_model_id
    )['provisionedModelArn']  

print ("your model is being provisioned. You can view the status of provisioning in the custom model details page in console.")
print(provisioned_model_arn)