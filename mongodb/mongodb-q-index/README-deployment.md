# Q Index Countries Deployment Guide

This guide explains how to deploy the Q Business application with Q Index for the Countries data.

## Prerequisites

- AWS CLI installed and configured
- AWS account with permissions to create CloudFormation stacks, IAM roles, S3 buckets, and Q Business resources
- The countries.md file containing the CIA World Factbook data

## Deployment Steps

### 1. Deploy the CloudFormation Stack

```bash
aws cloudformation create-stack \
  --stack-name QIndexCountriesStack \
  --template-body file://qindex-countries.yaml \
  --capabilities CAPABILITY_IAM
```

This command creates a new CloudFormation stack with the following resources:
- An S3 bucket for storing the countries data
- IAM roles with appropriate permissions for Q Business to access the S3 bucket

You can monitor the stack creation progress:

```bash
aws cloudformation describe-stacks --stack-name QIndexCountriesStack
```

### 2. Upload the Countries Data to S3

After the CloudFormation stack is created successfully, upload the countries.md file to the S3 bucket:

```bash
aws s3 cp /Users/ialek/projects/qindex-mdb/countries/countries.md s3://qindex-countries-data/
```

Replace `qindex-countries-data` with the actual bucket name if you changed it in the CloudFormation parameters.

### 3. Create a Q Business Application

Create a Q Business application using the AWS Management Console:

1. Go to the AWS Management Console
2. Search for "Amazon Q Business" and select it
3. Click "Create application"
4. Enter "CountriesKnowledgeBase" as the application name
5. Enter "World countries information from CIA World Factbook" as the description
6. Select the IAM role created by the CloudFormation stack (QBusinessServiceRole)
7. Click "Create application"

### 4. Create a Data Source

Add the S3 bucket as a data source to your Q Business application:

1. In the Q Business console, select your application
2. Go to the "Data sources" tab
3. Click "Add data source"
4. Select "Amazon S3" as the data source type
5. Enter "CountriesData" as the data source name
6. Select the S3 bucket created by the CloudFormation stack
7. Select the IAM role created by the CloudFormation stack
8. Click "Add data source"

### 5. Start the Data Source Synchronization

Start the data source synchronization to index the countries data:

1. In the Q Business console, select your application
2. Go to the "Data sources" tab
3. Find your data source and click "Sync now"

Alternatively, you can use the AWS CLI:

```bash
# Get the application ID and data source ID
APPLICATION_ID=$(aws qbusiness list-applications --query "applicationSummaries[?displayName=='CountriesKnowledgeBase'].applicationId" --output text)
DATA_SOURCE_ID=$(aws qbusiness list-data-sources --application-id $APPLICATION_ID --query "dataSourceSummaries[?displayName=='CountriesData'].dataSourceId" --output text)

# Start the data source sync job
aws qbusiness start-data-source-sync-job \
  --application-id $APPLICATION_ID \
  --data-source-id $DATA_SOURCE_ID
```

### 6. Create a Q Index

Create a Q Index for your application:

1. In the Q Business console, select your application
2. Go to the "Indexes" tab
3. Click "Create index"
4. Enter "CountriesIndex" as the index name
5. Select "Enterprise" as the index type
6. Click "Create index"

### 7. Create a Retriever

Create a retriever for your Q Index:

1. In the Q Business console, select your application
2. Go to the "Retrievers" tab
3. Click "Create retriever"
4. Enter "CountriesRetriever" as the retriever name
5. Select your index
6. Click "Create retriever"

### 8. Test the Q Index

You can test your Q Index using the AWS Management Console or the AWS CLI:

```bash
# Get the application ID and retriever ID
APPLICATION_ID=$(aws qbusiness list-applications --query "applicationSummaries[?displayName=='CountriesKnowledgeBase'].applicationId" --output text)
RETRIEVER_ID=$(aws qbusiness list-retrievers --application-id $APPLICATION_ID --query "retrieverSummaries[?displayName=='CountriesRetriever'].retrieverId" --output text)

# Test the retriever with a query
aws qbusiness retrieve-and-generate \
  --application-id $APPLICATION_ID \
  --retriever-id $RETRIEVER_ID \
  --input '{"text": "Tell me about the geography of France"}'
```

## Integration with MongoDB Atlas

To integrate the Q Index with your MongoDB Atlas application, you'll need to:

1. Use the AWS SDK in your application to call the Q Business API
2. Use the application ID and retriever ID from the Q Business console
3. Process the responses from Q Index and combine them with data from MongoDB Atlas

Example code for integration:

```python
import boto3
from pymongo import MongoClient

# Initialize Q Business client
qbusiness = boto3.client('qbusiness')

# Initialize MongoDB client
mongo_client = MongoClient('your-mongodb-atlas-connection-string')
db = mongo_client['your-database']
collection = db['your-collection']

def query_countries_data(query_text):
    # Query Q Index
    response = qbusiness.retrieve_and_generate(
        applicationId='your-application-id',
        retrieverId='your-retriever-id',
        input={
            'text': query_text
        }
    )
    
    # Process Q Index response
    q_index_result = response['generatedContent']
    
    # Query MongoDB Atlas for additional data
    mongo_results = collection.find({'related_to': query_text})
    
    # Combine results
    combined_results = {
        'q_index': q_index_result,
        'mongodb': list(mongo_results)
    }
    
    return combined_results
```

## Cleanup

To delete all resources created by the CloudFormation stack:

```bash
# First, empty the S3 bucket
aws s3 rm s3://qindex-countries-data --recursive

# Then delete the CloudFormation stack
aws cloudformation delete-stack --stack-name QIndexCountriesStack
```

Additionally, you'll need to manually delete the Q Business application, data source, index, and retriever from the AWS Management Console.
