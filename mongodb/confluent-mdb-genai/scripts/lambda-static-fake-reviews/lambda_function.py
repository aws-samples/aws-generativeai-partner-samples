import json
import boto3
import random
from datetime import datetime
from confluent_kafka import Producer
from confluent_kafka.serialization import SerializationContext, MessageField
from confluent_kafka.schema_registry import SchemaRegistryClient, Schema
from confluent_kafka.schema_registry.avro import AvroSerializer
import os

# AWS S3 client
s3 = boto3.client('s3')

# Define S3 bucket and key details
bucket_name = os.getenv('BUCKET_NAME')
#bucket_name = 'confluent-mongo-aws-genai'

# Define Avro schemas for key and value
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

# Load Kafka configuration
def read_kafka_config():
    config = {}
    try:
        with open("client.properties") as fh:
            for line in fh:
                line = line.strip()
                if len(line) != 0 and line[0] != "#":
                    parameter, value = line.strip().split('=', 1)
                    config[parameter] = value.strip()
    except Exception as e:
        print(f"Error reading Kafka config: {e}")
    return config

def load_json_from_s3(bucket, key):
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        data = response['Body'].read().decode('utf-8')
        return json.loads(data)
    except Exception as e:
        print(f"Error loading {key} from S3: {e}")
        return []

class Review(object):
    def __init__(self, review):
        self.user_id = review['user_id']
        self.asin = review['asin']
        self.rating = str(review['rating'])  # Ensure rating is converted to string
        self.title = review['title']
        self.text = review['text']
        self.images = review.get('images', [])  # Default to empty array if 'images' is not provided
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
            "images": self.images,  # Always ensure this is an empty array if no images
            "parent_asin": self.parent_asin,
            "timestamp": self.timestamp,
            "helpful_vote": self.helpful_vote,
            "verified_purchase": self.verified_purchase
        }

def lambda_handler(event, context):
    # Load Amazon user IDs
    user_ids = load_json_from_s3(bucket_name, 'amazon-user-ids.json')
    if not user_ids:
        print("No user IDs found.")
        return

    # Randomly select 5 unique user IDs
    selected_user_ids = random.sample(user_ids, 5)

    # Load ASINs for each category
    categories = ['All_Beauty', 'Appliances', 'Cell_Phones_and_Accessories', 'Handmade_Products', 'Toys_and_Games']
    category_asins = {}
    for category in categories:
        category_asins[category] = load_json_from_s3(bucket_name, f'product-ids-by-category/{category}_asins.json')

    # Define the negative fake review content
    fake_review_content = {
        "rating": "1.0",
        "title": "Terrible product, very disappointed!",
        "text": "The product quality was extremely poor, broke after a single use. Customer service was unhelpful and refused to issue a refund.",
        "images": [],  # Set empty array for images
        "helpful_vote": 0,
        "verified_purchase": False
    }

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

    # Create Kafka producer
    producer = Producer({
        'bootstrap.servers': os.getenv('BOOTSTRAP_SERVER'),
        'security.protocol': 'SASL_SSL',
        'sasl.mechanisms': 'PLAIN',
        'sasl.username': os.getenv('KAFKA_API_KEY'),
        'sasl.password': os.getenv('KAFKA_API_SECRET')
    })


    # Map each of the 5 random user IDs to a random product in a different category
    reviews = []
    for i, user_id in enumerate(selected_user_ids):
        category = categories[i]
        # Randomly select an ASIN from the category
        asin = random.choice(category_asins[category])  
        review = fake_review_content.copy()
        review['user_id'] = user_id
        review['asin'] = asin
        review['parent_asin'] = asin
        review['timestamp'] = int(datetime.now().timestamp() * 1000)  # Current timestamp in milliseconds
        reviews.append(Review(review))  # Store Review objects

    # Produce reviews to Kafka topic
    for review in reviews:
        try:
            key = {
                "user_id": review.user_id,
                "asin": review.asin
            }

            producer.produce(
                topic='amazon-reviews',
                key=key_avro_serializer(key, SerializationContext('amazon-reviews', MessageField.KEY)),
                value=value_avro_serializer(review, SerializationContext('amazon-reviews', MessageField.VALUE))
            )
            print(f"Produced message to topic 'amazon-reviews': key = {json.dumps(key)}, value = {json.dumps(review.to_dict())}")
        except Exception as e:
            print(f"Error producing message to Kafka: {e}")

    # Ensure all messages are sent
    producer.flush()

    return {
        'statusCode': 200,
        'body': json.dumps(f'Successfully produced {len(reviews)} reviews to Kafka topic.'),
        'continue': True
    }
