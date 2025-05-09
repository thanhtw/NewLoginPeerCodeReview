"""
LLM Provider Selector UI module for Java Peer Review Training System.

This module provides the ProviderSelectorUI class for selecting between
different LLM providers (Ollama and Groq) and managing API keys.
"""

import streamlit as st
import logging
import os
from typing import Dict, Any, Optional, Tuple, List, Callable
from utils.language_utils import t, get_current_language

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProviderSelectorUI:
    """
    UI Component for selecting and configuring the LLM provider.
    
    This class handles displaying provider selection options and
    configuring the selected provider.
    """
    
    def __init__(self, llm_manager):
        """
        Initialize the ProviderSelectorUI.
        
        Args:
            llm_manager: LLMManager instance for provider operations
        """
        self.llm_manager = llm_manager
        
        # Initialize session state for provider selection
        if "provider_selection" not in st.session_state:
            st.session_state.provider_selection = {
                "provider": self.llm_manager.provider,
                "groq_api_key": self.llm_manager.groq_api_key,
                "setup_complete": False,
                "show_setup_modal": True,
                "setup_error": None
            }
    
    def render_provider_setup_modal(self) -> bool:
        """
        Render a modal dialog for initial provider setup.
        
        Returns:
            bool: True if setup is complete, False if setup is still needed
        """
        # Check if setup is already complete
        if st.session_state.provider_selection.get("setup_complete", False):
            return True
        
        # Don't show modal if it's been explicitly hidden
        if not st.session_state.provider_selection.get("show_setup_modal", True):
            return False
        
        # Create a modal-like UI for provider setup
        with st.container():
            st.markdown(f"<h2 style='text-align: center;'>{t('llm_provider_setup')}</h2>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center;'>{t('please_select_LLM')}</p>", unsafe_allow_html=True)
            
            # Provider selection
            provider_options = [f"{t('ollama_mode')}", f"{t('groq_mode')}"]
            selected_option = st.radio(
                f"{t('select_LLM')}", 
                options=provider_options,
                index=0 if self.llm_manager.provider == "ollama" else 1,
                horizontal=True
            )
            
            # Convert selection to provider name
            provider = "ollama" if selected_option == f"{t('ollama_mode')}" else "groq"
            
            # Configuration based on provider
            if provider == "ollama":
                st.info(f"{t('select_ollama')}")
                
                # Check Ollama connection
                connection_status, message = self.llm_manager.check_ollama_connection()
                if connection_status:
                    st.success(f"✅ {t('connected_ollama')}")
                else:
                    st.error(f"❌ {t('ollama_error')}: {message}")
                    st.markdown("""
                    ### Troubleshooting
                    
                    1. Make sure Ollama is installed and running
                    2. Check that Ollama is accessible at http://localhost:11434
                    3. If using a custom URL, set OLLAMA_BASE_URL in your .env file
                    """)
                
                # Ollama setup button
                if st.button(f"{t('use_ollama')}"):
                    # Set provider explicitly - this will update the environment variable
                    success = self.llm_manager.set_provider("ollama")
                    
                    if success:
                        st.session_state.provider_selection["provider"] = "ollama"
                        st.session_state.provider_selection["setup_complete"] = True
                        st.session_state.provider_selection["setup_error"] = None
                        st.rerun()
                    else:
                        st.session_state.provider_selection["setup_error"] = "Failed to set up Ollama provider"
                    
            else:  # Groq
                st.info(f"{t('groq_api_message')}")
                
                # API key input
                api_key = st.text_input(
                    f"{t('groq_api_key')}", 
                    value=st.session_state.provider_selection.get("groq_api_key", ""),
                    type="password",
                    help="Get your API key from https://console.groq.com/"
                )
                
                # Save API key to session state
                st.session_state.provider_selection["groq_api_key"] = api_key
                
                # Test connection button
                if st.button(f"{t('test_connection')}"):
                    if not api_key:
                        st.error(f"{t('api_key_required')}")
                    else:
                        # Set provider with API key
                        success = self.llm_manager.set_provider("groq", api_key)
                        
                        if success:
                            st.success(f"✅ {t('connect_groq_success')}")
                            st.session_state.provider_selection["provider"] = "groq"
                            st.session_state.provider_selection["setup_complete"] = True
                            st.session_state.provider_selection["setup_error"] = None
                            st.rerun()
                        else:
                            st.error(f"❌ {t('connect_groq_failed')}")
                            st.session_state.provider_selection["setup_error"] = "Failed to connect to Groq API"
            
            # Display setup error if any
            if st.session_state.provider_selection.get("setup_error"):
                st.error(st.session_state.provider_selection["setup_error"])
        
        # Return True if setup is complete, False otherwise
        return st.session_state.provider_selection.get("setup_complete", False)
    
    def render_provider_status(self):
        """Render the current provider status in the sidebar."""
        with st.sidebar:
            st.subheader(f"LLM {t('provider')} {t('status')}")
            
            # Display current provider
            provider = self.llm_manager.provider
            if provider == "ollama":
                st.info("🖥️ " + t("using_ollama"))
                
                # Check connection status
                connection_status, _ = self.llm_manager.check_ollama_connection()
                if connection_status:
                    st.success(t("connected_ollama"))
                else:
                    st.error(f"Not {t('connected')} to Ollama")
            
            elif provider == "groq":
                st.info(f"☁️ {t('using_groq')}")
                
                # Check connection status
                connection_status, _ = self.llm_manager.check_groq_connection()
                if connection_status:
                    # Display masked API key
                    api_key = self.llm_manager.groq_api_key
                    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "Not set"
                    st.success(f"{t('connected_groq')} (Key: {masked_key})")
                else:
                    st.error(t("not_connected_to_groq"))
            
            # Button to change provider
            if st.button(f"{t('change_provider')}"):
                # Reset provider setup
                st.session_state.provider_selection["setup_complete"] = False
                st.session_state.provider_selection["show_setup_modal"] = True
                
                # Force page reload
                st.rerun()

    def force_reinitialize(self):
        """Force reinitialization of components after provider change."""
        # Clear LLM Manager model cache
        self.llm_manager.initialized_models = {}
        
        # Update environment variable to persist
        os.environ["LLM_PROVIDER"] = self.llm_manager.provider
        
        # Log the reinitialization
        logger.info(f"Forced reinitialization with provider: {self.llm_manager.provider}")
        
        # Force UI refresh
        st.rerun()