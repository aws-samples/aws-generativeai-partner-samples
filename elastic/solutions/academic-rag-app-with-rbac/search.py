import os
import json
import base64
from typing import Dict, List, Any, Optional
from pprint import pprint
from datetime import datetime
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import bedrock_claude

load_dotenv()

class Search:
    """
    Elasticsearch client for academic document search with RBAC.
    Interfaces with an existing 'academic_documents' index with ELSER sparse embeddings.
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
        
        try:
            client_info = self.es.info()
            print('Connected to Elasticsearch!')
            pprint(client_info.body)
        except Exception as e:
            print(f"Error connecting to Elasticsearch: {e}")
            raise

    def create_document_mapping(self):
        """Create mapping for academic documents with RBAC fields"""
        index = os.getenv("ELASTIC_INDEX")
        
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
        if not self.es.indices.exists(index=index):
            self.es.indices.create(index=index, body=mapping)
            return f"Index {index} created with RBAC mapping"
        else:
            return f"Index {index} already exists"

    def search(self, query: str, user_roles=None, size: int = 3) -> Dict[str, Any]:
        """
        Search the academic documents index using ELSER sparse embeddings with RBAC filtering.
        
        Args:
            query: The user's search query
            user_roles: List of user roles for RBAC filtering
            size: Number of results to return (default: 3)
            
        Returns:
            Dictionary containing search results
        """
        index = os.getenv("ELASTIC_INDEX")
        
        # Build query with ELSER sparse embeddings
        es_query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "nested": {
                                "path": "semantic_content.inference.chunks",
                                "query": {
                                    "sparse_vector": {
                                        "inference_id": ".elser-2-elasticsearch",
                                        "field": "semantic_content.inference.chunks.embeddings",
                                        "query": query
                                    }
                                },
                                "inner_hits": {
                                    "size": 2,
                                    "name": index + ".semantic_content",
                                    "_source": [
                                        "semantic_content.inference.chunks.text"
                                    ]
                                }
                            }
                        }
                    ]
                }
            },
            "size": size
        }
        
        # Add RBAC filtering if user roles are provided
        if user_roles:
            es_query["query"]["bool"]["filter"] = [
                {
                    "terms": {
                        "allowed_roles": user_roles
                    }
                }
            ]
        
        # Execute search
        results = self.es.search(index=index, body=es_query)
        result = results["hits"]["hits"]
        return results, result

    def verify_document_access(self, doc_id, user_roles):
        """
        Verify if user has access to a specific document.
        
        Args:
            doc_id: Document ID to check
            user_roles: List of user roles
            
        Returns:
            Boolean indicating if user has access
        """
        index = os.getenv("ELASTIC_INDEX")
        
        # Query to check if document exists and user has access
        query = {
            "query": {
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
        }
        
        results = self.es.search(index=index, body=query)
        
        # If we found a document, user has access
        return results["hits"]["total"]["value"] > 0

    def retrieve_document(self, doc_id: str, user_roles=None) -> Dict[str, Any]:
        """
        Retrieve a specific document by ID with RBAC check.
        
        Args:
            doc_id: The document ID to retrieve
            user_roles: List of user roles for RBAC check
            
        Returns:
            Dictionary containing the document data
        """
        index = os.getenv("ELASTIC_INDEX")
        
        # First get the document
        document = self.es.get(index=index, id=doc_id)
        
        # If user_roles provided, check access
        if user_roles:
            allowed_roles = document["_source"].get("allowed_roles", [])
            
            # Check if user has any of the required roles
            has_access = any(role in allowed_roles for role in user_roles)
            
            if not has_access:
                raise PermissionError(f"User does not have access to document {doc_id}")
        
        return document

    def clean_text(self, text):
        """Remove newlines, tabs, and empty strings from text."""
        for char in ['\\n', '\n', '\\t', '\t', '', '']:
            text = text.replace(char, '')
        return text

    def format_search_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Format search results into a structured list of sources.
        
        Args:
            results: Raw Elasticsearch results
            
        Returns:
            List of formatted source documents with metadata
        """
        sources = []
        
        # Extract hits from the response
        hits = results.get('hits', {}).get('hits', [])
        for hit in hits:
            # Extract document metadata
            source = hit.get('_source', {})
            score = hit.get('_score', 0)

            # Get document content
            content = ""
            try:
                # Try to get content from chunks first
                content = source.get('semantic_content', {}).get('inference', {}).get('chunks', [{}])[0].get('text', '')
                content = "".join(content.splitlines())
            except (IndexError, AttributeError):
                # Fallback to attachment content if chunks aren't available
                content = source.get('attachment', {}).get('content', '')
            content = self.clean_text(content) # removes /n /t and other characters

            # Format the source document
            formatted_source = {
                'id': hit.get('_id', ''),
                'title': source.get('attachment', {}).get('title', 'Untitled Document'),
                'content': content,
                'score': score,
                'created_on': source.get('attachment', {}).get('date', {}),
                'updated_at': source.get('attachment', {}).get('modified', {}),
                'allowed_roles': source.get('allowed_roles', [])
            }

            sources.append(formatted_source)
        return sources

    def create_bedrock_prompt(result):
        index = os.getenv("ELASTIC_INDEX")
        index_source_fields = {
            index: [
                "semantic_content"
            ]
        }
        context = ""
        for hit in result:
            inner_hit_path = f"{hit['_index']}.{index_source_fields.get(hit['_index'])[0]}"
            ## For semantic_text matches, we need to extract the text from the inner_hits
            if 'inner_hits' in hit and inner_hit_path in hit['inner_hits']:
                context += '\n --- \n'.join(
                    inner_hit['_source']['text'] for inner_hit in hit['inner_hits'][inner_hit_path]['hits']['hits'])

            else:
                source_field = index_source_fields.get(hit["_index"])[0]
                hit_context = hit["_source"][source_field]
                context += f"{hit_context}\n"
            context = context.replace('\\n', '')
            context = context.replace('\n', '')

        prompt = f"""Instructions:
  - You are an assistant for question-answering tasks.
  - Answer questions truthfully and factually using only the context presented.
  - If you don't know the answer, just say that you don't know, don't make up an answer.
  - You must always cite the document where the answer was extracted using inline academic citation style [], using the position.
  - Use markdown format for code examples.
  - You are correct, factual, precise, and reliable.

          Context:
          {context}
          """

        return prompt
        
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
