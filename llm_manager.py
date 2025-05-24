"""
LLM Manager module for Java Peer Review Training System.

This module provides the LLMManager class for handling model initialization,
configuration, and management of Groq LLM provider with lazy connection testing.
"""

import os
import logging
import time
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv 

# Groq integration
from langchain_groq import ChatGroq 
from langchain_core.messages import HumanMessage
GROQ_AVAILABLE = True

from langchain_core.language_models import BaseLanguageModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LLMManager:
    """
    LLM Manager for handling model initialization, configuration and management.
    Supports Groq LLM provider with lazy connection testing.
    """
    
    def __init__(self):
        """Initialize the LLM Manager with environment variables."""
        load_dotenv(override=True)
        
        # Provider settings - set to Groq
        self.provider = "groq"
        
        # Groq settings
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.groq_api_base = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1")
        self.groq_default_model = os.getenv("GROQ_DEFAULT_MODEL", "llama3-8b-8192")
        
        # Available Groq models
        self.groq_available_models = [
            "llama3-8b-8192",
            "llama3-70b-8192",
            "mixtral-8x7b-32768",
            "gemma-7b-it"
        ]
        
        # Track initialized models
        self.initialized_models = {}
        
        # Connection caching to avoid repeated tests
        self._connection_cache = {}
        self._cache_duration = 300  # 5 minutes
    
    def set_provider(self, provider: str, api_key: str = None) -> bool:
        """
        Set the LLM provider to use and persist the selection.
        No longer tests connection immediately - this is done lazily on first use.
        
        Args:
            provider: Provider name (must be 'groq')
            api_key: API key for Groq (required)
            
        Returns:
            bool: True if configuration successful, False otherwise
        """
        if provider.lower() != "groq":
            logger.error(f"Unsupported provider: {provider}. Only 'groq' is supported.")
            return False
            
        # Set the provider in instance and persist to environment
        self.provider = "groq"
        os.environ["LLM_PROVIDER"] = "groq"
        logger.debug(f"Provider set to: {self.provider}")
        
        # Clear initialized models to force reinitialization
        self.initialized_models = {}
        
        # Handle Groq setup
        if not GROQ_AVAILABLE:
            logger.error("Groq integration is not available. Please install langchain-groq package.")
            return False
            
        # Validate and set API key
        if not api_key and not self.groq_api_key:
            logger.error("API key is required for Groq provider")
            return False
            
        if api_key:
            self.groq_api_key = api_key
            os.environ["GROQ_API_KEY"] = api_key
        
        # Clear connection cache when provider changes
        self._connection_cache = {}
        
        # REMOVED: Connection testing - will be done on first LLM use
        logger.debug(f"Successfully configured Groq provider")
        return True    
    
    def _is_connection_cached(self) -> Tuple[bool, Optional[bool], Optional[str]]:
        """
        Check if we have a recent connection test result cached.
        
        Returns:
            Tuple[bool, Optional[bool], Optional[str]]: (has_cache, is_connected, message)
        """
        if not self._connection_cache:
            return False, None, None
            
        cache_time = self._connection_cache.get("timestamp", 0)
        current_time = time.time()
        
        # Check if cache is still valid
        if current_time - cache_time < self._cache_duration:
            return True, self._connection_cache.get("connected", False), self._connection_cache.get("message", "")
        
        # Cache expired
        return False, None, None
    
    def _cache_connection_result(self, connected: bool, message: str):
        """
        Cache the connection test result.
        
        Args:
            connected: Whether connection was successful
            message: Connection status message
        """
        self._connection_cache = {
            "connected": connected,
            "message": message,
            "timestamp": time.time()
        }
    
    def check_groq_connection(self, force_check: bool = False) -> Tuple[bool, str]:
        """
        Check if Groq API is accessible with the current API key.
        Uses caching to avoid repeated checks unless forced.
        
        Args:
            force_check: Force a new connection check even if cached
            
        Returns:
            Tuple[bool, str]: (is_connected, message)
        """
        # Check cache first unless forced
        if not force_check:
            has_cache, is_connected, message = self._is_connection_cached()
            if has_cache:
                logger.debug(f"Using cached connection status: {is_connected}")
                return is_connected, message
        
        if not self.groq_api_key:
            result = False, "No Groq API key provided"
            self._cache_connection_result(*result)
            return result
            
        if not GROQ_AVAILABLE:
            result = False, "Groq integration is not available. Please install langchain-groq package."
            self._cache_connection_result(*result)
            return result
            
        try:
            # Use a minimal API call to test the connection
            chat = ChatGroq(
                api_key=self.groq_api_key,
                model_name="llama3-8b-8192"  # Use the smallest model for testing
            )
            
            # Make a minimal API call
            response = chat.invoke([HumanMessage(content="test")])
            
            # If we get here, the connection is successful
            result = True, f"Connected to Groq API successfully"
            logger.debug("Groq connection test successful")
            
        except Exception as e:
            error_message = str(e)
            if "auth" in error_message.lower() or "api key" in error_message.lower():
                result = False, "Invalid Groq API key"
            else:
                result = False, f"Error connecting to Groq API: {error_message}"
            logger.debug(f"Groq connection test failed: {result[1]}")
        
        # Cache the result
        self._cache_connection_result(*result)
        return result

    def initialize_model(self, model_name: str, model_params: Dict[str, Any] = None) -> Optional[BaseLanguageModel]:
        """
        Initialize a Groq model with lazy connection testing.
        Connection is only tested when the model is actually used.
        
        Args:
            model_name (str): Name of the model to initialize
            model_params (Dict[str, Any], optional): Model parameters
            
        Returns:
            Optional[BaseLanguageModel]: Initialized LLM or None if initialization fails
        """
        return self._initialize_groq_model(model_name, model_params)
    
    def _initialize_groq_model(self, model_name: str, model_params: Dict[str, Any] = None) -> Optional[BaseLanguageModel]:
        """
        Initialize a Groq model without immediate connection testing.
        Uses simple ChatGroq instance for maximum reliability.
        
        Args:
            model_name: Name of the model to initialize
            model_params: Model parameters
            
        Returns:
            Initialized ChatGroq instance or None if initialization fails
        """
        if not GROQ_AVAILABLE:
            logger.error("Groq integration is not available. Please install langchain-groq package.")
            return None
            
        if not self.groq_api_key:
            logger.error("No Groq API key provided")
            return None
            
        # Apply default model parameters if none provided
        if model_params is None:
            model_params = self._get_groq_default_params(model_name)
            
        try:
            # Create ChatGroq directly for maximum reliability
            llm = ChatGroq(
                api_key=self.groq_api_key,
                model_name=model_name,
                temperature=model_params.get("temperature", 0.7),
                verbose=True
            )
            
            logger.debug(f"Successfully initialized Groq model: {model_name}")
            return llm
                
        except Exception as e:
            logger.error(f"Error initializing Groq model {model_name}: {str(e)}")
            return None
    
    def initialize_model_from_env(self, model_key: str, temperature_key: str) -> Optional[BaseLanguageModel]:
        """
        Initialize a model using environment variables.
        
        Args:
            model_key (str): Environment variable key for model name
            temperature_key (str): Environment variable key for temperature
            
        Returns:
            Optional[BaseLanguageModel]: Initialized LLM or None if initialization fails
        """
        logger.debug(f"Initializing model from env with Groq provider")
        
        # Get Groq model name from environment variables
        groq_model_key = f"GROQ_{model_key}"
        model_name = os.getenv(groq_model_key, self.groq_default_model)
        
        # Map environment variable names to Groq model names if needed
        if model_name == "llama3:8b":
            model_name = "llama3-8b-8192"
        elif model_name == "llama3:70b":
            model_name = "llama3-70b-8192"
        
        logger.debug(f"Using Groq model: {model_name}")
        
        # Get temperature
        try:
            temperature = float(os.getenv(temperature_key, "0.7"))
        except (ValueError, TypeError):
            logger.warning(f"Invalid temperature value for {temperature_key}, using default 0.7")
            temperature = 0.7
        
        # Set up model parameters
        model_params = {
            "temperature": temperature
        }
        
        # Initialize the model
        logger.debug(f"Initializing model {model_name} with params: {model_params}")
        return self.initialize_model(model_name, model_params)
    
    def _get_groq_default_params(self, model_name: str) -> Dict[str, Any]:
        """
        Get default parameters for a Groq model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Default parameters for the model
        """
        # Basic defaults for Groq
        params = {
            "temperature": 0.7,
            "max_tokens": 1024
        }
        
        # Adjust based on model name and role
        if "generative" in model_name or "llama3" in model_name:
            params["temperature"] = 0.8  # Slightly higher creativity for generative tasks
        elif "review" in model_name or "mixtral" in model_name:
            params["temperature"] = 0.3  # Lower temperature for review tasks
        elif "summary" in model_name:
            params["temperature"] = 0.4  # Moderate temperature for summary tasks
        elif "compare" in model_name:
            params["temperature"] = 0.5  # Balanced temperature for comparison tasks
        
        return params

    def get_available_models(self) -> list:
        """
        Get list of available Groq models.
        
        Returns:
            List of available model names
        """
        return self.groq_available_models.copy()
    
    def is_model_available(self, model_name: str) -> bool:
        """
        Check if a model is available in Groq.
        
        Args:
            model_name: Name of the model to check
            
        Returns:
            True if model is available, False otherwise
        """
        return model_name in self.groq_available_models