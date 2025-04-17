from typing import Any, List, Dict, Optional
import json
import re
import asyncio
from elasticsearch import AsyncElasticsearch
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("elasticsearch_retriever")

# Elasticsearch configuration
ES_CLOUD_ID = ""
ES_API_KEY = ""

# Initialize Elasticsearch client
es_client = AsyncElasticsearch(
    cloud_id=ES_CLOUD_ID,
    api_key=ES_API_KEY
)

# Specify the list of indices to search
SEARCH_INDICES = ["customers"]


@mcp.tool()
async def search_elasticsearch(query: str, top_k: int = 5) -> str:
    """
    Search Elasticsearch indices for information related to the query.
    
    Args:
        query: Natural language question or search query
        top_k: Number of top results to return (default: 5)
    """
    try:
        # Verify that our configured indices exist
        existing_indices = []
        for index in SEARCH_INDICES:
            if await es_client.indices.exists(index=index):
                existing_indices.append(index)
        
        if not existing_indices:
            return f"None of the configured indices {SEARCH_INDICES} exist or are accessible."
        
        # Build a dynamic query based on the index mappings
        search_query = await build_dynamic_query(existing_indices, query)
        search_query["size"] = top_k
        
        # Search only across the indices in our defined list
        results = await es_client.search(
            index=",".join(existing_indices),
            body=search_query,
            _source=True
        )
        
        # Format results
        if results["hits"]["total"]["value"] == 0:
            return f"No results found for query: '{query}' in indices: {', '.join(existing_indices)}"
        
        formatted_results = []
        for hit in results["hits"]["hits"]:
            formatted_result = f"Index: {hit['_index']}\n"
            formatted_result += f"Score: {hit['_score']}\n"
            formatted_result += f"Document ID: {hit['_id']}\n"
            formatted_result += "Document Content:\n"
            
            # Format source content
            source = hit["_source"]
            for key, value in source.items():
                if isinstance(value, (dict, list)):
                    formatted_result += f"{key}: {json.dumps(value, indent=2)}\n"
                else:
                    formatted_result += f"{key}: {value}\n"
            
            formatted_results.append(formatted_result)
        
        return "\n\n---\n\n".join(formatted_results)
    
    except Exception as e:
        return f"Error searching Elasticsearch: {str(e)}\n{traceback.format_exc()}"

async def build_dynamic_query(indices, query_text):
    """
    Dynamically build a query based on the index mappings, handling nested fields automatically.
    """
    # Initialize the bool query structure
    query = {
        "query": {
            "bool": {
                "should": []
            }
        }
    }
    
    # Process each index
    for index in indices:
        # Get the mapping for this index
        mapping = await es_client.indices.get_mapping(index=index)
        
        # Extract the mappings for the current index
        if index in mapping and 'mappings' in mapping[index]:
            index_mappings = mapping[index]['mappings']
            should_clauses = await process_mapping_fields(index_mappings, '', query_text)
            query["query"]["bool"]["should"].extend(should_clauses)
    
    return query

async def process_mapping_fields(mapping, path_prefix, query_text):
    """
    Process all fields in the mapping and create appropriate query clauses.
    Recursively handles nested fields.
    """
    should_clauses = []
    
    # Get all properties from the mapping
    properties = mapping.get('properties', {})
    
    # Process each field
    for field_name, field_config in properties.items():
        field_type = field_config.get('type')
        full_path = f"{path_prefix}.{field_name}" if path_prefix else field_name
        
        # Handle nested fields recursively
        if field_type == 'nested':
            # Add a nested query for this field
            nested_path = full_path
            nested_clauses = await process_mapping_fields(field_config, nested_path, query_text)
            
            # Only add this nested clause if we have subclauses for it
            if nested_clauses:
                nested_query = {
                    "nested": {
                        "path": nested_path,
                        "query": {
                            "bool": {
                                "should": nested_clauses
                            }
                        },
                        "score_mode": "avg"
                    }
                }
                should_clauses.append(nested_query)
        
        # Handle text, keyword fields (searchable)
        elif field_type in ['text', 'keyword']:
            match_query = {
                "match": {
                    full_path: {
                        "query": query_text,
                        "fuzziness": "AUTO" if field_type == 'text' else "0"
                    }
                }
            }
            should_clauses.append(match_query)
        
        # Handle numeric fields for potential matches
        elif field_type in ['long', 'integer', 'short', 'byte', 'double', 'float', 'half_float']:
            # Try to see if the query text is a number
            try:
                numeric_value = float(query_text)
                range_query = {
                    "range": {
                        full_path: {
                            "gte": numeric_value * 0.9,
                            "lte": numeric_value * 1.1
                        }
                    }
                }
                should_clauses.append(range_query)
            except ValueError:
                # Not a number, skip this field
                pass
        
        # Handle date fields
        elif field_type == 'date':
            # Check if the query looks like a date
            if re.search(r'\d{4}-\d{2}-\d{2}', query_text):
                date_query = {
                    "match": {
                        full_path: query_text
                    }
                }
                should_clauses.append(date_query)
    
    # If no field-specific clauses were created, add a multi_match for this level
    if not should_clauses and not path_prefix:
        multi_match_query = {
            "multi_match": {
                "query": query_text,
                "fields": ["*"],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        }
        should_clauses.append(multi_match_query)
    
    return should_clauses

async def close_client():
    """Close Elasticsearch client"""
    await es_client.close()

if __name__ == "__main__":
    try:
        print("Starting Elasticsearch MCP server...")
        # Run the server
        mcp.run(transport='stdio')
    finally:
        asyncio.run(close_client())