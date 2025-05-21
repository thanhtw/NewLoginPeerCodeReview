"""
Feedback System for Java Peer Review Training System.

This module provides a unified system for displaying feedback on student reviews
and handling the feedback tab functionality with proper workflow state management.
"""

import streamlit as st
import logging
import pandas as pd
import matplotlib.pyplot as plt
import time
import traceback
from typing import List, Dict, Any, Optional, Tuple, Callable
from auth.badge_manager import BadgeManager
from auth.mysql_auth import MySQLAuthManager
from utils.language_utils import t, get_current_language, get_db_field_name, get_multilingual_field

import plotly.express as px
import plotly.graph_objects as go
from auth.badge_manager import BadgeManager
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FeedbackSystem:
    """
    Unified feedback system for the Java Peer Review Training System.
    
    This class combines the UI rendering and workflow state management
    for the feedback tab. It handles displaying analysis results,
    generating comparison reports, and updating user statistics.
    """
    
    def __init__(self, workflow, auth_ui=None):
        """
        Initialize the FeedbackSystem with workflow and auth components.
        
        Args:
            workflow: The JavaCodeReviewGraph workflow instance
            auth_ui: Optional AuthUI instance for updating user statistics
        """
        self.badge_manager = BadgeManager()
        self.auth_manager = MySQLAuthManager()
        self.workflow = workflow
        self.auth_ui = auth_ui
        self.stats_updates = {}  # Track stats updates to avoid duplicates

    def render_feedback_tab(self):
        """
        Render the feedback tab with review analysis, user badges, and progress visualization.
        Checks if review is completed before showing feedback.
        """
        state = st.session_state.workflow_state
        
        # Check if review process is completed
        review_completed = self._check_review_completion(state)
        
        # Block access if review not completed
        if not review_completed:
            self._display_completion_required_message(state)
            return
        
        # Get the latest review analysis and history
        latest_review, review_history = self._extract_review_data(state)
        
        # Generate comparison report if needed
        if latest_review and latest_review.analysis and (not hasattr(state, 'comparison_report') or not state.comparison_report):
            self._generate_comparison_report(state, latest_review)
        
        # Get the latest review analysis
        latest_analysis = latest_review.analysis if latest_review else None
        
        # Update user statistics if AuthUI is provided and we have analysis
        if self.auth_ui and latest_analysis:
            self._update_user_statistics(state, latest_analysis)
        
        # Get user ID from session state
        user_id = st.session_state.auth.get("user_id") if "auth" in st.session_state else None
        
        # Add tabs for different sections of feedback
        feedback_tabs = st.tabs([t("review_feedback"), t("badges"), t("progress"), t("leaderboard")])
        
        with feedback_tabs[0]:
            # Display the feedback results      
            self.render_results(
                comparison_report=state.comparison_report,           
                review_analysis=latest_analysis,
                review_history=review_history        
            )
        
        with feedback_tabs[1]:
            # Show user badges
            if user_id:
                self.render_badge_showcase(user_id)
            else:
                st.info("Login to track your badges!")
        
        with feedback_tabs[2]:
            # Show progress visualization
            if user_id:
                self.render_progress_dashboard(user_id)
            else:
                st.info("Login to track your progress!")
        
        with feedback_tabs[3]:
            # Show leaderboard
            if user_id:
                self.render_leaderboard(user_id)
            else:
                st.info("Login to view the leaderboard!")
        
        # Add a button to start a new session
        st.markdown("---")
        self._render_new_session_button()

    def render_results(self, 
                      comparison_report: str = None,                     
                      review_analysis: Dict[str, Any] = None,
                      review_history: List[Dict[str, Any]] = None) -> None:
        """
        Render the analysis results and feedback with improved review visibility.
        
        Args:
            comparison_report: Comparison report text           
            review_analysis: Analysis of student review
            review_history: History of review iterations
        """
      
        if not comparison_report and not review_analysis:
            st.info(t("no_analysis_results"))
            return
        
        # First show performance summary metrics at the top
        if review_history and len(review_history) > 0 and review_analysis:
            self._render_performance_summary(review_analysis, review_history)
        
        # Display the comparison report
        if comparison_report:
            st.subheader(t("educational_feedback"))            
            st.markdown(
                f'<div class="comparison-report">{comparison_report}</div>',
                unsafe_allow_html=True
            )
        
        # Always show review history for better visibility
        if review_history and len(review_history) > 0:
            st.subheader(t("your_review"))
            
            # First show the most recent review prominently
            if review_history:
                latest_review = review_history[-1]    
                review_analysis = latest_review["review_analysis"]
                iteration = latest_review["iteration_number"]
                
                st.markdown(f"#### {t('your_final_review').format(iteration=iteration)}")
                
                # Format the review text with syntax highlighting
                st.markdown("```text\n" +latest_review["student_review"] + "\n```")
                                
            # Show earlier reviews in an expander if there are multiple
            if len(review_history) > 1:
                with st.expander(t("review_history"), expanded=False):
                    tabs = st.tabs([f"{t('attempt')} {rev['iteration_number']}" for i, rev in enumerate(review_history)])
                    
                    for i, (tab, review) in enumerate(zip(tabs, review_history)):
                        with tab:
                            review_analysis = review["review_analysis"]
                            st.markdown("```text\n" + review[t('student_review')] + "\n```")
                            
                            st.write(f"**{t('found')}:** {review_analysis[t('identified_count')]} {t('of')} "
                                    f"{review_analysis[t('total_problems')]} {t('issues')} "
                                    f"({review_analysis[t('identified_percentage')]:.1f}% {t('accuracy')})")
        
        # Display analysis details in an expander
        if review_analysis:            
            with st.expander(t("detailed_analysis"), expanded=True):
                tabs = st.tabs([t("identified_issues"), t("missed_issues")])
                
                with tabs[0]:  # Identified Issues
                    self._render_identified_issues(review_analysis)
                
                with tabs[1]:  # Missed Issues
                    self._render_missed_issues(review_analysis)

        # Add horizontal separator
        st.markdown("---")             
            
    def _render_performance_summary(self, review_analysis: Dict[str, Any], review_history: List[Dict[str, Any]]):
        """Render enhanced performance summary metrics and charts with CJK font support"""
        st.subheader(t("review_performance_summary"))
        
        # Create performance metrics using the original error count if available
        col1, col2 = st.columns(2)
        
        # Get the correct total_problems count from original_error_count if available
        original_error_count = review_analysis[t('total_problems')]
        # Calculate metrics using the original count for consistency
        identified_count = review_analysis[t('identified_count')]
        accuracy = (identified_count / original_error_count * 100) if original_error_count > 0 else 0
                
        with col1:
            st.metric(
                t("overall_accuracy"), 
                f"{accuracy:.1f}%",
                delta=None,
                delta_color="normal"
            )
            
        with col2:
            st.metric(
                t("issues_identified"), 
                f"{identified_count}/{original_error_count}",
                delta=None
            )
            
        # Create a progress chart if multiple iterations
        if len(review_history) > 1:
            # Extract data for chart
            iterations = []
            identified_counts = []
            accuracy_percentages = []
            
            for review in review_history:
                analysis = review["review_analysis"]
                iterations.append(review["iteration_number"])
                # Use consistent error count for all iterations
                review_identified = analysis[t("identified_count")]
                identified_counts.append(review_identified)
                
                # Calculate accuracy consistently
                review_accuracy = (review_identified / original_error_count * 100) if original_error_count > 0 else 0
                accuracy_percentages.append(review_accuracy)
                    
            # Create a DataFrame for the chart
            chart_data = pd.DataFrame({
                t("iteration"): iterations,
                t("issues_found"): identified_counts,
                f"{t('accuracy')} (%)": accuracy_percentages
            })
            
            # Display the chart with two y-axes
            st.subheader(t("progress_across_iterations"))
            
            # Set font configuration for matplotlib for CJK support
            import matplotlib
            import matplotlib.font_manager as fm
            
            # Configure matplotlib to use a font that supports CJK characters
            # Try to find appropriate fonts based on platform
            font_list = matplotlib.rcParams['font.sans-serif']
            
            # Add CJK compatible fonts to the front of the list
            # Common CJK compatible fonts across different platforms
            cjk_fonts = ['Noto Sans CJK JP', 'Noto Sans CJK TC', 'Noto Sans CJK SC', 
                        'Microsoft YaHei', '微软雅黑', 'Microsoft JhengHei', '微軟正黑體',
                        'SimHei', '黑体', 'WenQuanYi Zen Hei', 'WenQuanYi Micro Hei',
                        'Hiragino Sans GB', 'STHeiti', 'Source Han Sans CN', 
                        'Source Han Sans TW', 'Source Han Sans JP',
                        'DroidSansFallback', 'Droid Sans Fallback']
            
            # Set the font family to ensure CJK support
            matplotlib.rcParams['font.family'] = 'sans-serif'
            matplotlib.rcParams['font.sans-serif'] = cjk_fonts + font_list
            
            # Use a non-DejaVu font explicitly for this plot
            try:
                # Trying to use a specific CJK-compatible font if available
                plt.rcParams['font.sans-serif'] = cjk_fonts
                # Set Unicode fallback font
                plt.rcParams['axes.unicode_minus'] = False
            except Exception as e:
                # Log the error but continue
                logger.warning(f"Could not set matplotlib font: {str(e)}")
            
            # Using matplotlib for more control - with CJK font configuration
            fig, ax1 = plt.subplots(figsize=(10, 4))
            
            color = 'tab:blue'
            ax1.set_xlabel(t('iteration'))
            ax1.set_ylabel(t('issues_found'), color=color)
            ax1.plot(chart_data[t("iteration")], chart_data[t("issues_found")], marker='o', color=color)
            ax1.tick_params(axis='y', labelcolor=color)
            ax1.grid(True, linestyle='--', alpha=0.7)
            
            ax2 = ax1.twinx()  # Create a second y-axis
            color = 'tab:red'
            ax2.set_ylabel(f"{t('accuracy')} (%)", color=color)
            ax2.plot(chart_data[t("iteration")], chart_data[f"{t('accuracy')} (%)"], marker='s', color=color)
            ax2.tick_params(axis='y', labelcolor=color)
            
            fig.tight_layout()
            st.pyplot(fig)
    
    def _render_identified_issues(self, review_analysis: Dict[str, Any]):
        """Render identified issues section with enhanced styling and proper language support"""
        identified_problems = review_analysis[t("identified_problems")]

        if not identified_problems:
            st.info(t("no_identified_issues"))
            return
                
        st.subheader(f"{t('correctly_identified_issues')} ({len(identified_problems)})")
        
        # Group issues by category if possible
        categorized_issues = {}
        for issue in identified_problems:
            # Try to extract category information
            category = None
            if isinstance(issue, dict) and t("category") in issue:
                category = issue[t('category')]
            elif isinstance(issue, str):
                # Try to extract category from string format like "CATEGORY - Issue name"
                parts = issue.split(" - ", 1)
                if len(parts) > 1:
                    category = parts[0]
            
            # Default category if none found
            if not category:
                category = "Other"
                
            # Add to categorized dictionary
            if category not in categorized_issues:
                categorized_issues[category] = []
            
            categorized_issues[category].append(issue)
        
        # Display issues by category with collapsible sections
        for category, issues in categorized_issues.items():
            if category and issues:     
                for i, issue in enumerate(issues, 1):
                    if isinstance(issue, dict):
                        problem = issue[t('problem')]
                        student_comment = issue[t('student_comment')]
                        #feedback = issue[t('feedback')]                        
                        st.markdown(
                            f"""
                            <div style="border-left: 4px solid #4CAF50; padding: 10px; margin: 10px 0;
                                        border-radius: 4px; background-color: rgba(76, 175, 80, 0.1);">
                                <div style="margin-bottom: 5px;"><strong>{t("problem")}:</strong> {problem}</div>
                                <div style="margin-bottom: 5px;"><strong>{t("student_comment")}:</strong> {student_comment}</div>
                               
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        # Fallback for plain string issues
                        st.markdown(
                            f"""
                            <div style="border-left: 4px solid #4CAF50; padding: 10px; margin: 10px 0;
                                        border-radius: 4px; background-color: rgba(76, 175, 80, 0.1);">
                                <strong>{i}. {issue}</strong>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
    
    def _render_missed_issues(self, review_analysis: Dict[str, Any]):
        """Render missed issues section with enhanced styling and proper language support"""

        missed_problems = review_analysis[t("missed_problems")]
        
        if not missed_problems:
            st.success(t("all_issues_found"))
            return
                
        st.subheader(f"{t('issues_missed')} ({len(missed_problems)})")
        
        # Group issues by category similar to identified issues method
        categorized_issues = {}
        
        for issue in missed_problems:
            # Extract category similar to identified issues method
            category = None
            if isinstance(issue, dict) and t("category") in issue:
                category = issue[t("category")]
            elif isinstance(issue, str):
                parts = issue.split(" - ", 1)
                if len(parts) > 1:
                    category = parts[0]
            
            if not category:
                category = "Other"
                
            if category not in categorized_issues:
                categorized_issues[category] = []
            
            categorized_issues[category].append(issue)
        
        # Display issues by category with collapsible sections
        for category, issues in categorized_issues.items():
            if category and issues:             
                for i, issue in enumerate(issues, 1):
                    if isinstance(issue, dict):
                        problem = issue[t('problem')]
                        hint = issue[t('hint')]
                        st.markdown(
                            f"""
                            <div style="border-left: 4px solid #dc3545; padding: 10px; margin: 10px 0;
                                        border-radius: 4px; background-color: rgba(220, 53, 69, 0.1);">
                                <div style="margin-bottom: 5px;"><strong>{t("problem")}:</strong> {problem}</div>
                                {f'<div style="margin-bottom: 5px;"><strong>{t("hint")}:</strong> {hint}</div>' if hint else ''}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        # Fallback for plain string
                        st.markdown(
                            f"""
                            <div style="border-left: 4px solid #dc3545; padding: 10px; margin: 10px 0;
                                        border-radius: 4px; background-color: rgba(220, 53, 69, 0.1);">
                                <strong>{i}. {issue}</strong>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
    
    def _check_review_completion(self, state) -> bool:
        """
        Determine if the review process is completed.
        
        Args:
            state: The workflow state
            
        Returns:
            bool: True if review is completed, False otherwise
        """
        review_completed = False
        
        # Check if max iterations reached or review is sufficient
        if hasattr(state, 'current_iteration') and hasattr(state, 'max_iterations'):
            if getattr(state, 'current_iteration', 0) > getattr(state, 'max_iterations', 3):
                review_completed = True
                logger.debug(t("review_completed_max_iterations"))
            elif getattr(state, 'review_sufficient', False):
                review_completed = True
                logger.debug(t("review_completed_sufficient"))
        
        # Check for all errors identified - HIGHEST PRIORITY CHECK
        if hasattr(state, 'review_history') and state.review_history and len(state.review_history) > 0:
            latest_review = state.review_history[-1]
            analysis = latest_review.analysis if hasattr(latest_review, 'analysis') else {}
            identified_count = analysis[t('identified_count')]
            total_problems = analysis[t('total_problems')]
            
            if identified_count == total_problems and total_problems > 0:
                review_completed = True
                logger.debug(f"{t('review_completed_all_identified')} {total_problems} {t('issues')}")
                
        return review_completed
    
    def _display_completion_required_message(self, state):
        """Display message requiring completion of review before viewing feedback."""
        st.warning(f"{t('complete_review_first')}")
        st.info(f"{t('current_process_review1')} {getattr(state, 'current_iteration', 1)-1}/{getattr(state, 'max_iterations', 3)} {t('current_process_review2')}")
    
    def _extract_review_data(self, state):
        """
        Extract review data from the workflow state.
        
        Args:
            state: The workflow state
            
        Returns:
            Tuple: (latest_review, review_history)
        """
        latest_review = None
        review_history = []
        
        # Make sure we have review history
        if hasattr(state, 'review_history') and state.review_history:
            review_history_list = state.review_history           
            if review_history_list and len(review_history_list) > 0:
                latest_review = review_history_list[-1]
                
                # Convert review history to the format expected by FeedbackDisplayUI
                for review in review_history_list:                   
                    review_history.append({
                        "iteration_number":  getattr(review, "iteration_number", 0),
                        "student_review": getattr(review, "student_review", ""),
                        "review_analysis": getattr(review, "analysis", {})
                    })
                
        return latest_review, review_history
    
    def _generate_comparison_report(self, state, latest_review):
        """
        Generate a comparison report for the review feedback.
        
        Args:
            state: The workflow state
            latest_review: The latest review attempt
        """
        try:
            # Get the known problems from the evaluation result instead of code_snippet.known_problems
            if hasattr(state, 'evaluation_result') and state.evaluation_result and 'found_errors' in state.evaluation_result:
                stamp = state.evaluation_result
                found_errors = stamp[t("found_errors")]
                
                # Get the evaluator from the workflow
                evaluator = self.workflow.workflow_nodes.evaluator
                
                if evaluator:
                    # Generate a comparison report using the evaluator's method
                    state.comparison_report = evaluator.generate_comparison_report(
                        found_errors,
                        latest_review.analysis
                    )
                    logger.debug(t("generated_comparison_report"))
                else:
                    logger.error("Evaluator not available for generating comparison report")
                    state.comparison_report = (
                        f"# {t('review_feedback')}\n\n"
                        f"{t('error_generating_report')} "
                        f"{t('check_review_history')}."
                    )
        except Exception as e:
            logger.error(f"{t('error')} {t('generating_comparison_report')}: {str(e)}")
            logger.error(traceback.format_exc())  # Log full stacktrace
            if not hasattr(state, 'comparison_report') or not state.comparison_report:
                state.comparison_report = (
                    f"# {t('review_feedback')}\n\n"
                    f"{t('error_generating_report')} "
                    f"{t('check_review_history')}."
                )
    
    def _update_user_statistics(self, state, latest_analysis):
        """
        Update user statistics based on review performance.
        Now with level-up animation.
        
        Args:
            state: The workflow state
            latest_analysis: The analysis of the latest review
        """
        # Check if we already updated stats for this iteration
        current_iteration = getattr(state, 'current_iteration', 1)
        identified_count = latest_analysis[t("identified_count")]
        stats_key = f"stats_updated_{current_iteration}_{identified_count}"
    
        if stats_key not in st.session_state and stats_key not in self.stats_updates:
            try:
                # Extract accuracy and identified_count from the latest review
                accuracy = latest_analysis[t("accuracy_percentage")]
                    
                # Log details before update
                logger.debug(f"{t('preparing_update_stats')}: {t('accuracy')}={accuracy:.1f}%, " + 
                        f"{t('score')}={identified_count} ({t('identified_count')}), key={stats_key}")
                
                # Update user stats with identified_count as score
                result = self.auth_ui.update_review_stats(accuracy, identified_count)
                    
                # Store the update result for debugging
                st.session_state[stats_key] = result
                self.stats_updates[stats_key] = True
                
                # Log the update result
                if result and result.get("success", False):
                    logger.debug(f"Successfully updated user statistics: {result}")
                    
                    # Add explicit UI message about the update
                    #st.success(f"Statistics updated! Added {identified_count} to your score.")
                    
                    # Show level promotion message and animation if level changed
                    if result.get("level_changed", False):
                        old_level = result.get("old_level", "").capitalize()
                        new_level = result.get("new_level", "").capitalize()
                        
                        # Import the animation function
                        try:
                            from ui.animation import level_up_animation
                            level_up_animation(old_level, new_level)
                        except ImportError:
                            # Fallback if animation module is not available
                            st.balloons()  # Add visual celebration effect
                            st.success(f"🎉 Congratulations! Your level has been upgraded from {old_level} to {new_level}!")
                        
                        # Give the database a moment to complete the update
                        time.sleep(0.5)
                else:                 
                    logger.error(f"{t('failed_update_statistics')}:")
                    st.error(f"{t('failed_update_statistics')}:")

                
            except Exception as e:
                logger.error(f"{t('error')} {t('updating_user_statistics')}: {str(e)}")
                logger.error(traceback.format_exc())
                st.error(f"{t('error')} {t('updating_statistics')}: {str(e)}")
                
    def _render_new_session_button(self):
        """Render button to start a new session."""
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
                self.stats_updates = {}                    
                # Set the full reset flag
                st.session_state.full_reset = True
                st.rerun()

    def render_badge_showcase(self, user_id: str) -> None:
        """
        Render the user's earned badges in a visually appealing way.
        
        Args:
            user_id: The user's ID
        """
        badge_manager = BadgeManager()
        badges = badge_manager.get_user_badges(user_id)
        
        if not badges:
            st.info("No badges earned yet. Complete reviews to earn badges!")
            return
        
        st.subheader("🏆 Achievement Badges")
        
        # Group badges by category
        badge_categories = {}
        for badge in badges:
            category = badge.get("category", "Other")
            if category not in badge_categories:
                badge_categories[category] = []
            badge_categories[category].append(badge)
        
        # Create tabs for each category
        if badge_categories:
            tabs = st.tabs(list(badge_categories.keys()))
            
            for i, (category, category_badges) in enumerate(badge_categories.items()):
                with tabs[i]:
                    col_count = min(3, len(category_badges))
                    cols = st.columns(col_count)
                    
                    for j, badge in enumerate(category_badges):
                        col_idx = j % col_count
                        with cols[col_idx]:
                            awarded_at_value = badge.get("awarded_at", "")
                            if isinstance(awarded_at_value, datetime.datetime):
                                awarded_at = awarded_at_value.strftime("%Y-%m-%d")  # Format as YYYY-MM-DD
                            else:
                                # Fallback to original string split if it's not a datetime
                                awarded_at = str(awarded_at_value).split(' ')[0] if awarded_at_value else ""
                            st.markdown(f"""
                            <div style="text-align: center; padding: 15px; background-color: rgba(100, 100, 255, 0.1); 
                                        border-radius: 10px; margin-bottom: 15px;">
                                <div style="font-size: 3rem;">{badge.get("icon", "🏅")}</div>
                                <div style="font-weight: bold; margin: 5px 0;">{badge.get("name", "Badge")}</div>
                                <div style="font-size: 0.8rem; color: #666;">{badge.get("description", "")}</div>
                                <div style="font-size: 0.7rem; margin-top: 10px;">Earned on {awarded_at}</div>
                            </div>
                            """, unsafe_allow_html=True)

    def render_progress_dashboard(self, user_id: str) -> None:
        """
        Render a visual dashboard of the user's progress.
        
        Args:
            user_id: The user's ID
        """
        badge_manager = BadgeManager()
        
        # Get category stats
        category_stats = badge_manager.get_category_stats(user_id)
        
        st.subheader("📊 Progress Dashboard")
        
        if not category_stats:
            st.info("Complete more reviews to see your progress across error categories!")
            return
        
        # Create mastery heatmap
        categories = []
        mastery_levels = []
        encountered_counts = []
        identified_counts = []
        
        for stat in category_stats:
            categories.append(stat.get("category", "Unknown"))
            mastery_levels.append(stat.get("mastery_level", 0) * 100)  # Convert to percentage
            encountered_counts.append(stat.get("encountered", 0))
            identified_counts.append(stat.get("identified", 0))
        
        # Create three columns for different visualizations
        col1, col2 = st.columns(2)
        
        with col1:
            # Mastery level across categories
            fig = px.bar(
                x=categories,
                y=mastery_levels,
                title="Error Category Mastery",
                labels={"x": "Category", "y": "Mastery Level (%)"},
                color=mastery_levels,
                color_continuous_scale="Viridis",
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Errors encountered vs identified
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=categories,
                y=encountered_counts,
                name="Encountered",
                marker_color="indianred"
            ))
            fig.add_trace(go.Bar(
                x=categories,
                y=identified_counts,
                name="Identified",
                marker_color="lightsalmon"
            ))
            fig.update_layout(
                title="Errors Encountered vs Identified",
                xaxis_title="Category",
                yaxis_title="Count",
                barmode="group",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Create skill tree visualization
        st.subheader("🌳 Skill Tree")
        
        # Calculate overall mastery percentage
        total_encountered = sum(encountered_counts)
        total_identified = sum(identified_counts)
        overall_mastery = total_identified / total_encountered if total_encountered > 0 else 0
        
        # Create skill tree with plotly
        fig = go.Figure()
        
        # Central node
        fig.add_trace(go.Scatter(
            x=[0], y=[0],
            mode="markers+text",
            marker=dict(size=30, color="rgba(100, 100, 255, 0.8)"),
            text=["Java Review<br>Skills"],
            textposition="middle center",
            hoverinfo="text",
            hovertext=[f"Overall Mastery: {overall_mastery * 100:.1f}%"]
        ))
        
        # Category nodes
        angles = [i * (2 * 3.14159 / len(categories)) for i in range(len(categories))]
        x_coords = [3 * 3.5 * 3.4 * 3 * 3.7 * 3.8 * 3.5 * 3.3 * 3.3 * 3 * 3.7 * 3.8 * 3.5 * 3.3 * 3.3 * 2 * 3.2 * 3.3 * 3.2 * 3.3 * 3.3 * 2 * 3.2 * 3.3 * 3.2 * 3.3 * 3.3 * 2 * 3.2 * 3.3 * 3.2 * 3.3 * 3.3 * 2 * 3.2 * 3.3 * 3.2 * 3.3 * 3.3 * 2 * 3.2 * 3.3 * 3.2 * 3.3 * 3.3 * 2 * 3.2 * 3.3 * 3.2 * 3.3 * 3.3 * 2 * 3.2 * 3.3 * 3.2 * 3.3 * 3.3 * 2 * 3.2 * 3.3 * 3.2 * 3.3 * 3.3 * 2 * 3.2 * 3.3 * 3.2 * 3.3 * 3.3 * 2 * 3.2 * 3.3 * 3.2 * 3.3 * 3.3 * 2 * 3.2 * 3.3 * 3.2 * 3.3 * 3.3 * 2 * 3.2 * 3.3 * 3.2 * 3.3 * 3.3 * 2 * 3.2 * 3.3 * 3.2 * 3.3 * 3.3 * 2 * 3.2 * 3.3 * 2 * math.cos(angle) for angle in angles]
        y_coords = [2 * math.sin(angle) for angle in angles]
        
        # Add category nodes
        for i, category in enumerate(categories):
            mastery = mastery_levels[i] / 100  # Convert back to 0-1
            color = f"rgba({int(255 * (1 - mastery))}, {int(255 * mastery)}, 100, 0.8)"
            
            fig.add_trace(go.Scatter(
                x=[x_coords[i]], y=[y_coords[i]],
                mode="markers+text",
                marker=dict(size=25, color=color),
                text=[category],
                textposition="middle center",
                hoverinfo="text",
                hovertext=[f"{category}<br>Mastery: {mastery_levels[i]:.1f}%<br>Encountered: {encountered_counts[i]}<br>Identified: {identified_counts[i]}"]
            ))
            
            # Add edges
            fig.add_trace(go.Scatter(
                x=[0, x_coords[i]], y=[0, y_coords[i]],
                mode="lines",
                line=dict(width=2, color=color),
                hoverinfo="none"
            ))
        
        fig.update_layout(
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=500,
            margin=dict(l=0, r=0, b=0, t=0),
            plot_bgcolor="rgba(240, 240, 240, 0.8)"
        )
        
        st.plotly_chart(fig, use_container_width=True)

    def render_leaderboard(self, user_id: str) -> None:
        """
        Render the point-based leaderboard.
        
        Args:
            user_id: The current user's ID
        """
        badge_manager = BadgeManager()
        leaders = badge_manager.get_leaderboard(10)
        user_rank = badge_manager.get_user_rank(user_id)
        
        st.subheader("🏆 " + t("leaderboard"))
        
        if not leaders:
            st.info(t("no_users_leaderboard"))
            return
        
        # Get current language for field selection
        current_lang = get_current_language()
        display_name_field = f"display_name_{current_lang}" if current_lang in ["en", "zh-tw"] else "display_name"
        level_field = f"level_name_{current_lang}" if current_lang in ["en", "zh-tw"] else "level"
        
        # Create leaderboard table with translated headers
        st.markdown(f"""
        <style>
        .leaderboard-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .leaderboard-table th, .leaderboard-table td {{
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .leaderboard-table tr:hover {{
            background-color: rgba(100, 100, 255, 0.05);
        }}
        .leaderboard-table th {{
            background-color: rgba(100, 100, 255, 0.1);
        }}
        .current-user {{
            background-color: rgba(100, 255, 100, 0.1) !important;
            font-weight: bold;
        }}
        .gold {{
            color: gold;
            font-weight: bold;
        }}
        .silver {{
            color: silver;
            font-weight: bold;
        }}
        .bronze {{
            color: #cd7f32;
            font-weight: bold;
        }}
        </style>
        
        <table class="leaderboard-table">
            <tr>
                <th>{t("rank")}</th>
                <th>{t("user")}</th>
                <th>{t("level")}</th>
                <th>{t("points")}</th>
                <th>{t("badges")}</th>
            </tr>
        """, unsafe_allow_html=True)

        
        for leader in leaders:
            rank = leader.get("rank", 0)
            rank_class = "gold" if rank == 1 else "silver" if rank == 2 else "bronze" if rank == 3 else ""
            user_class = "current-user" if leader.get("uid") == user_id else ""
            
            # Get trophy emoji based on rank
            rank_emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
            
            # Get display name and level with language support
            display_name = leader.get(display_name_field, leader.get("display_name", t("unknown")))
            level_display = leader.get(level_field, leader.get("level", "basic")).capitalize()
            
            st.markdown(f"""
            <tr class="{user_class}">
                <td class="{rank_class}">{rank_emoji}</td>
                <td>{display_name}</td>
                <td>{level_display}</td>
                <td>{leader.get("total_points", 0)}</td>
                <td>{leader.get("badge_count", 0)}</td>
            </tr>
            """, unsafe_allow_html=True)
        
        st.markdown("</table>", unsafe_allow_html=True)
        
        # Show user's rank if not in top 10
        if user_id and not any(leader.get("uid") == user_id for leader in leaders):
            rank = user_rank.get("rank", 0)
            total_users = user_rank.get("total_users", 0)
            
            st.info(f"Your rank: {rank} of {total_users} users")

def render_feedback_tab(workflow, auth_ui=None):
    """
    Render the feedback and analysis tab with enhanced visualization 
    and user statistics updating.
    
    Args:
        workflow: The JavaCodeReviewGraph workflow instance
        auth_ui: Optional AuthUI instance for updating user statistics
    """
    # Create the feedback system instance
    feedback_system = FeedbackSystem(workflow, auth_ui)
    
    # Render the feedback tab
    feedback_system.render_feedback_tab()