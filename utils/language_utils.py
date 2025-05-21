"""
Language utilities for Java Peer Review Training System.

This module provides utilities for handling language selection and translation.
Updated to work with multilingual database fields.
"""

import streamlit as st
import os
import logging
import sys
from typing import Dict, Any, Optional

# Add the parent directory to the path to allow absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import language package
from language import get_translations, get_llm_prompt_instructions, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

# Configure logging
logger = logging.getLogger(__name__)

def init_language():
    """Initialize language selection in session state."""
    if "language" not in st.session_state:
        st.session_state.language = DEFAULT_LANGUAGE

def set_language(lang: str):
    """
    Set the application language.
    
    Args:
        lang: Language code (e.g., 'en', 'zh')
    """
    if lang in SUPPORTED_LANGUAGES:
        st.session_state.language = lang
    else:
        logger.warning(f"Unsupported language: {lang}, using default: {DEFAULT_LANGUAGE}")
        st.session_state.language = DEFAULT_LANGUAGE

def get_current_language() -> str:
    """
    Get the current language.
    
    Returns:
        Current language code
    """
    return st.session_state.get("language", DEFAULT_LANGUAGE)

def t(key: str) -> str:
    """
    Translate a text key to the current language.
    
    Args:
        key: Text key to translate
        
    Returns:
        Translated text
    """
    current_lang = get_current_language()
    translations = get_translations(current_lang)
    
    # Return the translation if found, otherwise return the key itself
    return translations.get(key, key)

def get_db_field_name(field_base: str) -> str:
    """
    Get the language-specific database field name based on current language.
    
    Args:
        field_base: Base field name (e.g., 'name', 'description')
        
    Returns:
        Language-specific field name (e.g., 'name_en', 'description_zh')
    """
    current_lang = get_current_language()
    if current_lang == "en":
        return f"{field_base}_en"
    elif current_lang == "zh":
        return f"{field_base}_zh"
    else:
        # Default to English for unsupported languages
        return f"{field_base}_en"

def get_multilingual_field(data: Dict[str, Any], field_base: str) -> str:
    """
    Extract the appropriate language field from a database record.
    
    Args:
        data: Database record as dictionary
        field_base: Base field name (e.g., 'name', 'description')
        
    Returns:
        Value from the appropriate language field
    """
    current_lang = get_current_language()
    # Try language-specific field first
    if current_lang == "en":
        field_name = f"{field_base}_en"
    elif current_lang == "zh":
        field_name = f"{field_base}_zh"
    else:
        field_name = f"{field_base}_en"  # Default to English
    
    # If the language-specific field exists, use it
    if field_name in data:
        return data[field_name]
    
    # Otherwise, try the base field
    if field_base in data:
        return data[field_base]
    
    # If neither exists, return empty string
    return ""

def get_llm_instructions() -> str:
    """
    Get the LLM instructions for the current language.
    
    Returns:
        Instructions string for LLM
    """
    current_lang = get_current_language()
    return get_llm_prompt_instructions(current_lang)

def render_language_selector():
    """Render a language selector in the sidebar."""
    with st.sidebar:
        st.subheader(t("language"))
        cols = st.columns([1, 1])
        
        with cols[0]:
            if st.button("English", use_container_width=True, 
                         disabled=get_current_language() == "en"):
                # Save authentication state
                current_auth = st.session_state.get("auth", None)
                current_user_level = st.session_state.get("user_level", None)
                current_provider = st.session_state.get("provider_selection", None)
                
                # Set a dedicated language change reset flag (not full_reset)
                st.session_state["language_change_reset"] = True
                
                # Save auth for restoration
                st.session_state["language_auth_preserve"] = current_auth
                st.session_state["language_user_level_preserve"] = current_user_level
                st.session_state["language_provider_preserve"] = current_provider
                
                # Change language
                set_language("en")
                st.rerun()
                
        with cols[1]:
            if st.button("繁體中文", use_container_width=True, 
                         disabled=get_current_language() == "zh"):
                # Save authentication state
                current_auth = st.session_state.get("auth", None)
                current_user_level = st.session_state.get("user_level", None)
                current_provider = st.session_state.get("provider_selection", None)
                
                # Set a dedicated language change reset flag (not full_reset)
                st.session_state["language_change_reset"] = True
                
                # Save auth for restoration
                st.session_state["language_auth_preserve"] = current_auth
                st.session_state["language_user_level_preserve"] = current_user_level
                st.session_state["language_provider_preserve"] = current_provider
                
                # Change language
                set_language("zh")
                st.rerun()