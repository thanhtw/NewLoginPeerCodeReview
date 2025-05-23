"""
UI package for Java Peer Review Training System.

This package contains UI components for the Streamlit interface
that handle user interaction and display of results.
"""

# Core UI components
from ui.components.code_generator import CodeGeneratorUI
from ui.components.code_display import CodeDisplayUI
from ui.components.feedback_system import FeedbackSystem
from ui.components.auth_ui import AuthUI


# UI utilities
from ui.utils.main_ui import (
    init_session_state,
    render_llm_logs_tab,
    create_enhanced_tabs,
    render_sidebar
)

# Animation components
from ui.components.animation import level_up_animation
from ui.components.tutorial import CodeReviewTutorial
from ui.components.profile_leaderboard import ProfileLeaderboardSidebar


__all__ = [
    # Core components
    'CodeGeneratorUI',
    'CodeDisplayUI', 
    'FeedbackSystem',
    'AuthUI',
    
    # UI utilities
    'init_session_state',
    'render_llm_logs_tab',
    'create_enhanced_tabs',
    'render_sidebar',
    
    # Animation components
    'level_up_animation',
    'CodeReviewTutorial',
    'ProfileLeaderboardSidebar'
]