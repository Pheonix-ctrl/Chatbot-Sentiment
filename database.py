import os
import psycopg2
import psycopg2.extras
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import logging
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Database manager for Supabase PostgreSQL connection
    Handles SQL execution for client sentiment analytics
    """
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # Parse the database URL to get connection parameters
        self.connection_params = self._parse_database_url(self.database_url)
        
    def _parse_database_url(self, url: str) -> dict:
        """Parse DATABASE_URL into connection parameters"""
        parsed = urlparse(url)
        return {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path[1:],  # Remove leading slash
            'user': parsed.username,
            'password': parsed.password,
            'sslmode': 'require'  # Supabase requires SSL
        }
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = psycopg2.connect(**self.connection_params)
            yield conn
        except psycopg2.Error as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results as list of dictionaries
        
        Args:
            sql: SQL query string
            params: Optional parameters for the query
            
        Returns:
            List of dictionaries representing query results
            
        Raises:
            DatabaseError: If query execution fails
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(sql, params)
                    
                    # Handle different types of queries
                    if cursor.description:
                        # SELECT query - fetch results
                        results = cursor.fetchall()
                        # Convert RealDictRow to regular dict for JSON serialization
                        return [dict(row) for row in results]
                    else:
                        # INSERT/UPDATE/DELETE - return affected rows count
                        return [{"affected_rows": cursor.rowcount}]
                        
        except psycopg2.Error as e:
            logger.error(f"Query execution error: {e}")
            logger.error(f"Failed query: {sql}")
            raise DatabaseError(f"Database query failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during query execution: {e}")
            raise DatabaseError(f"Unexpected database error: {str(e)}")
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    return result[0] == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column information for a table"""
        sql = """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name = %s
        ORDER BY ordinal_position
        """
        return self.execute_query(sql, (table_name,))
    
    def validate_sql_safety(self, sql: str) -> bool:
        """
        Basic SQL safety validation
        Prevents potentially dangerous operations
        """
        sql_upper = sql.upper().strip()
        
        # Blocked operations
        dangerous_keywords = [
            'DROP', 'DELETE', 'INSERT', 'UPDATE', 'CREATE', 'ALTER', 
            'TRUNCATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE'
        ]
        
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                logger.warning(f"Blocked potentially dangerous SQL containing: {keyword}")
                return False
        
        # Must start with SELECT
        if not sql_upper.startswith('SELECT') and not sql_upper.startswith('WITH'):
            logger.warning("SQL must start with SELECT or WITH")
            return False
            
        return True
    
    def execute_safe_query(self, sql: str) -> List[Dict[str, Any]]:
        """
        Execute query with safety validation
        Only allows SELECT statements
        """
        if not self.validate_sql_safety(sql):
            raise DatabaseError("SQL query failed safety validation")
        
        return self.execute_query(sql)


class DatabaseError(Exception):
    """Custom exception for database-related errors"""
    pass


# Singleton instance
db_manager = DatabaseManager()


# Convenience functions
def execute_sql(sql: str) -> List[Dict[str, Any]]:
    """Execute SQL query using the global database manager"""
    return db_manager.execute_safe_query(sql)


def test_database_connection() -> bool:
    """Test the database connection"""
    return db_manager.test_connection()


def get_table_structure(table_name: str) -> List[Dict[str, Any]]:
    """Get table column information"""
    return db_manager.get_table_info(table_name)