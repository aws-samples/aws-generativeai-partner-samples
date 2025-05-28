import json
import os
import logging
import pymongo
from pymongo import MongoClient
import boto3
from botocore.exceptions import ClientError
from langchain.embeddings import BedrockEmbeddings

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients setup
q_business_client = boto3.client('qbusiness')
bedrock_runtime = boto3.client('bedrock-runtime')
secrets_manager = boto3.client('secretsmanager')

def get_secret():
    """Get MongoDB URI from AWS Secrets Manager"""
    secret_name = os.environ['MONGODB_SECRET_NAME']
    try:
        response = secrets_manager.get_secret_value(SecretId=secret_name)
        if 'SecretString' in response:
            secret = json.loads(response['SecretString'])
            return secret['MONGODB_URI']
    except ClientError as e:
        logger.error(f"Error retrieving secret: {e}")
        raise e

def setup_bedrock():
    """Set up and return Bedrock runtime client"""
    return boto3.client('bedrock-runtime')

def get_mongo_client():
    """Get MongoDB client using connection string from Secrets Manager"""
    mongodb_uri = get_secret()
    return MongoClient(mongodb_uri)

def get_travel_collection(client, database=None, collection=None):
    """Get MongoDB collection based on provided or default database and collection names"""
    db_name = database or os.environ.get('MONGODB_DATABASE', 'travel')
    coll_name = collection or os.environ.get('MONGODB_COLLECTION', 'asia')
    return client[db_name][coll_name]

def mongodb_search(query, client=None, database=None, collection=None):
    """
    Perform semantic search in MongoDB using vector search
    """
    logger.info(f"Performing semantic search for: {query}")
    
    # Set up Bedrock for embeddings
    bedrock_client = setup_bedrock()
    
    # Generate embeddings using LangChain
    embeddings = BedrockEmbeddings(
        client=bedrock_client,
        model_id="amazon.titan-embed-text-v1",
    )
    text_as_embeddings = embeddings.embed_documents([query])
    embedding_value = text_as_embeddings[0]
    logger.info("Successfully generated embeddings using LangChain")
    
    # Get MongoDB client and collection
    if client is None:
        client = get_mongo_client()
    
    mongo_collection = get_travel_collection(client, database, collection)
    field_name_to_be_vectorized = "About Place"
    
    # Perform vector search
    logger.info("Performing vector search in MongoDB")
    try:
        response = mongo_collection.aggregate(
            [
                {
                    "$vectorSearch": {
                        "index": "travel_vector_index",
                        "path": "details_embedding",
                        "queryVector": embedding_value,
                        "numCandidates": 200,
                        "limit": 10,
                    }
                },
                {
                    "$project": {
                        "score": {"$meta": "vectorSearchScore"},
                        field_name_to_be_vectorized: 1,
                        "_id": 0,
                    }
                },
            ]
        )
        
        # Convert results to list
        docs = list(response)
        logger.info(f"Found {len(docs)} results from vector search")
        return docs
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        # Try a simple regex search as fallback
        try:
            # Create a regex pattern for case-insensitive partial matching
            pattern = {"$regex": query, "$options": "i"}
            
            # Search across multiple fields
            cursor = mongo_collection.find({
                "$or": [
                    {"Country": pattern},
                    {"Place Name": pattern},
                    {"About Place": pattern}
                ]
            }).limit(10)
            
            results = list(cursor)
            
            # Convert ObjectId to string for JSON serialization
            for doc in results:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            
            return results
        except Exception as fallback_error:
            logger.error(f"Fallback search failed: {fallback_error}")
            return []

def lambda_handler(event, context):
    """
    Lambda handler for MongoDB Atlas, Q Index, and LLM integration
    """
    try:
        # Extract parameters from the event
        # Use environment variables for database and collection
        database = os.environ.get('MONGODB_DATABASE', 'travel')
        collection = os.environ.get('MONGODB_COLLECTION', 'asia')
        query = event.get('query')
        conversation_id = event.get('conversation_id')  # Get conversation_id if provided
        parent_message_id = event.get('parent_message_id')  # Get parent_message_id if provided
        
        # Connect to MongoDB Atlas
        client = get_mongo_client()
        db = client[database]
        coll = db[collection]
        
        # Process natural language query using Q Index
        q_index_result, new_conversation_id, new_parent_message_id = process_with_q_index(
            query, conversation_id, parent_message_id
        )
        
        # Get MongoDB results using mongodb_search
        mongodb_result = mongodb_search(query, client, database, collection)
        
        # Generate LLM response using Q Index and MongoDB results
        llm_response = generate_llm_response(query, q_index_result, mongodb_result)
        
        # Combine all results
        result = {
            'q_index_result': q_index_result,
            'mongodb_result': mongodb_result,
            'llm_response': llm_response,
            'conversation_id': new_conversation_id,  # Return the conversation ID for future use
            'parent_message_id': new_parent_message_id  # Return the parent_message_id for future use
        }
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'result': result
            })
        }
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

def process_with_q_index(query, conversation_id=None, parent_message_id=None):
    """
    Process natural language query using Q Index via chat_sync instead of search_relevant_content
    """
    try:
        # Get the Q Business application ID from environment variables
        application_id = os.environ.get('Q_BUSINESS_APP_ID', '031c3f4d-bc75-441c-9f2f-0f5ec61d794e')
        
        # Prepare the request parameters
        request_params = {
            'applicationId': application_id,
            'userMessage': json.dumps({
                "content": {
                    "text": query
                }
            })
        }
        
        # Include conversation_id and parentMessageId if provided
        if conversation_id:
            request_params['conversationId'] = conversation_id
            logger.info(f"Using existing conversation ID: {conversation_id}")
        else:
            logger.info("Starting new conversation (no conversation ID provided)")
            
        if parent_message_id:
            request_params['parentMessageId'] = parent_message_id
            logger.info(f"Using parent message ID: {parent_message_id}")
        
        # Call Q Business using chat_sync API
        response = q_business_client.chat_sync(**request_params)
        logger.info(f"Q Business response type: {type(response)}")
        
        # Get the conversation ID and system message ID for future use
        returned_conversation_id = response.get('conversationId')
        logger.info(f"Received conversation ID from response: {returned_conversation_id}")
        
        # Process the chat response
        search_results = []
        if 'systemMessage' in response and 'content' in response['systemMessage']:
            search_results.append({
                'title': 'Q Business Response',
                'excerpt': response['systemMessage']['content'].get('text', ''),
                'source': 'Q Business Chat'
            })
            
            # Add source attributions if available
            if 'sourceAttributions' in response:
                for i, source in enumerate(response['sourceAttributions']):
                    search_results.append({
                        'title': source.get('title', f'Source {i+1}'),
                        'excerpt': source.get('snippet', ''),
                        'document_id': source.get('url', ''),
                        'source': 'Q Index'
                    })
        
        return search_results, returned_conversation_id, parent_message_id
    except Exception as e:
        import traceback
        logger.error(f"Error calling Q Business chat_sync: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        # Return empty results if Q Business access fails
        return [], conversation_id, None

def generate_llm_response(query, q_index_results, mongodb_results):
    """
    Generate a response using an LLM with Q Index and MongoDB results as context
    """
    try:
        # Get the model ID from environment variables or use default
        model_id = os.environ.get('LLM_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
        
        # Prepare context from Q Index results
        q_index_context = ""
        if q_index_results:
            q_index_context = "Information from Q Index:\n\n"
            for result in q_index_results:
                q_index_context += f"Title: {result.get('title', 'No title')}\n"
                q_index_context += f"Content: {result.get('excerpt', 'No content')}\n\n"
        
        # Prepare context from MongoDB results
        mongodb_context = ""
        if mongodb_results:
            mongodb_context = "Information from MongoDB:\n\n"
            for i, result in enumerate(mongodb_results):
                mongodb_context += f"Document {i+1}:\n"
                for key, value in result.items():
                    if key != '_id':  # Skip the ID field
                        mongodb_context += f"{key}: {value}\n"
                mongodb_context += "\n"
        
        # Combine contexts
        combined_context = q_index_context + mongodb_context
        
        # Create prompt for the LLM
        prompt = f"""
You are an AI assistant that helps users find information about countries and travel destinations. 
You have access to data from both Q Index (which contains information from the CIA World Factbook) 
and a MongoDB database with additional travel information.

Based on the following context, please provide a comprehensive answer to the user's query.
If the information in the context is insufficient, acknowledge this and provide the best answer you can.

USER QUERY: {query}

CONTEXT:
{combined_context}

Please provide a well-structured, informative response that addresses the user's query directly.
"""
        
        # Call Amazon Bedrock to generate a response
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read().decode('utf-8'))
        llm_response = response_body['content'][0]['text']
        
        return llm_response
    except Exception as e:
        logger.error(f"Error generating LLM response: {e}")
        return "I'm sorry, I couldn't generate a response based on the available information. Please try a different query or check the system logs for more details."
