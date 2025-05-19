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
        index = os.getenv("ELASTIC_INDEX")
        
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
        result = self.es.index(index=index, document=doc)
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
        
        index = os.getenv("ELASTIC_INDEX")
        
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
            index=index,
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
        index = os.getenv("ELASTIC_INDEX")
        
        # Update only the allowed_roles field
        update_doc = {
            "doc": {
                "allowed_roles": allowed_roles
            }
        }
        
        result = self.es.update(index=index, id=doc_id, body=update_doc)
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
        index = os.getenv("ELASTIC_INDEX")
        
        result = self.es.delete(index=index, id=doc_id)
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
        index = os.getenv("ELASTIC_INDEX")
        
        # Use the update_by_query API
        update_script = {
            "script": {
                "source": "ctx._source.allowed_roles = params.roles",
                "lang": "painless",
                "params": {
                    "roles": allowed_roles
                }
            },
            "query": query
        }
        
        result = self.es.update_by_query(index=index, body=update_script)
        updated_count = result['updated']
        
        print(f"Updated roles for {updated_count} documents")
        return updated_count

# Example usage
if __name__ == "__main__":
    indexer = DocumentIndexer(use_cloud=True)
    
    # Example: Index a text document with RBAC
    doc_id = indexer.index_document(
        title="Student Handbook 2023",
        content="This handbook contains important information for all students...",
        allowed_roles=["student", "faculty", "admin"],
        metadata={"department": "Student Affairs", "year": 2023}
    )
    
    # Example: Update document roles
    indexer.update_document_roles(doc_id, ["student", "admin"])
    
    # Example: Bulk update roles for all documents with "financial" in the content
    query = {
        "match": {
            "attachment.content": "financial"
        }
    }
    indexer.bulk_update_roles(query, ["admin", "finance"])
