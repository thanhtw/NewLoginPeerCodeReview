"""
LLM Manager module for Java Peer Review Training System.

This module provides the LLMManager class for handling model initialization,
configuration, and management of Groq LLM provider.
"""

import os
import logging
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
    Supports Groq LLM provider.
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
    
    def set_provider(self, provider: str, api_key: str = None) -> bool:
        """
        Set the LLM provider to use and persist the selection.
        
        Args:
            provider: Provider name (must be 'groq')
            api_key: API key for Groq (required)
            
        Returns:
            bool: True if successful, False otherwise
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
        
        # Test the API key
        if not self.check_groq_connection()[0]:
            logger.error("Failed to connect to Groq API. Please check your API key.")
            return False
        
        # Log successful provider change
        logger.debug(f"Successfully configured Groq provider")
        return True    
    
    def check_groq_connection(self) -> Tuple[bool, str]:
        """
        Check if Groq API is accessible with the current API key.
        
        Returns:
            Tuple[bool, str]: (is_connected, message)
        """
        if not self.groq_api_key:
            return False, "No Groq API key provided"
            
        if not GROQ_AVAILABLE:
            return False, "Groq integration is not available. Please install langchain-groq package."
            
        try:
            # Use a minimal API call to test the connection
            chat = ChatGroq(
                api_key=self.groq_api_key,
                model_name="llama3-8b-8192"  # Use the smallest model for testing
            )
            
            # Make a minimal API call
            response = chat.invoke([HumanMessage(content="test")])
            
            # If we get here, the connection is successful
            return True, f"Connected to Groq API successfully"
            
        except Exception as e:
            error_message = str(e)
            if "auth" in error_message.lower() or "api key" in error_message.lower():
                return False, "Invalid Groq API key"
            else:
                return False, f"Error connecting to Groq API: {error_message}"

    def initialize_model(self, model_name: str, model_params: Dict[str, Any] = None) -> Optional[BaseLanguageModel]:
        """
        Initialize a Groq model.
        
        Args:
            model_name (str): Name of the model to initialize
            model_params (Dict[str, Any], optional): Model parameters
            
        Returns:
            Optional[BaseLanguageModel]: Initialized LLM or None if initialization fails
        """
        return self._initialize_groq_model(model_name, model_params)
    
    def _initialize_groq_model(self, model_name: str, model_params: Dict[str, Any] = None) -> Optional[BaseLanguageModel]:
        """
        Initialize a Groq model.
        
        Args:
            model_name: Name of the model to initialize
            model_params: Model parameters
            
        Returns:
            Initialized LLM or None if initialization fails
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
            # Initialize the Groq model
            temperature = model_params.get("temperature", 0.7)
            
            # Use the ChatGroq class from langchain_groq
            llm = ChatGroq(
                api_key=self.groq_api_key,
                model_name=model_name,
                temperature=temperature,
                verbose=True
            )
            
            # Test with a simple message to ensure the model works
            try:
                _ = llm.invoke([HumanMessage(content="test")])
                logger.debug(f"Successfully initialized Groq model: {model_name}")
                return llm
            except Exception as e:
                logger.debug(f"Error testing Groq model {model_name}: {str(e)}")
                return None
                
        except Exception as e:
            logger.debug(f"Error initializing Groq model {model_name}: {str(e)}")
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
        temperature = float(os.getenv(temperature_key, "0.7"))       
        
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