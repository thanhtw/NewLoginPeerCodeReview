"""
Language package for Java Peer Review Training System.

This package contains language modules for internationalization support.
"""

import importlib
import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# Map of supported languages to their module names
SUPPORTED_LANGUAGES = {
    "en": "language.en",
    "zh-tw": "language.zh_tw"
}

# Default language to use as fallback
DEFAULT_LANGUAGE = "en"

def get_language_module(lang_code: str):
    """
    Dynamically import and return the language module for the given language code.
    
    Args:
        lang_code: Language code (e.g., 'en', 'zh-tw')
        
    Returns:
        Language module or default language module if not found
    """
    if lang_code not in SUPPORTED_LANGUAGES:
        logger.warning(f"Unsupported language: {lang_code}, falling back to {DEFAULT_LANGUAGE}")
        lang_code = DEFAULT_LANGUAGE
    
    module_name = SUPPORTED_LANGUAGES[lang_code]
    
    try:
        # Dynamically import the language module
        return importlib.import_module(module_name)
    except ImportError as e:
        logger.error(f"Failed to import language module {module_name}: {str(e)}")
        # Fall back to English if there's an error
        return importlib.import_module(SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])

def get_translations(lang_code: str) -> Dict[str, str]:
    """
    Get the translations dictionary for the specified language.
    
    Args:
        lang_code: Language code (e.g., 'en', 'zh-tw')
        
    Returns:
        Dictionary of translations
    """
    language_module = get_language_module(lang_code)
    return getattr(language_module, "translations", {})

def get_llm_prompt_instructions(lang_code: str) -> str:
    """
    Get the LLM prompt instructions for the specified language.
    
    Args:
        lang_code: Language code (e.g., 'en', 'zh-tw')
        
    Returns:
        Instructions string for LLM
    """
    language_module = get_language_module(lang_code)
    return getattr(language_module, "llm_instructions", "")

# Export supported languages for the UI
__all__ = ["get_translations", "get_llm_prompt_instructions", "SUPPORTED_LANGUAGES", "DEFAULT_LANGUAGE"]