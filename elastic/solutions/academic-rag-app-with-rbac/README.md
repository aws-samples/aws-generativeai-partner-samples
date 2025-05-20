# Academic Q&A Chatbot with RBAC

A Flask-based academic Q&A chatbot that integrates Elasticsearch and Amazon Bedrock with Claude to provide accurate answers from academic documents, with Role-Based Access Control (RBAC) for document security.

## Features

- **Vector Search**: Retrieves the top 3 most relevant academic documents for each query using ELSER sparse embeddings
- **AI-Powered Answers**: Generates concise, contextual responses using Claude through Amazon Bedrock
- **Source Citations**: Includes citations to specific source documents
- **Interactive UI**: Clean interface with collapsible source sections and async request handling
- **Role-Based Access Control**: Restricts document access based on user roles
- **User Authentication**: Login system with role-based permissions
- **Admin Panel**: Interface for managing users, roles, and document access

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

- **Elasticsearch**: Handles document storage, vector search capabilities, and document filtering
- **Amazon Bedrock**: Provides the AI inference capabilities to generate natural language responses
- **Flask**: Powers the front-end web interface for user interaction
- **Vector Search**: Enables semantic understanding of queries rather than just keyword matching
- **Flask-Login**: Handles user authentication and session management
- **RBAC**: Restricts document access based on user roles

## Project Structure 
- `app.py`: Flask web application with authentication and RBAC
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
   - `CLAUDE_MODEL_ID`: Claude model ID (default: anthropic.claude-3-7-sonnet-20250219-v1:0)
   - `SECRET_KEY`: Secret key for Flask sessions (generate a random string)


4. **Run the application**:
   ```bash
   python app.py
   ```
   The application will be available at `http://localhost:5000`

## RBAC Implementation

The application implements Role-Based Access Control (RBAC) with the following features:

### 1. User Authentication System

- **Flask-Login Integration**: Secure user authentication and session management
- **User Model**: Custom User class with role management capabilities
- **Login/Logout Flow**: Complete authentication workflow with session handling
- **Protected Routes**: Routes requiring authentication are properly protected

### 2. Role-Based Document Access

- **Document Role Tagging**: Each document in Elasticsearch has an `allowed_roles` field
- **Query Filtering**: Search queries automatically filter results based on user roles
- **Access Verification**: Additional verification when accessing specific documents
- **Role-Required Decorator**: Custom decorator to protect routes based on roles

### 3. Admin Features

- **Admin Panel**: Special interface for administrators to manage the system
- **User Management**: Interface for creating, editing, and deleting users
- **Role Management**: Tools for defining and assigning roles
- **Document Access Control**: Interface for setting document permissions

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

## Using the Document Indexer

The application includes a `document_indexer.py` utility for adding documents with role permissions:

```python
from document_indexer import DocumentIndexer

# Initialize the indexer
indexer = DocumentIndexer()

# Index a document with role permissions
indexer.index_document(
    title="Student Handbook 2023",
    content="This handbook contains important information for all students...",
    allowed_roles=["student", "faculty", "admin"]
)

# Index a PDF document with role permissions
indexer.index_pdf_document(
    file_path="path/to/document.pdf",
    allowed_roles=["faculty", "admin"],
    title="Faculty Guidelines"
)

# Update permissions for an existing document
indexer.update_document_roles("document_id", ["admin", "researcher"])

# Bulk update permissions for documents matching a query
query = {
    "match": {
        "attachment.content": "financial"
    }
}
indexer.bulk_update_roles(query, ["admin", "finance"])
```

## API Usage

The chatbot provides a simple API endpoint that respects RBAC permissions:

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
  "answer": "Claude's response based on accessible documents...",
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

## Security Considerations

For production environments, consider these additional security enhancements:

1. **Password Hashing**: Implement password hashing using a library like Flask-Bcrypt
2. **Database Integration**: Replace the mock user database with a real database
3. **JWT Authentication**: Consider using JWT for API authentication
4. **HTTPS**: Ensure all communication is encrypted with HTTPS
5. **Rate Limiting**: Implement rate limiting to prevent abuse
6. **Audit Logging**: Add logging for authentication and document access events
