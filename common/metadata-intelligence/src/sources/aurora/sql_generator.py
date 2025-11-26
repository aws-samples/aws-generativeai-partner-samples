"""Natural language to SQL generation using AWS Bedrock."""

import json
import boto3
from typing import Dict, Any, Optional
import logging
from .schema_provider import SchemaProvider

logger = logging.getLogger(__name__)


class SQLGenerator:
    """Generates SQL queries from natural language using AWS Bedrock."""
    
    def __init__(self, schema_provider: SchemaProvider):
        self.schema_provider = schema_provider
        self.bedrock_client = boto3.client('bedrock-runtime')
        self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"  # Claude 3 Sonnet
        
    async def generate_sql(self, natural_language_query: str) -> Dict[str, Any]:
        """
        Generate SQL from natural language query.
        
        Args:
            natural_language_query: User's natural language query
            
        Returns:
            Dictionary containing generated SQL and metadata
        """
        try:
            # Get database schema context
            schema_context = await self.schema_provider.get_schema_context()
            schema_prompt = self.schema_provider.get_schema_prompt_context(schema_context)
            
            # Build the prompt for the LLM
            prompt = self._build_sql_generation_prompt(natural_language_query, schema_prompt)
            
            # Call Bedrock to generate SQL
            response = await self._call_bedrock(prompt)
            
            # Extract SQL from the response
            sql_result = self._parse_bedrock_response(response)
            
            logger.info(f"Generated SQL for query: '{natural_language_query[:50]}...'")
            
            return {
                "success": True,
                "sql": sql_result["sql"],
                "explanation": sql_result.get("explanation", ""),
                "confidence": sql_result.get("confidence", 0.8),
                "original_query": natural_language_query,
                "schema_used": len(schema_context.get("tables", {})) > 0
            }
            
        except Exception as e:
            logger.error(f"SQL generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "original_query": natural_language_query,
                "sql": None
            }
    
    def _build_sql_generation_prompt(self, user_query: str, schema_context: str) -> str:
        """Build the prompt for SQL generation."""
        
        prompt = f"""You are an expert PostgreSQL query generator. Your task is to convert natural language queries into accurate SQL queries based on the provided database schema.

IMPORTANT GUIDELINES:
1. Generate ONLY valid PostgreSQL SQL queries
2. Use the exact table and column names from the schema
3. Consider data types when writing WHERE clauses
4. Use appropriate JOINs when querying multiple tables
5. Return results that directly answer the user's question
6. Use LIMIT when appropriate to avoid overwhelming results
7. Handle case-insensitive searches with ILIKE when searching text
8. Use proper aggregation functions (COUNT, SUM, AVG) when requested

DATABASE SCHEMA:
{schema_context}

USER QUERY: "{user_query}"

Please respond with a JSON object in this exact format:
{{
    "sql": "your_generated_sql_query_here",
    "explanation": "brief explanation of what the query does",
    "confidence": 0.9,
    "tables_used": ["table1", "table2"]
}}

EXAMPLES:

User: "Show me all customers"
Response: {{"sql": "SELECT * FROM customers LIMIT 100;", "explanation": "Retrieves all customer records with a limit for performance", "confidence": 0.95, "tables_used": ["customers"]}}

User: "How many orders were placed last month?"
Response: {{"sql": "SELECT COUNT(*) FROM orders WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') AND created_at < DATE_TRUNC('month', CURRENT_DATE);", "explanation": "Counts orders placed in the previous month", "confidence": 0.9, "tables_used": ["orders"]}}

User: "Find customers who spent more than $1000"
Response: {{"sql": "SELECT c.*, SUM(o.total_amount) as total_spent FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.id HAVING SUM(o.total_amount) > 1000;", "explanation": "Finds customers with total spending over $1000", "confidence": 0.85, "tables_used": ["customers", "orders"]}}

Now generate the SQL query for the user's request:"""

        return prompt
    
    async def _call_bedrock(self, prompt: str) -> Dict[str, Any]:
        """Call AWS Bedrock to generate SQL."""
        try:
            # Prepare the request body for Claude
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.1,  # Low temperature for consistent, precise responses
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            # Call Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json"
            )
            
            # Parse the response
            response_body = json.loads(response['body'].read())
            
            if 'content' in response_body and len(response_body['content']) > 0:
                return {
                    "success": True,
                    "content": response_body['content'][0]['text']
                }
            else:
                raise Exception("No content in Bedrock response")
                
        except Exception as e:
            logger.error(f"Bedrock API call failed: {str(e)}")
            raise Exception(f"Failed to generate SQL using Bedrock: {str(e)}")
    
    def _parse_bedrock_response(self, bedrock_response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the Bedrock response to extract SQL and metadata."""
        try:
            content = bedrock_response["content"]
            
            # Try to find JSON in the response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                result = json.loads(json_str)
                
                # Validate required fields
                if "sql" not in result:
                    raise ValueError("No SQL found in response")
                
                # Clean up the SQL
                sql = result["sql"].strip()
                if sql.endswith(';'):
                    sql = sql[:-1]  # Remove trailing semicolon for consistency
                
                return {
                    "sql": sql,
                    "explanation": result.get("explanation", ""),
                    "confidence": result.get("confidence", 0.8),
                    "tables_used": result.get("tables_used", [])
                }
            else:
                # Fallback: try to extract SQL from free text
                # Look for SQL patterns in the response
                lines = content.split('\n')
                sql_lines = []
                in_sql = False
                
                for line in lines:
                    line = line.strip()
                    if any(line.upper().startswith(cmd) for cmd in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']):
                        in_sql = True
                        sql_lines.append(line)
                    elif in_sql and (line.endswith(';') or line == ''):
                        if line.endswith(';'):
                            sql_lines.append(line)
                        break
                    elif in_sql:
                        sql_lines.append(line)
                
                if sql_lines:
                    sql = ' '.join(sql_lines).strip()
                    if sql.endswith(';'):
                        sql = sql[:-1]
                    
                    return {
                        "sql": sql,
                        "explanation": "SQL extracted from response",
                        "confidence": 0.7,
                        "tables_used": []
                    }
                else:
                    raise ValueError("Could not extract SQL from response")
                    
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            raise ValueError(f"Invalid JSON response from Bedrock: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to parse Bedrock response: {str(e)}")
            raise ValueError(f"Could not parse SQL from response: {str(e)}")
    
    def validate_sql_syntax(self, sql: str) -> Dict[str, Any]:
        """
        Basic SQL syntax validation.
        
        Args:
            sql: The SQL query to validate
            
        Returns:
            Dictionary with validation results
        """
        try:
            sql = sql.strip()
            
            # Basic validation checks
            validation_results = {
                "valid": True,
                "errors": [],
                "warnings": []
            }
            
            # Check for basic SQL structure
            sql_upper = sql.upper()
            
            # Must start with a valid SQL command
            valid_starts = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH']
            if not any(sql_upper.startswith(cmd) for cmd in valid_starts):
                validation_results["errors"].append("Query must start with a valid SQL command")
                validation_results["valid"] = False
            
            # Check for balanced parentheses
            if sql.count('(') != sql.count(')'):
                validation_results["errors"].append("Unbalanced parentheses")
                validation_results["valid"] = False
            
            # Check for basic SELECT structure if it's a SELECT query
            if sql_upper.startswith('SELECT'):
                if ' FROM ' not in sql_upper:
                    validation_results["warnings"].append("SELECT query without FROM clause")
            
            # Check for potential SQL injection patterns (basic)
            dangerous_patterns = ['--', '/*', '*/', 'EXEC', 'EXECUTE', 'SP_']
            for pattern in dangerous_patterns:
                if pattern in sql_upper:
                    validation_results["warnings"].append(f"Contains potentially dangerous pattern: {pattern}")
            
            # Check for very long queries
            if len(sql) > 5000:
                validation_results["warnings"].append("Query is very long, consider breaking it down")
            
            return validation_results
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
            }
