"""
Error Selector UI module for Java Peer Review Training System.

This module provides the ErrorSelectorUI class for selecting Java error categories
to include in the generated code problems.
"""

import streamlit as st
import logging
import random
from typing import List, Dict, Any, Optional, Tuple, Callable
from utils.language_utils import t

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ErrorSelectorUI:
    """
    UI Component for selecting Java error categories.
    
    This class handles displaying and selecting Java error categories
    from java errors.
    """
    
    def __init__(self):
        """Initialize the ErrorSelectorUI component with empty selections."""
        # Track selected categories - initialize with empty collections if not in session state
        if "selected_error_categories" not in st.session_state:
            st.session_state.selected_error_categories = {
               "java_errors": []
            }
        elif not isinstance(st.session_state.selected_error_categories, dict):
            # Fix if it's not a proper dictionary
            st.session_state.selected_error_categories = {
                "java_errors": []
            }
        elif "java_errors" not in st.session_state.selected_error_categories:
            # Make sure java_errors key exists
            st.session_state.selected_error_categories["java_errors"] = []
        
        # Track error selection mode
        if "error_selection_mode" not in st.session_state:
            st.session_state.error_selection_mode = "advanced"
        
        # Track expanded categories
        if "expanded_categories" not in st.session_state:
            st.session_state.expanded_categories = {}
            
        # Track selected specific errors - initialize as empty list
        if "selected_specific_errors" not in st.session_state:
            st.session_state.selected_specific_errors = []
    
    def render_category_selection(self, all_categories: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Render the error category selection UI for advanced mode with enhanced styling and layout.
        Each error category from Java_code_review_errors.json is displayed as a visually distinct card.
        Works with both English and Traditional Chinese.
        
        Args:
            all_categories: Dictionary with 'java_errors' categories
            
        Returns:
            Dictionary with selected categories
        """
        st.subheader(t("select_error_categories"))
        
        # Add help text explaining how this mode works
        st.info(t("advanced_mode_help"))
        
        java_error_categories = all_categories.get("java_errors", [])
        
        # Ensure the session state structure is correct
        if "selected_error_categories" not in st.session_state:
            st.session_state.selected_error_categories = {"java_errors": []}
        if "java_errors" not in st.session_state.selected_error_categories:
            st.session_state.selected_error_categories["java_errors"] = []
        
        # Get the current selection state from session
        current_selections = st.session_state.selected_error_categories.get("java_errors", [])
        
        # Use a card-based grid layout for categories
        st.markdown('<div class="problem-area-grid">', unsafe_allow_html=True)
        
        # Define category icons and descriptions for better visual appeal
        category_info = {
            "Logical": {
                "icon": "🧠",
                "description": t("logical_desc")
            },
            "Syntax": {
                "icon": "🔍",
                "description": t("syntax_desc")
            },
            "Code Quality": {
                "icon": "✨",
                "description": t("code_quality_desc")
            },
            "Standard Violation": {
                "icon": "📏",
                "description": t("standard_violation_desc")
            },
            "Java Specific": {
                "icon": "☕",
                "description": t("java_specific_desc")
            },
            # Chinese category mappings
            "邏輯錯誤": {
                "icon": "🧠",
                "description": t("logical_desc")
            },
            "語法錯誤": {
                "icon": "🔍",
                "description": t("syntax_desc")
            },
            "程式碼品質": {
                "icon": "✨",
                "description": t("code_quality_desc")
            },
            "標準違規": {
                "icon": "📏",
                "description": t("standard_violation_desc")
            },
            "Java 特定錯誤": {
                "icon": "☕",
                "description": t("java_specific_desc")
            }
        }
        
        # Generate cards for each category
        for i, category in enumerate(java_error_categories):
            # Create a unique and safe key for this category
            category_key = f"java_category_{i}"
            
            # Check if category is already selected from session state
            is_selected = category in current_selections
            
            # Get icon and description - fallback to defaults if not found
            icon = category_info.get(category, {}).get("icon", "📁")
            description = category_info.get(category, {}).get("description", t("error_category"))
            
            # Get translated category name - if it's already in the correct language, this will just return the original
            category_name = t(category.lower()) if category.lower() in ["logical", "syntax", "code_quality", "standard_violation", "java_specific"] else category
            
            # Create a card with toggle effect for each category
            selected_class = "selected" if is_selected else ""
            st.markdown(f"""
            <div class="problem-area-card {selected_class}" id="{category_key}_card" 
                onclick="this.classList.toggle('selected'); 
                        document.getElementById('{category_key}_checkbox').click();">
                <div class="problem-area-title">
                    {icon} {category_name}
                    <span class="icon">{'✓' if is_selected else ''}</span>
                </div>
                <p class="problem-area-description">{description}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Hidden checkbox to track state (will be clicked by the card's onclick handler)
            # Use index-based unique keys instead of category text
            selected = st.checkbox(
                f"Category {i}",  # Just a label, won't be displayed
                key=category_key,
                value=is_selected,
                label_visibility="collapsed"  # Hide the actual checkbox
            )
            
            # Update selection state based on checkbox
            if selected:
                if category not in current_selections:
                    current_selections.append(category)
            else:
                if category in current_selections:
                    current_selections.remove(category)
        
        # Close the grid container
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Selection summary
        st.write("### " + t("selected_categories"))
        if not current_selections:
            st.warning(t("no_categories"))
        else:
            # Display selected categories with visual enhancements
            st.markdown('<div class="selected-categories">', unsafe_allow_html=True)
            for i, category in enumerate(current_selections):
                icon = category_info.get(category, {}).get("icon", "📁")
                category_name = t(category.lower()) if category.lower() in ["logical", "syntax", "code_quality", "standard_violation", "java_specific"] else category
                
                # Use index-based unique identifier for each category display
                st.markdown(f"""
                <div class="selected-category-item" id="selected_category_{i}">
                    <span class="category-icon">{icon}</span>
                    <span class="category-name">{category_name}</span>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Update selections in session state
        st.session_state.selected_error_categories["java_errors"] = current_selections
        
        return st.session_state.selected_error_categories
    
    def render_specific_error_selection(self, error_repository) -> List[Dict[str, Any]]:
        """
        Render UI for selecting specific errors to include in generated code.
        Each group in Java_code_review_errors.json is displayed as a tab.
        
        Args:
            error_repository: Repository for accessing Java error data
            
        Returns:
            List of selected specific errors
        """
        st.subheader(t("select_specific_errors"))
        
        # Get all categories
        all_categories = error_repository.get_all_categories()
        java_error_categories = all_categories.get("java_errors", [])
        
        # Container for selected errors
        if "selected_specific_errors" not in st.session_state:
            st.session_state.selected_specific_errors = []
            
        # Check if there are any categories to display
        if not java_error_categories:
            st.warning("No error categories found. Please check that the error repository is properly configured.")
            return st.session_state.selected_specific_errors
            
        # Create tabs for each error category
        error_tabs = st.tabs(java_error_categories)

        # For each category tab
        for i, category in enumerate(java_error_categories):
            with error_tabs[i]:
                # Get errors for this category
                errors = error_repository.get_category_errors(category)
                if not errors:
                    st.info(f"{t('no_errors_found')} {category} {t('category')}.")
                    continue
                    
                # Display each error with a select button
                for j, error in enumerate(errors):
                    # Handle potential missing field names
                    error_name = error.get("error_name", "Unknown")
                    description = error.get("description", "")
                    
                    # Check if already selected
                    is_selected = any(
                        e["name"] == error_name and e["category"] == category
                        for e in st.session_state.selected_specific_errors
                    )
                    
                    # Add select button with an index to ensure unique keys
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.markdown(f"**{error_name}**")
                        st.markdown(f"*{description}*")
                    with col2:
                        if not is_selected:
                            # Add indices to ensure key uniqueness
                            unique_key = f"select_{i}_{j}_{category}"
                            if st.button(t("select"), key=unique_key):
                                st.session_state.selected_specific_errors.append({
                                    "type": "java_error",
                                    "category": category,
                                    "name": error_name,
                                    "description": description,
                                    "implementation_guide": error.get("implementation_guide", "")
                                })
                                st.rerun()
                        else:
                            # Just display "Selected" text without a button
                            st.success(t("selected"))
                    
                    st.markdown("---")
        
        # Show selected errors
        st.subheader(t("selected_issues"))
        
        if not st.session_state.selected_specific_errors:
            st.info(t("no_specific_issues"))
        else:
            for idx, error in enumerate(st.session_state.selected_specific_errors):
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"**{error['category']} - {error['name']}**")
                    st.markdown(f"*{error['description']}*")
                with col2:
                    # Use numerical index only to avoid potential issues with Chinese characters in keys
                    remove_key = f"remove_{idx}"
                    if st.button(t("remove"), key=remove_key):
                        st.session_state.selected_specific_errors.pop(idx)
                        st.rerun()
        
        return st.session_state.selected_specific_errors
        
    def render_mode_selector(self) -> str:
        """
        Render the mode selector UI with improved mode switching behavior.
        
        Returns:
            Selected mode ("advanced" or "specific")
        """
        st.markdown("#### " + t("error_selection_mode"))
        
        # Create a more descriptive selection with radio buttons
        mode_options = [
            t("advanced_mode"),
            t("specific_mode")
        ]
        
        # Convert session state to index
        current_mode = st.session_state.error_selection_mode
        current_index = 0
        if current_mode == "specific":
            current_index = 1
        
        # Error selection mode radio buttons with CSS class for styling
        st.markdown('<div class="error-mode-radio">', unsafe_allow_html=True)
        selected_option = st.radio(
            t("error_selection_prompt"),
            options=mode_options,
            index=current_index,
            key="error_mode_radio",
            label_visibility="collapsed",
            horizontal=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Update error selection mode based on selection
        new_mode = st.session_state.error_selection_mode
        if t("advanced_mode") in selected_option and st.session_state.error_selection_mode != "advanced":
            new_mode = "advanced"
        elif t("specific_mode") in selected_option and st.session_state.error_selection_mode != "specific":
            new_mode = "specific"
        
        # Only update if the mode has changed
        if new_mode != st.session_state.error_selection_mode:
            # Store previous mode for reference
            previous_mode = st.session_state.error_selection_mode
            
            # Update the mode
            st.session_state.error_selection_mode = new_mode
                
            # Initialize or reset appropriate selections when mode changes
            if new_mode == "specific":
                # Make sure selected_specific_errors exists
                if "selected_specific_errors" not in st.session_state:
                    st.session_state.selected_specific_errors = []
        
        
        return st.session_state.error_selection_mode
    
    def get_code_params_for_level(self, user_level: str = None) -> Dict[str, str]:
        """
        Get code generation parameters automatically based on user level
        without displaying UI controls.
        """
        # Normalize the user level to lowercase and default to medium if None
        normalized_level = user_level.lower() if user_level else "medium"
        
        # Set appropriate difficulty based on normalized user level
        difficulty_mapping = {
            "basic": f"{t('easy')}",
            "medium": f"{t('medium')}",
            "senior": f"{t('hard')}"
        }
        difficulty_level = difficulty_mapping.get(normalized_level, "medium")
        
        # Set code length based on difficulty
        length_mapping = {
           f"{t('easy')}": f"{t('short')}",
           f"{t('medium')}": f"{t('medium')}",
           f"{t('hard')}": f"{t('long')}"
        }
        code_length = length_mapping.get(difficulty_level, "medium")
       
        # Update session state for consistency
        st.session_state.difficulty_level = difficulty_level.capitalize()
        st.session_state.code_length = code_length.capitalize()
        
        return {
            "difficulty_level": difficulty_level,
            "code_length": code_length
        }