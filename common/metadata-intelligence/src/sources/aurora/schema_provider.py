"""Database schema context provider for natural language to SQL generation."""

from typing import Dict, Any, List, Optional
import logging
from .connection import AuroraConnection

logger = logging.getLogger(__name__)


class SchemaProvider:
    """Provides comprehensive database schema context for SQL generation."""
    
    def __init__(self, connection: AuroraConnection):
        self.connection = connection
        self._schema_cache = None
        self._cache_timestamp = None
    
    async def get_schema_context(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get comprehensive schema context for SQL generation.
        
        Args:
            force_refresh: Force refresh of cached schema data
            
        Returns:
            Dictionary containing tables, columns, relationships, and sample data
        """
        if self._schema_cache is None or force_refresh:
            logger.info("Building comprehensive schema context...")
            
            try:
                # Get basic table information
                tables = await self._get_tables_with_columns()
                
                # Get foreign key relationships
                relationships = await self._get_foreign_key_relationships()
                
                # Get table sizes and sample data
                table_stats = await self._get_table_statistics()
                
                # Build comprehensive context
                self._schema_cache = {
                    "database_type": "PostgreSQL",
                    "tables": tables,
                    "relationships": relationships,
                    "statistics": table_stats,
                    "total_tables": len(tables),
                    "schema_summary": self._build_schema_summary(tables, relationships)
                }
                
                logger.info(f"Schema context built: {len(tables)} tables, {len(relationships)} relationships")
                
            except Exception as e:
                logger.error(f"Failed to build schema context: {str(e)}")
                # Return minimal context on error
                self._schema_cache = {
                    "database_type": "PostgreSQL",
                    "tables": {},
                    "relationships": [],
                    "statistics": {},
                    "error": str(e)
                }
        
        return self._schema_cache
    
    async def _get_tables_with_columns(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed table and column information."""
        query = """
        SELECT 
            t.schemaname,
            t.tablename,
            c.column_name,
            c.data_type,
            c.is_nullable,
            c.column_default,
            c.character_maximum_length,
            c.numeric_precision,
            c.numeric_scale,
            c.ordinal_position,
            CASE 
                WHEN pk.column_name IS NOT NULL THEN true 
                ELSE false 
            END as is_primary_key
        FROM pg_tables t
        JOIN information_schema.columns c 
            ON c.table_schema = t.schemaname 
            AND c.table_name = t.tablename
        LEFT JOIN (
            SELECT 
                kcu.table_schema,
                kcu.table_name,
                kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
        ) pk ON pk.table_schema = c.table_schema 
            AND pk.table_name = c.table_name 
            AND pk.column_name = c.column_name
        WHERE t.schemaname NOT IN ('information_schema', 'pg_catalog')
        ORDER BY t.schemaname, t.tablename, c.ordinal_position
        """
        
        rows = await self.connection.execute_query(query)
        
        tables = {}
        for row in rows:
            schema_table = f"{row['schemaname']}.{row['tablename']}"
            
            if schema_table not in tables:
                tables[schema_table] = {
                    "schema": row['schemaname'],
                    "name": row['tablename'],
                    "columns": []
                }
            
            column_info = {
                "name": row['column_name'],
                "data_type": row['data_type'],
                "is_nullable": row['is_nullable'] == 'YES',
                "is_primary_key": row['is_primary_key'],
                "default_value": row['column_default'],
                "max_length": row['character_maximum_length'],
                "precision": row['numeric_precision'],
                "scale": row['numeric_scale'],
                "position": row['ordinal_position']
            }
            
            tables[schema_table]["columns"].append(column_info)
        
        return tables
    
    async def _get_foreign_key_relationships(self) -> List[Dict[str, Any]]:
        """Get foreign key relationships between tables."""
        query = """
        SELECT
            tc.constraint_name,
            tc.table_schema as source_schema,
            tc.table_name as source_table,
            kcu.column_name as source_column,
            ccu.table_schema as target_schema,
            ccu.table_name as target_table,
            ccu.column_name as target_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu 
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema NOT IN ('information_schema', 'pg_catalog')
        ORDER BY tc.table_schema, tc.table_name
        """
        
        rows = await self.connection.execute_query(query)
        
        relationships = []
        for row in rows:
            relationships.append({
                "constraint_name": row['constraint_name'],
                "source_table": f"{row['source_schema']}.{row['source_table']}",
                "source_column": row['source_column'],
                "target_table": f"{row['target_schema']}.{row['target_table']}",
                "target_column": row['target_column']
            })
        
        return relationships
    
    async def _get_table_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get table row counts and basic statistics."""
        try:
            # Get table sizes
            query = """
            SELECT 
                schemaname,
                tablename,
                n_tup_ins as inserted_rows,
                n_tup_upd as updated_rows,
                n_tup_del as deleted_rows,
                n_live_tup as live_rows,
                n_dead_tup as dead_rows,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze
            FROM pg_stat_user_tables
            ORDER BY n_live_tup DESC
            """
            
            rows = await self.connection.execute_query(query)
            
            stats = {}
            for row in rows:
                table_key = f"{row['schemaname']}.{row['tablename']}"
                stats[table_key] = {
                    "live_rows": row['live_rows'] or 0,
                    "dead_rows": row['dead_rows'] or 0,
                    "inserted_rows": row['inserted_rows'] or 0,
                    "updated_rows": row['updated_rows'] or 0,
                    "deleted_rows": row['deleted_rows'] or 0,
                    "last_analyze": row['last_analyze'],
                    "estimated_size": self._estimate_table_size(row['live_rows'] or 0)
                }
            
            return stats
            
        except Exception as e:
            logger.warning(f"Could not retrieve table statistics: {str(e)}")
            return {}
    
    def _estimate_table_size(self, row_count: int) -> str:
        """Estimate table size category based on row count."""
        if row_count == 0:
            return "empty"
        elif row_count < 100:
            return "tiny"
        elif row_count < 10000:
            return "small"
        elif row_count < 1000000:
            return "medium"
        else:
            return "large"
    
    def _build_schema_summary(self, tables: Dict[str, Any], relationships: List[Dict[str, Any]]) -> str:
        """Build a human-readable summary of the database schema."""
        summary_parts = []
        
        # Table summary
        table_count = len(tables)
        summary_parts.append(f"Database contains {table_count} tables")
        
        # Column count
        total_columns = sum(len(table['columns']) for table in tables.values())
        summary_parts.append(f"Total columns: {total_columns}")
        
        # Relationship summary
        if relationships:
            summary_parts.append(f"Foreign key relationships: {len(relationships)}")
        
        # Main tables (those with most columns or relationships)
        if tables:
            sorted_tables = sorted(
                tables.items(), 
                key=lambda x: len(x[1]['columns']), 
                reverse=True
            )
            main_tables = [name.split('.')[-1] for name, _ in sorted_tables[:3]]
            summary_parts.append(f"Main tables: {', '.join(main_tables)}")
        
        return ". ".join(summary_parts) + "."
    
    def get_schema_prompt_context(self, schema_context: Dict[str, Any]) -> str:
        """
        Generate a formatted schema context string for LLM prompts.
        
        Args:
            schema_context: Schema context from get_schema_context()
            
        Returns:
            Formatted string suitable for LLM prompts
        """
        if "error" in schema_context:
            return f"Schema information unavailable: {schema_context['error']}"
        
        context_parts = []
        
        # Database overview
        context_parts.append(f"Database: {schema_context['database_type']}")
        context_parts.append(f"Summary: {schema_context['schema_summary']}")
        context_parts.append("")
        
        # Tables and columns
        context_parts.append("TABLES AND COLUMNS:")
        for table_name, table_info in schema_context["tables"].items():
            table_display_name = table_info["name"]
            context_parts.append(f"\nTable: {table_display_name}")
            
            # Add table stats if available
            if table_name in schema_context.get("statistics", {}):
                stats = schema_context["statistics"][table_name]
                context_parts.append(f"  Size: {stats['estimated_size']} ({stats['live_rows']} rows)")
            
            # Add columns
            context_parts.append("  Columns:")
            for col in table_info["columns"]:
                col_desc = f"    - {col['name']} ({col['data_type']}"
                if col['is_primary_key']:
                    col_desc += ", PRIMARY KEY"
                if not col['is_nullable']:
                    col_desc += ", NOT NULL"
                col_desc += ")"
                context_parts.append(col_desc)
        
        # Relationships
        if schema_context["relationships"]:
            context_parts.append("\nRELATIONSHIPS:")
            for rel in schema_context["relationships"]:
                source_table = rel["source_table"].split(".")[-1]
                target_table = rel["target_table"].split(".")[-1]
                context_parts.append(
                    f"  {source_table}.{rel['source_column']} -> {target_table}.{rel['target_column']}"
                )
        
        return "\n".join(context_parts)
