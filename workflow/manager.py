"""
Workflow Manager for Java Peer Review Training System.

This module provides a central manager class that integrates
all components of the workflow system.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

from langgraph.graph import StateGraph
from state_schema import WorkflowState, ReviewAttempt

from data.json_error_repository import JsonErrorRepository

from core.code_generator import CodeGenerator
from core.student_response_evaluator import StudentResponseEvaluator
from core.code_evaluation import CodeEvaluationAgent

from workflow.node import WorkflowNodes
from workflow.conditions import WorkflowConditions
from workflow.builder import GraphBuilder

from utils.llm_logger import LLMInteractionLogger
from utils.language_utils import t
import streamlit as st

# Configure logging
logger = logging.getLogger(__name__)

class WorkflowManager:
    """
    Manager class for the Java Code Review workflow system.
    This class integrates all components of the workflow system and provides
    a high-level API for interacting with the workflow.
    """
    def __init__(self, llm_manager):
        """
        Initialize the workflow manager with the LLM manager.
        
        Args:
            llm_manager: Manager for LLM models
        """
        self.llm_manager = llm_manager
        self.llm_logger = LLMInteractionLogger()
        
        # Initialize repositories
        self.error_repository = JsonErrorRepository()
        
        # Initialize domain objects
        self._initialize_domain_objects()
        
        # Create workflow nodes and conditions
        self.workflow_nodes = self._create_workflow_nodes()
        self.conditions = WorkflowConditions()
        
        # Build workflow graph
        self.workflow = self._build_workflow_graph()
    
    def _initialize_domain_objects(self) -> None:
        """
        Initialize domain objects with appropriate LLMs.
        Connection testing is now done lazily on first LLM use.
        Handles cases where models might not initialize successfully.
        """
        logger.debug("Initializing domain objects for workflow")
        
        # Initialize models for different functions without testing connection
        # Connection will be tested when models are actually used
        generative_model = self._initialize_model_for_role("GENERATIVE")
        review_model = self._initialize_model_for_role("REVIEW")
        summary_model = self._initialize_model_for_role("SUMMARY")
        
        # Log model initialization status
        models_status = {
            "GENERATIVE": generative_model is not None,
            "REVIEW": review_model is not None,
            "SUMMARY": summary_model is not None
        }
        logger.debug(f"Model initialization status: {models_status}")
        
        # Initialize domain objects with models (they can handle None models gracefully)
        self.code_generator = CodeGenerator(generative_model, self.llm_logger)
        self.code_evaluation = CodeEvaluationAgent(generative_model, self.llm_logger)
        self.evaluator = StudentResponseEvaluator(review_model, llm_logger=self.llm_logger)
        
        # Store feedback models for generating final feedback
        self.summary_model = summary_model
        
        # Count successful initializations
        successful_models = sum(models_status.values())
        total_models = len(models_status)
        
        if successful_models == total_models:
            logger.debug(f"All {total_models} domain objects initialized successfully (connections will be tested on first use)")
        elif successful_models > 0:
            logger.warning(f"Initialized {successful_models}/{total_models} models successfully. Some features may be limited.")
        else:
            logger.error("Failed to initialize any models. LLM features will not be available.")
        
        logger.debug("Domain objects initialization completed")

    def _initialize_model_for_role(self, role: str):
        """
        Initialize an LLM for a specific role without testing connection.
        Connection will be tested when the model is actually used.
        Provides better error handling and logging.
        
        Args:
            role: Role identifier (e.g., "GENERATIVE", "REVIEW")
            
        Returns:
            Initialized LLM or None if initialization fails
        """
        try:
            logger.debug(f"Attempting to initialize {role} model")
            
            # Initialize model without testing connection
            model = self.llm_manager.initialize_model_from_env(f"{role}_MODEL", f"{role}_TEMPERATURE")
            
            if model:
                logger.debug(f"Successfully initialized {role} model (connection will be tested on first use)")
                return model
            else:
                logger.warning(f"Failed to initialize {role} model - model object is None")
                return None
                
        except Exception as e:
            logger.error(f"Exception while initializing {role} model: {str(e)}")
            return None
    
    def _create_workflow_nodes(self) -> WorkflowNodes:
        """
        Create workflow nodes with initialized domain objects.
        
        Returns:
            WorkflowNodes instance
        """
        logger.debug("Creating workflow nodes")
        nodes = WorkflowNodes(
            self.code_generator,
            self.code_evaluation,
            self.error_repository,
            self.llm_logger
        )
        
        # Attach evaluator to nodes (needed for analyze_review_node)
        nodes.evaluator = self.evaluator
        
        return nodes
    
    def _build_workflow_graph(self) -> StateGraph:
        """
        Build the workflow graph using the graph builder.
        Stores the builder instance for later visualization.
        
        Returns:
            StateGraph: The constructed workflow graph
        """
        logger.debug("Building workflow graph")
        self.graph_builder = GraphBuilder(self.workflow_nodes)
        return self.graph_builder.build_graph()
    
    def get_all_error_categories(self) -> Dict[str, List[str]]:
        """
        Get all available error categories.
        
        Returns:
            Dictionary with error categories
        """
        return self.error_repository.get_all_categories()
    
    def submit_review(self, state: WorkflowState, student_review: str) -> WorkflowState:
        """
        Submit a student review and update the state.
        
        Args:
            state: Current workflow state
            student_review: The student's review text
            
        Returns:
            Updated workflow state with analysis
        """
        logger.debug(f"Submitting review for iteration {state.current_iteration}")
        
        # Create a new review attempt
        review_attempt = ReviewAttempt(
            student_review=student_review,
            iteration_number=state.current_iteration,
            analysis={},
            targeted_guidance=None
        )
        
        # Add to review history
        state.review_history.append(review_attempt)
        
        # Run the state through the analyze_review node
        updated_state = self.workflow_nodes.analyze_review_node(state)
        
        # Check if this is the last iteration or review is sufficient
        if (updated_state.current_iteration > updated_state.max_iterations or 
            updated_state.review_sufficient):
            # Generate comparison report for feedback tab
            self._generate_review_feedback(updated_state)
        
        return updated_state
    
    def _generate_review_feedback(self, state: WorkflowState) -> None:
        """
        Generate feedback for review completion with proper language support.
        Now also updates category statistics.
        
        Args:
            state: Current workflow state
        """
        # Check if we have review history
        if not state.review_history:
            logger.warning(t("no_review_history_found"))
            return
                
        # Get latest review
        latest_review = state.review_history[-1]       
        # Generate comparison report if not already generated
        if not state.comparison_report and state.evaluation_result:
            try:
                logger.debug(t("generating_comparison_report"))
                # Extract error information from evaluation results
                found_errors = state.evaluation_result.get(t('found_errors'), [])                
                # Get original error count for consistent metrics
                original_error_count = state.original_error_count                
                # Update the analysis with the original error count if needed
                if original_error_count > 0 and "original_error_count" not in latest_review.analysis:
                    latest_review.analysis["original_error_count"] = original_error_count
                    
                    # Recalculate percentages based on original count
                    identified_count = latest_review.analysis[t('identified_count')]
                    latest_review.analysis[t("identified_percentage")] = (identified_count / original_error_count) * 100
                    latest_review.analysis[t("accuracy_percentage")] = (identified_count / original_error_count) * 100
                        
                # Convert review history to format expected by generate_comparison_report
                converted_history = []
                for review in state.review_history:
                    converted_history.append({
                        "iteration_number": review.iteration_number,
                        "student_comment": review.student_review,
                        "review_analysis": review.analysis,
                        "targeted_guidance": review.targeted_guidance
                    })
                        
                if hasattr(self, "evaluator") and self.evaluator:
                    state.comparison_report = self.evaluator.generate_comparison_report(
                        found_errors,
                        latest_review.analysis,
                        converted_history
                    )
                    logger.debug(t("generated_comparison_report"))
                
                if "auth" in st.session_state and st.session_state.auth.get("is_authenticated", False):
                    user_id = st.session_state.auth.get("user_id")
                    if user_id:
                        # Check if badge manager is available
                        try:
                            from auth.badge_manager import BadgeManager
                            badge_manager = BadgeManager()
                            
                            # Get error categories from found_errors
                            if state.evaluation_result and t('found_errors') in state.evaluation_result:
                                found_errors = state.evaluation_result[t('found_errors')]
                                
                                # Group by category
                                category_stats = {}
                                for error in found_errors:
                                    error_str = str(error)
                                    # Extract category from error string (e.g., "LOGICAL - Off-by-one error")
                                    parts = error_str.split(" - ", 1)
                                    if len(parts) > 0:
                                        category = parts[0]
                                        if category not in category_stats:
                                            category_stats[category] = {"encountered": 0, "identified": 0}
                                        category_stats[category]["encountered"] += 1
                                
                                # Update identified counts from review analysis
                                if latest_review and latest_review.analysis:
                                    identified = latest_review.analysis.get(t('identified_problems'), [])
                                    for problem in identified:
                                        problem_str = str(problem)
                                        parts = problem_str.split(" - ", 1)
                                        if len(parts) > 0:
                                            category = parts[0]
                                            if category in category_stats:
                                                category_stats[category]["identified"] += 1
                                
                                # Update stats for each category
                                for category, stats in category_stats.items():
                                    badge_manager.update_category_stats(
                                        user_id,
                                        category,
                                        stats["encountered"],
                                        stats["identified"]
                                    )
                        except ImportError:
                            logger.warning("Badge manager not available")
                        except Exception as e:
                            logger.error(f"Error updating category stats: {str(e)}")
                
                    
            except Exception as e:
                logger.error(f"{t('error')} {t('generating_comparison_report')}: {str(e)}")
                state.comparison_report = (
                    f"# {t('review_feedback')}\n\n"
                    f"{t('error_generating_report')} "
                    f"{t('check_review_history')}."
                )