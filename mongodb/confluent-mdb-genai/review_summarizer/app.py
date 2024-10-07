import json
import pymongo
import boto3
import json
from kafka import KafkaProducer
import base64

def get_secret(secret_name):
    
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager')

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        secret = get_secret_value_response['SecretString']
        return secret
    except Exception as e:
        logger.error("Error getting secret", exc_info=True)
        raise e


# Configure Kafka producer
bootstrap_server = get_secret("confluent/bootstrap")
bootstrap_servers = [bootstrap_server]
topic_name = 'enriched_product'

# Define a function to send messages to Kafka
kafka_secret = json.loads(get_secret("confluentMongoDB2"))

# Create Kafka Producer instance
producer = KafkaProducer(bootstrap_servers=bootstrap_servers
                         ,security_protocol="SASL_SSL"
                         ,sasl_mechanism="PLAIN"
                         ,sasl_plain_username=kafka_secret['username']
                         ,sasl_plain_password=kafka_secret['password']
                         )

def send_message(message):
    producer.send(topic_name, value=json.dumps(message).encode('utf-8'))
    producer.flush()
    
mongo_uri = get_secret("workshop/atlas_secret")

client = pymongo.MongoClient(mongo_uri)

def generate_embeddings(model_id, body):
    """
    Generate a vector of embeddings for a text input using Amazon Titan Embeddings G1 - Text on demand.
    Args:
        model_id (str): The model ID to use.
        body (str) : The request body to use.
    Returns:
        response (JSON): The embedding created by the model and the number of input tokens.
    """

    logger.info("Generating embeddings with Amazon Titan Embeddings G1 - Text model %s", model_id)

    bedrock = boto3.client(service_name='bedrock-runtime')

    accept = "application/json"
    content_type = "application/json"

    response = bedrock.invoke_model(
        body=body, modelId=model_id, accept=accept, contentType=content_type
    )

    response_body = json.loads(response.get('body').read())

    return response_body


def lambda_handler(event, context):
    partition=list(event['records'].keys())[0]
    records = event['records'][partition]
    for record in records:
        print("got the record, decoding base64")
        rec=base64.b64decode(record['value'])
        print(f"got record: {rec}")
        print("decoded base64, parsing JSON")
        review=json.loads(rec)

        text = review['text']
        asin = review['asin']

        col = client["confluent_atlas_customer_review"]["reviews"]
        data = col.find({"asin":asin}).sort("timestamp", pymongo.DESCENDING).limit(5)
        text = ""
        for result in data:
            text += result["text"] +"\n"
 
        brt = boto3.client(service_name='bedrock-runtime')

        body = json.dumps({
            "prompt": f"\n\nHuman: You are tool summarizing reviews. Condense the following product review in two sentences. Refer to persons in the summary as customers: ${text} \n\nAssistant:",
            "max_tokens_to_sample": 300,
            "temperature": 0.1,
            "top_p": 0.9,
        })

        modelId = 'anthropic.claude-instant-v1'
        accept = 'application/json'
        contentType = 'application/json'

        response = brt.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)

        response_body = json.loads(response.get('body').read())

        product = {
            "asin": asin,
            "review_summary": response_body.get('completion')
        }

                # text
        print(f"Processed product: {product}")
        
        # send the review to Kafka
        send_message(product)
    
    print(f"Processed records: {str(len(records))}")
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Processed records: {str(len(records))}",
        }),
    }
