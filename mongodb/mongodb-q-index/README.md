# Q Index MongoDB Atlas Integration

A chatbot application that integrates Q Index with MongoDB Atlas using AWS Lambda and Streamlit, providing a natural language interface to query country information from the CIA World Factbook.

## Project Overview

This project provides a natural language interface to interact with MongoDB Atlas collections. It uses:

- **Streamlit**: For the web-based chatbot interface
- **AWS Lambda**: To orchestrate the interaction between Q Index and MongoDB Atlas
- **Q Business & Q Index**: For natural language processing and query generation
- **MongoDB Atlas**: As the database backend storing CIA World Factbook data

The application allows users to:
- Ask natural language questions about countries and their characteristics
- View query results in a chat interface
- Maintain conversation context for follow-up questions

## Project Structure

```
mongodb-q-index/
├── app/
│   └── app.py             # Main Streamlit application
├── lambda/
│   └── lambda_function.py # AWS Lambda function handler with Q Index integration
├── parameters.json        # SAM template parameters
└── template.yaml         # SAM template for Lambda deployment
```

## Data Source

The project uses data from the CIA World Factbook archives (https://www.cia.gov/the-world-factbook/about/archives/) as its knowledge base. This comprehensive dataset includes information about countries worldwide, including:
- Geography (area, climate, natural resources)
- Government (type, leaders, capital)
- People & Society (population, demographics, languages)
- Economy (GDP, exports, imports)

The data is loaded into Q Index to provide the knowledge base for answering questions. The Lambda function combines Q Index results with data from MongoDB Atlas to generate comprehensive responses.
- People & Society (population, demographics, languages)
- Economy (GDP, exports, imports)

This data is loaded into MongoDB Atlas and indexed for efficient querying through Q Index.

## Prerequisites

- Python 3.8+
- AWS account with permissions for:
  - Lambda
  - CloudFormation
  - IAM roles
  - S3 buckets
  - Q Business resources
- MongoDB Atlas account
- AWS SAM CLI installed
- AWS CLI installed and configured

## Deployment Guide

### 1. Setting Up MongoDB Atlas Secret

1. Create a secret in AWS Secrets Manager:
   ```bash
   aws secretsmanager create-secret \
       --name MONGODB_ATLAS_URI \
       --secret-string '{"MONGODB_URI":"your-mongodb-connection-string"}'
   ```

2. Note the ARN of the created secret for use in the Lambda function's environment variables.

### 2. Setting Up Q Business Application

1. Create a Q Business application:
   ```bash
   # Create CloudFormation stack for required resources
   aws cloudformation create-stack \
     --stack-name QIndexCountriesStack \
     --template-body file://qindex-countries.yaml \
     --capabilities CAPABILITY_IAM
   ```

2. Upload the data:
   ```bash
   # Upload your CIA World Factbook data to the S3 bucket
   aws s3 cp your-data-file s3://bucket-name/
   ```

3. In the AWS Management Console:
   - Go to Amazon Q Business
   - Create new application "CountriesKnowledgeBase"
   - Add S3 bucket as data source
   - Create an index (Enterprise type)
   - Create a retriever
   - Note the application ID and retriever ID

### 3. Deploying the Lambda Function

The project uses AWS SAM for deployment. The template includes all necessary IAM permissions and environment configurations.

1. Deploy using SAM CLI with parameters file:
   ```bash
   sam deploy \
     --stack-name q-index-mongodb \
     --parameter-overrides file://parameters.json \
     --resolve-s3 \
     --capabilities CAPABILITY_IAM
   ```

   Or specify parameters directly:
   ```bash
   sam deploy \
     --stack-name q-index-mongodb \
     --parameter-overrides \
       MongoDBSecretName=MONGODB_ATLAS_URI \
       MongoDBDatabase=travel \
       MongoDBCollection=asia \
       QBusinessAppId=your-app-id \
       QBusinessRetrieverId=your-retriever-id \
       BedrockModelId=anthropic.claude-3-sonnet-20240229-v1:0 \
     --resolve-s3 \
     --capabilities CAPABILITY_IAM
   ```

2. Testing the Deployed Function:

   a. Test initial query:
   ```bash
   aws lambda invoke \
     --function-name QIndexMongoDBIntegration \
     --payload '{"query": "Tell me about France"}' \
     --cli-binary-format raw-in-base64-out \
     response.json
   ```

   b. For follow-up queries, use the conversation ID from the previous response:
   ```bash
   aws lambda invoke \
     --function-name QIndexMongoDBIntegration \
     --payload '{"query": "What is its climate?", "conversation_id": "CONVERSATION_ID_FROM_PREVIOUS_RESPONSE"}' \
     --cli-binary-format raw-in-base64-out \
     followup-response.json
   ```

### 4. Running the Streamlit App

1. Start the Streamlit application:
   ```bash
   streamlit run app/app.py
   ```

2. Open your browser to http://localhost:8501

## Usage Instructions

### Chatting with Your Data

1. Type your question in the input field at the bottom of the chat interface.
2. Press Enter to submit your question.
3. The chatbot will process your question using Q Index and display the answer.

### Example Questions

- "Tell me about France's geography"
- "What is the population of Germany?"
- "Compare the economies of Spain and Italy"
- "What languages are spoken in Switzerland?"

### Viewing Raw Data

- Toggle the "Show Raw Data" checkbox in the sidebar to view detailed responses including Q Index results and MongoDB data.

### Clearing Chat History

- Click the "Clear Chat History" button in the sidebar to start a new conversation.

## Implementation Details

### Lambda Function

The Lambda function serves as middleware between the frontend and backend services:

1. Processes natural language queries using Q Index
2. Executes MongoDB queries to retrieve relevant data
3. Combines Q Index and MongoDB results to create an augmented prompt
4. Sends the augmented prompt to Amazon Bedrock for processing
5. Returns the combined results and LLM response

### Conversation Management

The Lambda function maintains conversation context:

1. Initial queries generate a new conversation ID
2. Follow-up queries use the previous conversation ID
3. Context is maintained across the entire conversation

## Cleanup

To remove all deployed resources:

1. Empty the S3 bucket:
   ```bash
   aws s3 rm s3://bucket-name --recursive
   ```

2. Delete the CloudFormation stacks:
   ```bash
   aws cloudformation delete-stack --stack-name QIndexCountriesStack
   aws cloudformation delete-stack --stack-name q-index-mongodb
   ```

3. In the AWS Console, manually delete:
   - Q Business application
   - Data source
   - Index
   - Retriever

## License

This project is licensed under the MIT License - see the LICENSE file for details.
