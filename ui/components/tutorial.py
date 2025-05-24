"""
Interactive Tutorial Component for Java Peer Review Training System.

This module provides an interactive tutorial that demonstrates the code review process
with examples of poor and good quality reviews, including LLM-based evaluation.
"""

import re
import os
import streamlit as st
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
    Interactive tutorial for code review training with AI-powered evaluation.
    """
    
    def __init__(self):
        """Initialize the tutorial component."""
        self._initialize_llm_components()
        self._setup_tutorial_content()
        self._load_evaluation_thresholds()
    
    def _initialize_llm_components(self):
        """Initialize LLM components for review evaluation."""
        try:
            self.llm_manager = LLMManager()
            self.review_llm = self.llm_manager.initialize_model_from_env("REVIEW_MODEL", "REVIEW_TEMPERATURE")
            if self.review_llm:
                self.evaluator = StudentResponseEvaluator(self.review_llm)
                logger.debug("LLM components initialized for tutorial (connection will be tested on first use)")
            else:
                logger.warning("Failed to initialize review LLM")
                self.evaluator = None
                
        except Exception as e:
            logger.error(f"Error initializing LLM components: {str(e)}")
            self.evaluator = None
    
    def _setup_tutorial_content(self):
        """Set up tutorial content including sample code and examples."""
        # Sample code with multiple errors
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
            t('missingImportError'),
            t('offByOneError'),
            t('stringComparisonError'),
            t('nullCheckError1'),
            t('validationError'),
            t('nullCheckError2')
        ]
        
        # Tutorial examples
        self.poor_review = t('codeIssuesHeader')
        
        review_items = [
            t('line1ImportError'),
            t('line10LoopError'), 
            t('line12StringError'),
            t('line9NullError'),
            t('line6ValidationError'),
            t('line17RemoveError')
        ]
        
        self.good_review = "<br>".join([f"• {item}" for item in review_items])
    
    def _load_evaluation_thresholds(self):
        """Load evaluation thresholds from environment variables."""
        self.meaningful_threshold = float(os.getenv("MEANINGFUL_SCORE", "0.6"))
        self.accuracy_threshold = float(os.getenv("ACCURACY_SCORE", "0.7"))
    
    def render(self, on_complete: Callable = None):
        """
        Render the interactive tutorial.
        
        Args:
            on_complete: Callback function to run when tutorial is completed
        """
        # Check if tutorial should be shown
        if self._should_skip_tutorial():
            if on_complete:
                on_complete()
            return
        
        # Render tutorial header
        st.markdown(f"<h2 style='text-align: center;'>{t('1stPractice')}</h2>", unsafe_allow_html=True)
        
        # Progress tracking
        tutorial_step = st.session_state.get("tutorial_step", 0)
        progress_bar = st.progress(tutorial_step / 5)
        
        # Render appropriate tutorial step
        step_handlers = {
            0: self._render_introduction,
            1: self._render_sample_code,
            2: self._render_poor_example,
            3: self._render_good_example,
            4: self._render_practice_step,
            5: self._render_completion
        }
        
        handler = step_handlers.get(tutorial_step, self._render_completion)
        handler(on_complete)
        
        # Update progress
        progress_bar.progress(tutorial_step / 5)
    
    def _should_skip_tutorial(self) -> bool:
        """Check if tutorial should be skipped."""
        tutorial_completed = self._check_tutorial_completion()
        return tutorial_completed and not st.session_state.get("tutorial_retake", False)
    
    def _render_introduction(self, on_complete: Callable = None):
        """Render the introduction step."""
        st.info(t("Welcome to the Java Code Review Training System! This tutorial will guide you through the process of reviewing code for errors."))
        st.markdown(t("In this system, you'll be presented with Java code snippets that contain intentional errors. Your task is to identify these errors and provide detailed feedback."))
        
        if st.button(t("Next"), key="intro_next"):
            st.session_state.tutorial_step = 1
            st.rerun()
    
    def _render_sample_code(self, on_complete: Callable = None):
        """Render the sample code step."""
        st.info(t("Here's a sample Java code snippet with several errors:"))
        st.code(self.sample_code_with_lines, language="java")
        st.markdown(t("This code contains several issues that need to be identified."))
        
        if st.button(t("Next"), key="code_next"):
            st.session_state.tutorial_step = 2
            st.rerun()
    
    def _render_poor_example(self, on_complete: Callable = None):
        """Render the poor review example step."""
        st.info(t("First, let's see an example of a POOR quality review:"))
        
        st.markdown(f"""
        <div style="border: 1px solid red; border-radius: 5px; padding: 15px; background-color: rgba(255, 0, 0, 0.05); margin-bottom: 15px">
            <h4 style="color: red">{t("Poor Quality Review")}</h4>
            <p>{self.poor_review}</p>
        </div>
        """, unsafe_allow_html=True)
        
        self._render_poor_review_analysis()
        
        if st.button(t("Next"), key="poor_next"):
            st.session_state.tutorial_step = 3
            st.rerun()
    
    def _render_good_example(self, on_complete: Callable = None):
        """Render the good review example step."""
        st.info(t("Now, let's see an example of a GOOD quality review:"))
        
        st.markdown(f"""
        <div style="border: 1px solid green; border-radius: 5px; padding: 15px; background-color: rgba(0, 255, 0, 0.05); margin-bottom: 15px">
            <h4 style="color: green">{t("Good Quality Review")}</h4>
            <pre style="white-space: pre-wrap;">{self.good_review}</pre>
        </div>
        """, unsafe_allow_html=True)
        
        self._render_good_review_analysis()
        
        if st.button(t("Next"), key="good_next"):
            st.session_state.tutorial_step = 4
            st.rerun()
    
    def _render_practice_step(self, on_complete: Callable = None):
        """Render the interactive practice step."""
        st.info(t("Now it's your turn! Try writing a review for one of the errors in the code:"))
        
        # Show code again
        st.code(self.sample_code_with_lines, language="java")
        
        # Focus on specific error
        self._render_focused_error()
        
        # Review input
        user_review = st.text_area(
            t("Write your review comment for this error:"), 
            height=100, 
            key="tutorial_review"
        )
        
        # Show previous evaluation if available
        self._render_previous_evaluation()
        
        # Handle submission
        if st.button(t("Submit"), key="practice_submit"):
            self._handle_practice_submission(user_review)
    
    def _render_completion(self, on_complete: Callable = None):
        """Render the completion step."""
        st.success(t("Congratulations! You've completed the tutorial."))
        
        self._render_key_principles()
        
        if st.button(t("Start Coding!"), key="complete_button"):
            self._complete_tutorial(on_complete)
    
    def _render_poor_review_analysis(self):
        """Render analysis of why the poor review is inadequate."""
        st.markdown(t("This review is not helpful because:"))
        poor_points = [
            t("It doesn't specify which issues exist"),
            t("It doesn't point to specific line numbers"),
            t("It doesn't explain what's wrong and why"),
            t("It doesn't suggest how to fix the issues")
        ]
        
        for point in poor_points:
            st.markdown(f"- {point}")
    
    def _render_good_review_analysis(self):
        """Render analysis of why the good review is effective."""
        st.markdown(t("This review is effective because:"))
        good_points = [
            t("It identifies specific line numbers"),
            t("It clearly explains what's wrong with each issue"),
            t("It explains why each issue is problematic"),
            t("It suggests how to fix each issue")
        ]
        
        for point in good_points:
            st.markdown(f"- {point}")
    
    def _render_focused_error(self):
        """Render the focused error for practice."""
        import random
        
        if "tutorial_focus_error" not in st.session_state:
            st.session_state.tutorial_focus_error = random.randint(0, len(self.known_errors) - 1)
        
        focus_error = self.known_errors[st.session_state.tutorial_focus_error]
        st.markdown(f"**{t('Focus on this error')}:** {focus_error}")
    
    def _render_previous_evaluation(self):
        """Render previous evaluation result if available."""
        if "tutorial_evaluation" in st.session_state:
            eval_result = st.session_state.tutorial_evaluation
            if eval_result["success"]:
                st.success(eval_result["feedback"])
            else:
                st.warning(eval_result["feedback"])
    
    def _render_key_principles(self):
        """Render key principles for good code reviews."""
        st.markdown(t("Remember these key principles for good code reviews:"))
        principles = [
            t("Be specific about line numbers and issues"),
            t("Explain what's wrong and why"),
            t("Provide constructive suggestions"),
            t("Be thorough and check different types of errors")
        ]
        
        for i, principle in enumerate(principles, 1):
            st.markdown(f"{i}. {principle}")
    
    def _handle_practice_submission(self, user_review: str):
        """Handle practice submission and evaluation."""
        if len(user_review.strip()) < 10:
            st.warning(t("Please write a more detailed review"))
        else:
            with st.spinner(t("Evaluating your review with AI...")):
                evaluation_result = self._evaluate_user_review(user_review)
                st.session_state.tutorial_evaluation = evaluation_result
                
                if evaluation_result["success"]:
                    st.success(evaluation_result["feedback"])
                    st.session_state.tutorial_step = 5
                    st.rerun()
                else:
                    st.info(t('faile_review'))
    
    def _complete_tutorial(self, on_complete: Callable = None):
        """Complete the tutorial and award badge."""
        tutorial_marked = self._mark_tutorial_completed()
        
        if tutorial_marked:
            st.session_state.tutorial_completed = True
            st.success(t("Tutorial completed! You earned the Tutorial Master badge! 🎓"))
        else:
            st.warning(t("Tutorial completed, but there was an issue saving your progress."))
            st.session_state.tutorial_completed = True
        
        # Clear tutorial retake flag
        if "tutorial_retake" in st.session_state:
            del st.session_state["tutorial_retake"]
        
        if on_complete:
            on_complete()
        st.rerun()
    
    def _evaluate_user_review(self, user_review: str) -> Dict[str, Any]:
        """Evaluate user review using LLM or fallback method."""
        # Validate format first
        is_valid_format, format_error = self._validate_review_format(user_review)
        if not is_valid_format:
            return {
                "success": False,
                "feedback": format_error,
                "meaningful_score": 0.0,
                "accuracy_score": 0.0,
                "format_error": True
            }
        
        if not self.evaluator:
            # Fallback evaluation
            return self._fallback_evaluation(user_review)
        
        try:
            # Use LLM evaluation
            analysis = self.evaluator.evaluate_review(
                code_snippet=self.sample_code,
                known_problems=self.known_errors,
                student_review=user_review
            )
            
            return self._process_evaluation_analysis(analysis)
            
        except Exception as e:
            logger.error(f"Error evaluating user review: {str(e)}")
            return {
                "success": False,
                "feedback": t("Error evaluating your review. Please try again."),
                "meaningful_score": 0.0,
                "accuracy_score": 0.0
            }
    
    def _validate_review_format(self, student_review: str) -> Tuple[bool, str]:
        """Validate the format of a student review."""
        if not student_review or not student_review.strip():
            return False, t("review_cannot_be_empty")
        
        # Check for line format pattern
        valid_line_pattern = re.compile(r'(?:Line|行)\s*\d+\s*[:：]')
        lines = student_review.strip().split('\n')
        valid_lines = [i+1 for i, line in enumerate(lines) if valid_line_pattern.search(line)]
        
        if valid_lines:
            return True, ""
        
        return False, t("please_use_format_line_description")
    
    def _fallback_evaluation(self, user_review: str) -> Dict[str, Any]:
        """Provide fallback evaluation when LLM is not available."""
        is_good = len(user_review.strip()) >= 10
        return {
            "success": is_good,
            "feedback": t("Great job! Your review looks good.") if is_good else t("Please write a more detailed review"),
            "meaningful_score": 1.0 if is_good else 0.3,
            "accuracy_score": 1.0 if is_good else 0.3
        }
    
    def _process_evaluation_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Process LLM evaluation analysis."""
        if not analysis or not isinstance(analysis, dict):
            return {
                "success": False,
                "feedback": t("Unable to evaluate your review. Please try again."),
                "meaningful_score": 0.0,
                "accuracy_score": 0.0
            }
        
        # Extract and calculate scores
        identified_problems = analysis.get(t("identified_problems"), [])
        meaningful_score = 0.0
        accuracy_score = 0.0
        
        if identified_problems:
            total_meaningful = 0.0
            total_accuracy = 0.0
            valid_problems = 0
            
            for problem in identified_problems:
                if isinstance(problem, dict):
                    try:
                        meaningful = float(problem.get(t('Meaningfulness'), 0.0))
                        accuracy = float(problem.get(t('accuracy'), 0.0))
                        
                        total_meaningful += meaningful
                        total_accuracy += accuracy
                        valid_problems += 1
                    except (ValueError, TypeError):
                        continue
            
            if valid_problems > 0:
                meaningful_score = total_meaningful / valid_problems
                accuracy_score = total_accuracy / valid_problems
        
        # Determine success
        passes_meaningful = meaningful_score >= self.meaningful_threshold
        passes_accuracy = accuracy_score >= self.accuracy_threshold
        success = passes_meaningful and passes_accuracy
        
        # Generate feedback
        if success:
            feedback = t("Great job! Your review looks good.")
        else:
            feedback_parts = []
            if not passes_meaningful:
                feedback_parts.append(t('review_meaning_Poor'))
            if not passes_accuracy:
                feedback_parts.append(t('review_accuracy_poor'))
            
            feedback = t("Please improve your review: ") + ". ".join(feedback_parts)
        
        return {
            "success": success,
            "feedback": feedback,
            "meaningful_score": meaningful_score,
            "accuracy_score": accuracy_score
        }
    
    def _check_tutorial_completion(self) -> bool:
        """Check if tutorial is completed."""
        if not st.session_state.get("auth", {}).get("is_authenticated", False):
            return False
        
        if st.session_state.get("tutorial_completed", False):
            return True
        
        user_info = st.session_state.get("auth", {}).get("user_info", {})
        return user_info.get("tutorial_completed", False)
    
    def _mark_tutorial_completed(self) -> bool:
        """Mark tutorial as completed in database."""
        try:
            from ui.components.auth_ui import AuthUI
            auth_ui = AuthUI()
            success = auth_ui.mark_tutorial_completed()
            
            if success:
                st.session_state.tutorial_completed = True
                
                # Award badge
                try:
                    from auth.badge_manager import BadgeManager
                    badge_manager = BadgeManager()
                    user_id = st.session_state.get("auth", {}).get("user_id")
                    if user_id:
                        badge_manager.award_badge(user_id, "tutorial-master")
                except Exception as e:
                    logger.error(f"Error awarding tutorial badge: {str(e)}")
            
            return success
            
        except ImportError:
            logger.error("Could not import AuthUI")
            return False