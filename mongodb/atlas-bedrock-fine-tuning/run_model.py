import boto3
import json

session = boto3.session.Session()

#get region from session
region = session.region_name
bedrock_runtime = boto3.client(service_name="bedrock-runtime", region_name = region )
provisioned_model_arn = '' #Replace with provisioned model arn.

prompt_data = 'Write in less than 200 words the plot of the movie: Where Eagles Dare'

text_gen_config = {
    "maxTokenCount": 200,
    "stopSequences": [], 
    "temperature": 0.2,
    "topP": 0.9
}

body = json.dumps({
    "inputText": prompt_data,
    "textGenerationConfig": text_gen_config  
})

# provide the modelId of the provisioned custom model
modelId = provisioned_model_arn
accept = 'application/json'
contentType = 'application/json'

# invoke the provisioned custom model
response = bedrock_runtime.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)

response_body = json.loads(response.get('body').read())
print(response_body)