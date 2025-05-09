"""
Code Display UI module for Java Peer Review Training System.

This module provides the CodeDisplayUI class for displaying Java code snippets
and handling student review input.
"""

import streamlit as st
import logging
from typing import List, Dict, Any, Optional, Tuple, Callable
from utils.code_utils import add_line_numbers
from utils.language_utils import t, get_current_language

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CodeDisplayUI:
    """
    UI Component for displaying Java code snippets.
    
    This class handles displaying Java code snippets with syntax highlighting,
    line numbers, and optional instructor view.    """
    
    def render_code_display(self, code_snippet, known_problems: List[str] = None, instructor_mode: bool = False) -> None:
        if not code_snippet:
            st.info(t("no_code_generated_use_generate"))
            return

        if isinstance(code_snippet, str):
            display_code = code_snippet
        else:
            if hasattr(code_snippet, 'clean_code') and code_snippet.clean_code:
                display_code = code_snippet.clean_code
            else:
                st.warning(t("code_exists_but_empty"))
                return
        numbered_code = self._add_line_numbers(display_code)
        st.code(numbered_code, language="java")
               


    def _add_line_numbers(self, code: str) -> str:
        """Add line numbers to code snippet using shared utility."""
        return add_line_numbers(code)
    
    def render_review_input(self, student_review: str = "", 
                    on_submit_callback: Callable[[str], None] = None,
                    iteration_count: int = 1,
                    max_iterations: int = 3,
                    targeted_guidance: str = None,
                    review_analysis: Dict[str, Any] = None) -> None:
        """
        Render a professional text area for student review input with guidance.
        
        Args:
            student_review: Initial value for the text area
            on_submit_callback: Callback function when review is submitted
            iteration_count: Current iteration number
            max_iterations: Maximum number of iterations
            targeted_guidance: Optional guidance for the student
            review_analysis: Optional analysis of previous review attempt
        """
        
        # Review container start
        st.markdown('<div class="review-container">', unsafe_allow_html=True)
        
        # Review header with iteration badge if not the first iteration
        if iteration_count > 1:
            st.markdown(
                f'<div class="review-header">'
                f'<span class="review-title">{t("submit_review")}</span>'
                f'<span class="iteration-badge">{t("attempt")} {iteration_count} {t("of")} {max_iterations}</span>'
                f'</div>', 
                unsafe_allow_html=True
            )
        else:
            st.markdown(f'<div class="review-header"><span class="review-title">{t("submit_review")}</span></div>', unsafe_allow_html=True)
        
        # Create a layout for guidance and history
        if targeted_guidance or (review_analysis and iteration_count > 1):
            guidance_col, history_col = st.columns([2, 1])
            
            # Display targeted guidance if available (for iterations after the first)
            with guidance_col:
                if targeted_guidance and iteration_count > 1:
                    st.markdown(
                        f'<div class="guidance-box">'
                        f'<div class="guidance-title"><span class="guidance-icon">🎯</span> {t("review_guidance")}</div>'
                        f'{targeted_guidance}'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                    
                    # Show previous attempt results if available
                    if review_analysis:
                        st.markdown(
                            f'<div class="analysis-box">'
                            f'<div class="guidance-title"><span class="guidance-icon">📊</span> {t("previous_results")}</div>'
                            f'{t("you_identified")} {review_analysis.get("identified_count", 0)} {t("of")} '
                            f'{review_analysis.get("total_problems", 0)} {t("issues")} '
                            f'({review_analysis.get("identified_percentage", 0):.1f}%). '
                            f'{t("try_find_more_issues")}'
                            f'</div>',
                            unsafe_allow_html=True
                        )
            
            # Display previous review if available
            with history_col:
                if student_review and iteration_count > 1:
                    st.markdown(f'<div class="guidance-title"><span class="guidance-icon">📝</span> {t("previous_review")}</div>', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="review-history-box">'
                        f'<pre style="margin: 0; white-space: pre-wrap; font-size: 0.85rem; color: var(--text);">{student_review}</pre>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
        
        # Display review guidelines - UPDATED for natural language
        with st.expander(f"📋 {t('review_guidelines')}", expanded=False):
            st.markdown(f"""
            ### {t('how_to_write')}
            
            1. **{t('be_specific')}**
            2. **{t('be_comprehensive')}**
            3. **{t('be_constructive')}**
            4. **{t('check_for')}**
            - {t('syntax_compilation_errors')}
            - {t('logical_errors_bugs')}
            - {t('naming_conventions')}
            - {t('code_style_formatting')}
            - {t('documentation_completeness')}
            - {t('security_vulnerabilities')}
            - {t('efficiency_performance')}
            5. **{t('format_your_review')}**
            ```
            {t('review_format_example')}
            ```
            
            ### {t('review_example')}
            
            ```
            {t('example_review_comment1')}
            
            {t('example_review_comment2')}
            
            {t('example_review_comment3')}
            
            {t('example_review_comment4')}
            ```
            
            {t('formal_categories_note')}
            """)
        
        # Get or update the student review
        st.write(f"### {t('your_review')}:")
        
        # Create a unique key for the text area
        text_area_key = f"student_review_input_{iteration_count}"
        
        # Initialize with previous review text only on first load of this iteration
        initial_value = ""
        if iteration_count == 1 or not student_review:
            initial_value = ""  # Start fresh for first iteration or if no previous review
        else:
            # For subsequent iterations, preserve existing input in session state if any
            if text_area_key in st.session_state:
                initial_value = st.session_state[text_area_key]
            else:
                initial_value = ""  # Start fresh in new iterations
        
        # Get or update the student review with custom styling
        student_review_input = st.text_area(
            t("enter_review"),
            value=initial_value, 
            height=300,
            key=text_area_key,
            placeholder=t("review_placeholder"),
            label_visibility="collapsed",
            help=t("review_help_text")
        )
        
        # Create button container for better layout
        st.markdown('<div class="button-container">', unsafe_allow_html=True)
        
        # Submit button with professional styling
        submit_text = t("submit_review_button") if iteration_count == 1 else f"{t('submit_review_button')} ({t('attempt')} {iteration_count}/{max_iterations})"
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown('<div class="submit-button">', unsafe_allow_html=True)
            submit_button = st.button(submit_text, type="primary", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="clear-button">', unsafe_allow_html=True)
            clear_button = st.button(t("clear"), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)  # Close button container
        
        # Handle clear button
        if clear_button:
            st.session_state[text_area_key] = ""
            st.rerun()
        
        # Handle submit button with improved validation
        if submit_button:
            if not student_review_input.strip():
                st.error(t("please_enter_review"))
            elif on_submit_callback:
                # Show a spinner while processing
                with st.spinner(t("processing_review")):
                    # Call the submission callback
                    on_submit_callback(student_review_input)
                    
                    # Store the submitted review in session state for this iteration
                    if f"submitted_review_{iteration_count}" not in st.session_state:
                        st.session_state[f"submitted_review_{iteration_count}"] = student_review_input
        
        # Close review container
        st.markdown('</div>', unsafe_allow_html=True)