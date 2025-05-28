import os
import boto3
import json

def lambda_handler(event, context):
    bedrock_agent = boto3.client('bedrock-agent-runtime')
    bedrock = boto3.client('bedrock')
    
    # Get environment variables
    knowledge_base_id = os.environ['KNOWLEDGE_BASE_ID']
    data_source_id = os.environ['DATA_SOURCE_ID']
    
    try:
        # Start ingestion job for the data source
        response = bedrock.start_ingestion_job(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id,
            description='Refresh knowledge base after S3 update'
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Successfully started ingestion job',
                'jobId': response['ingestionJobId']
            })
        }
    except Exception as e:
        print(f"Error starting ingestion job: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Error starting ingestion job: {str(e)}'
            })
        }