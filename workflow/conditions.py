"""
Workflow Conditions for Java Peer Review Training System.

This module contains the conditional logic for determining
which paths to take in the LangGraph workflow.
"""

import logging
from typing import Dict, Any, List, Optional
from state_schema import WorkflowState
from utils.language_utils import get_field_value, get_state_attribute, t

# Configure logging
logger = logging.getLogger(__name__)

class WorkflowConditions:
    """
    Conditional logic for the Java Code Review workflow.
    
    This class contains all the conditional functions used to determine
    the next step in the workflow based on the current state.
    """
    
    @staticmethod
    def should_regenerate_or_review(state: WorkflowState) -> str:
        """
        Determine if we should regenerate code or move to review.
        Enhanced to handle Groq-specific issues.
        
        Args:
            state: Current workflow state
            
        Returns:
            "regenerate_code" if we need to regenerate code based on evaluation feedback
            "review_code" if the code is valid or we've reached max attempts
        """
        logger.debug(f"Deciding workflow path with state: step={get_state_attribute(state, 'current_step')}, "
                f"valid={get_state_attribute(state, 'evaluation_result') and get_field_value(get_state_attribute(state, 'evaluation_result'), 'valid', False)}, "
                f"attempts={get_state_attribute(state, 'evaluation_attempts', 0)}/{get_state_attribute(state, 'max_evaluation_attempts', 3)}")
        
         # Check if current step is explicitly set to regenerate
        if get_state_attribute(state, "current_step") == "regenerate":
            logger.info("Path decision: regenerate_code (explicit current_step)")
            return "regenerate_code"
        
        
        # IMPORTANT: Explicitly check validity flag first
        if get_state_attribute(state, "evaluation_result") and get_field_value(get_state_attribute(state, "evaluation_result"), "valid", False) == True:
            logger.info("Path decision: review_code (evaluation passed)")
            return "review_code"

        # Check if we have missing or extra errors and haven't reached max attempts
        has_missing_errors = get_state_attribute(state, "evaluation_result") and len(get_field_value(get_state_attribute(state, "evaluation_result"), "missing_errors", [])) > 0
        has_extra_errors = get_state_attribute(state, "evaluation_result") and len(get_field_value(get_state_attribute(state, "evaluation_result"), "extra_errors", [])) > 0
        needs_regeneration = has_missing_errors or has_extra_errors
        
        # Get current and max attempt counts with safe defaults
        current_attempts = get_state_attribute(state, 'evaluation_attempts', 0)
        max_attempts = get_state_attribute(state, 'max_evaluation_attempts', 3)
        
        # If we need regeneration and haven't reached max attempts, regenerate
        if needs_regeneration and current_attempts < max_attempts:
            reason = "missing errors" if has_missing_errors else "extra errors"
            logger.info(f"Path decision: regenerate_code (found {reason})")
            return "regenerate_code"
        
        # If we've reached max attempts or don't need regeneration, move to review
        logger.info(f"Path decision: review_code (attempts: {current_attempts}/{max_attempts})")
        return "review_code"
    
    
    @staticmethod
    def should_continue_review(state: WorkflowState) -> str:
        """
        Determine if we should continue with another review iteration or generate summary.
        
        This is used for the conditional edge from the analyze_review node.
        
        Args:
            state: Current workflow state
            
        Returns:
            "continue_review" if more review iterations are needed
            "generate_summary" if the review is sufficient or max iterations reached or all issues identified
        """
        logger.debug(f"Deciding review path with state: iteration={get_state_attribute(state, 'current_iteration')}/{get_state_attribute(state, 'max_iterations')}, "
                f"sufficient={get_state_attribute(state, 'review_sufficient')}")
        
        # Check if we've reached max iterations
        if state.current_iteration > state.max_iterations:
            logger.info(f"Review path decision: generate_summary (max iterations reached: {state.current_iteration})")
            return "generate_summary"
        
        # Check if the review is sufficient
        if get_state_attribute(state, "review_sufficient"):
            logger.info("Review path decision: generate_summary (review sufficient)")
            return "generate_summary"
        
        # Check if all issues have been identified
        latest_review = state.review_history[-1] if state.review_history else None

        if latest_review and latest_review.analysis:
            identified_count = get_field_value(latest_review.analysis, "identified_count", 0)
            total_problems = get_field_value(latest_review.analysis, "total_problems", 0)
            if identified_count == total_problems and total_problems > 0:
                # Also set review_sufficient to True to maintain state consistency
                state.review_sufficient = True
                logger.info(f"Review path decision: generate_summary (all {total_problems} issues identified)")
                return "generate_summary"
        
        # Otherwise, continue reviewing
        logger.info(f"Review path decision: continue_review (iteration {get_state_attribute(state, 'current_iteration')}, not sufficient)")
        return "review_code"