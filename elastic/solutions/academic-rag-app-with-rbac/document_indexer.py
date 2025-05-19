import os
import json
import base64
from datetime import datetime
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DocumentIndexer:
    """
    Utility class for indexing documents with RBAC information in Elasticsearch.
    Uses Elasticsearch APIs directly for role-based access control.
    """
    
    def __init__(self, use_cloud=True):
        """
        Initialize the Elasticsearch client.
        
        Args:
            use_cloud: Boolean to determine if cloud or local instance should be used
        """
        if use_cloud:
            # Use environment variables for cloud credentials
            cloud_id = os.getenv("ELASTIC_CLOUD_ID")
            api_key = os.getenv("ELASTIC_API_KEY")
            
            if not cloud_id or not api_key:
                raise ValueError("ELASTIC_CLOUD_ID and ELASTIC_API_KEY must be set in .env file or environment variables")
            
            self.es = Elasticsearch(
                cloud_id=cloud_id,
                api_key=api_key
            )
        else:
            # For local development
            self.es = Elasticsearch(hosts=["http://localhost:9200"])
        
        # Verify connection
        try:
            client_info = self.es.info()
            print('Connected to Elasticsearch!')
            print(f"Elasticsearch version: {client_info.body['version']['number']}")
        except Exception as e:
            print(f"Error connecting to Elasticsearch: {e}")
            raise
        
        self.index_name = os.getenv("ELASTIC_INDEX")
    
    def create_document_mapping(self):
        """Create mapping for academic documents with RBAC fields"""
        mapping = {
            "mappings": {
                "properties": {
                    "title": {"type": "text"},
                    "content": {"type": "text"},
                    "allowed_roles": {"type": "keyword"},  # Using keyword for exact matching
                    "created_on": {"type": "date"},
                    "updated_at": {"type": "date"},
                    "semantic_content": {
                        "type": "nested",
                        "properties": {
                            "inference": {
                                "type": "nested",
                                "properties": {
                                    "chunks": {
                                        "type": "nested",
                                        "properties": {
                                            "text": {"type": "text"},
                                            "embeddings": {
                                                "type": "sparse_vector"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        # Check if index exists
        if not self.es.indices.exists(index=self.index_name):
            self.es.indices.create(index=self.index_name, body=mapping)
            return f"Index {self.index_name} created with RBAC mapping"
        else:
            return f"Index {self.index_name} already exists"
    
    def index_document(self, title, content, allowed_roles, file_path=None, metadata=None):
        """
        Index a document with RBAC information.
        
        Args:
            title: Document title
            content: Document content text
            allowed_roles: List of roles allowed to access this document
            file_path: Optional path to the original file
            metadata: Optional additional metadata
            
        Returns:
            Document ID
        """
        # Prepare document with RBAC information
        doc = {
            "attachment": {
                "title": title,
                "content": content,
                "date": datetime.now().isoformat(),
                "modified": datetime.now().isoformat()
            },
            "allowed_roles": allowed_roles,
            "indexed_at": datetime.now().isoformat()
        }
        
        # Add file information if provided
        if file_path:
            doc["file_path"] = file_path
            doc["file_name"] = os.path.basename(file_path)
        
        # Add additional metadata if provided
        if metadata:
            doc["metadata"] = metadata
        
        # Index the document
        result = self.es.index(index=self.index_name, document=doc)
        print(f"Document indexed with ID: {result['_id']}")
        
        return result['_id']
    
    def index_pdf_document(self, file_path, allowed_roles, title=None, metadata=None):
        """
        Index a PDF document with RBAC information.
        
        Args:
            file_path: Path to the PDF file
            allowed_roles: List of roles allowed to access this document
            title: Optional document title (defaults to filename)
            metadata: Optional additional metadata
            
        Returns:
            Document ID
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Use filename as title if not provided
        if not title:
            title = os.path.basename(file_path)
        
        # Read PDF file as base64
        with open(file_path, 'rb') as file:
            pdf_content = base64.b64encode(file.read()).decode('utf-8')
        
        # Prepare document with PDF content and RBAC information
        doc = {
            "data": pdf_content,
            "allowed_roles": allowed_roles,
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "indexed_at": datetime.now().isoformat()
        }
        
        # Add title if provided
        if title:
            doc["title"] = title
        
        # Add additional metadata if provided
        if metadata:
            doc["metadata"] = metadata
        
        # Use the ingest attachment processor pipeline
        result = self.es.index(
            index=self.index_name,
            pipeline="attachment",
            document=doc
        )
        
        print(f"PDF document indexed with ID: {result['_id']}")
        return result['_id']
    
    def update_document_roles(self, doc_id, allowed_roles):
        """
        Update the allowed roles for a document.
        
        Args:
            doc_id: Document ID
            allowed_roles: New list of allowed roles
            
        Returns:
            Update result
        """
        # Update only the allowed_roles field
        update_doc = {
            "doc": {
                "allowed_roles": allowed_roles,
                "updated_at": datetime.now().isoformat()
            }
        }
        
        result = self.es.update(index=self.index_name, id=doc_id, body=update_doc)
        print(f"Updated roles for document {doc_id}: {allowed_roles}")
        
        return result
    
    def delete_document(self, doc_id):
        """
        Delete a document by ID.
        
        Args:
            doc_id: Document ID to delete
            
        Returns:
            Delete result
        """
        result = self.es.delete(index=self.index_name, id=doc_id)
        print(f"Deleted document {doc_id}")
        
        return result
    
    def bulk_update_roles(self, query, allowed_roles):
        """
        Update allowed roles for multiple documents matching a query.
        
        Args:
            query: Elasticsearch query to match documents
            allowed_roles: New list of allowed roles
            
        Returns:
            Number of documents updated
        """
        # Use the update_by_query API
        update_script = {
            "script": {
                "source": "ctx._source.allowed_roles = params.roles; ctx._source.updated_at = params.updated_at",
                "lang": "painless",
                "params": {
                    "roles": allowed_roles,
                    "updated_at": datetime.now().isoformat()
                }
            },
            "query": query
        }
        
        result = self.es.update_by_query(index=self.index_name, body=update_script)
        updated_count = result['updated']
        
        print(f"Updated roles for {updated_count} documents")
        return updated_count
    
    def create_user_api_key(self, username, roles):
        """
        Create an Elasticsearch API key for a user with specific roles.
        
        Args:
            username: Username for the API key
            roles: List of roles to assign
            
        Returns:
            Dictionary with API key information
        """
        # Create API key with role information in metadata
        api_key_body = {
            "name": f"user_{username}_key",
            "expiration": "30d",  # 30 days expiration
            "metadata": {
                "username": username,
                "roles": roles
            }
        }
        
        response = self.es.security.create_api_key(body=api_key_body)
        
        # Encode the API key for client use
        encoded_api_key = base64.b64encode(
            f"{response['id']}:{response['api_key']}".encode('utf-8')
        ).decode('utf-8')
        
        return {
            "id": response["id"],
            "encoded_api_key": encoded_api_key,
            "username": username,
            "roles": roles
        }
    
    def validate_api_key(self, api_key_id):
        """
        Validate an API key and extract user roles from metadata.
        
        Args:
            api_key_id: ID of the API key to validate
            
        Returns:
            Dictionary with user information or None if invalid
        """
        try:
            # Get API key information
            api_key_info = self.es.security.get_api_key(id=api_key_id)
            
            if not api_key_info["api_keys"]:
                return None
            
            key_info = api_key_info["api_keys"][0]
            
            # Check if key is enabled and not expired
            if not key_info["enabled"]:
                return None
            
            # Extract user information from metadata
            metadata = key_info.get("metadata", {})
            username = metadata.get("username")
            roles = metadata.get("roles", [])
            
            return {
                "username": username,
                "roles": roles,
                "valid": True
            }
        except Exception as e:
            print(f"Error validating API key: {e}")
            return None

# Example usage
if __name__ == "__main__":
    indexer = DocumentIndexer(use_cloud=True)
    
    # Create index mapping if it doesn't exist
    indexer.create_document_mapping()
    
    # Example: Index a text document with RBAC
    doc_id = indexer.index_document(
        title="Student Handbook 2023",
        content="This handbook contains important information for all students...",
        allowed_roles=["student", "faculty", "admin"],
        metadata={"department": "Student Affairs", "year": 2023}
    )
    
    # Example: Create API key for a user
    api_key = indexer.create_user_api_key("student_user", ["student"])
    print(f"API Key for student_user: {api_key['encoded_api_key']}")
