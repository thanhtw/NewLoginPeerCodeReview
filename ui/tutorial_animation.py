# Create a new file: ui/tutorial_animation.py

import streamlit as st
import time
from typing import Callable, Dict, Any
from utils.language_utils import t, get_current_language

class CodeReviewTutorial:
    """
    Interactive tutorial that demonstrates the code review process with
    examples of poor and good quality reviews.
    """
    
    def __init__(self):
        """Initialize the tutorial component."""
        # Check if tutorial has been completed
        if "tutorial_completed" not in st.session_state:
            st.session_state.tutorial_completed = False
        
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

        # self.good_review = f"""• {t('line1ImportError')}
        # - {t('line10LoopError')}
        # - {t('line12StringError')}
        # - {t('line9NullError')}
        # - {t('line6ValidationError')}
        # - {t('line17RemoveError')}"""

    
    def render(self, on_complete: Callable = None):
        """
        Render the interactive tutorial.
        
        Args:
            on_complete: Callback function to run when tutorial is completed
        """
        if st.session_state.tutorial_completed:
            # Skip if already completed
            if on_complete:
                on_complete()
            return
            
        st.markdown(f"<h2 style='text-align: center;'>{t('Java Code Review Tutorial')}</h2>", unsafe_allow_html=True)
        
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
            st.code(self.sample_code, language="java")
            
            st.markdown(t("This code contains several issues that need to be identified."))
            
            if st.button(t("Next"), key="code_next"):
                st.session_state.tutorial_step = 2
                st.rerun()
                
        # Step 3: Show poor quality review
        elif tutorial_step == 2:
            st.info(t("First, let's see an example of a POOR quality review:"))
            
            st.markdown(f"""
            <div style="border: 1px solid red; border-radius: 5px; padding: 15px; background-color: rgba(255, 0, 0, 0.05)">
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
            <div style="border: 1px solid green; border-radius: 5px; padding: 15px; background-color: rgba(0, 255, 0, 0.05)">
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
                
        # Step 5: Interactive practice
        elif tutorial_step == 4:
            st.info(t("Now it's your turn! Try writing a review for one of the errors in the code:"))
            
            # Show the code again
            st.code(self.sample_code, language="java")
            
            # Pick a random error to focus on
            import random
            random_error_index = random.randint(0, len(self.known_errors) - 1)
            focus_error = self.known_errors[random_error_index]
            
            st.markdown(f"**{t('Focus on this error')}:** {focus_error}")
            
            user_review = st.text_area(t("Write your review comment for this error:"), height=100)
            
            if st.button(t("Submit"), key="practice_submit"):
                if len(user_review) < 10:
                    st.warning(t("Please write a more detailed review"))
                else:
                    st.success(t("Great job! Your review looks good."))
                    st.session_state.tutorial_step = 5
                    st.rerun()
                    
        # Step 6: Complete
        elif tutorial_step == 5:
            st.success(t("Congratulations! You've completed the tutorial."))
            st.markdown(t("Remember these key principles for good code reviews:"))
            st.markdown("1. " + t("Be specific about line numbers and issues"))
            st.markdown("2. " + t("Explain what's wrong and why"))
            st.markdown("3. " + t("Provide constructive suggestions"))
            st.markdown("4. " + t("Be thorough and check different types of errors"))
            
            if st.button(t("Start Coding!"), key="complete_button"):
                st.session_state.tutorial_completed = True
                if on_complete:
                    on_complete()
                st.rerun()
        
        # Update progress
        progress_bar.progress(tutorial_step / 5)