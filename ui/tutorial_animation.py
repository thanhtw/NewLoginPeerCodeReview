import re
import os
import streamlit as st
import time
import os
import logging
from typing import Callable, Dict, Any, Tuple
from utils.language_utils import t
from utils.code_utils import add_line_numbers
from core.student_response_evaluator import StudentResponseEvaluator
from llm_manager import LLMManager


# Configure logging
logger = logging.getLogger(__name__)

class CodeReviewTutorial:
    """
    Interactive tutorial that demonstrates the code review process with
    examples of poor and good quality reviews.
    Now includes LLM-based evaluation of user reviews and database tracking.
    """
    
    def __init__(self):
        """Initialize the tutorial component."""
        # Initialize LLM components for evaluation
        self._initialize_llm_components()
        
        # Sample code with errors for the tutorial
        self.sample_code = """public class UserManager {
    private List<User> users;
    
    public UserManager() {
        users = new ArrayList<User>();
    }
    
    public void addUser(User user) {
        // Add user to list without validation
        users.add(user);
    }
    
    public User findUser(String userId) {
        // No null check before accessing userId
        for (int i = 0; i <= users.size(); i++) {
            User user = users.get(i);
            if (user.getId() == userId) {
                return user;
            }
        }
        return null;
    }
    
    public void removeUser(String userId) {
        User user = findUser(userId);
        users.remove(user);
    }
}"""
        self.sample_code_with_lines = add_line_numbers(self.sample_code)
        # Known errors in the sample code
        self.known_errors = [
            f"{t('missingImportError')}",
            f"{t('offByOneError')}",
            f"{t('stringComparisonError')}",
            f"{t('nullCheckError1')}",
            f"{t('validationError')}",
            f"{t('nullCheckError2')}"
        ]
        
        # Poor quality review example
        self.poor_review = f"""{t('codeIssuesHeader')}"""
        
        # Good quality review example
        review_items = [
            t('line1ImportError'),
            t('line10LoopError'), 
            t('line12StringError'),
            t('line9NullError'),
            t('line6ValidationError'),
            t('line17RemoveError')
        ]

        self.good_review = "<br>".join([f"• {item}" for item in review_items])
        
        # Load thresholds from environment variables
        self.meaningful_threshold = float(os.getenv("MEANINGFUL_SCORE", "0.6"))
        self.accuracy_threshold = float(os.getenv("ACCURACY_SCORE", "0.7"))
    
    def _initialize_llm_components(self):
        """Initialize LLM manager and evaluator for review assessment."""
        try:
            # Initialize LLM manager
            self.llm_manager = LLMManager()
            
            # Check if we have a working LLM connection
            if self.llm_manager.provider == "groq":
                connection_ok, _ = self.llm_manager.check_groq_connection()
            elif self.llm_manager.provider == "ollama":
                connection_ok, _ = self.llm_manager.check_ollama_connection()
            else:
                connection_ok = False
            
            if connection_ok:
                # Initialize a model for review evaluation
                self.review_llm = self.llm_manager.initialize_model_from_env("REVIEW_MODEL", "REVIEW_TEMPERATURE")
                
                if self.review_llm:
                    # Initialize the student response evaluator
                    self.evaluator = StudentResponseEvaluator(self.review_llm)
                    logger.debug("LLM components initialized successfully for tutorial")
                else:
                    logger.warning("Failed to initialize review LLM for tutorial")
                    self.evaluator = None
            else:
                logger.warning("No LLM connection available for tutorial evaluation")
                self.evaluator = None
                
        except Exception as e:
            logger.error(f"Error initializing LLM components for tutorial: {str(e)}")
            self.evaluator = None
    
    def validate_review_format(self, student_review: str) -> Tuple[bool, str]:
        """
        Validate the format of a student review.
        
        Args:
            student_review: The student's review text
            
        Returns:
            Tuple[bool, str]: (is_valid, reason) where is_valid is True if the review
                            format is valid, and reason explains any validation errors
        """
        if not student_review or not student_review.strip():
            return False, t("review_cannot_be_empty")
        
        # Check if the review has at least one line that follows the expected format
        # Expected format: "Line X: Description of issue"
        valid_line_pattern = re.compile(r'(?:Line|行)\s*\d+\s*[:：]')
        
        # Split the review into lines and check each line
        lines = student_review.strip().split('\n')
        valid_lines = [i+1 for i, line in enumerate(lines) if valid_line_pattern.search(line)]
        
        # If we have at least one valid line, the review is valid
        if valid_lines:
            return True, ""
        
        # Otherwise, return a validation error
        return False, t("please_use_format_line_description")

    def _evaluate_user_review(self, user_review: str) -> Dict[str, Any]:
        """
        Evaluate user review using LLM with the same logic as the main application.
        First validates the review format before proceeding with LLM evaluation.
        
        Args:
            user_review: The user's review text
            
        Returns:
            Dictionary with evaluation results
        """
        # First, validate the review format
        is_valid_format, format_error = self.validate_review_format(user_review)

        if not is_valid_format:
            return {
                "success": False,
                "feedback": format_error,
                "meaningful_score": 0.0,
                "accuracy_score": 0.0,
                "format_error": True
            }

        if not self.evaluator:
            # Fallback to simple length check if LLM is not available
            logger.warning("LLM evaluator not available, using fallback evaluation")
            return {
                "success": len(user_review.strip()) >= 10,
                "feedback": t("Great job! Your review looks good.") if len(user_review.strip()) >= 10 else t("Please write a more detailed review"),
                "meaningful_score": 1.0 if len(user_review.strip()) >= 10 else 0.3,
                "accuracy_score": 1.0 if len(user_review.strip()) >= 10 else 0.3
            }
        
        try:
            # Use the same evaluation method as the main application
            analysis = self.evaluator.evaluate_review(
                code_snippet=self.sample_code,
                known_problems=self.known_errors,
                student_review=user_review
            )
            
            if not analysis or not isinstance(analysis, dict):
                logger.warning("Invalid analysis result from evaluator")
                return {
                    "success": False,
                    "feedback": t("Unable to evaluate your review. Please try again."),
                    "meaningful_score": 0.0,
                    "accuracy_score": 0.0
                }
            
            # Extract metrics from analysis
            identified_count = analysis.get(t("identified_count"), 0)
            total_problems = analysis.get(t("total_problems"), len(self.known_errors))
            identified_problems = analysis.get(t("identified_problems"), [])
            
            # Calculate scores based on the identified problems
            meaningful_score = 0.0
            accuracy_score = 0.0
            
            if identified_problems and len(identified_problems) > 0:
                # Calculate average meaningfulness and accuracy from identified problems
                total_meaningful = 0.0
                total_accuracy = 0.0
                valid_problems = 0
                
                for problem in identified_problems:
                    if isinstance(problem, dict):
                        meaningful = problem.get(f"{t('Meaningfulness')}", 0.0)
                        accuracy = problem.get(f"{t('accuracy')}", 0.0)
                        
                        # Handle both numeric and string representations
                        try:
                            meaningful = float(meaningful) if meaningful else 0.0
                            accuracy = float(accuracy) if accuracy else 0.0
                            
                            total_meaningful += meaningful
                            total_accuracy += accuracy
                            valid_problems += 1
                        except (ValueError, TypeError):
                            continue
                
                if valid_problems > 0:
                    meaningful_score = total_meaningful / valid_problems
                    accuracy_score = total_accuracy / valid_problems
            
            # Determine if review passes thresholds
            passes_meaningful = meaningful_score >= self.meaningful_threshold
            passes_accuracy = accuracy_score >= self.accuracy_threshold
            success = passes_meaningful and passes_accuracy
            
            # Generate feedback based on results
            if success:
                feedback = t("Great job! Your review looks good.")
            else:
                feedback_parts = []
                if not passes_meaningful:
                    feedback_parts.append(f"{t('review_meaning_Poor')}")
                if not passes_accuracy:
                    feedback_parts.append(f"{t('review_accuracy_poor')}")
                
                feedback = t("Please improve your review: ") + ". ".join(feedback_parts)
            
            return {
                "success": success,
                "feedback": feedback,
                "meaningful_score": meaningful_score,
                "accuracy_score": accuracy_score,
                "identified_count": identified_count,
                "total_problems": total_problems
            }
            
        except Exception as e:
            logger.error(f"Error evaluating user review in tutorial: {str(e)}")
            return {
                "success": False,
                "feedback": t("Error evaluating your review. Please try again."),
                "meaningful_score": 0.0,
                "accuracy_score": 0.0
            }
    
    def _check_tutorial_completion_status(self) -> bool:
        """
        Check if the user has completed the tutorial from the database.
        
        Returns:
            bool: True if tutorial is completed, False otherwise
        """
        # Check if user is authenticated
        if not st.session_state.get("auth", {}).get("is_authenticated", False):
            return False
            
        # Check session state first for performance
        if st.session_state.get("tutorial_completed", False):
            return True
            
        # Get user info from session
        user_info = st.session_state.get("auth", {}).get("user_info", {})
        tutorial_completed = user_info.get("tutorial_completed", False)
        
        # If we have the info in session, use it
        if tutorial_completed:
            st.session_state.tutorial_completed = True
            return True
            
        return False
    
    def _mark_tutorial_completed(self) -> bool:
        """
        Mark the tutorial as completed in the database.
        
        Returns:
            bool: True if successfully marked, False otherwise
        """
        # Check if AuthUI is available
        if hasattr(st.session_state, 'auth_ui') and st.session_state.auth_ui:
            auth_ui = st.session_state.auth_ui
        else:
            # Try to get from main app
            try:
                from ui.auth_ui import AuthUI
                auth_ui = AuthUI()
            except ImportError:
                logger.error("Could not import AuthUI to mark tutorial completion")
                return False
        
        # Mark tutorial as completed
        success = auth_ui.mark_tutorial_completed()
        
        if success:
            # Update session state
            st.session_state.tutorial_completed = True
            logger.debug("Tutorial marked as completed successfully")
            
            # Award tutorial completion badge if available
            try:
                from auth.badge_manager import BadgeManager
                badge_manager = BadgeManager()
                user_id = st.session_state.get("auth", {}).get("user_id")
                if user_id:
                    badge_manager.award_badge(user_id, "tutorial-master")
                    logger.debug("Awarded tutorial-master badge")
            except ImportError:
                logger.debug("Badge manager not available for tutorial completion")
            except Exception as e:
                logger.error(f"Error awarding tutorial badge: {str(e)}")
        
        return success
    
    def render(self, on_complete: Callable = None):
        """
        Render the interactive tutorial.
        
        Args:
            on_complete: Callback function to run when tutorial is completed
        """
        # Check if tutorial should be shown
        tutorial_completed = self._check_tutorial_completion_status()
        
        # If tutorial is completed and not being retaken, skip it
        if tutorial_completed and not st.session_state.get("tutorial_retake", False):
            st.session_state.tutorial_completed = True
            if on_complete:
                on_complete()
            return
            
        st.markdown(f"<h2 style='text-align: center;'>{t('1stPractice')}</h2>", unsafe_allow_html=True)
        
        # Progress indicator
        tutorial_step = st.session_state.get("tutorial_step", 0)
        progress_bar = st.progress(tutorial_step / 5)  # 5 steps total
        
        # Step 1: Introduction
        if tutorial_step == 0:
            st.info(t("Welcome to the Java Code Review Training System! This tutorial will guide you through the process of reviewing code for errors."))
            st.markdown(t("In this system, you'll be presented with Java code snippets that contain intentional errors. Your task is to identify these errors and provide detailed feedback."))
            
            if st.button(t("Next"), key="intro_next"):
                st.session_state.tutorial_step = 1
                st.rerun()
                
        # Step 2: Show sample code with errors
        elif tutorial_step == 1:
            st.info(t("Here's a sample Java code snippet with several errors:"))
            st.code(self.sample_code_with_lines, language="java")
            
            st.markdown(t("This code contains several issues that need to be identified."))
            
            if st.button(t("Next"), key="code_next"):
                st.session_state.tutorial_step = 2
                st.rerun()
                
        # Step 3: Show poor quality review
        elif tutorial_step == 2:
            st.info(t("First, let's see an example of a POOR quality review:"))
            
            st.markdown(f"""
            <div style="border: 1px solid red; border-radius: 5px; padding: 15px; background-color: rgba(255, 0, 0, 0.05); margin-bottom: 15px">
                <h4 style="color: red">{t("Poor Quality Review")}</h4>
                <p>{self.poor_review}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(t("This review is not helpful because:"))
            st.markdown("- " + t("It doesn't specify which issues exist"))
            st.markdown("- " + t("It doesn't point to specific line numbers"))
            st.markdown("- " + t("It doesn't explain what's wrong and why"))
            st.markdown("- " + t("It doesn't suggest how to fix the issues"))
            
            if st.button(t("Next"), key="poor_next"):
                st.session_state.tutorial_step = 3
                st.rerun()
                
        # Step 4: Show good quality review
        elif tutorial_step == 3:
            st.info(t("Now, let's see an example of a GOOD quality review:"))
            
            st.markdown(f"""
            <div style="border: 1px solid green; border-radius: 5px; padding: 15px; background-color: rgba(0, 255, 0, 0.05);  margin-bottom: 15px">
                <h4 style="color: green">{t("Good Quality Review")}</h4>
                <pre style="white-space: pre-wrap;">{self.good_review}</pre>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(t("This review is effective because:"))
            st.markdown("- " + t("It identifies specific line numbers"))
            st.markdown("- " + t("It clearly explains what's wrong with each issue"))
            st.markdown("- " + t("It explains why each issue is problematic"))
            st.markdown("- " + t("It suggests how to fix each issue"))
            
            if st.button(t("Next"), key="good_next"):
                st.session_state.tutorial_step = 4
                st.rerun()
                
        # Step 5: Interactive practice with LLM evaluation
        elif tutorial_step == 4:
            st.info(t("Now it's your turn! Try writing a review for one of the errors in the code:"))
            
            # Show the code again
            st.code(self.sample_code_with_lines, language="java")
            
            # Pick a random error to focus on
            import random
            if "tutorial_focus_error" not in st.session_state:
                st.session_state.tutorial_focus_error = random.randint(0, len(self.known_errors) - 1)
            
            focus_error = self.known_errors[st.session_state.tutorial_focus_error]
            
            st.markdown(f"**{t('Focus on this error')}:** {focus_error}")
            
            user_review = st.text_area(t("Write your review comment for this error:"), height=100, key="tutorial_review")
            
            # Show previous evaluation result if available
            if "tutorial_evaluation" in st.session_state:
                eval_result = st.session_state.tutorial_evaluation
                if eval_result["success"]:
                    st.success(eval_result["feedback"])
                else:
                    st.warning(eval_result["feedback"])
                            
            if st.button(t("Submit"), key="practice_submit"):
                if len(user_review.strip()) < 10:
                    st.warning(t("Please write a more detailed review"))
                else:
                    # Show evaluation progress
                    with st.spinner(t("Evaluating your review with AI...")):
                        # Evaluate the user's review using LLM
                        evaluation_result = self._evaluate_user_review(user_review)
                        
                        # Store evaluation result
                        st.session_state.tutorial_evaluation = evaluation_result
                        
                        # Check if review passes
                        if evaluation_result["success"]:
                            st.success(evaluation_result["feedback"])
                            st.session_state.tutorial_step = 5
                            st.rerun()
                        else:
                            st.info(f"{t('faile_review')}")
                            
        # Step 6: Complete
        elif tutorial_step == 5:
            st.success(t("Congratulations! You've completed the tutorial."))
            st.markdown(t("Remember these key principles for good code reviews:"))
            st.markdown("1. " + t("Be specific about line numbers and issues"))
            st.markdown("2. " + t("Explain what's wrong and why"))
            st.markdown("3. " + t("Provide constructive suggestions"))
            st.markdown("4. " + t("Be thorough and check different types of errors"))
            
            if st.button(t("Start Coding!"), key="complete_button"):
                # Mark tutorial as completed in database
                tutorial_marked = self._mark_tutorial_completed()
                
                if tutorial_marked:
                    st.session_state.tutorial_completed = True
                    st.success(t("Tutorial completed! You earned the Tutorial Master badge! 🎓"))
                else:
                    st.warning(t("Tutorial completed, but there was an issue saving your progress."))
                    # Still mark as completed in session
                    st.session_state.tutorial_completed = True
                
                # Clear tutorial retake flag if it was set
                if "tutorial_retake" in st.session_state:
                    del st.session_state["tutorial_retake"]
                
                if on_complete:
                    on_complete()
                st.rerun()
        
        # Update progress
        progress_bar.progress(tutorial_step / 5)