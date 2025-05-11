"""
UI package for Java Peer Review Training System.

This package contains UI components for the Streamlit interface
that handle user interaction and display of results.
"""

from ui.CodeGeneratorUI import CodeGeneratorUI
from ui.code_review import CodeDisplayUI
from ui.feedback_system import FeedbackSystem

__all__ = [
    'CodeGeneratorUI',
    'CodeDisplayUI',
    'FeedbackSystem'    
]