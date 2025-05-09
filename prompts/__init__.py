"""
Prompts module for Java Peer Review Training System.

This module provides language-specific prompt templates for all LLM interactions.
"""

import logging
import importlib
from typing import Dict, Any, Optional
from utils.language_utils import get_current_language

# Configure logging
logger = logging.getLogger(__name__)

# Map of supported languages to their module names
PROMPT_MODULES = {
    "en": "prompts.en",
    "zh-tw": "prompts.zh_tw"
}

# Default language to use as fallback
DEFAULT_LANGUAGE = "en"

def get_prompt_module(lang_code: str = None):
    """
    Dynamically import and return the prompt module for the given language code.
    
    Args:
        lang_code: Language code (e.g., 'en', 'zh-tw')
        
    Returns:
        Prompt module or default prompt module if not found
    """
    # If no language specified, get current language
    if not lang_code:
        lang_code = get_current_language()
        
    # Validate language code
    if lang_code not in PROMPT_MODULES:
        logger.warning(f"Unsupported language for prompts: {lang_code}, falling back to {DEFAULT_LANGUAGE}")
        lang_code = DEFAULT_LANGUAGE
    
    module_name = PROMPT_MODULES[lang_code]
    
    try:
        # Dynamically import the prompt module
        return importlib.import_module(module_name)
    except ImportError as e:
        logger.error(f"Failed to import prompt module {module_name}: {str(e)}")
        # Fall back to English if there's an error
        return importlib.import_module(PROMPT_MODULES[DEFAULT_LANGUAGE])

def get_prompt_template(template_name: str, lang_code: str = None) -> str:
    """
    Get a specific prompt template in the specified language.
    
    Args:
        template_name: Name of the prompt template
        lang_code: Language code (e.g., 'en', 'zh-tw')
        
    Returns:
        Prompt template string
    """
    prompt_module = get_prompt_module(lang_code)
    
    # Get the template from the module
    if hasattr(prompt_module, template_name):
        template = getattr(prompt_module, template_name)
        # Ensure the template is treated as a raw string
        # This helps prevent escape sequence issues
        if not isinstance(template, str):
            logger.warning(f"Template '{template_name}' is not a string")
            return ""
        return template
    
    # Log warning and return empty string if template not found
    logger.warning(f"Prompt template '{template_name}' not found in language '{lang_code}'")
    
    # Try to get the template from the default language
    if lang_code != DEFAULT_LANGUAGE:
        default_module = get_prompt_module(DEFAULT_LANGUAGE)
        if hasattr(default_module, template_name):
            logger.info(f"Using {DEFAULT_LANGUAGE} fallback for template '{template_name}'")
            return getattr(default_module, template_name)
    
    # Return empty string if template not found in any language
    return ""

def invoke_llm_safely(llm, prompt, default_response="Error: Could not generate response"):
    """
    Safely invoke an LLM with proper error handling.
    
    Args:
        llm: Language model to invoke
        prompt: Prompt to send to the LLM
        default_response: Default response if invocation fails
        
    Returns:
        LLM response or default response if invocation fails
    """
    if not llm:
        logger.warning("No LLM available for invocation")
        return default_response
        
    try:
        response = llm.invoke(prompt)
        return response
    except Exception as e:
        logger.error(f"Error invoking LLM: {str(e)}")
        return default_response