"""
Code Display UI component for Java Peer Review Training System.

This module provides components for displaying Java code snippets
and handling student review input.
"""

import streamlit as st
import logging
import datetime
from typing import List, Dict, Any, Optional, Callable

from utils.code_utils import add_line_numbers
from utils.language_utils import t

# Configure logging
logger = logging.getLogger(__name__)

class CodeDisplayUI:
    """
    UI Component for displaying Java code snippets and handling review input.
    
    This class handles displaying Java code snippets with syntax highlighting,
    line numbers, and rendering review input forms.
    """
    
    def render_code_display(self, code_snippet, known_problems: List[str] = None, instructor_mode: bool = False) -> None:
        """
        Render a code snippet with line numbers.
        
        Args:
            code_snippet: Code snippet object or string
            known_problems: List of known problems for instructor view
            instructor_mode: Whether to show instructor view
        """
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
                
        numbered_code = add_line_numbers(display_code)
        st.code(numbered_code, language="java")
    
    def render_review_input(self, 
                          student_review: str = "", 
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
        # Review container
        st.markdown('<div class="review-container">', unsafe_allow_html=True)
        
        # Review header with iteration badge
        self._render_review_header(iteration_count, max_iterations)
        
        # Guidance and history layout
        if targeted_guidance:
            self._render_guidance_section(targeted_guidance, review_analysis, student_review, iteration_count)
        
        # Review guidelines
        self._render_review_guidelines()
        
        # Review input and submission
        submitted = self._render_review_form(iteration_count, on_submit_callback)
        
        # Close review container
        st.markdown('</div>', unsafe_allow_html=True)
    
    def _render_review_header(self, iteration_count: int, max_iterations: int) -> None:
        """Render the review header with iteration badge."""
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
    
    def _render_guidance_section(self, targeted_guidance: str, review_analysis: Dict[str, Any], student_review: str, iteration_count: int) -> None:
        """Render the guidance and history section."""
        guidance_col, history_col = st.columns([2, 1])
        
        with guidance_col:
            if targeted_guidance and iteration_count > 1:
                st.markdown(
                    f'<div class="guidance-box">'
                    f'<div class="guidance-title"><span class="guidance-icon">🎯</span> {t("review_guidance")}</div>'
                    f'{targeted_guidance}'
                    f'</div>',
                    unsafe_allow_html=True
                )
                
                if review_analysis:
                    st.markdown(
                        f'<div class="analysis-box">'
                        f'<div class="guidance-title"><span class="guidance-icon">📊</span> {t("previous_results")}</div>'
                        f'{t("you_identified")} {review_analysis[t("identified_count")]} {t("of")} '
                        f'{review_analysis[t("total_problems")]} {t("issues")} '
                        f'({review_analysis[t("identified_percentage")]:.1f}%) '
                        f'{t("try_find_more_issues")}'
                        f'</div>',
                        unsafe_allow_html=True
                    )
        
        with history_col:
            if student_review and iteration_count > 1:
                st.markdown(f'<div class="guidance-title"><span class="guidance-icon">📝</span> {t("previous_review")}</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="review-history-box">'
                    f'<pre style="margin: 0; white-space: pre-wrap; font-size: 0.85rem; color: var(--text);">{student_review}</pre>'
                    f'</div>',
                    unsafe_allow_html=True
                )
    
    def _render_review_guidelines(self) -> None:
        """Render the review guidelines in an expander."""
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
    
    def _render_review_form(self, iteration_count: int, on_submit_callback: Callable) -> bool:
        """Render the review form and handle submission."""
        st.write(f"### {t('your_review')}:")
        
        # Create unique key for text area
        text_area_key = f"student_review_input_{iteration_count}"
        
        # Get initial value
        initial_value = ""
        if iteration_count > 1 and text_area_key in st.session_state:
            initial_value = st.session_state[text_area_key]
        
        # Review input
        student_review_input = st.text_area(
            t("enter_review"),
            value=initial_value, 
            height=300,
            key=text_area_key,
            placeholder=t("review_placeholder"),
            label_visibility="collapsed",
            help=t("review_help_text")
        )
        
        # Buttons
        st.markdown('<div class="button-container">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            submit_text = t("submit_review_button") if iteration_count == 1 else f"{t('submit_review_button')} ({t('attempt')} {iteration_count})"
            submit_button = st.button(submit_text, type="primary", use_container_width=True)
        
        with col2:
            clear_button = st.button(t("clear"), use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Handle buttons
        if clear_button:
            st.session_state[text_area_key] = ""
            st.rerun()
        
        if submit_button:
            if not student_review_input.strip():
                st.error(t("please_enter_review"))
                return False
            elif on_submit_callback:
                with st.spinner(t("processing_review")):
                    on_submit_callback(student_review_input)
                    if f"submitted_review_{iteration_count}" not in st.session_state:
                        st.session_state[f"submitted_review_{iteration_count}"] = student_review_input
                return True
        
        return False


def render_review_tab(workflow, code_display_ui):
    """
    Render the review tab UI with proper state access.
    
    Args:
        workflow: JavaCodeReviewGraph workflow
        code_display_ui: CodeDisplayUI instance for displaying code
    """
    st.subheader(f"{t('review_java_code')}")
    
    # Check workflow state
    if not hasattr(st.session_state, 'workflow_state') or not st.session_state.workflow_state:
        st.info(f"{t('no_code_generated')}")
        return
        
    # Check code snippet
    if not hasattr(st.session_state.workflow_state, 'code_snippet') or not st.session_state.workflow_state.code_snippet:
        st.info(f"{t('no_code_generated')}")
        return
    
    # Get known problems for instructor view
    known_problems = _extract_known_problems(st.session_state.workflow_state)
    
    # Display code
    code_display_ui.render_code_display(
        getattr(st.session_state.workflow_state, 'code_snippet', None),
        known_problems=known_problems
    )
    
    # Handle review submission logic
    _handle_review_submission(workflow, code_display_ui)


def _extract_known_problems(state) -> List[str]:
    """Extract known problems from workflow state."""
    known_problems = []
    
    # Extract from evaluation result
    evaluation_result = getattr(state, 'evaluation_result', None)
    if evaluation_result and t('found_errors') in evaluation_result:
        known_problems = evaluation_result[t('found_errors')]
    
    # Fallback to selected errors
    if not known_problems:
        selected_specific_errors = getattr(state, 'selected_specific_errors', None)
        if selected_specific_errors:
            known_problems = [
                f"{error.get(t('type'), '').upper()} - {error.get(t('name'), '')}" 
                for error in selected_specific_errors
            ]
    
    return known_problems


def _handle_review_submission(workflow, code_display_ui):
    """Handle the review submission logic."""
    # Get current review state
    state = st.session_state.workflow_state
    current_iteration = getattr(state, 'current_iteration', 1)
    max_iterations = getattr(state, 'max_iterations', 3)
    
    # Get review data
    review_history = getattr(state, 'review_history', None)
    latest_review = review_history[-1] if review_history and len(review_history) > 0 else None
    
    # Extract review information
    targeted_guidance = None
    review_analysis = None
    student_review = ""
    
    if latest_review:
        targeted_guidance = getattr(latest_review, "targeted_guidance", None)
        review_analysis = getattr(latest_review, "analysis", None)
        student_review = getattr(latest_review, 'student_review', "")
    
    # Check if all errors found
    all_errors_found = False
    if review_analysis:
        identified_count = review_analysis.get(t('identified_count'), 0)
        total_problems = review_analysis.get(t('total_problems'), 0)
        if identified_count == total_problems and total_problems > 0:
            all_errors_found = True
    
    # Handle submission logic
    review_sufficient = getattr(state, 'review_sufficient', False)
    
    if current_iteration <= max_iterations and not review_sufficient and not all_errors_found:
        def on_submit_review(review_text):
            logger.debug(f"Submitting review (iteration {current_iteration})")
            _process_student_review(workflow, review_text)
        
        code_display_ui.render_review_input(
            student_review=student_review,
            on_submit_callback=on_submit_review,
            iteration_count=current_iteration,
            max_iterations=max_iterations,
            targeted_guidance=targeted_guidance,
            review_analysis=review_analysis
        )
    else:
        if review_sufficient or all_errors_found:
            st.success(f"{t('all_errors_found')}")
            if not st.session_state.get("feedback_tab_switch_attempted", False):
                st.session_state.feedback_tab_switch_attempted = True
                st.session_state.active_tab = 2
                st.rerun()
        else:
            st.warning(t("iterations_completed").format(max_iterations=max_iterations))


def _process_student_review(workflow, student_review: str) -> bool:
    """Process a student review with progress indicator."""
    with st.status(t("processing_review"), expanded=True) as status:
        try:
            # Validate workflow state
            if not hasattr(st.session_state, 'workflow_state'):
                status.update(label=f"{t('error')}: {t('workflow_not_initialized')}", state="error")
                st.session_state.error = t("please_generate_problem_first")
                return False
                
            state = st.session_state.workflow_state
            
            # Validate code snippet
            if not hasattr(state, "code_snippet") or state.code_snippet is None:
                status.update(label=f"{t('error')}: {t('no_code_snippet_available')}", state="error")
                st.session_state.error = t("please_generate_problem_first")
                return False
            
            # Validate review content
            if not student_review.strip():
                status.update(label=f"{t('error')}: {t('review_cannot_be_empty')}", state="error")
                st.session_state.error = t("please_enter_review")
                return False
            
            # Validate review format
            evaluator = workflow.workflow_nodes.evaluator
            if evaluator:
                is_valid, reason = evaluator.validate_review_format(student_review)
                if not is_valid:
                    status.update(label=f"{t('error')}: {reason}", state="error")
                    st.session_state.error = reason
                    return False
            
            # Store current review
            current_iteration = getattr(state, "current_iteration", 1)
            st.session_state[f"submitted_review_{current_iteration}"] = student_review
            
            # Update status
            status.update(label=t("analyzing_review"), state="running")
            
            # Submit review
            updated_state = workflow.submit_review(state, student_review)
            
            # Check for errors
            if updated_state.error:
                status.update(label=f"{t('error')}: {updated_state.error}", state="error")
                st.session_state.error = updated_state.error
                return False
            
            # Update session state
            st.session_state.workflow_state = updated_state
            
            # Complete
            status.update(label=t("analysis_complete"), state="complete")
            st.rerun()
            
            return True
            
        except Exception as e:
            error_msg = f"{t('error')} {t('processing_student_review')}: {str(e)}"
            logger.error(error_msg)
            status.update(label=error_msg, state="error")
            st.session_state.error = error_msg
            return False