import os
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import base64
from datetime import datetime

# Load environment variables
load_dotenv()

class ElasticRBAC:
    """
    Handles all Elasticsearch RBAC operations including authentication, 
    document access control, and API key management.
    """
    
    def __init__(self):
        """Initialize the Elasticsearch client with proper error handling."""
        self.es = None
        self.index_name = os.getenv("ELASTIC_INDEX", "academic_documents")
        self.initialized = False
        
        try:
            # Use environment variable to control whether to use cloud or local Elasticsearch
            use_cloud = os.getenv("USE_ELASTIC_CLOUD", "true").lower() == "true"
            
            if use_cloud:
                # Use environment variables for cloud credentials
                cloud_id = os.getenv("ELASTIC_CLOUD_ID")
                api_key = os.getenv("ELASTIC_API_KEY")
                
                if not cloud_id or not api_key:
                    raise ValueError("ELASTIC_CLOUD_ID and ELASTIC_API_KEY must be set")
                
                self.es = Elasticsearch(
                    cloud_id=cloud_id,
                    api_key=api_key
                )
            else:
                # For local development
                self.es = Elasticsearch(hosts=["http://localhost:9200"])
            
            # Verify connection
            info = self.es.info()
            print(f"Connected to Elasticsearch {info.body['version']['number']}")
            self.initialized = True
            
        except Exception as e:
            print(f"Error initializing Elasticsearch: {e}")
    
    def is_ready(self):
        """Check if Elasticsearch client is initialized and ready."""
        return self.initialized and self.es is not None
    
    def create_document_mapping(self):
        """Create mapping for academic documents with RBAC fields."""
        if not self.is_ready():
            return "Elasticsearch not initialized"
            
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
        
        try:
            # Check if index exists
            if not self.es.indices.exists(index=self.index_name):
                self.es.indices.create(index=self.index_name, body=mapping)
                return f"Index {self.index_name} created with RBAC mapping"
            else:
                return f"Index {self.index_name} already exists"
        except Exception as e:
            return f"Error creating index: {e}"
    
    def create_user_api_key(self, username, roles):
        """
        Create an Elasticsearch API key for a user with specific roles.
        
        Args:
            username: Username for the API key
            roles: List of roles to assign
            
        Returns:
            Dictionary with API key information or None if error
        """
        if not self.is_ready():
            return None
            
        try:
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
        except Exception as e:
            print(f"Error creating API key: {e}")
            return None
    
    def validate_api_key(self, api_key_id):
        """
        Validate an API key and extract user roles from metadata.
        
        Args:
            api_key_id: ID of the API key to validate
            
        Returns:
            Dictionary with user information or None if invalid
        """
        if not self.is_ready():
            return None
            
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
    
    def search_documents(self, query_text, user_roles):
        """
        Search for documents with RBAC filtering based on user roles.
        
        Args:
            query_text: The search query text
            user_roles: List of user roles for access control
            
        Returns:
            Tuple of (search_results, formatted_results) or (None, None) if error
        """
        if not self.is_ready():
            return None, None
            
        try:
            # Build query with role-based access control
            query = {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "attachment.content": query_text
                            }
                        }
                    ],
                    "filter": [
                        {
                            "terms": {
                                "allowed_roles": user_roles
                            }
                        }
                    ]
                }
            }
            
            # Execute search with RBAC filtering
            search_results = self.es.search(
                index=self.index_name,
                body={
                    "query": query,
                    "size": 3,  # Return top 3 results
                    "_source": ["attachment.title", "attachment.content", "allowed_roles"]
                }
            )
            
            # Format results for the application
            formatted_results = []
            for hit in search_results["hits"]["hits"]:
                source = hit["_source"]
                formatted_results.append({
                    "id": hit["_id"],
                    "title": source.get("attachment", {}).get("title", "Untitled"),
                    "content": source.get("attachment", {}).get("content", ""),
                    "score": hit["_score"],
                    "allowed_roles": source.get("allowed_roles", [])
                })
            
            return search_results, formatted_results
        except Exception as e:
            print(f"Error searching documents: {e}")
            return None, None
    
    def verify_document_access(self, doc_id, user_roles):
        """
        Verify if a user has access to a specific document.
        
        Args:
            doc_id: Document ID to check
            user_roles: List of user roles
            
        Returns:
            Boolean indicating if user has access
        """
        if not self.is_ready():
            return False
            
        try:
            # Query to check if document exists and user has access
            query = {
                "bool": {
                    "must": [
                        {
                            "ids": {
                                "values": [doc_id]
                            }
                        }
                    ],
                    "filter": [
                        {
                            "terms": {
                                "allowed_roles": user_roles
                            }
                        }
                    ]
                }
            }
            
            # Execute query
            result = self.es.search(
                index=self.index_name,
                body={
                    "query": query,
                    "size": 1
                }
            )
            
            # Check if any results were returned
            return result["hits"]["total"]["value"] > 0
        except Exception as e:
            print(f"Error verifying document access: {e}")
            return False
    
    def retrieve_document(self, doc_id, user_roles):
        """
        Retrieve a document with RBAC check.
        
        Args:
            doc_id: Document ID to retrieve
            user_roles: List of user roles for access control
            
        Returns:
            Document or None if not found or no access
        """
        if not self.is_ready():
            return None
            
        try:
            # First verify access
            if not self.verify_document_access(doc_id, user_roles):
                raise PermissionError("Access denied to this document")
            
            # Retrieve document
            document = self.es.get(index=self.index_name, id=doc_id)
            return document
        except Exception as e:
            print(f"Error retrieving document: {e}")
            return None
    
    def index_document(self, title, content, allowed_roles, metadata=None):
        """
        Index a document with RBAC information.
        
        Args:
            title: Document title
            content: Document content text
            allowed_roles: List of roles allowed to access this document
            metadata: Optional additional metadata
            
        Returns:
            Document ID or None if error
        """
        if not self.is_ready():
            return None
            
        try:
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
            
            # Add additional metadata if provided
            if metadata:
                doc["metadata"] = metadata
            
            # Index the document
            result = self.es.index(index=self.index_name, document=doc)
            return result['_id']
        except Exception as e:
            print(f"Error indexing document: {e}")
            return None