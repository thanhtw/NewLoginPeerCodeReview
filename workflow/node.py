"""
Workflow Nodes for Java Peer Review Training System.

This module contains the node implementations for the LangGraph workflow,
separating node logic from graph construction for better maintainability.
"""

import logging
import re
from typing import Dict, Any, List, Tuple, Optional

from state_schema import WorkflowState, CodeSnippet
from utils.code_utils import extract_both_code_versions, create_regeneration_prompt, get_error_count_from_state
import random
from utils.language_utils import t

# Configure logging
logger = logging.getLogger(__name__)

class WorkflowNodes:
    """
    Node implementations for the Java Code Review workflow.
    
    This class contains all node handlers that process state transitions
    in the LangGraph workflow, extracted for better separation of concerns.
    """
    
    def __init__(self, code_generator, code_evaluation, error_repository, llm_logger):
        """
        Initialize workflow nodes with required components.
        
        Args:
            code_generator: Component for generating Java code with errors
            code_evaluation: Component for evaluating generated code quality
            error_repository: Repository for accessing Java error data
            llm_logger: Logger for tracking LLM interactions
        """
        self.code_generator = code_generator
        self.code_evaluation = code_evaluation
        self.error_repository = error_repository
        self.llm_logger = llm_logger
    
    def generate_code_node(self, state: WorkflowState) -> WorkflowState:
        """
        Generate Java code with errors based on selected parameters.
        Ensures exact match between selected and generated errors.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with generated code
        """
        try:
            # Get parameters from state
            code_length = getattr(state, "code_length", "medium")
            difficulty_level = getattr(state, "difficulty_level", "medium")
            selected_error_categories = getattr(state, "selected_error_categories", {})
            selected_specific_errors = getattr(state, "selected_specific_errors", [])
            
            # Reset state for a fresh generation
            state.evaluation_attempts = 0
            state.evaluation_result = None
            state.code_generation_feedback = None

            # Randomly select a domain if not already set
            if not hasattr(state, "domain") or not state.domain:
                # Use the domains from code_generator if available
                if hasattr(self.code_generator, 'domains') and self.code_generator.domains:
                    state.domain = random.choice(self.code_generator.domains)
                else:
                    # Default domains if not available in code_generator
                    domains = [
                        "user_management", "file_processing", "data_validation", 
                        "calculation", "inventory_system", "notification_service",
                        "logging", "banking", "e-commerce", "student_management"
                    ]
                    state.domain = random.choice(domains)
                
                logger.debug(f"Selected domain for code generation: {state.domain}")
            
            # Determine whether we're using specific errors or categories
            using_specific_errors = len(selected_specific_errors) > 0
            
            # Get appropriate errors based on selection mode
            if using_specific_errors:
                # Using specific errors mode
                if not selected_specific_errors:
                    state.error = t("no_specific_errors_selected")
                    return state
                       
                logger.debug(f"Using specific errors mode with {len(selected_specific_errors)} errors")
                selected_errors = selected_specific_errors
                original_error_count = len(selected_errors)
            else:
                # Using category-based selection mode
                if not selected_error_categories or not selected_error_categories.get("java_errors", []):
                    state.error = t("no_categories")
                    return state
                            
                logger.debug(f"Using category-based mode with categories: {selected_error_categories}")
                
                # Get exact number based on difficulty
                required_error_count = get_error_count_from_state(difficulty_level)
    
                selected_errors, _ = self.error_repository.get_errors_for_llm(
                    selected_categories=selected_error_categories,
                    count=required_error_count,
                    difficulty=difficulty_level
                )
                
                # Make sure we have the right number of errors
                if len(selected_errors) < required_error_count:
                    logger.warning(f"Got fewer errors ({len(selected_errors)}) than requested ({required_error_count})")
                    original_error_count = len(selected_errors)
                elif len(selected_errors) > required_error_count:
                    logger.warning(f"Got more errors ({len(selected_errors)}) than requested ({required_error_count})")
                    selected_errors = selected_errors[:required_error_count]
                    original_error_count = required_error_count
                else:
                    original_error_count = required_error_count
           
            # Log detailed information about selected errors for debugging           
            logger.debug(f"Final error count for generation: {len(selected_errors)}")
            
            # Generate code with selected errors
            response = self.code_generator._generate_with_llm(
                code_length=code_length,
                difficulty_level=difficulty_level,
                selected_errors=selected_errors,
                domain=getattr(state, "domain", "")
            )

            # Extract both annotated and clean versions
            annotated_code, clean_code = extract_both_code_versions(response)
            # Create code snippet object
            code_snippet = CodeSnippet(
                code=annotated_code,
                clean_code=clean_code,
                raw_errors={
                    "java_errors": selected_errors
                },
                expected_error_count=original_error_count
            )
                                  
            # Update state with the original error count for consistency
            state.original_error_count = original_error_count
            
            # Update state
            state.code_snippet = code_snippet
            state.current_step = "evaluate"
            return state
                    
        except Exception as e:           
            logger.error(f"{t('error')} generating code: {str(e)}", exc_info=True)
            state.error = f"{t('error')} generating code: {str(e)}"
            return state

    def regenerate_code_node(self, state: WorkflowState) -> WorkflowState:
        """
        Regenerate code based on evaluation feedback.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with regenerated code
        """
        try:
            logger.debug(f"Starting enhanced code regeneration (Attempt {getattr(state, 'evaluation_attempts', 0)})")
            
            # Use the code generation feedback to generate improved code
            feedback_prompt = getattr(state, "code_generation_feedback", None)
            
            # Generate code with feedback prompt
            if hasattr(self.code_generator, 'llm') and self.code_generator.llm:
                # Log the regeneration prompt before sending to LLM
                metadata = {
                    "code_length": getattr(state, "code_length", "medium"),
                    "difficulty_level": getattr(state, "difficulty_level", "medium"),
                    "domain": getattr(state, "domain", ""),
                    "selected_errors": getattr(state, "selected_error_categories", {}),
                    "attempt": getattr(state, "evaluation_attempts", 0),
                    "max_attempts": getattr(state, "max_evaluation_attempts", 3)
                }
                
                # Log the prompt before it's sent to the LLM
                self.llm_logger.log_regeneration_prompt(feedback_prompt, metadata)
                
                # Generate the code
                response = self.code_generator.llm.invoke(feedback_prompt)
                
                # Log the full regeneration with response
                self.llm_logger.log_code_regeneration(feedback_prompt, response, metadata)
                
                # Process the response
                annotated_code, clean_code = extract_both_code_versions(response)                
                
                # Get requested errors from state
                requested_errors = self._extract_requested_errors(state)
                
                # Create updated code snippet
                state.code_snippet = CodeSnippet(
                    code=annotated_code,
                    clean_code=clean_code,
                    raw_errors={
                        "java_errors": requested_errors
                    }
                )
                
                # Move to evaluation step again
                state.current_step = "evaluate"
                logger.debug(f"Code regenerated successfully on attempt {getattr(state, 'evaluation_attempts', 0)}")
                
                return state
            else:
                # If no LLM available, fall back to standard generation
                logger.warning("No LLM available for regeneration. Falling back to standard generation.")
                return self.generate_code_node(state)
            
        except Exception as e:                 
            logger.error(f"Error regenerating code: {str(e)}", exc_info=True)
            state.error = f"Error regenerating code: {str(e)}"
            return state
        
    def evaluate_code_node(self, state: WorkflowState) -> WorkflowState:
        try:
            logger.debug("Starting code evaluation node")
            
            # Validate code snippet
            if not hasattr(state, 'code_snippet') or state.code_snippet is None:
                state.error = t("no_code_snippet_evaluation")
                return state
                    
            # Get the code with annotations
            code = state.code_snippet.code if hasattr(state, "code_snippet") and state.code_snippet else None
            
            # Get requested errors from state
            requested_errors = self._extract_requested_errors(state)
            requested_count = len(requested_errors)           
            # Ensure we're using the original error count for consistency
            original_error_count = getattr(state, "original_error_count", 0)            
            if original_error_count == 0 and hasattr(state, "code_snippet") and hasattr(state.code_snippet, 'expected_error_count'):
                # If not set in state, try to get it from code snippet
                original_error_count = state.code_snippet.expected_error_count
                # Update state with this count
                state.original_error_count = original_error_count
                
            # If we still don't have it, use the requested count
            if original_error_count == 0:
                original_error_count = requested_count
                state.original_error_count = original_error_count
                
            logger.debug(f"Evaluating code for {original_error_count} expected errors")
            
            # Evaluate the code
            raw_evaluation_result = self.code_evaluation.evaluate_code(
                code, requested_errors
            )
            
            # IMPORTANT: Ensure evaluation_result is a dictionary
            if not isinstance(raw_evaluation_result, dict):
                logger.error(f"Expected dict for evaluation_result, got {type(raw_evaluation_result)}")
                # Create a default dictionary with the necessary structure
                evaluation_result = {
                    "found_errors": [],
                    "missing_errors": [f"{error.get('type', '').upper()} - {error.get('name', '')}" 
                                    for error in requested_errors],
                    "valid": False,
                    "feedback": f"Error in evaluation. Please ensure the code contains all {original_error_count} requested errors.",
                    "original_error_count": original_error_count  # Add original count for consistency
                }
            else:
                evaluation_result = raw_evaluation_result
                # Add the original error count to the evaluation result
                evaluation_result["original_error_count"] = original_error_count

                # IMPORTANT: Explicitly set valid flag based on missing and extra errors
                missing_errors = evaluation_result.get(t('missing_errors'), [])
                
                # Only valid if no missing errors and no extra errors
                has_missing = len(missing_errors) > 0               
                evaluation_result['valid'] = not (has_missing)
                
                # Log explicit validation status
                logger.debug(f"Code validation: valid={evaluation_result.get(t('valid'), False)}, " +  # CHANGE
                        f"missing={len(missing_errors)}")
                
            # Update state with evaluation results
            state.evaluation_result = evaluation_result
            state.evaluation_attempts += 1
            
            # Log evaluation results
            found_count = len(evaluation_result.get(t('found_errors'), []))  # CHANGE
            missing_count = len(evaluation_result.get(t('missing_errors'), []))  # CHANGE
            logger.debug(f"Code evaluation complete: {found_count}/{original_error_count} errors implemented, {missing_count} missing")
            
            feedback = None
            
            # If we have missing errors or extra errors, we need to regenerate the code
            needs_regeneration = missing_count > 0
            
            # If we have extra errors, use the updated regeneration function that handles extras
            if missing_count > 0:
                logger.warning(f"Missing {missing_count} out of {original_error_count} requested errors")
                
                # Use standard regeneration prompt but enhance it for clarity
                if hasattr(self.code_evaluation, 'generate_improved_prompt'):
                    feedback = self.code_evaluation.generate_improved_prompt(
                        code, requested_errors, evaluation_result
                    )
                else:
                    # Use the regeneration prompt with emphasis on adding missing errors
                    feedback = create_regeneration_prompt(
                        code=code,
                        domain=getattr(state, "domain", ""),
                        missing_errors=evaluation_result.get('missing_errors', []),
                        found_errors=evaluation_result.get('found_errors', []), 
                        requested_errors=requested_errors
                    )
            else:
                # No missing or extra errors - we're good!
                logger.debug(f"All {original_error_count} requested errors implemented correctly")
                            
                feedback = create_regeneration_prompt(
                    code=code,
                    domain=getattr(state, "domain", ""),  
                    missing_errors=[],
                    found_errors=evaluation_result.get(t('found_errors'), []),
                    requested_errors=requested_errors                    
                )
                    
            state.code_generation_feedback = feedback
        
            # IMPROVED DECISION LOGIC: Prioritize fixing missing errors over max attempts
            # If evaluation passed (all errors implemented with exact count)
            if evaluation_result.get(t("valid"), False):
                state.current_step = "review"
                logger.debug("All errors successfully implemented, proceeding to review")
            elif needs_regeneration and state.evaluation_attempts < getattr(state, "max_evaluation_attempts", 3):
                # If we have missing errors or extra errors and haven't reached max attempts, regenerate
                state.current_step = "regenerate"
                if missing_count > 0:
                    logger.debug(f"Found {missing_count} missing errors, proceeding to regeneration")
            else:
                # Otherwise, we've either reached max attempts or have no more missing errors
                state.current_step = "review"
                if state.evaluation_attempts >= getattr(state, "max_evaluation_attempts", 3):                
                    logger.warning(f"Reached maximum evaluation attempts ({getattr(state, 'max_evaluation_attempts', 3)}). Proceeding to review.")
                else:
                    logger.debug("No missing errors to fix, proceeding to review")
            
            return state
            
        except Exception as e:
            logger.error(f"Error evaluating code: {str(e)}", exc_info=True)
            state.error = f"Error evaluating code: {str(e)}"
            return state

    def review_code_node(self, state: WorkflowState) -> WorkflowState:
        """
        Review code node - this is a placeholder since user input happens in the UI.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        # This node is primarily a placeholder since the actual review is submitted via the UI
        state.current_step = "review"
        return state
    
    def analyze_review_node(self, state: WorkflowState) -> WorkflowState:
        try:
            # Validate review history
            if not state.review_history:
                state.error = t("no_review_submitted")
                return state
                    
            latest_review = state.review_history[-1]
            student_review = latest_review.student_review
            
            # Validate code snippet
            if not state.code_snippet:
                state.error = t("no_code_snippet_available")
                return state
                    
            code_snippet = state.code_snippet.code
            raw_errors = state.code_snippet.raw_errors
            
            known_problems = []
            original_error_count =  getattr(state, "original_error_count", 0)

            if isinstance(raw_errors, dict):
                for error_type, errors in raw_errors.items():
                    for error in errors:
                        if isinstance(error, dict):
                            error_name = error.get(t('error_name_variable'))
                            category = error.get(t('category'))
                            description = error.get(t('description'))
                            known_problems.append(f"{category} - {error_name}: {description}")
            
            # Get the student response evaluator
            evaluator = getattr(self, "evaluator", None)
            if not evaluator:
                state.error = t("student_evaluator_not_initialized")
                return state
            
            # Use the standard evaluation method
            analysis = evaluator.evaluate_review(
                code_snippet=code_snippet,
                known_problems=known_problems,
                student_review=student_review
            )

          
            # IMPROVED: Update analysis using t() function for key translation
            if original_error_count > 0:
                found_problems_count = len(known_problems)
                identified_count = analysis[t('identified_count')]
                
                # Use translated keys with t() function
                analysis[t("total_problems")] = original_error_count
                analysis[t("original_error_count")] = original_error_count
                
                # Calculate percentage
                percentage = (identified_count / original_error_count) * 100
                
                # Set percentage fields using translated keys
                analysis[t("identified_percentage")] = percentage
                analysis[t("accuracy_percentage")] = percentage
                
                logger.debug(f"Updated review analysis: {identified_count}/{original_error_count} " +
                    f"({percentage:.1f}%) [Found problems: {found_problems_count}]")
                
                # Mark review as sufficient if all errors are found
                if identified_count == original_error_count:
                    analysis["review_sufficient"] = True
                    analysis[t("review_sufficient")] = True
                    logger.debug("All errors found! Marking review as sufficient.")

          
            # Update the review with analysis
            latest_review.analysis = analysis
            review_sufficient = analysis.get("review_sufficient", False)
            state.review_sufficient = review_sufficient
            
            # Generate targeted guidance if needed
            if not review_sufficient and state.current_iteration < state.max_iterations:
                targeted_guidance = evaluator.generate_targeted_guidance(
                    code_snippet=code_snippet,
                    known_problems=known_problems,
                    student_review=student_review,
                    review_analysis=analysis,
                    iteration_count=state.current_iteration,
                    max_iterations=state.max_iterations
                )               
                latest_review.targeted_guidance = targeted_guidance              
            # Increment iteration count
            state.current_iteration += 1
            
            # Update state
            state.current_step = "analyze"
            
            return state
        
        except Exception as e:
            logger.error(f"Error analyzing review: {str(e)}", exc_info=True)
            state.error = f"Error analyzing review: {str(e)}"
            return state
       
    def _extract_requested_errors(self, state: WorkflowState) -> List[Dict[str, Any]]:
        """
        Extract requested errors from the state with improved error handling and type safety.
        
        Args:
            state: Current workflow state
            
        Returns:
            List of requested errors
        """
        requested_errors = []
        
        # First check if code_snippet exists
        if not hasattr(state, 'code_snippet') or state.code_snippet is None:  #
            logger.warning("No code snippet in state for extracting requested errors")
            return requested_errors
        
        # Check if raw_errors exists and is a dictionary
        if hasattr(state, 'code_snippet') and hasattr(state.code_snippet, "raw_errors"):
            raw_errors = state.code_snippet.raw_errors           
            # Type check for raw_errors
            if not isinstance(raw_errors, dict):
                logger.warning(f"Expected dict for raw_errors, got {type(raw_errors)}")
                return requested_errors
            
            # Extract errors from java_errors key
            if "java_errors" in raw_errors:
                errors = raw_errors.get("java_errors", [])
                if not isinstance(errors, list):
                    logger.warning(f"Expected list for java_errors, got {type(errors)}")
                    return requested_errors
                for error in errors:
                    if not isinstance(error, dict):
                        logger.warning(f"Expected dict for error, got {type(error)}")
                        continue
                    # Make sure the error has required fields
                    if t("category") not in error:
                        error[t("category")] = error.get( t("category"), "")
                    
                    if t("error_name_variable") not in error:
                        error[t("error_name_variable")] = error.get( t("error_name_variable"), "")

                    if t("description") not in error:
                        error[t("description")] = error.get( t("description"), "")
                    
                    if t("implementation_guide") not in error:
                        error[t("implementation_guide")] = error.get( t("implementation_guide"), "")
                    requested_errors.append(error)
        
        # Alternative method: Check selected_specific_errors
        elif hasattr(state, 'selected_specific_errors') and state.selected_specific_errors:
            # Check if it's a list
            if isinstance(state.selected_specific_errors, list):
                # Filter out non-dict entries
                for error in state.selected_specific_errors:
                    if isinstance(error, dict) and "name" in error and "type" in error:
                        requested_errors.append(error)
        
        # If we still don't have any errors, check selected_error_categories
        if not requested_errors and hasattr(state, 'selected_error_categories'):
            # Check if it's a dict
            if hasattr(state, 'selected_error_categories') and isinstance(state.selected_error_categories, dict):
                # This doesn't give us specific errors, but we can log that we found categories
                logger.debug("Found selected_error_categories but no specific errors")
    
        logger.debug(f"Extracted {len(requested_errors)} requested errors")
        
        return requested_errors
        