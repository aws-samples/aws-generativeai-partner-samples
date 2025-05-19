import os
import json
from typing import Dict, List, Any, Optional
from pprint import pprint
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import bedrock_claude

load_dotenv()

class Search:
    """
    Elasticsearch client for academic document search.
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
        
        # Base query with ELSER sparse embeddings
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
            # Add a filter for allowed_roles field
            es_query["query"]["bool"]["filter"] = [
                {
                    "terms": {
                        "allowed_roles": user_roles
                    }
                }
            ]
        
        # Use the newer Elasticsearch client API style (without 'body' parameter)
        results = self.es.search(
            index=index,
            **es_query
        )
        
        result = results["hits"]["hits"]
        return results, result

    def retrieve_document(self, doc_id: str) -> Dict[str, Any]:
        """
        Retrieve a specific document by ID.
        
        Args:
            doc_id: The document ID to retrieve
            
        Returns:
            Dictionary containing the document data
        """
        index = os.getenv("ELASTIC_INDEX")
        return self.es.get(index=index, id=doc_id)

    def clean_text(self, text):
        """Remove newlines, tabs, and empty strings from text."""
        for char in ['\\n', '\n', '\\t', '\t', '', '']:
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
            # print(source.get('updated_at'))

            # Get document content
            content = ""
            try:
                # Try to get content from chunks first
                content = source.get('semantic_content', {}).get('inference', {}).get('chunks', [{}])[0].get('text', '')
                content = "".join(content.splitlines())
            except (IndexError, AttributeError):
                # Fallback to attachment content if chunks aren't available
                content = source.get('attachment', {}).get('content', '')
            content = self.clean_text(content) ## removes /n /t and other characters


            # Format the source document
            formatted_source = {
                'id': hit.get('_id', ''),
                'title': source.get('attachment', {}).get('title', 'Untitled Document'),
                'content': content,
                'score': score,
                'created_on': source.get('attachment', {}).get('date', {}),
                'updated_at': source.get('attachment', {}).get('modified', {})
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
        #print(result['hits']['hits'][0]['_source']['semantic_content']['inference']['chunks'][0]['text'])
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

        #print(prompt)
        return prompt