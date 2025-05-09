"""
Feedback Tab UI module for Java Peer Review Training System.

This module provides the functions for rendering the feedback and analysis tab.
"""

import streamlit as st
import logging
import time
import traceback
from typing import Dict, List, Any, Optional, Callable
from utils.code_utils import generate_comparison_report
from utils.language_utils import t, get_current_language

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def render_feedback_tab(workflow, feedback_display_ui, auth_ui=None):
    """
    Render the feedback and analysis tab with enhanced visualization 
    and user statistics updating.
    
    Args:
        workflow: The JavaCodeReviewGraph workflow instance
        feedback_display_ui: FeedbackDisplayUI instance for rendering feedback
        auth_ui: Optional AuthUI instance for updating user statistics
    """
    state = st.session_state.workflow_state

    # Add debug message to check what's being passed
    logger.info(f"Feedback tab received auth_ui: {auth_ui is not None}")

    # Check if review process is completed
    review_completed = False
    if hasattr(state, 'current_iteration') and hasattr(state, 'max_iterations'):
        if state.current_iteration > state.max_iterations:
            review_completed = True
            logger.info(t("review_completed_max_iterations"))
        elif hasattr(state, 'review_sufficient') and state.review_sufficient:
            review_completed = True
            logger.info(t("review_completed_sufficient"))
        
        # Check for all errors identified - HIGHEST PRIORITY CHECK
        if state.review_history and len(state.review_history) > 0:
            latest_review = state.review_history[-1]
            analysis = latest_review.analysis if hasattr(latest_review, 'analysis') else {}
            
            identified_count = analysis.get("identified_count", 0)
            total_problems = analysis.get("total_problems", 0) 
            
            if identified_count == total_problems and total_problems > 0:
                review_completed = True
                if not hasattr(state, 'review_sufficient') or not state.review_sufficient:
                    # Ensure state is consistent
                    state.review_sufficient = True
                logger.info(f"{t('review_completed_all_identified')} {total_problems} {t('issues')}")

    # Block access if review not completed
    if not review_completed:
        st.warning(f"{t('complete_review_first')}")
        st.info(f"{t('current_process_review1')} {state.current_iteration-1}/{state.max_iterations} {t('current_process_review2')}")       
        return
    
    # Get the latest review analysis and history
    latest_review = None
    review_history = []
    
    # Make sure we have review history
    if state.review_history:
        latest_review = state.review_history[-1]
        
        # Convert review history to the format expected by FeedbackDisplayUI
        for review in state.review_history:
            review_history.append({
                "iteration_number": review.iteration_number,
                "student_review": review.student_review,
                "review_analysis": review.analysis
            })
    
    # If we have review history but no comparison report, generate one
    if latest_review and latest_review.analysis and not state.comparison_report:
        try:
            # Get the known problems from the evaluation result instead of code_snippet.known_problems
            if state.evaluation_result and 'found_errors' in state.evaluation_result:
                found_errors = state.evaluation_result.get('found_errors', [])
                
                # Generate a comparison report if it doesn't exist
                state.comparison_report = generate_comparison_report(
                    found_errors,
                    latest_review.analysis
                )
                logger.info(t("generated_comparison_report"))
        except Exception as e:
            logger.error(f"{t('error')} {t('generating_comparison_report')}: {str(e)}")
            logger.error(traceback.format_exc())  # Log full stacktrace
            if not state.comparison_report:
                state.comparison_report = (
                    f"# {t('review_feedback')}\n\n"
                    f"{t('error_generating_report')} "
                    f"{t('check_review_history')}."
                )
    
    # Get the latest review analysis
    latest_analysis = latest_review.analysis if latest_review else None
    
    # Update user statistics if AuthUI is provided and we have analysis
    if auth_ui and latest_analysis:       
        current_iteration = getattr(state, 'current_iteration', 1) 
        identified_count = latest_analysis.get("identified_count", 0)
        stats_key = f"stats_updated_{current_iteration}_{identified_count}"
    
    if stats_key not in st.session_state:
        try:
            # Extract accuracy and identified_count from the latest review
            accuracy = latest_analysis.get("identified_percentage", 0)
            
            # Log details before update
            logger.info(f"{t('preparing_update_stats')}: {t('accuracy')}={accuracy:.1f}%, " + 
                    f"{t('score')}={identified_count} ({t('identified_count')}), key={stats_key}")
            
            # Update user stats with identified_count as score
            result = auth_ui.update_review_stats(accuracy, identified_count)
            
            # Store the update result for debugging
            st.session_state[stats_key] = result
            
            # Log the update result
            if result and result.get("success", False):
                logger.info(f"{t('successfully_updated_statistics')}: {result}")
                
                # Add explicit UI message about the update
                st.success(f"{t('statistics_updated')}! {t('added')} {identified_count} {t('to_your_score')}.")
                
                # Show level promotion message if level changed
                if result.get("level_changed", False):
                    old_level = result.get("old_level", "").capitalize()
                    new_level = result.get("new_level", "").capitalize()
                    st.balloons()  # Add visual celebration effect
                    st.success(f"🎉 {t('congratulations')}! {t('level_upgraded')} {old_level} {t('to')} {new_level}!")
                
                # Give the database a moment to complete the update
                time.sleep(0.5)
                
                # Force UI refresh after successful update
                st.rerun()
            else:
                err_msg = result.get('error', t('unknown_error')) if result else t('no_result_returned')
                logger.error(f"{t('failed_update_statistics')}: {err_msg}")
                st.error(f"{t('failed_update_statistics')}: {err_msg}")
        except Exception as e:
            logger.error(f"{t('error')} {t('updating_user_statistics')}: {str(e)}")
            logger.error(traceback.format_exc())
            st.error(f"{t('error')} {t('updating_statistics')}: {str(e)}")
    
    # Display feedback results
    feedback_display_ui.render_results(
        comparison_report=state.comparison_report,
        review_summary=state.review_summary,
        review_analysis=latest_analysis,
        review_history=review_history        
    )
    
    # Add a button to start a new session
    st.markdown("---")
    new_session_col1, new_session_col2 = st.columns([3, 1])
    with new_session_col1:
        st.markdown(f"### {t('new_session')}")
        st.markdown(t("new_session_desc"))
    with new_session_col2:
        if st.button(t("start_new_session"), use_container_width=True):
            # Clear all update keys in session state
            keys_to_remove = [k for k in st.session_state.keys() if k.startswith("stats_updated_")]
            for key in keys_to_remove:
                del st.session_state[key]
                
            # Set the full reset flag
            st.session_state.full_reset = True
            
            # Return to the generate tab
            st.session_state.active_tab = 0
            
            # Force UI refresh
            st.rerun()