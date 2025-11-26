"""Aurora database connection management."""

import asyncio
import asyncpg
import boto3
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AuroraConnection:
    """Manages connections to Aurora PostgreSQL."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None
        self._connection_string = None
        self._credentials = None
        self.use_data_api = config.get("use_data_api", False)
        self.rds_client = None
        
        if self.use_data_api:
            self.rds_client = boto3.client('rds-data')
            self.cluster_arn = config.get("cluster_arn")
            self.secret_arn = config.get("secret_arn")
            self.database = config.get("database", "postgres")
    
    async def _get_credentials_from_secrets_manager(self) -> Dict[str, str]:
        """Get Aurora credentials from AWS Secrets Manager."""
        secret_arn = self.config.get("secret_arn")
        if not secret_arn:
            # Fallback to direct credentials
            return {
                "username": self.config.get("user", "postgres"),
                "password": self.config.get("password", ""),
                "host": self.config.get("host", "localhost"),
                "port": str(self.config.get("port", 5432)),
                "dbname": self.config.get("database", "postgres")
            }
        
        try:
            session = boto3.Session()
            client = session.client('secretsmanager')
            
            response = client.get_secret_value(SecretId=secret_arn)
            secret = json.loads(response['SecretString'])
            
            return {
                "username": secret.get("username", "postgres"),
                "password": secret.get("password", ""),
                "host": secret.get("host", self.config.get("host", "localhost")),
                "port": str(secret.get("port", self.config.get("port", 5432))),
                "dbname": secret.get("dbname", self.config.get("database", "postgres"))
            }
        except Exception as e:
            logger.error(f"Failed to get credentials from Secrets Manager: {str(e)}")
            # Fallback to config values
            return {
                "username": self.config.get("user", "postgres"),
                "password": self.config.get("password", ""),
                "host": self.config.get("host", "localhost"),
                "port": str(self.config.get("port", 5432)),
                "dbname": self.config.get("database", "postgres")
            }
    
    def _validate_config(self) -> bool:
        """Validate Aurora configuration parameters."""
        required_params = []
        
        # Check if we have secret_arn OR direct connection params
        secret_arn = self.config.get("secret_arn")
        host = self.config.get("host")
        
        if not secret_arn and not host:
            logger.error("Aurora configuration missing: either 'secret_arn' or 'host' must be provided")
            return False
        
        # If using direct connection, validate required params
        if not secret_arn:
            missing_params = []
            for param in ["host", "database"]:
                if not self.config.get(param):
                    missing_params.append(param)
            
            if missing_params:
                logger.error(f"Aurora configuration missing required parameters: {missing_params}")
                return False
        
        logger.info("Aurora configuration validation passed")
        return True
    
    async def _test_data_api_connection(self):
        """Test the Data API connection by executing a simple query."""
        try:
            response = self.rds_client.execute_statement(
                resourceArn=self.cluster_arn,
                secretArn=self.secret_arn,
                database=self.database,
                sql="SELECT 1 as test"
            )
            
            if not response.get('records'):
                raise RuntimeError("Data API test query returned no results")
            
            logger.info("Aurora Data API connection test successful")
        except Exception as e:
            raise RuntimeError(f"Data API connection test failed: {str(e)}")
    
    def _convert_data_api_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert RDS Data API response to standard format."""
        if not response.get('records'):
            return []
        
        columns = [col['name'] for col in response.get('columnMetadata', [])]
        records = response['records']
        
        result = []
        for record in records:
            row = {}
            for i, col_name in enumerate(columns):
                if i < len(record):
                    # Extract value from Data API format
                    field = record[i]
                    if 'stringValue' in field:
                        row[col_name] = field['stringValue']
                    elif 'longValue' in field:
                        row[col_name] = field['longValue']
                    elif 'doubleValue' in field:
                        row[col_name] = field['doubleValue']
                    elif 'booleanValue' in field:
                        row[col_name] = field['booleanValue']
                    elif 'isNull' in field and field['isNull']:
                        row[col_name] = None
                    else:
                        row[col_name] = str(field)
                else:
                    row[col_name] = None
            result.append(row)
        
        return result
    
    async def _test_connection_pool(self):
        """Test the connection pool by executing a simple query."""
        if not self.pool:
            raise RuntimeError("Connection pool is None")
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                if result != 1:
                    raise RuntimeError("Connection test query returned unexpected result")
            logger.info("Aurora connection pool test successful")
        except Exception as e:
            raise RuntimeError(f"Connection pool test failed: {str(e)}")
    
    async def execute_query(self, query: str, params: Optional[List] = None) -> List[Dict[str, Any]]:
        """Execute a query and return results."""
        if self.use_data_api:
            try:
                response = self.rds_client.execute_statement(
                    resourceArn=self.cluster_arn,
                    secretArn=self.secret_arn,
                    database=self.database,
                    sql=query,
                    includeResultMetadata=True
                )
                return self._convert_data_api_response(response)
            except Exception as e:
                logger.error(f"Data API query execution failed: {str(e)}")
                raise
        else:
            if not self.pool:
                raise RuntimeError("Connection pool not initialized")
            
            async with self.pool.acquire() as conn:
                if params:
                    rows = await conn.fetch(query, *params)
                else:
                    rows = await conn.fetch(query)
                
                return [dict(row) for row in rows]
    
    async def _build_connection_string(self) -> str:
        """Build connection string from credentials."""
        if not self._credentials:
            self._credentials = await self._get_credentials_from_secrets_manager()
        
        return f"postgresql://{self._credentials['username']}:{self._credentials['password']}@{self._credentials['host']}:{self._credentials['port']}/{self._credentials['dbname']}"
    
    async def initialize(self) -> bool:
        """Initialize connection pool or Data API client."""
        try:
            if self.use_data_api:
                # Validate Data API configuration
                if not self.cluster_arn or not self.secret_arn:
                    raise ValueError("Data API requires cluster_arn and secret_arn")
                
                # Test Data API connection
                await self._test_data_api_connection()
                logger.info("Aurora Data API connection initialized successfully")
                return True
            else:
                # Validate required configuration
                if not self._validate_config():
                    raise ValueError("Invalid Aurora configuration - missing required parameters")
                
                # Build connection string with credentials
                connection_string = await self._build_connection_string()
                
                self.pool = await asyncpg.create_pool(
                    connection_string,
                    min_size=1,
                    max_size=10,
                    command_timeout=30
                )
                
                # Test the connection pool
                await self._test_connection_pool()
                
                logger.info("Aurora connection pool initialized successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to initialize Aurora connection: {str(e)}")
            # Clean up any partial initialization
            if self.pool:
                try:
                    await self.pool.close()
                    self.pool = None
                except:
                    pass
            raise RuntimeError(f"Aurora connection initialization failed: {str(e)}")
    
    async def execute_query(self, query: str, params: Optional[List] = None) -> List[Dict[str, Any]]:
        """Execute a query and return results."""
        if self.use_data_api:
            try:
                response = self.rds_client.execute_statement(
                    resourceArn=self.cluster_arn,
                    secretArn=self.secret_arn,
                    database=self.database,
                    sql=query,
                    includeResultMetadata=True
                )
                return self._convert_data_api_response(response)
            except Exception as e:
                logger.error(f"Data API query execution failed: {str(e)}")
                raise
        else:
            if not self.pool:
                raise RuntimeError("Connection pool not initialized")
            
            async with self.pool.acquire() as conn:
                if params:
                    rows = await conn.fetch(query, *params)
                else:
                    rows = await conn.fetch(query)
                
                return [dict(row) for row in rows]
    
    async def get_table_info(self) -> List[Dict[str, Any]]:
        """Get information about all tables."""
        query = """
        SELECT 
            schemaname,
            tablename,
            tableowner
        FROM pg_tables 
        WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
        ORDER BY schemaname, tablename
        """
        return await self.execute_query(query)
    
    async def health_check(self) -> bool:
        """Check connection health."""
        try:
            await self.execute_query("SELECT 1")
            return True
        except Exception:
            return False
    
    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Aurora connection pool closed")
