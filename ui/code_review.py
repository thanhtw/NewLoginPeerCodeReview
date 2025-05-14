"""
Code Review UI module for Java Peer Review Training System.

This module provides components for displaying Java code snippets,
handling student review input, and processing review submissions.
"""

import streamlit as st
import logging
import time
import datetime
from typing import List, Dict, Any, Optional, Tuple, Callable
from utils.code_utils import add_line_numbers
from utils.language_utils import t, get_current_language, get_state_attribute, get_field_value


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
                            f'{t("you_identified")} {review_analysis[t("identified_count")]} {t("of")} '
                            f'{review_analysis[t("total_problems")]} {t("issues")} '
                            f'({review_analysis[t("identified_percentage")]}) % '
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

def process_student_review(workflow, student_review: str):
    """
    Process a student review with progress indicator and improved error handling.
    Validate the format and show immediate feedback to the student.
    
    Args:
        workflow: The JavaCodeReviewGraph workflow instance
        student_review: The student's review text
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Show progress during analysis
    with st.status(t("processing_review"), expanded=True) as status:
        try:
            # Get current state
            if not hasattr(st.session_state, 'workflow_state'):
                status.update(label=f"{t('error')}: {t('workflow_not_initialized')}", state="error")
                st.session_state.error = t("please_generate_problem_first")
                return False
                
            state = st.session_state.workflow_state
            
            # Check if code snippet exists
            if not get_state_attribute(state, "code_snippet"):
                status.update(label=f"{t('error')}: {t('no_code_snippet_available')}", state="error")
                st.session_state.error = t("please_generate_problem_first")
                return False
            
            # Check if student review is empty
            if not student_review.strip():
                status.update(label=f"{t('error')}: {t('review_cannot_be_empty')}", state="error")
                st.session_state.error = t("please_enter_review")
                return False
            
            # Get the evaluator from the workflow to validate the format
            evaluator = workflow.workflow_nodes.evaluator
            
            if evaluator:
                # Validate the review format
                is_valid, reason = evaluator.validate_review_format(student_review)
                
                if not is_valid:
                    status.update(label=f"{t('error')}: {reason}", state="error")
                    st.session_state.error = reason
                    return False
            
            # Store the current review in session state for display consistency
            current_iteration = get_state_attribute(state, "current_iteration")
            st.session_state[f"submitted_review_{current_iteration}"] = student_review
            
            # Update status
            status.update(label=t("analyzing_review"), state="running")
            
            # Log submission attempt
            logger.info(f"Submitting review (iteration {current_iteration}): {student_review[:100]}...")
            
            # Create a placeholder for history display before submission processing
            # This ensures the UI shows the review even during processing
            if 'review_history_placeholder' not in st.session_state:
                st.session_state.review_history_placeholder = []
                
            # Add current review to temporary history for immediate display
            st.session_state.review_history_placeholder.append({
                "iteration_number": current_iteration,
                "student_review": student_review,
                "timestamp": datetime.datetime.now().isoformat()
            })
            
            # Submit the review and update the state
            updated_state = workflow.submit_review(state, student_review)
            
            # Clear the placeholder now that we have real data
            st.session_state.review_history_placeholder = []
            
            # Check for errors
            if updated_state.error:
                status.update(label=f"{t('error')}: {updated_state.error}", state="error")
                st.session_state.error = updated_state.error
                logger.error(f"{t('error')} during review analysis: {updated_state.error}")
                return False
            
            # Update session state
            st.session_state.workflow_state = updated_state
            
            # Log successful analysis
            logger.info(f"Review analysis complete for iteration {current_iteration}")
            
            # Update status
            status.update(label=t("analysis_complete"), state="complete")
            
            # Force UI refresh 
            st.rerun()
            
            return True
            
        except Exception as e:
            error_msg = f"{t('error')} {t('processing_student_review')}: {str(e)}"
            logger.error(error_msg)
            status.update(label=error_msg, state="error")
            st.session_state.error = error_msg
            return False

def render_review_tab(workflow, code_display_ui):
    """
    Render the review tab UI with proper state access.
    
    Args:
        workflow: JavaCodeReviewGraph workflow
        code_display_ui: CodeDisplayUI instance for displaying code
    """
    st.subheader(f"{t('review_java_code')}")
    
    # Access code from workflow_state instead of directly from session_state
    # This ensures we're using the correct state path
    if not hasattr(st.session_state, 'workflow_state') or not st.session_state.workflow_state:
        st.info(f"{t('no_code_generated')}")
        return
        
    # Check if we have a code snippet in the workflow state
    if not get_state_attribute(st.session_state.workflow_state, 'code_snippet'):
        st.info(f"{t('no_code_generated')}")
        return
    
    # Get known problems for instructor view
    known_problems = []
    
    # Extract known problems from evaluation result
    evaluation_result = get_state_attribute(st.session_state.workflow_state, 'evaluation_result')
    if evaluation_result and 'found_errors' in evaluation_result:
        known_problems = evaluation_result[t('found_errors')]
       
    
    # If we couldn't get known problems from evaluation, try to get from selected errors
    if not known_problems:
        selected_specific_errors = get_state_attribute(st.session_state.workflow_state, 'selected_specific_errors')
        if selected_specific_errors:
            # Format selected errors to match expected format
            known_problems = [
                f"{error.get('type', '').upper()} - {error.get('name', '')}" 
                for error in selected_specific_errors
            ]
   
    code_display_ui.render_code_display(
        get_state_attribute(st.session_state.workflow_state, 'code_snippet'), 
        known_problems=known_problems
    )
    
    # Get current review state
    current_iteration = get_state_attribute(st.session_state.workflow_state, 'current_iteration', 1)
    max_iterations = get_state_attribute(st.session_state.workflow_state, 'max_iterations', 3)
    
    # Get the latest review if available
    latest_review = None
    targeted_guidance = None
    review_analysis = None
    
    review_history = get_state_attribute(st.session_state.workflow_state, 'review_history')
    
    
    if review_history and len(review_history) > 0:
        latest_review = review_history[-1]       
        targeted_guidance = latest_review.dict().get("targeted_guidance", None)
        review_analysis = latest_review.dict().get("analysis", None)
      

    all_errors_found = False
    if review_analysis:
        identified_count = review_analysis[t('identified_count')] 
        total_problems =  review_analysis[t('total_problems')]
        if identified_count == total_problems and total_problems > 0:
            all_errors_found = True
    
    # Only allow submission if we're under the max iterations
    review_sufficient = get_state_attribute(st.session_state.workflow_state, 'review_sufficient', False)
    if current_iteration <= max_iterations and not review_sufficient and not all_errors_found:
        # Get the current student review (empty for first iteration)
        student_review = ""
        if latest_review is not None:
            student_review = get_state_attribute(latest_review, 'student_review', "")
        
        # Define submission callback
        def on_submit_review(review_text):
            logger.info(f"Submitting review (iteration {current_iteration})")
            process_student_review(workflow, review_text)
        
        # Render review input with current state
        code_display_ui.render_review_input(
            student_review=student_review,
            on_submit_callback=on_submit_review,
            iteration_count=current_iteration,
            max_iterations=max_iterations,
            targeted_guidance=targeted_guidance,
            review_analysis=review_analysis
        )
    else:
        # Display appropriate message based on why review is blocked
        if review_sufficient or all_errors_found:
            st.success(f"{t('all_errors_found')}")
            
            # Add the View Feedback button
            if st.button(f"{t('view_feedback')}", key="automatic_feedback_button"):
                st.session_state.active_tab = 2  # 2 is the index of the feedback tab
                st.rerun()
                
            # Add a flag to prevent infinite reruns
            if not st.session_state.get("feedback_tab_switch_attempted", False):
                # Set the flag to indicate we've attempted to switch
                st.session_state.feedback_tab_switch_attempted = True
                st.session_state.active_tab = 2
                st.rerun()
        else:
            # For normal completion (not all errors found), just show the warning
            st.warning(t("iterations_completed").format(max_iterations=max_iterations))
            
            if st.button(f"{t('view_feedback')}", key="manual_feedback_button"):
                st.session_state.active_tab = 2
                st.rerun()