"""
Main UI utilities for Java Peer Review Training System.

This module provides core UI utility functions for the Streamlit interface,
including session state management, tab rendering, and LLM logs.
"""

import streamlit as st
import os
import logging
import re
import json
import time
from typing import Dict, List, Any, Optional

from utils.llm_logger import LLMInteractionLogger
from state_schema import WorkflowState
from utils.language_utils import t, get_current_language

# Configure logging
logger = logging.getLogger(__name__)

def init_session_state():
    """Initialize session state with default values."""
    # Initialize workflow state
    if 'workflow_state' not in st.session_state:
        st.session_state.workflow_state = WorkflowState()
    
    # Initialize UI state
    ui_defaults = {
        'active_tab': 0,
        'error': None,
        'workflow_steps': [],
        'sidebar_tab': "Status",
        'user_level': None
    }
    
    for key, default_value in ui_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
    
    # Initialize workflow state attributes
    _init_workflow_state_attributes()
    
    # Initialize LLM logger
    if 'llm_logger' not in st.session_state:
        st.session_state.llm_logger = LLMInteractionLogger()
    
    # Clean up legacy session state
    _cleanup_legacy_session_state()


def _init_workflow_state_attributes():
    """Initialize workflow state attributes if missing."""
    workflow_state = st.session_state.workflow_state
    
    attributes = {
        'current_step': 'generate',
        'evaluation_attempts': 0,
        'max_evaluation_attempts': 3
    }
    
    for attr, default_value in attributes.items():
        if not hasattr(workflow_state, attr):
            setattr(workflow_state, attr, default_value)


def _cleanup_legacy_session_state():
    """Remove legacy session state entries that are no longer used."""
    # Remove direct code_snippet references (should be in workflow_state)
    if 'code_snippet' in st.session_state:
        # Transfer to workflow_state if needed
        if hasattr(st.session_state.workflow_state, 'code_snippet') and not st.session_state.workflow_state.code_snippet:
            st.session_state.workflow_state.code_snippet = st.session_state.code_snippet
        del st.session_state.code_snippet


def create_enhanced_tabs(labels: List[str]):
    """
    Create enhanced UI tabs with proper state management.
    
    Args:
        labels: List of tab labels
        
    Returns:
        List of tab objects
    """
    # Create tabs
    tabs = st.tabs(labels)
    
    # Handle forced tab reset
    if st.session_state.get("force_tab_zero", False):
        st.session_state.active_tab = 0
        del st.session_state["force_tab_zero"]
    
    # Get current active tab
    current_tab = st.session_state.active_tab
    
    # Check review completion for feedback tab access
    if current_tab == 2:  # Feedback tab
        if not _is_review_completed():
            st.warning("Please complete all review attempts before accessing feedback.")
            st.session_state.active_tab = 1
            current_tab = 1
    
    # Update active tab
    if current_tab != 0:
        st.session_state.active_tab = current_tab
    
    return tabs


def _is_review_completed() -> bool:
    """Check if review process is completed."""
    if not hasattr(st.session_state, 'workflow_state'):
        return False
    
    state = st.session_state.workflow_state
    
    # Check max iterations or sufficient review
    if hasattr(state, 'current_iteration') and hasattr(state, 'max_iterations'):
        if state.current_iteration > state.max_iterations:
            return True
        if hasattr(state, 'review_sufficient') and state.review_sufficient:
            return True
    
    # Check if all errors identified
    if hasattr(state, 'review_history') and state.review_history:
        latest_review = state.review_history[-1]
        if hasattr(latest_review, 'analysis'):
            analysis = latest_review.analysis
            identified = analysis.get(t('identified_count'), 0)
            total = analysis.get(t('total_problems'), 0)
            if identified == total and total > 0:
                return True
    
    return False


def render_sidebar(llm_manager):
    """
    Render the sidebar with application info and model status.
    
    Args:
        llm_manager: LLMManager instance
    """
    with st.sidebar:
        # LLM Provider info
        st.subheader(f"LLM {t('provider')}")
        
        provider = llm_manager.provider.capitalize()
        
        if provider == "Groq":
            connection_status, message = llm_manager.check_groq_connection()
            status_text = f"✅ Connected" if connection_status else "❌ Disconnected"
            
            st.markdown(f"**{t('provider')}:** {provider}")
            st.markdown(f"**Status:** {status_text}")
            
            if not connection_status:
                st.error(f"Error: {message}")


def render_llm_logs_tab():
    """Render the LLM logs tab with enhanced filtering and display."""
    st.subheader(t("llm_logs_title"))
    
    # Check if logger is available
    if not hasattr(st.session_state, 'llm_logger'):
        st.info(t("llm_logger_not_initialized"))
        return
    
    llm_logger = st.session_state.llm_logger
    
    # Controls
    _render_log_controls()
    
    # Get and display logs
    log_count = st.session_state.get('log_display_count', 10)
    logs = llm_logger.get_recent_logs(log_count)
    
    if logs:
        # Apply filters
        filtered_logs = _apply_log_filters(logs)
        
        if filtered_logs:
            st.success(t("displaying_logs").format(count=len(filtered_logs)))
            _render_log_entries(filtered_logs)
        else:
            st.info(t("no_logs_match"))
    else:
        st.info(t("no_logs_found"))
        _render_log_info()
    
    # Clear logs functionality
    _render_clear_logs_section()


def _render_log_controls():
    """Render log filtering and control options."""
    col1, col2 = st.columns([5, 1])
    
    with col2:
        if st.button(t("refresh_logs"), key="refresh_logs_btn"):
            st.rerun()
    
    with col1:
        log_count = st.slider(
            t("logs_to_display"), 
            min_value=5, 
            max_value=30, 
            value=10, 
            step=5,
            key='log_display_count'
        )


def _apply_log_filters(logs: List[Dict]) -> List[Dict]:
    """Apply filtering to log entries."""
    # Get unique log types
    log_types = sorted(list(set(log.get("type", "unknown") for log in logs)))
    
    # Type filter
    selected_types = st.multiselect(
        t("filter_by_type"), 
        log_types, 
        default=log_types,
        key='log_type_filter'
    )
    
    # Date filter
    timestamps = [log.get("timestamp", "") for log in logs if "timestamp" in log]
    dates = []
    
    if timestamps:
        dates = sorted(set(ts.split("T")[0] for ts in timestamps if "T" in ts))
        if dates:
            selected_dates = st.multiselect(
                t("filter_by_date"), 
                dates, 
                default=dates,
                key='log_date_filter'
            )
            
            # Apply date filter
            logs = [log for log in logs 
                   if "timestamp" in log and log["timestamp"].split("T")[0] in selected_dates]
    
    # Apply type filter
    return [log for log in logs if log.get("type", "unknown") in selected_types]


def _render_log_entries(logs: List[Dict]):
    """Render individual log entries with enhanced formatting."""
    for idx, log in enumerate(logs):
        # Format timestamp
        timestamp = log.get("timestamp", t("unknown_time"))
        if "T" in timestamp:
            date, time = timestamp.split("T")
            time = time.split(".")[0]
            display_time = f"{date} {time}"
        else:
            display_time = timestamp
        
        # Create expander title
        log_type = log.get("type", t("unknown_type")).replace("_", " ").title()
        expander_title = f"{log_type} - {display_time}"
        
        with st.expander(expander_title):
            _render_log_content(log, idx)


def _render_log_content(log: Dict, idx: int):
    """Render the content of a single log entry."""
    log_tabs = st.tabs([
        t("prompt_tab"), 
        t("response_tab"), 
        t("metadata_tab")
    ])
    
    with log_tabs[0]:  # Prompt tab
        st.text_area(
            t("prompt_sent"), 
            value=log.get("prompt", ""), 
            height=250,
            key=f"prompt_{idx}_{log.get('timestamp', '')}",
            disabled=True
        )
    
    with log_tabs[1]:  # Response tab
        response = log.get("response", "")
        if response:
            _render_response_content(response, idx, log)
        else:
            st.info(t("no_response"))
    
    with log_tabs[2]:  # Metadata tab
        metadata = log.get("metadata", {})
        if metadata:
            st.json(metadata)
        else:
            st.info(t("no_metadata"))


def _render_response_content(response: str, idx: int, log: Dict):
    """Render response content with syntax highlighting for code blocks."""
    if "```" in response:
        # Handle code blocks
        parts = response.split("```")
        for i, part in enumerate(parts):
            if i % 2 == 0:  # Regular text
                if part.strip():
                    st.markdown(part)
            else:  # Code block
                language = ""
                if part.strip() and "\n" in part:
                    language_line, code = part.split("\n", 1)
                    if language_line.strip():
                        language = language_line.strip()
                        part = code
                
                if language:
                    st.code(part, language=language)
                else:
                    st.code(part)
    else:
        # Plain text response
        st.text_area(
            t("response_label"), 
            value=response, 
            height=300,
            key=f"response_{idx}_{log.get('timestamp', '')}",
            disabled=True
        )


def _render_log_info():
    """Render informational content about logs."""
    st.markdown(t("log_info_markdown"))


def _render_clear_logs_section():
    """Render the clear logs section with confirmation."""
    st.markdown("---")
    
    if st.button(t("clear_logs")):
        st.warning(t("clear_logs_warning"))
        confirm_key = "confirm_clear_logs"
        
        if confirm_key not in st.session_state:
            st.session_state[confirm_key] = False
        
        if st.session_state[confirm_key] or st.button(t("confirm_clear_logs"), key="confirm_clear_btn"):
            if hasattr(st.session_state, 'llm_logger'):
                st.session_state.llm_logger.clear_logs()
                st.session_state[confirm_key] = False
                st.success(t("logs_cleared"))
                st.rerun()
            else:
                st.error(t("llm_logger_not_initialized"))