# db/mysql_connection.py
import mysql.connector
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
import os
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MySQLConnection:
    """
    MySQL database connection manager for the Java Peer Review Training System.
    """
    
    _instance = None
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super(MySQLConnection, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the database connection."""
        if self._initialized:
            return
            
        # Get database configuration from environment variables
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_user = os.getenv("DB_USER", "root")
        self.db_password = os.getenv("DB_PASSWORD", "selab")
        self.db_name = os.getenv("DB_NAME", "streamlit_app")
        self.db_port = int(os.getenv("DB_PORT", "3306"))
        
        # Initialize connection to None
        self.connection = None
        self._initialized = True
        
        # Create database and tables if they don't exist
        self._initialize_database()
    
    def _get_connection(self):
        """Get a database connection with improved error handling."""
        try:
            if self.connection is None or not self.connection.is_connected():
                # Log connection attempt
                #logger.info(f"Connecting to MySQL: {self.db_user}@{self.db_host}:{self.db_port}/{self.db_name}")
                
                # Add authentication_plugin parameter for compatibility
                self.connection = mysql.connector.connect(
                    host=self.db_host,
                    user=self.db_user,
                    password=self.db_password,
                    database=self.db_name,
                    port=self.db_port,
                    auth_plugin='mysql_native_password',  # Try alternative auth method
                    use_pure=True  # Use pure Python implementation for better compatibility
                )
                logger.info("Connected to MySQL successfully")
            return self.connection
        except mysql.connector.Error as e:
            logger.error(f"Error connecting to MySQL: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def _initialize_database(self):
        """Create the database and tables if they don't exist."""
        try:
            # First, connect without specifying a database to create it if needed
            logger.info(f"Initializing database: {self.db_name}")
            init_conn = mysql.connector.connect(
                host=self.db_host,
                user=self.db_user,
                password=self.db_password,
                port=self.db_port
            )
            
            cursor = init_conn.cursor()
            
            # Create database if it doesn't exist
            logger.info(f"Creating database if not exists: {self.db_name}")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.db_name}")
            cursor.execute(f"USE {self.db_name}")
            
            # Create users table if it doesn't exist - REMOVED average_accuracy column
            logger.info("Creating users table if not exists")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    uid VARCHAR(36) PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    display_name VARCHAR(255) NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    level ENUM('basic', 'medium', 'senior') DEFAULT 'basic',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviews_completed INT DEFAULT 0,
                    score INT DEFAULT 0
                )
            """)
            
            # Commit changes and close connection
            init_conn.commit()
            cursor.close()
            init_conn.close()
            
            logger.info("Database and tables initialized successfully")
            
        except mysql.connector.Error as e:
            logger.error(f"Error initializing database: {str(e)}")
            logger.error(traceback.format_exc())
    
    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False):
        """
        Execute a query and return the results.
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            connection = self._get_connection()
            if not connection:
                logger.error("Failed to get database connection")
                time.sleep(1)  # Wait before retry
                retry_count += 1
                continue
                
            try:
                cursor = connection.cursor(dictionary=True)
                
                # Log query with parameters
                if params:
                    param_str = str(params)
                    #logger.info(f"Executing query: {query} with params: {param_str}")
                else:
                    logger.info(f"Executing query: {query}")
                
                cursor.execute(query, params or ())
                
                if query.strip().upper().startswith(("SELECT", "SHOW")):
                    if fetch_one:
                        result = cursor.fetchone()
                    else:
                        result = cursor.fetchall()
                    cursor.close()
                    return result
                else:
                    connection.commit()
                    affected_rows = cursor.rowcount
                    cursor.close()
                    #logger.info(f"Query executed successfully. Affected rows: {affected_rows}")
                    return affected_rows
            except mysql.connector.Error as e:
                #logger.error(f"Error executing query: {str(e)}")
                #logger.error(f"Query: {query}")
                #logger.error(f"Params: {params}")
                logger.error(traceback.format_exc())
                
                # Check for connection-related errors to retry
                should_retry = False
                if "2006" in str(e) or "2013" in str(e):  # Common MySQL connection lost error codes
                    logger.info("Connection lost, attempting to reconnect...")
                    self.connection = None  # Force reconnection
                    should_retry = True
                
                if should_retry and retry_count < max_retries - 1:
                    retry_count += 1
                    time.sleep(1)  # Wait before retry
                    continue
                else:
                    return None
            except Exception as e:
                logger.error(f"Unexpected error executing query: {str(e)}")
                #logger.error(traceback.format_exc())
                return None