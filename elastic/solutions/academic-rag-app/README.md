# Academic Q&A Chatbot

A Flask-based academic Q&A chatbot that integrates Elasticsearch and AWS Bedrock with Claude to provide accurate answers from academic documents.

## Features

- **Vector Search**: Retrieves the top 3 most relevant academic documents for each query using ELSER sparse embeddings
- **AI-Powered Answers**: Generates concise, contextual responses using Claude through AWS Bedrock
- **Source Citations**: Includes citations to specific source documents
- **Interactive UI**: Clean interface with collapsible source sections and async request handling


## Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone --depth 1 --no-checkout https://github.com/aws-samples aws-generativeai-partner-samples.git
   cd aws-generativeai-partner-samples/
   git sparse-checkout set elastic
   git checkout

   cd solutions/acamedic-rag-app
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:<br>
Copy .env.example & save as .env: `cp .env.example .env` (then edit with your credentials)
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your Elasticsearch and AWS credentials.
    #### Environment Configuration
    The following environment variables need to be configured:
   - `ELASTIC_CLOUD_ID`: Your Elasticsearch Cloud ID
   - `ELASTIC_API_KEY`: Your Elasticsearch API key
   - `USE_ELASTIC_CLOUD`: Set to "true" for cloud or "false" for local Elasticsearch
   - `ELASTIC_INDEX`: academic_documents
   - `AWS_REGION`: AWS region (e.g., us-east-1)
   - `AWS_ACCESS_KEY_ID`: Your AWS access key
   - `AWS_SECRET_ACCESS_KEY`: Your AWS secret access key
   - `CLAUDE_MODEL_ID`: Claude model ID (default: anthropic.claude-3-sonnet-20240229-v1:0)


4. **Run the application**:
   ```bash
   python app.py
   ```
   The application will be available at `http://localhost:5000`


## Project Architecture
- `app.py`: Flask web application
- `search.py`: Elasticsearch integration for academic document search
- `bedrock_claude.py`: AWS Bedrock client for Claude integration
- `templates/`: HTML templates for the web interface

## API Usage

The chatbot provides a simple API endpoint:

```
POST /api/ask
Content-Type: application/json

{
  "question": "What are the recent advances in RAG?"
}
```

Response:
```json
{
  "answer": "Claude's response...",
  "sources": [
    {
      "id": "doc123",
      "title": "Document Title",
      "content": "Document content...",
      "score": 0.87,
      "created_on": "2023-09-15T14:30:00Z",
      "updated_at": "2023-10-20T09:45:00Z"
    },
    ...
  ]
}
```

## Requirements

- Python 3.8+
- Flask
- Elasticsearch Python client
- AWS SDK for Python (boto3)
- An Elasticsearch instance with academic_documents index with ELSER
- AWS Bedrock access with permissions to use Claude models