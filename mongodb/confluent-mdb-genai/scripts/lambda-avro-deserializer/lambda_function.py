import boto3
import logging
from confluent_kafka.serialization import SerializationContext, MessageField
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka import Producer
from confluent_kafka.serialization import SerializationContext, MessageField
from confluent_kafka.schema_registry import SchemaRegistryClient

import json
import os
import base64 
logger = logging.getLogger()
logger.setLevel("INFO")

def lambda_handler(event,context):
    logger.info(f"Reading and serliazing schema string")
    path = os.path.realpath(os.path.dirname(__file__))
    with open(f"{path}/schema.avsc") as f:
        schema_str = f.read()
    logger.info(f"Imported Schema.")

    sr_config = {        
        'url': os.getenv('SR_URL'),
        'basic.auth.user.info': os.getenv('SR_CRED')
    }
    conf = {
        'bootstrap.servers': os.getenv('BOOTSTRAP_SERVER'),
        'security.protocol': 'SASL_SSL',
        'sasl.mechanisms': 'PLAIN',
        'sasl.username': os.getenv('KAFKA_API_KEY'),
        'sasl.password': os.getenv('KAFKA_API_SECRET')
    }
    #Need to get the avro schema from the Flink output 
    topic="valid_reviews_with_user_info"
    schema_registry_client = SchemaRegistryClient(sr_config)
    avro_deserializer = AvroDeserializer(schema_registry_client,schema_str)
    partition=list(event['records'].keys())[0]
    message=event['records'][partition]
    #print(message)
    decoded_value=base64.b64decode(message[0]['value'])
    value=avro_deserializer(decoded_value, SerializationContext(topic, MessageField.VALUE))
    print("Decoded Value: ")
    print(value)

        
    #will need to parse out the value
    payload_details = value
    message = {
        "user_id" : payload_details['user_id'],
        "rating" : payload_details['rating'],
        "title" : payload_details['title'],
        "text" : payload_details['text'],
        "images" : payload_details['images'],
        "asin" : payload_details['asin'],
        "parent_asin" : payload_details['parent_asin'],
        "timestamp" : payload_details['timestamp'],
        "helpful_vote" : payload_details['helpful_vote'],
        "verified_purchase" : payload_details['verified_purchase'],
        "window_start" : payload_details['window_start'],
        "window_end" : payload_details['window_end'],
        "review_count" : payload_details['review_count'],
        "address" : payload_details['address'],
        "city" : payload_details['city'],
        "country" : payload_details['country'],
        "email" : payload_details['email'],
        "first_name" : payload_details['first_name'],
        "gender" : payload_details['gender'],
        "last_name" : payload_details['last_name'],
        "payment_method" : payload_details['payment_method'],
        "phone_number" : payload_details['phone_number'],
        "state" : payload_details['state'],
        "zip_code" : payload_details['zip_code']
    }
    message_json = json.dumps(message, indent=4, sort_keys=True, default=str) 
    print(message_json)
    producer = Producer(conf)
    producer.produce("valid_reviews_with_user_info_json", key="", value=str(message_json))
    producer.flush()
 