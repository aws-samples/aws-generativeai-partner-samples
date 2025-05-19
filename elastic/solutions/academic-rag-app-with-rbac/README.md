# Academic Q&A Chatbot with Elasticsearch API-based RBAC

A Flask-based academic Q&A chatbot that integrates Elasticsearch and Amazon Bedrock with Claude to provide accurate answers from academic documents, with Role-Based Access Control (RBAC) implemented using Elasticsearch security APIs.

## Features

- **Vector Search**: Retrieves the top 3 most relevant academic documents for each query using ELSER sparse embeddings
- **AI-Powered Answers**: Generates concise, contextual responses using Claude through Amazon Bedrock
- **Source Citations**: Includes citations to specific source documents
- **Interactive UI**: Clean interface with collapsible source sections and async request handling
- **Elasticsearch API-based RBAC**: Uses Elasticsearch security APIs for robust role-based access control
- **API Key Authentication**: Secures user sessions with Elasticsearch API keys
- **Admin Panel**: Interface for managing users, roles, and document access
- **Robust Error Handling**: Graceful handling of service unavailability and initialization errors

## Architecture

![Architecture Diagram](static/architecture.png)

This diagram illustrates the architecture of an academic question-answering system that combines Elasticsearch for document retrieval and Amazon Bedrock for generating accurate answers.

1. **User Interface**: A Python Flask front-end provides the interface where users enter their academic questions (shown on the left with a search box).

2. **Document Repository**: The system has bulk-uploaded PDF documents containing academic information (employee handbooks, class registration procedures, university information, career counseling resources, etc.) which are indexed in an Elasticsearch "academic_documents" index.

3. **Search Process**: 
   - When a user submits a question, it's sent to Elasticsearch's Vector Search functionality
   - Elasticsearch retrieves the most relevant results from the academic documents based on user's roles
   - The system combines the user's question with the most relevant document excerpts

4. **Answer Generation**: 
   - The combined information is sent to Amazon Bedrock (Amazon's AI service)
   - Amazon Bedrock processes the question and reference materials using Language Models (LLMs) trained on public datasets
   - The service can be deployed either in public or private hosted environments

5. **Response Delivery**: The system returns "The best answer" to the user, which is contextually accurate based on the academic documents the user has permission to access

## Key Components

- **Elasticsearch**: Handles document storage, vector search capabilities, and RBAC security
- **Amazon Bedrock**: Provides the AI inference capabilities to generate natural language responses
- **Flask**: Powers the front-end web interface for user interaction
- **Vector Search**: Enables semantic understanding of queries rather than just keyword matching
- **Flask-Login**: Handles user authentication and session management
- **Elasticsearch API Keys**: Secures user sessions and enforces role-based permissions

## Project Structure 
- `app_rbac.py`: New improved Flask application with better error handling and RBAC
- `elastic_rbac.py`: Dedicated class for all Elasticsearch RBAC operations
- `search.py`: Elasticsearch integration for academic document search with RBAC filtering
- `bedrock_claude.py`: Amazon Bedrock client for Claude integration
- `models.py`: User model for authentication and role management
- `document_indexer.py`: Utility for indexing documents with role permissions
- `templates/`: HTML templates for the web interface

## Requirements

- Python 3.8+
- Flask
- Flask-Login
- Elasticsearch Python client
- AWS SDK for Python (boto3)
- An Elasticsearch instance with academic_documents index with ELSER
- Amazon Bedrock access with permissions to use Claude models
- Elasticsearch with security features enabled (X-Pack)

## Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone --depth 1 --no-checkout https://github.com/aws-samples aws-generativeai-partner-samples.git
   cd aws-generativeai-partner-samples/
   git sparse-checkout set elastic
   git checkout

   cd solutions/academic-rag-app-with-rbac
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
   - `SECRET_KEY`: Secret key for Flask sessions (generate a random string)


4. **Run the application**:
   
   Original version:
   ```bash
   python app.py
   ```
   
   New improved version with better error handling:
   ```bash
   python app_rbac.py
   ```
   
   The application will be available at `http://localhost:5000`

## RBAC Implementation with Elasticsearch APIs

This application implements Role-Based Access Control (RBAC) using Elasticsearch's native security APIs:

### 1. API Key-Based Authentication

- **API Key Generation**: Each user gets a unique Elasticsearch API key with role metadata
- **Key Validation**: API keys are validated against Elasticsearch's security API
- **Session Management**: Flask-Login integrates with Elasticsearch API keys
- **Automatic Expiration**: API keys can be configured to expire after a set period

### 2. Document-Level Security

- **Role Field Indexing**: Documents are indexed with an `allowed_roles` field
- **Query Filtering**: Search queries include a terms filter on the `allowed_roles` field
- **Access Verification**: Document access is verified using Elasticsearch queries
- **Bulk Role Management**: Roles can be updated in bulk using update_by_query

### 3. Security Benefits

- **Database-Level Security**: Access control is enforced at the database level
- **Scalability**: Elasticsearch's security model is designed to scale
- **Performance**: Role filtering happens efficiently at query time
- **Auditability**: Elasticsearch provides audit logs for security events

## Available Roles

- **student**: Access to general student documents
- **faculty**: Access to faculty and teaching resources
- **admin**: Full access to all documents and admin features
- **researcher**: Access to research papers and data

## Demo Accounts

For testing purposes, the following demo accounts are available:

- Username: `student`, Password: `password123`, Role: Student
- Username: `faculty`, Password: `password123`, Role: Faculty
- Username: `admin`, Password: `password123`, Role: Admin
- Username: `researcher`, Password: `password123`, Role: Researcher
- Username: `superuser`, Password: `password123`, Roles: All roles

## Using the New ElasticRBAC Class

The application now includes an improved `elastic_rbac.py` class for all Elasticsearch RBAC operations:

```python
from elastic_rbac import ElasticRBAC

# Initialize the RBAC service with proper error handling
rbac = ElasticRBAC()

# Check if service is ready before using
if rbac.is_ready():
    # Create index mapping if it doesn't exist
    rbac.create_document_mapping()
    
    # Index a document with role permissions
    doc_id = rbac.index_document(
        title="Student Handbook 2023",
        content="This handbook contains important information for all students...",
        allowed_roles=["student", "faculty", "admin"],
        metadata={"department": "Student Affairs", "year": 2023}
    )
    
    # Create API key for a user
    api_key_info = rbac.create_user_api_key("student_user", ["student"])
    if api_key_info:
        print(f"API Key: {api_key_info['encoded_api_key']}")
    
    # Validate an API key
    user_info = rbac.validate_api_key("api_key_id")
    if user_info and user_info["valid"]:
        print(f"Valid API key for user: {user_info['username']}")
        print(f"Roles: {user_info['roles']}")
    
    # Search documents with RBAC filtering
    search_results, formatted_results = rbac.search_documents(
        "academic policies", 
        user_roles=["student"]
    )
    
    # Verify document access
    has_access = rbac.verify_document_access("document_id", ["student"])
else:
    print("Elasticsearch service is not available")
```

## Original Document Indexer

The application still includes the original `document_indexer.py` utility for backward compatibility:

## API Usage

The chatbot provides a simple API endpoint that respects RBAC permissions:

```
POST /api/ask
Content-Type: application/json
Authorization: ApiKey {encoded_api_key}

{
  "question": "What are the recent advances in RAG?"
}
```

Response:
```json
{
  "answer": "Claude's response based on accessible documents...",
  "sources": [
    {
      "id": "doc123",
      "title": "Document Title",
      "content": "Document content...",
      "score": 0.87,
      "created_on": "2023-09-15T14:30:00Z",
      "updated_at": "2023-10-20T09:45:00Z",
      "allowed_roles": ["student", "faculty"]
    },
    ...
  ]
}
```

## Security Considerations

For production environments, consider these additional security enhancements:

1. **API Key Storage**: Store API keys securely, not in memory
2. **Database Integration**: Replace the mock user database with a real database
3. **HTTPS**: Ensure all communication is encrypted with HTTPS
4. **Rate Limiting**: Implement rate limiting to prevent abuse
5. **Audit Logging**: Enable Elasticsearch audit logging for security monitoring
6. **Role Mapping**: Use Elasticsearch role mappings for more granular permissions
