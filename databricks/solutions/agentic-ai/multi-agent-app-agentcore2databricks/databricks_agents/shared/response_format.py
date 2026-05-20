"""
Structured output schemas shared between Databricks agents.
These define the JSON format that agents return to the AgentCore Supervisor.
"""

ANALYST_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "sql_queries": {
            "type": "array",
            "items": {"type": "string"},
            "description": "SQL queries that were executed",
        },
        "columns": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Column names in the primary result set",
        },
        "rows": {
            "type": "array",
            "items": {"type": "array"},
            "description": "Result rows (first 100 max)",
        },
        "row_count": {"type": "integer", "description": "Total rows returned"},
        "tables_accessed": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Fully qualified table names accessed",
        },
        "summary": {
            "type": "string",
            "description": "Natural language summary of findings",
        },
    },
    "required": ["sql_queries", "summary", "tables_accessed"],
}

VALIDATOR_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "is_valid": {"type": "boolean", "description": "Whether results passed validation"},
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
            "description": "Confidence level in the results",
        },
        "checks_passed": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Validation checks that passed",
        },
        "checks_failed": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Validation checks that failed",
        },
        "notes": {"type": "string", "description": "Additional context"},
    },
    "required": ["is_valid", "confidence", "checks_passed", "checks_failed"],
}
