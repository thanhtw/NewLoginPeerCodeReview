"""
Authentication UI module for Java Peer Review Training System.

This module provides the AuthUI class for handling user authentication,
registration, and profile management using local JSON files.
"""

import streamlit as st
import logging
import time
from typing import Dict, Any, Optional, Callable
import os
from pathlib import Path
import base64

from auth.mysql_auth import MySQLAuthManager
from utils.language_utils import t, get_current_language

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
    
    def _load_image(self, file_name, width=100):
        """Load and encode an image for HTML display."""
        # Determine the path to the image
        script_dir = Path(__file__).parent.parent
        image_path = script_dir / "static" / "images" / file_name
        
        # Check if the image exists
        if not image_path.exists():
            return ""
            
        # Get the static URL for the image
        try:
            with open(image_path, "rb") as img_file:
                img_bytes = img_file.read()
                encoded = base64.b64encode(img_bytes).decode()
                return f'<img src="data:image/png;base64,{encoded}" width="{width}">'
        except Exception as e:
            logger.error(f"Error loading image {file_name}: {str(e)}")
            return ""
    
    def render_auth_page(self) -> bool:
        """
        Render the authentication page with login and registration forms.
        
        Returns:
            bool: True if user is authenticated, False otherwise
        """
        # Load and display a logo if available
        logo_html = self._load_image("java_logo.png", width=120)
        
        # Apply custom CSS for the login page
        st.markdown("""
        <style>
        .auth-container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }
        .auth-header {
            text-align: center;
            margin-bottom: 20px;
        }
        .auth-form {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .auth-form h3 {
            margin-bottom: 20px;
            color: #4c68d7;
            text-align: center;
        }
        .auth-divider {
            text-align: center;
            margin: 20px 0;
            color: #666;
        }
        .auth-footer {
            text-align: center;
            margin-top: 20px;
            font-size: 14px;
            color: #666;
        }
        .demo-section {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 10px;
        }
        </style>
        """, unsafe_allow_html=True)

        # Main container
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
            # Login form
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
                            "display_name": result.get("display_name"),
                            "email": result.get("email"),
                            "level": result.get("level", "basic")
                        }                     
                        st.success(t("login") + " " + t("login_failed"))
                        
                        # Force UI refresh
                        st.rerun()
                    else:
                        st.error(f"{t('login_failed')}: {result.get('error', t('invalid_credentials'))}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            # Registration form
            st.markdown('<div class="auth-form">', unsafe_allow_html=True)
            st.markdown(f'<h3>{t("register")}</h3>', unsafe_allow_html=True)
            
            display_name = st.text_input(t("display_name"), key="reg_name")
            email = st.text_input(t("email"), key="reg_email")
            password = st.text_input(t("password"), type="password", key="reg_password")
            confirm_password = st.text_input(t("confirm_password"), type="password", key="reg_confirm")
            
            # Student level selection
            level_options = ["Basic", "Medium", "Senior"]
            level_labels = {"en": level_options, "zh-tw": ["基礎", "中級", "高級"]}
            
            selected_level = st.selectbox(
                t("experience_level"),
                options=level_labels.get(get_current_language(), level_options),
                index=0,
                key="reg_level"
            )
            
            # Map the displayed level back to database value
            level_map = {
                "Basic": "basic", "Medium": "medium", "Senior": "senior",
                "基礎": "basic", "中級": "medium", "高級": "senior"
            }
            level = level_map.get(selected_level, "basic")
            
            if st.button(t("register"), use_container_width=True, key="register_button"):
                # Validate inputs
                if not display_name or not email or not password or not confirm_password:
                    st.error(t("fill_all_fields"))
                elif password != confirm_password:
                    st.error(t("passwords_mismatch"))
                else:
                    # Register user
                    result = self.auth_manager.register_user(
                        email=email,
                        password=password,
                        display_name=display_name,
                        level=level.lower()
                    )
                    
                    if result.get("success", False):
                        # Set authenticated state
                        st.session_state.auth["is_authenticated"] = True
                        st.session_state.auth["user_id"] = result.get("user_id")
                        st.session_state.auth["user_info"] = {
                            "display_name": result.get("display_name"),
                            "email": result.get("email"),
                            "level": result.get("level", "basic")
                        }
                        st.success(t("registration_failed"))
                        
                        # Force UI refresh
                        st.rerun()
                    else:
                        st.error(f"{t('registration_failed')}: {result.get('error', t('email_in_use'))}")
            st.markdown('</div>', unsafe_allow_html=True)
        # Close main container
        st.markdown('</div>', unsafe_allow_html=True)
        
        return st.session_state.auth["is_authenticated"]
    
    def render_user_profile(self):
        """Render the user profile section in the sidebar."""
        # Check if user is authenticated
        if not st.session_state.auth.get("is_authenticated", False):
            return
            
        # Get user info
        user_info = st.session_state.auth.get("user_info", {})
        display_name = user_info.get("display_name", "User")
        level = user_info.get("level", "basic").capitalize()     
        
        # Add styled profile section
        st.sidebar.markdown("""
        <style>
        .profile-container {
            padding: 15px;
            background-color: rgba(76, 104, 215, 0.1);
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .profile-name {
            font-weight: bold;
            font-size: 1.2em;
            margin-bottom: 5px;
        }
        .profile-item {
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid rgba(0,0,0,0.05);
        }
        .profile-label {
            color: #666;
        }
        .profile-value {
            font-weight: 500;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.sidebar.markdown(f"""
        <div class="profile-container">
            <div class="profile-name">{display_name}</div>
            <div class="profile-item">
                <span class="profile-label">{t("level")}:</span>
                <span class="profile-value">{level}</span>
            </div>
        """, unsafe_allow_html=True)
     
        # Get extended profile from database if user is not demo user
        if st.session_state.auth.get("user_id") != "demo-user":
            user_id = st.session_state.auth.get("user_id")
            try:
                profile = self.auth_manager.get_user_profile(user_id)
                if profile.get("success", False):
                    # Display additional stats
                    reviews = profile.get("reviews_completed", 0)
                    score = profile.get("score", 0)                   
                    st.sidebar.markdown(f"""
                    <div class="profile-item">
                        <span class="profile-label">{t("review_times")}:</span>
                        <span class="profile-value">{reviews}</span>
                    </div>
                    <div class="profile-item">
                        <span class="profile-label">{t("score")}:</span>
                        <span class="profile-value">{score}</span>
                    </div>
                    """, unsafe_allow_html=True)   
            except Exception as e:
                logger.error(f"Error getting user profile: {str(e)}")
                
        # Close profile container
        st.sidebar.markdown("</div>", unsafe_allow_html=True)
        
        # Application info
        st.sidebar.subheader(t("about"))
        st.sidebar.markdown(t("about_app"))
    
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
        logger.info(f"AuthUI: Updating stats for user {user_id}: accuracy={accuracy:.1f}%, score={score}")
        
        # IMPORTANT: Pass both accuracy AND score parameters to the auth manager
        result = self.auth_manager.update_review_stats(user_id, accuracy, score)

        if result and result.get("success", False):
            logger.info(f"Updated user statistics: reviews={result.get('reviews_completed')}, " +
                    f"score={result.get('score')}")
            
            # Update session state if level changed
            if result.get("level_changed", False):
                new_level = result.get("new_level")
                if new_level and st.session_state.auth.get("user_info"):
                    st.session_state.auth["user_info"]["level"] = new_level
                    logger.info(f"Updated user level in session to: {new_level}")
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
        # Skip database query for demo users
        if user_id == "demo-user":
            return st.session_state.auth.get("user_info", {}).get("level", "basic")
            
        try:
            # Query the database for the latest user info
            profile = self.auth_manager.get_user_profile(user_id)
            if profile.get("success", False):
                # Update the session state with the latest level
                level = profile.get("level", "basic")
                st.session_state.auth["user_info"]["level"] = level
                return level
            else:
                # Fallback to session state if query fails
                return st.session_state.auth.get("user_info", {}).get("level", "basic")
        except Exception as e:
            logger.error(f"Error getting user level from database: {str(e)}")
            # Fallback to session state
            return st.session_state.auth.get("user_info", {}).get("level", "basic")