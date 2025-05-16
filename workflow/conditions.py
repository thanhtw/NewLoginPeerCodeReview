"""
Workflow Conditions for Java Peer Review Training System.

This module contains the conditional logic for determining
which paths to take in the LangGraph workflow.
"""

import logging
from typing import Dict, Any, List, Optional
from state_schema import WorkflowState

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
        # Extract state attributes for clearer code
        current_step = getattr(state, "current_step", None)
        evaluation_result = getattr(state, "evaluation_result", None)
        evaluation_attempts = getattr(state, "evaluation_attempts", 0)
        max_evaluation_attempts = getattr(state, "max_evaluation_attempts", 3)
        
        logger.debug(f"Deciding workflow path with state: step={current_step}, "
                     f"valid={evaluation_result.get('valid', False) if evaluation_result else False}, "
                     f"attempts={evaluation_attempts}/{max_evaluation_attempts}")
        
        # Check if current step is explicitly set to regenerate
        if current_step == "regenerate":
            logger.debug("Path decision: regenerate_code (explicit current_step)")
            return "regenerate_code"
        
        # IMPORTANT: Explicitly check validity flag first
        if evaluation_result and evaluation_result.get("valid", False):
            logger.debug("Path decision: review_code (evaluation passed)")
            return "review_code"

        # Check if we have missing or extra errors and haven't reached max attempts
        has_missing_errors = evaluation_result and len(evaluation_result.get("missing_errors", [])) > 0
        needs_regeneration = has_missing_errors
        
        # If we need regeneration and haven't reached max attempts, regenerate
        if needs_regeneration and evaluation_attempts < max_evaluation_attempts:
            reason = "missing errors" if has_missing_errors else "extra errors"
            logger.debug(f"Path decision: regenerate_code (found {reason})")
            return "regenerate_code"
        
        # If we've reached max attempts or don't need regeneration, move to review
        logger.debug(f"Path decision: review_code (attempts: {evaluation_attempts}/{max_evaluation_attempts})")
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
        # Extract state attributes for clearer code
        current_iteration = getattr(state, "current_iteration", 1)
        max_iterations = getattr(state, "max_iterations", 3)
        review_sufficient = getattr(state, "review_sufficient", False)
        review_history = getattr(state, "review_history", [])
        
        logger.debug(f"Deciding review path with state: iteration={current_iteration}/{max_iterations}, "
                     f"sufficient={review_sufficient}")
     
        # Get the latest review analysis
        latest_review = review_history[-1] if review_history else None

     
        if latest_review and hasattr(latest_review, "analysis"):
            analysis = latest_review.analysis
            identified_count = analysis.get("identified_count", 0)
            total_problems = analysis.get("total_problems", 0)
            
            # Check if all issues have been identified OR we've reached the max iterations
            if (identified_count == total_problems and total_problems > 0) or current_iteration > max_iterations:              
                state.review_sufficient = True
                if identified_count == total_problems:
                    logger.debug(f"Review path decision: generate_summary (all {total_problems} issues identified)")
                else:
                    logger.debug(f"Review path decision: generate_summary (max iterations {max_iterations} reached)")
                return "generate_summary"
        if review_sufficient:
            logger.debug("Review path decision: generate_summary (review marked sufficient)")
            return "generate_summary"
        
        logger.debug(f"Review path decision: continue_review (iteration {current_iteration}/{max_iterations})")
        return "continue_review"