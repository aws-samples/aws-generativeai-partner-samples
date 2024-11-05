import json
import boto3
import pymongo
import langchain
from langchain.embeddings import BedrockEmbeddings
from kafka import KafkaProducer
import json
import base64
import os

topic_name = 'enriched_review'
bootstrap_server=os.getenv('BOOTSTRAP_SERVER')
username=os.getenv('KAFKA_API_KEY')
password=os.getenv('KAFKA_API_SECRET')
# Create Kafka Producer instance
producer = KafkaProducer(
    bootstrap_servers=os.getenv('BOOTSTRAP_SERVER')
    ,security_protocol="SASL_SSL"
    ,sasl_mechanism="PLAIN"
    ,sasl_plain_username=os.getenv('KAFKA_API_KEY')
    ,sasl_plain_password=os.getenv('KAFKA_API_SECRET')
    )


# Define a function to send messages to Kafka
def send_message(message):
    producer.send(topic_name, value=json.dumps(message).encode('utf-8'))
    producer.flush()

    
mongo_uri = os.getenv('MONGO_URI')

# Connect to the MongoDB database
client = pymongo.MongoClient(mongo_uri)
print("connected to mongoDB...")

db = client["confluent"]
collection = db["reviews"]
print("connected to collection...")

embedding_model_id = "amazon.titan-embed-text-v1"
bedrock = boto3.client('bedrock-runtime')
# boto3_bedrock = bedrock.get_bedrock_client()

# Initiate the embedding
embeddings = BedrockEmbeddings(model_id=embedding_model_id, client=bedrock)

def mdb_query(query):
    text_as_embeddings = embeddings.embed_documents([query])
    embedding_value = text_as_embeddings[0]
    print("embedding size: " + str(len(embedding_value)))

    # get the vector search results based on the filter conditions.
    response = collection.aggregate([
        {
            "$vectorSearch": {
                "index": "cofluent_nvector_index",
                "path": "text_embedding",
                "queryVector": text_as_embeddings[0],
                "numCandidates": 200,
                "limit": 5
            }
        }, {
            '$project': {
                'score': {'$meta': 'vectorSearchScore'}, 
                "text" : 1,
                'asin': 1,
                'user_id' : 1,
                '_id':0
            }
        }
    ])

    # Result is a list of docs with the array fields
    docs = list(response)

    # #return [Document(page_content = d["page_content"], metadata = d["metadata"]) for d in docs]
    return (docs, embedding_value)

# function to calculate similarity score
def calculate_similarity_score(res):
    cnt = 0
    for doc in res:
        if doc['score'] > 0.9:
            cnt += 1
    return cnt 



def lambda_handler(event, context):
    partition=list(event['records'].keys())[0]
    records = event['records'][partition]
    for record in records:
        print("got the record, decoding base64")
        rec=base64.b64decode(record['value'])
        print(f"got record: {rec}")
        print("decoded base64, parsing JSON")
        review=json.loads(rec)
        (res, embedding) = mdb_query(review["text"])

        review["similarity_score"] = calculate_similarity_score(res)
        review["text_embedding"] = embedding
        print("calculated similarity score, sending to Kafka")
        send_message(review)
        print("message sent to Kafka")

    print(f"Processed records: {str(len(records))}")
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Processed records: {str(len(records))}",
        }),
    }