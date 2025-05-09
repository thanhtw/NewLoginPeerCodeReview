"""
Feedback Display UI module for Java Peer Review Training System.

This module provides the FeedbackDisplayUI class for displaying feedback on student reviews.
"""

import streamlit as st
import logging
import pandas as pd
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Optional, Tuple, Callable
from utils.language_utils import t, get_current_language, get_field_value, get_state_attribute


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FeedbackDisplayUI:
    """
    UI Component for displaying feedback on student reviews.
    
    This class handles displaying analysis results, review history,
    and feedback on student reviews.
    """
    
    def render_results(self, 
                      comparison_report: str = None,
                      review_summary: str = None,
                      review_analysis: Dict[str, Any] = None,
                      review_history: List[Dict[str, Any]] = None,
                      on_reset_callback: Callable[[], None] = None) -> None:
        """
        Render the analysis results and feedback with improved review visibility.
        
        Args:
            comparison_report: Comparison report text
            review_summary: Review summary text
            review_analysis: Analysis of student review
            review_history: History of review iterations
            on_reset_callback: Callback function when reset button is clicked
        """
        if not comparison_report and not review_summary and not review_analysis:
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
                review_analysis = latest_review.get("review_analysis", {})
                iteration = latest_review.get("iteration_number", 0)
                
                st.markdown(f"#### {t('your_final_review').format(iteration=iteration)}")
                
                # Format the review text with syntax highlighting
                st.markdown("```text\n" + latest_review.get("student_review", "") + "\n```")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        t("issues_found"), 
                        f"{review_analysis.get('identified_count', 0)} {t('of')} {review_analysis.get('total_problems', 0)}",
                        delta=None
                    )
                with col2:
                    st.metric(
                        t("accuracy"), 
                        f"{review_analysis.get('accuracy_percentage', 0):.1f}%",
                        delta=None
                    )
                with col3:
                    false_positives = len(review_analysis.get('false_positives', []))
                    st.metric(
                        t("false_positives"), 
                        false_positives,
                        delta=None
                    )
            
            # Show earlier reviews in an expander if there are multiple
            if len(review_history) > 1:
                with st.expander(t("review_history"), expanded=False):
                    tabs = st.tabs([f"{t('attempt')} {rev.get('iteration_number', i+1)}" for i, rev in enumerate(review_history)])
                    
                    for i, (tab, review) in enumerate(zip(tabs, review_history)):
                        with tab:
                            review_analysis = review.get("review_analysis", {})
                            st.markdown("```text\n" + review.get("student_review", "") + "\n```")
                            
                            st.write(f"**{t('found')}:** {review_analysis.get('identified_count', 0)} {t('of')} "
                                    f"{review_analysis.get('total_problems', 0)} {t('issues')} "
                                    f"({review_analysis.get('accuracy_percentage', 0):.1f}% {t('accuracy')})")
        
        # Display analysis details in an expander
        if review_summary or review_analysis:
            with st.expander(t("detailed_analysis"), expanded=True):
                tabs = st.tabs([t("identified_issues"), t("missed_issues")])
                
                with tabs[0]:  # Identified Issues
                    self._render_identified_issues(review_analysis)
                
                with tabs[1]:  # Missed Issues
                    self._render_missed_issues(review_analysis)

        # Start over button
        st.markdown("---")             
            
    def _render_performance_summary(self, review_analysis: Dict[str, Any], review_history: List[Dict[str, Any]]):
        """Render enhanced performance summary metrics and charts"""
        st.subheader(t("review_performance_summary"))
        
        # Create performance metrics using the original error count if available
        col1, col2, col3 = st.columns(3)
        
        # Get the correct total_problems count from original_error_count if available
        original_error_count = get_field_value(review_analysis, "original_error_count", 0)
        if original_error_count <= 0:
            original_error_count = get_field_value(review_analysis, "total_problems", 0)
        
        # Calculate metrics using the original count for consistency
        identified_count = get_field_value(review_analysis, "identified_count", 0)
        accuracy = (identified_count / original_error_count * 100) if original_error_count > 0 else 0
        false_positives = len(get_field_value(review_analysis, "false_positives", []))
        
        # Generate color based on accuracy
        if accuracy >= 80:
            color = "#28a745"  # Green for good performance
            icon = "✅"
        elif accuracy >= 60:
            color = "#ffc107"  # Yellow for medium performance
            icon = "⚠️"
        else:
            color = "#dc3545"  # Red for needs improvement
            icon = "❌"
        
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
            
        with col3:
            st.metric(
                t("false_positives"), 
                f"{false_positives}",
                delta=None
            )
        
        # Add a visual progress bar for accuracy
        st.markdown(f"""
            <div style="margin: 10px 0 20px 0; background-color: #f0f2f5; border-radius: 5px; padding: 5px; position: relative;">
                <div style="width: {accuracy}%; background-color: {color}; height: 30px; border-radius: 3px; 
                    transition: width 0.5s ease-in-out; position: relative; text-align: center;">
                    <span style="position: absolute; top: 5px; left: 50%; transform: translateX(-50%); color: white; font-weight: bold;">
                        {accuracy:.1f}%
                    </span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 5px;">
                    <span style="color: #666;">0%</span>
                    <span style="color: #666;">25%</span>
                    <span style="color: #666;">50%</span>
                    <span style="color: #666;">75%</span>
                    <span style="color: #666;">100%</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
                
        # Create a progress chart if multiple iterations
        if len(review_history) > 1:
            # Extract data for chart
            iterations = []
            identified_counts = []
            accuracy_percentages = []
            
            for review in review_history:
                analysis = get_field_value(review, "review_analysis", {})
                iterations.append(get_field_value(review, "iteration_number", 0))
                
                # Use consistent error count for all iterations
                review_identified = get_field_value(analysis, "identified_count", 0)
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
            
            # Using matplotlib for more control
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
        """Render identified issues section with enhanced styling"""
        identified_problems = review_analysis.get("identified_problems", [])
        
        if not identified_problems:
            st.info(t("no_identified_issues"))
            return
            
        st.subheader(f"{t('correctly_identified_issues')} ({len(identified_problems)})")
        
        # Group issues by category if possible
        categorized_issues = {}
        
        for issue in identified_problems:
            # Try to extract category information
            category = None
            if isinstance(issue, dict) and "category" in issue:
                category = issue.get("category")
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
            with st.expander(f"{category} ({len(issues)})", expanded=True):
                for i, issue in enumerate(issues, 1):
                    issue_text = issue
                    if isinstance(issue, dict):
                        issue_text = issue.get("problem", str(issue))
                    
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; border-left: 4px solid #4CAF50; 
                            padding: 10px; margin: 10px 0; border-radius: 4px; 
                            background-color: rgba(76, 175, 80, 0.1);">
                            <div style="background-color: #4CAF50; color: white; border-radius: 50%; 
                                width: 28px; height: 28px; display: flex; align-items: center; 
                                justify-content: center; margin-right: 12px; flex-shrink: 0;">
                                <strong>✓</strong>
                            </div>
                            <div>
                                <strong>{i}. {issue_text}</strong>
                            </div>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
    
    def _render_missed_issues(self, review_analysis: Dict[str, Any]):
        """Render missed issues section with enhanced styling and tips"""
        missed_problems = review_analysis.get("missed_problems", [])
        
        if not missed_problems:
            st.success(t("all_issues_found"))
            return
            
        st.subheader(f"{t('issues_missed')} ({len(missed_problems)})")
        
        # Group issues by category similar to identified issues
        categorized_issues = {}
        
        for issue in missed_problems:
            # Extract category similar to identified issues method
            category = None
            if isinstance(issue, dict) and "category" in issue:
                category = issue.get("category")
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
            with st.expander(f"{category} ({len(issues)})", expanded=True):
                for i, issue in enumerate(issues, 1):
                    issue_text = issue
                    hint = None
                    
                    if isinstance(issue, dict):
                        issue_text = issue.get("problem", str(issue))
                        hint = issue.get("hint")
                    
                    # Add issue with hint if available
                    hint_html = ""
                    if hint:
                        hint_html = f"""
                        <div style="margin-top: 5px; font-style: italic; color: #666;">
                            <strong>Tip:</strong> {hint}
                        </div>
                        """
                    
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: flex-start; border-left: 4px solid #dc3545; 
                            padding: 10px; margin: 10px 0; border-radius: 4px;
                            background-color: rgba(220, 53, 69, 0.1);">
                            <div style="background-color: #dc3545; color: white; border-radius: 50%; 
                                width: 28px; height: 28px; display: flex; align-items: center; 
                                justify-content: center; margin-right: 12px; margin-top: 2px; flex-shrink: 0;">
                                <strong>✗</strong>
                            </div>
                            <div>
                                <strong>{i}. {issue_text}</strong>
                                {hint_html}
                            </div>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
    
    