"""
Review Tab UI module for Java Peer Review Training System.

This module provides the functions for rendering the review submission tab
and handling student reviews.
"""

import streamlit as st
import logging
import time
from typing import Dict, List, Any, Optional, Callable
import datetime
from utils.language_utils import t, get_current_language, get_state_attribute

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# In ui/review_tab.py
def process_student_review(workflow, student_review: str):
    """
    Process a student review with progress indicator and improved error handling.
    Show immediate feedback to the student.
    
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
            error_msg = f"{t('error')} processing student review: {str(e)}"
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
    if not hasattr(st.session_state.workflow_state, 'code_snippet') or not st.session_state.workflow_state.code_snippet:
        st.info(f"{t('no_code_generated')}")
        return
    
    # Get known problems for instructor view
    known_problems = []
    
    # Extract known problems from evaluation result
    if (hasattr(st.session_state.workflow_state, 'evaluation_result') and 
        st.session_state.workflow_state.evaluation_result and 
        'found_errors' in st.session_state.workflow_state.evaluation_result):
        found_errors = st.session_state.workflow_state.evaluation_result.get('found_errors', [])
        if found_errors:
            known_problems = found_errors
    
    # If we couldn't get known problems from evaluation, try to get from selected errors
    if not known_problems and hasattr(st.session_state.workflow_state, 'selected_specific_errors'):
        selected_errors = st.session_state.workflow_state.selected_specific_errors
        if selected_errors:
            # Format selected errors to match expected format
            known_problems = [
                f"{error.get('type', '').upper()} - {error.get('name', '')}" 
                for error in selected_errors
            ]
    
    # Display the code using the workflow state's code snippet and known problems
    code_display_ui.render_code_display(
        st.session_state.workflow_state.code_snippet, 
        known_problems=known_problems
    )
    
    # Get current review state
    current_iteration = getattr(st.session_state.workflow_state, 'current_iteration', 1)
    max_iterations = getattr(st.session_state.workflow_state, 'max_iterations', 3)
    
    # Get the latest review if available
    latest_review = None
    targeted_guidance = None
    review_analysis = None
    
    if hasattr(st.session_state.workflow_state, 'review_history') and st.session_state.workflow_state.review_history:
        if len(st.session_state.workflow_state.review_history) > 0:
            latest_review = st.session_state.workflow_state.review_history[-1]
            targeted_guidance = getattr(latest_review, 'targeted_guidance', None)
            review_analysis = getattr(latest_review, 'analysis', {})

    all_errors_found = False
    if review_analysis:
        identified_count = review_analysis.get("identified_count", 0)
        total_problems = review_analysis.get("total_problems", 0)
        if identified_count == total_problems and total_problems > 0:
            all_errors_found = True
    
    # Only allow submission if we're under the max iterations
    if current_iteration <= max_iterations and not st.session_state.workflow_state.review_sufficient and not all_errors_found:
        # Get the current student review (empty for first iteration)
        student_review = ""
        if latest_review is not None:
            student_review = latest_review.student_review
        
        # Define submission callback
        def on_submit_review(review_text):
            logger.info(f"Submitting review (iteration {current_iteration})")
            
            # Make sure we access and update the workflow_state directly
            state = st.session_state.workflow_state
            
            # Update state with the new review
            updated_state = workflow.submit_review(state, review_text)
            
            # Update session state with the new state
            st.session_state.workflow_state = updated_state
            
            # Check if this was the last iteration or review is sufficient
            if updated_state.current_iteration >= updated_state.max_iterations or updated_state.review_sufficient:
                logger.info(t("review_process_complete"))
                # Switch to feedback tab (index 2)
                st.session_state.active_tab = 2
                # Force rerun to update UI
            st.rerun()
        
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
        if st.session_state.workflow_state.review_sufficient or all_errors_found:
            st.success(f"{t('all_errors_found')}")
        else:
            st.warning(t("iterations_completed").format(max_iterations=max_iterations))
        
        if st.button(f"{t('view_feedback')}"):
            st.session_state.active_tab = 2  # 2 is the index of the feedback tab
            st.rerun()
        
        # Automatically switch to feedback tab if not already there
        if st.session_state.active_tab != 2:
            st.session_state.active_tab = 2
            st.rerun()