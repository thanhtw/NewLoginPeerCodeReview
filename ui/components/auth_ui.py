"""
Authentication UI module for Java Peer Review Training System.

This module provides the AuthUI class for handling user authentication,
registration, and profile management using local JSON files.
"""

import streamlit as st
import logging
import time
from typing import Dict, Any, Optional, Callable, Tuple
import os
from pathlib import Path
import base64

from auth.mysql_auth import MySQLAuthManager
from utils.language_utils import t, get_current_language, set_language

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AuthUI:
    """
    UI Component for user authentication and profile management.
    
    This class handles the login, registration, and profile display interfaces
    for user authentication with a local JSON file.
    """
    def __init__(self):
        """Initialize the AuthUI component with local auth manager."""
        self.auth_manager = MySQLAuthManager()
        
        # Initialize session state for authentication
        if "auth" not in st.session_state:
            st.session_state.auth = {
                "is_authenticated": False,
                "user_id": None,
                "user_info": {}
            }
    
    def render_auth_page(self) -> bool:
        """
        Render the authentication page with login and registration forms.
        Uses t() function for all translations instead of hardcoded maps.
        
        Returns:
            bool: True if user is authenticated, False otherwise
        """
        
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        
        # Header with logo and title
        st.markdown(f"""
            <div class="auth-header">                
                <h1 style="color: rgb(178 185 213); margin-bottom: 5px;">{t('app_title')}</h1>
                <p style="font-size: 1.1rem; color: #666;">{t('app_subtitle')}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Create columns for login and registration
        col1, col2 = st.columns(2)
        
        with col1:
            # Login form - unchanged
            st.markdown('<div class="auth-form">', unsafe_allow_html=True)
            st.markdown(f'<h3>{t("login")}</h3>', unsafe_allow_html=True)
            
            email = st.text_input(t("email"), key="login_email")
            password = st.text_input(t("password"), type="password", key="login_password")
            
            if st.button(t("login"), use_container_width=True, key="login_button"):
                if not email or not password:
                    st.error(t("fill_all_fields"))
                else:
                    # Authenticate user
                    result = self.auth_manager.authenticate_user(email, password)                    
                    if result.get("success", False):
                        # Set authenticated state
                        st.session_state.auth["is_authenticated"] = True
                        st.session_state.auth["user_id"] = result.get("user_id")
                        st.session_state.auth["user_info"] = {
                            "display_name_en": result.get("display_name_en"),
                            "display_name_zh": result.get("display_name_zh"),
                            "email": result.get("email"),
                            "level_name_en": result.get("level_name_en"),
                            "level_name_zh": result.get("level_name_zh"),
                            "reviews_completed": result.get("reviews_completed"),
                            "score": result.get("score"),
                            "tutorial_completed": result.get("tutorial_completed", False)
                        }                     
                        st.success(t("login_success"))
                        
                        # Force UI refresh
                        st.rerun()
                    else:
                        st.error(f"{t('login_failed')}: {result.get('error', t('invalid_credentials'))}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            # Registration form - updated to use t() function
            st.markdown('<div class="auth-form">', unsafe_allow_html=True)
            st.markdown(f'<h3>{t("register")}</h3>', unsafe_allow_html=True)
            
            # Get the current language
            current_lang = get_current_language()
            
            # Primary display name (will be used for both languages if only one is provided)
            display_name = st.text_input(t("display_name"), key="reg_name")
            
            # Show language-specific name fields if needed
            show_lang_specific = st.checkbox(t("specify_different_names_per_language"), value=False, key="show_lang_names")
            
            display_name_en = display_name
            display_name_zh = display_name
            
            if show_lang_specific:
                col_a, col_b = st.columns(2)
                with col_a:
                    display_name_en = st.text_input(t("english_name"), value=display_name, key="reg_name_en")
                with col_b:
                    display_name_zh = st.text_input(t("chinese_name"), value=display_name, key="reg_name_zh")
            
            email = st.text_input(t("email"), key="reg_email")
            password = st.text_input(t("password"), type="password", key="reg_password")
            confirm_password = st.text_input(t("confirm_password"), type="password", key="reg_confirm")
            
            # Student level selection using t() function
            level_internal_values = ["basic", "medium", "senior"]
            level_options = [t(level) for level in level_internal_values]
            
            selected_level_index = st.selectbox(
                t("experience_level"),
                options=level_options,
                index=0,
                key="reg_level"
            )
            
            # Get the internal level value from the index
            level = level_internal_values[level_options.index(selected_level_index)]
            
            # Store level names for both languages
            level_name_en = t(level) if current_lang == "en" else ""
            level_name_zh = t(level) if current_lang == "zh" else ""
            
            # If we didn't get level names for both languages, we need to switch language temporarily
            if not level_name_en or not level_name_zh:
                # Save current language
                saved_language = get_current_language()
                
                # Get English level name
                if not level_name_en:
                    set_language("en")
                    level_name_en = t(level)
                
                # Get Chinese level name
                if not level_name_zh:
                    set_language("zh")
                    level_name_zh = t(level)
                
                # Restore original language
                set_language(saved_language)
            
            if st.button(t("register"), use_container_width=True, key="register_button"):
                # Validate inputs
                if not display_name or not email or not password or not confirm_password:
                    st.error(t("fill_all_fields"))
                elif password != confirm_password:
                    st.error(t("passwords_mismatch"))
                else:
                    # Register user with multilingual support
                    result = self.auth_manager.register_user(
                        email=email,
                        password=password,                        
                        display_name_en=display_name_en,
                        display_name_zh=display_name_zh,                        
                        level_name_en=level_name_en,
                        level_name_zh=level_name_zh
                    )
                    
                    # Handle registration result
                    if result.get("success", False):
                        # Set authenticated state
                        st.session_state.auth["is_authenticated"] = True
                        st.session_state.auth["user_id"] = result.get("user_id")
                        st.session_state.auth["user_info"] = {
                            "display_name": result.get("display_name"),
                            "display_name_en": result.get("display_name_en"),
                            "display_name_zh": result.get("display_name_zh"),
                            "email": result.get("email"),
                            "level": result.get("level", "basic"),
                            "level_name_en": result.get("level_name_en"),
                            "level_name_zh": result.get("level_name_zh"),
                            "tutorial_completed": False  # New users haven't completed tutorial
                        }                     
                        st.success(t("registration_success"))
                        
                        # Force UI refresh
                        st.rerun()
                    else:
                        st.error(f"{t('registration_failed')}: {result.get('error', t('email_in_use'))}")
            st.markdown('</div>', unsafe_allow_html=True)
        # Close main container
        st.markdown('</div>', unsafe_allow_html=True)
        
        return st.session_state.auth["is_authenticated"]
    
    def render_user_profile(self):
        """Render the user profile section in the sidebar with proper language support."""
        # Check if user is authenticated
        if not st.session_state.auth.get("is_authenticated", False):
            return
                
        # Get user info
        user_info = st.session_state.auth.get("user_info", {})       
        # Get current language
        current_lang = get_current_language()
        
        # Use the appropriate language field
        display_name_field = f"display_name_{current_lang}" if current_lang in ["en", "zh"] else "display_name_en"
        level_field = f"level_name_{current_lang}" if current_lang in ["en", "zh"] else "level_name_en"
        
        # Fallback to standard fields if multilingual ones are not available
        display_name = user_info.get(display_name_field, user_info.get("display_name", "User"))
        level = user_info.get(level_field, user_info.get("level", "basic")).capitalize()
        reviews_completed = user_info.get("reviews_completed", 0)
        score = user_info.get("score", 0)
        
        st.sidebar.markdown(f"""
        <div class="profile-container">
            <div class="profile-name">{display_name}</div>
            <div class="profile-item">
                <span class="profile-label">{t("level")}:</span>
                <span class="profile-value">{level}</span>
            </div>
            <div class="profile-item">
                <span class="profile-label">{t("review_times")}:</span>
                <span class="profile-value">{reviews_completed}</span>
            </div>
            <div class="profile-item">
                <span class="profile-label">{t("score")}:</span>
                <span class="profile-value">{score}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Application info
        st.sidebar.subheader(t("about"))
        st.sidebar.markdown(t("about_app"))
        
        # Add logout button
        st.sidebar.markdown("---")
        if st.sidebar.button(t("logout"), use_container_width=True, key="logout_btn"):
            self.logout()        
       
        
    
    def logout(self):
        """Handle user logout by clearing authentication state and triggering full reset."""
        logger.debug("User logout initiated")
        
        # Clear authentication session
        st.session_state.auth = {
            "is_authenticated": False,
            "user_id": None,
            "user_info": {}
        }
        
        # Trigger full reset to clear all workflow-related state
        st.session_state.full_reset = True
        # Show logout message
        st.success(t("logout_success"))
        # Force UI refresh
        st.rerun()

    def update_review_stats(self, accuracy: float, score: int = 0):
        """
        Update a user's review statistics after completing a review.
        
        Args:
            accuracy: The accuracy of the review (0-100 percentage)
            score: Number of errors detected in the review
        """
        # Check if user is authenticated
        if not st.session_state.auth.get("is_authenticated", False):
            return {"success": False, "error": "User not authenticated"}
                
        # Skip for demo user
        if st.session_state.auth.get("user_id") == "demo-user":
            return {"success": True, "message": "Demo user - no updates needed"}
                
        # Update stats in the database
        user_id = st.session_state.auth.get("user_id")
        
        # Ensure score is an integer
        score = int(score) if score else 0
        
        # Add debug logging
        logger.debug(f"AuthUI: Updating stats for user {user_id}: accuracy={accuracy:.1f}%, score={score}")
        
        # IMPORTANT: Pass both accuracy AND score parameters to the auth manager
        result = self.auth_manager.update_review_stats(user_id, accuracy, score)

        if result and result.get("success", False):
            logger.debug(f"Updated user statistics: reviews={result.get('reviews_completed')}, " +
                    f"score={result.get('score')}")
            
            # Update session state if level changed
            if result.get("level_changed", False):
                new_level = result.get("new_level")
                if new_level and st.session_state.auth.get("user_info"):
                    st.session_state.auth["user_info"]["level"] = new_level
                    logger.debug(f"Updated user level in session to: {new_level}")
        else:
            err_msg = result.get('error', 'Unknown error') if result else "No result returned"
            logger.error(f"Failed to update review stats: {err_msg}")
        
        return result
    
    def is_authenticated(self) -> bool:
        """
        Check if user is authenticated.
        
        Returns:
            bool: True if user is authenticated, False otherwise
        """
        return st.session_state.auth.get("is_authenticated", False)
    
    def get_user_level(self) -> str:
        """
        Get the user's level directly from the database.
        
        Returns:
            str: User's level (basic, medium, senior) or None if not authenticated
        """
        if not self.is_authenticated():
            return None
        
        user_id = st.session_state.auth.get("user_id")
            
        try:
            # Query the database for the latest user info
            profile = self.auth_manager.get_user_profile(user_id)           
            current_language = get_current_language()
            
            if profile.get("success", False):
                # Update the session state with the latest level
                level = profile.get("level_name_"+ current_language, "basic")
                st.session_state.auth["user_info"]["level"] = level
                return level
            else:
                # Fallback to session state if query fails
                return st.session_state.auth.get("user_info", {}).get("level", "basic")
        except Exception as e:
            logger.error(f"Error getting user level from database: {str(e)}")
            # Fallback to session state
            return st.session_state.auth.get("user_info", {}).get("level", "basic")
    
    def has_completed_tutorial(self) -> bool:
        """
        Check if the user has completed the tutorial.
        
        Returns:
            bool: True if user has completed tutorial, False otherwise
        """
        if not self.is_authenticated():
            return False
            
        # First check session state
        user_info = st.session_state.auth.get("user_info", {})
        tutorial_completed = user_info.get("tutorial_completed", False)
        
        # If not completed in session, check database
        if not tutorial_completed:
            user_id = st.session_state.auth.get("user_id")
            if user_id:
                try:
                    profile = self.auth_manager.get_user_profile(user_id)
                    if profile.get("success", False):
                        tutorial_completed = profile.get("tutorial_completed", False)
                        # Update session state
                        st.session_state.auth["user_info"]["tutorial_completed"] = tutorial_completed
                except Exception as e:
                    logger.error(f"Error checking tutorial completion status: {str(e)}")
        
        return tutorial_completed
    
    def mark_tutorial_completed(self) -> bool:
        """
        Mark the tutorial as completed for the current user.
        
        Returns:
            bool: True if successfully updated, False otherwise
        """
        if not self.is_authenticated():
            return False
            
        user_id = st.session_state.auth.get("user_id")
        if not user_id:
            return False
            
        try:
            # Update database
            result = self.auth_manager.update_tutorial_completion(user_id, True)
            
            if result.get("success", False):
                # Update session state
                st.session_state.auth["user_info"]["tutorial_completed"] = True
                logger.debug(f"Marked tutorial as completed for user {user_id}")
                return True
            else:
                logger.error(f"Failed to update tutorial completion: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error marking tutorial as completed: {str(e)}")
            return False
        