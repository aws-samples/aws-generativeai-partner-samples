import json
import boto3
import random
from confluent_kafka import Producer
from confluent_kafka.serialization import SerializationContext, MessageField
from confluent_kafka.schema_registry import SchemaRegistryClient, Schema
from confluent_kafka.schema_registry.avro import AvroSerializer
from datetime import datetime
import os

# S3 Bucket Configuration


S3_BUCKET_NAME = os.getenv('BUCKET_NAME')  # Replace with your bucket name
#S3_BUCKET_NAME = 'confluent-mongo-aws-genai'  # Replace with your bucket name

CATEGORIES = [
    'All_Beauty',
    'Appliances',
    'Cell_Phones_and_Accessories',
    'Handmade_Products',
    'Toys_and_Games'
]

# Initialize S3 client
s3_client = boto3.client('s3')

# Read Kafka configuration from client.properties
def read_kafka_config():
    config = {}
    try:
        with open("client.properties") as fh:  # Update with the path to your properties file
            for line in fh:
                line = line.strip()
                if len(line) != 0 and line[0] != "#":
                    parameter, value = line.strip().split('=', 1)
                    config[parameter] = value.strip()
    except Exception as e:
        print(f"Error reading Kafka config: {e}")
    return config

# Define Avro schemas
key_schema_str = """
{
  "type": "record",
  "name": "Key",
  "fields": [
    {"name": "user_id", "type": "string"},
    {"name": "asin", "type": "string"}
  ]
}
"""

value_schema_str = """
{
  "fields": [
    {
      "default": null,
      "name": "user_id",
      "type": [
        "null",
        "string"
      ]
    },
    {
      "default": null,
      "name": "rating",
      "type": [
        "null",
        "string"
      ]
    },
    {
      "default": null,
      "name": "title",
      "type": [
        "null",
        "string"
      ]
    },
    {
      "default": null,
      "name": "text",
      "type": [
        "null",
        "string"
      ]
    },
    {
      "default": null,
      "name": "images",
      "type": [
        "null",
        {
          "items": [
            "null",
            "string"
          ],
          "type": "array"
        }
      ]
    },
    {
      "default": null,
      "name": "asin",
      "type": [
        "null",
        "string"
      ]
    },
    {
      "default": null,
      "name": "parent_asin",
      "type": [
        "null",
        "string"
      ]
    },
    {
      "default": null,
      "name": "timestamp",
      "type": [
        "null",
        {
          "logicalType": "local-timestamp-millis",
          "type": "long"
        }
      ]
    },
    {
      "default": null,
      "name": "helpful_vote",
      "type": [
        "null",
        "int"
      ]
    },
    {
      "default": null,
      "name": "verified_purchase",
      "type": [
        "null",
        "boolean"
      ]
    }
  ],
  "name": "record",
  "namespace": "org.apache.flink.avro.generated",
  "type": "record"
}
"""

class Review(object):
    def __init__(self, review):
        self.user_id = review['user_id']
        self.asin = review['asin']
        self.rating = str(review['rating'])  # Ensure rating is a string
        self.title = review['title']
        self.text = review['text']
        self.images = review['images']
        self.parent_asin = review['parent_asin']
        self.timestamp = review['timestamp']
        self.helpful_vote = review['helpful_vote']
        self.verified_purchase = review['verified_purchase']
        
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "asin": self.asin,
            "rating": self.rating,
            "title": self.title,
            "text": self.text,
            "images": self.images,
            "parent_asin": self.parent_asin,
            "timestamp": self.timestamp,
            "helpful_vote": self.helpful_vote,
            "verified_purchase": self.verified_purchase
        }

def lambda_handler(event, context):
    # Select a category folder in a round-robin fashion
    current_index = event.get('current_index', 0)
    category_folder = CATEGORIES[current_index % len(CATEGORIES)]

    # List all JSON files in the selected category folder
    response = s3_client.list_objects_v2(
        Bucket=S3_BUCKET_NAME,
        Prefix=f'reviews/{category_folder}/'
    )

    # Filter the objects to include only those with '.json' suffix
    json_files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.json')]

    # Check if there are any JSON files in the category
    if not json_files:
        raise Exception(f"No JSON files found in the folder: reviews/{category_folder}/")

    # Pick a random JSON file
    json_file = random.choice(json_files)

    # Read reviews from the selected JSON file
    response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=json_file)
    reviews = json.loads(response['Body'].read().decode('utf-8'))

    # Pick a random review
    review_data = random.choice(reviews)
    # Get the current timestamp in milliseconds since the Unix epoch
    current_timestamp = int(datetime.now().timestamp() * 1000)

    # Update the timestamp of the chosen review
    review_data['timestamp'] = current_timestamp
    review = Review(review_data)

    # Load Kafka configuration
    kafka_config = read_kafka_config()

    # Create Schema Registry client
    schema_registry_client = SchemaRegistryClient({
        #'url': kafka_config['schema.registry.url'],
        #'basic.auth.user.info': kafka_config['schema.registry.basic.auth.user.info']
        'url': os.getenv('SR_URL'),
        'basic.auth.user.info': os.getenv('SR_CRED')
    })

    # Define schemas
    key_schema = Schema(key_schema_str, 'AVRO')
    value_schema = Schema(value_schema_str, 'AVRO')

    # Register schemas if necessary (assumes already registered)
    schema_registry_client.register_schema("amazon-reviews-key", key_schema)
    schema_registry_client.register_schema("amazon-reviews-value", value_schema)

    # Create AvroSerializers
    key_avro_serializer = AvroSerializer(
        schema_registry_client,
        key_schema,
        lambda key, ctx: key
    )
    
    value_avro_serializer = AvroSerializer(
        schema_registry_client,
        value_schema,
        lambda review, ctx: review.to_dict(),
        {"auto.register.schemas": False, "use.latest.version": True}
    )

    # Create producer
    producer = Producer({
        'bootstrap.servers': os.getenv('BOOTSTRAP_SERVER'),
        'security.protocol': 'SASL_SSL',
        'sasl.mechanisms': 'PLAIN',
        'sasl.username': os.getenv('KAFKA_API_KEY'),
        'sasl.password': os.getenv('KAFKA_API_SECRET')
    })


    # Send the review to the Kafka topic
    try:
        # Create a JSON object for the key
        key = {
            "user_id": review.user_id,
            "asin": review.asin
        }

        producer.produce(
            topic='amazon-reviews',
            key=key_avro_serializer(key, SerializationContext('amazon-reviews', MessageField.KEY)),
            value=value_avro_serializer(review, SerializationContext('amazon-reviews', MessageField.VALUE))
        )
        producer.flush()
        print(f"Produced message to topic 'amazon-reviews': key = {json.dumps(key)}, value = {json.dumps(review.to_dict())}")
    except Exception as e:
        print(f"Error producing message to Kafka: {e}")

    # Prepare the next index for round-robin selection
    next_index = (current_index + 1) % len(CATEGORIES)

    # Return the state for the next invocation
    return {
        'current_index': next_index,
        'continue': True
    }
