"""
Generate Tab UI module for Java Peer Review Training System.

This module provides the functions for rendering the code generation tab
and handling the code generation process.
"""

import streamlit as st
import logging
from typing import Dict, List, Any, Optional, Callable
from data.json_error_repository import JsonErrorRepository
from utils.language_utils import t

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_code_problem(workflow, 
                        params: Dict[str, str], 
                        error_selection_mode: str,
                        selected_error_categories: Dict[str, List[str]],
                        selected_specific_errors: List[Dict[str, Any]] = None):
    """Generate a code problem with progress indicator and evaluation visualization."""
    try:
        # Initialize workflow steps
        if 'workflow_steps' not in st.session_state:
            st.session_state.workflow_steps = []
        
        # Reset and start tracking steps
        st.session_state.workflow_steps = [t("step1")]
        
        # Initialize state and parameters
        state = st.session_state.workflow_state
        code_length = str(params.get("code_length", "medium"))
        difficulty_level = str(params.get("difficulty_level", "medium"))
        state.code_length = code_length
        state.difficulty_level = difficulty_level
        
        # Verify we have error selections based on mode
        has_selections = False
        if error_selection_mode == "specific" and selected_specific_errors:
            has_selections = len(selected_specific_errors) > 0
            # Update state with specific errors
            state.selected_specific_errors = selected_specific_errors
            # Clear categories for this mode
            state.selected_error_categories = {"java_errors": []}
        elif error_selection_mode in ["standard", "advanced"]:
            java_errors_selected = selected_error_categories.get("java_errors", [])
            has_selections = len(java_errors_selected) > 0
            # Update state with selected categories
            state.selected_error_categories = selected_error_categories
            # Clear specific errors in this mode
            state.selected_specific_errors = []
        
        if not has_selections:
            st.error(t("no_categories"))
            return False
        
        # First stage: Generate initial code
        with st.status(t("step1"), expanded=True) as status:           
            state.current_step = "generate"
            state.evaluation_attempts = 0
            updated_state = workflow.generate_code_node(state)
            st.session_state.workflow_steps.append(t("step1"))
            
            # Important: Update the session state immediately after code generation
            st.session_state.workflow_state = updated_state
            
            if updated_state.error:
                st.error(f"Error: {updated_state.error}")
                return False
        
        # Second stage: Display the evaluation process
        st.info(t("step2"))
        
        # Create a process visualization using columns and containers instead of expanders
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader(t("code_generation_process"))
            
            # Create a progress container
            progress_container = st.container()
            with progress_container:
                # Create a progress bar
                progress_bar = st.progress(0.25)
                st.write(f"**{t('step1')}** {t('generating_code')}")
                
                # Evaluate the code
                with st.status(t("step2"), expanded=False):
                    updated_state.current_step = "evaluate"
                    updated_state = workflow.evaluate_code_node(updated_state)
                    # Update session state after each step
                    st.session_state.workflow_state = updated_state
                    st.session_state.workflow_steps.append(t("step2"))
                
                progress_bar.progress(0.5)
                st.write(f"**{t('step2')}** {t('completed')}")
                
                # Show evaluation results
                if hasattr(updated_state, 'evaluation_result') and updated_state.evaluation_result:
                    found = len(updated_state.evaluation_result.get("found_errors", []))
                    missing = len(updated_state.evaluation_result.get("missing_errors", []))
                    total = found + missing
                    if total == 0:
                        total = 1  # Avoid division by zero
                    
                    quality_percentage = (found / total * 100)
                    st.write(f"**{t('quality')}:** {quality_percentage:.1f}%: {found}/{total} {t('errors_found')}")
                    
                    # Regeneration cycle if needed
                    if missing > 0 and workflow.should_regenerate_or_review(updated_state) == "regenerate_code":
                        st.write(f"**{t('step3')}** {t('improving_code')}")
                        
                        attempt = 1
                        max_attempts = getattr(updated_state, 'max_evaluation_attempts', 3)
                        previous_found = found
                        
                        # Loop through regeneration attempts
                        while (attempt < max_attempts and 
                              workflow.should_regenerate_or_review(updated_state) == "regenerate_code"):
                            progress_value = 0.5 + (0.5 * (attempt / max_attempts))
                            progress_bar.progress(progress_value)
                            
                            # Regenerate code
                            with st.status(f"{t('step3')} ({attempt+1}/{max_attempts})...", expanded=False):
                                updated_state.current_step = "regenerate"
                                updated_state = workflow.regenerate_code_node(updated_state)
                                # Update session state after code regeneration
                                st.session_state.workflow_state = updated_state
                                st.session_state.workflow_steps.append(f"{t('step3')} ({attempt+1})")
                            
                            # Re-evaluate code
                            with st.status(t("reevaluating_code"), expanded=False):
                                updated_state.current_step = "evaluate"
                                updated_state = workflow.evaluate_code_node(updated_state)
                                # Update session state after evaluation
                                st.session_state.workflow_state = updated_state
                                st.session_state.workflow_steps.append(t("reevaluating_code"))
                            
                            # Show updated results
                            if hasattr(updated_state, 'evaluation_result'):
                                new_found = len(updated_state.evaluation_result.get("found_errors", []))
                                new_missing = len(updated_state.evaluation_result.get("missing_errors", []))
                                
                                st.write(f"**{t('quality')} {attempt+1}:** {new_found/total*100:.1f}%: {new_found}/{total} {t('errors_found')}")
                                
                                if new_found > previous_found:
                                    st.success(f"✅ {t('added')} {new_found - previous_found} {t('new_errors')}")
                                    
                                previous_found = new_found
                            
                            # Increment the attempt counter
                            attempt += 1
                            updated_state.evaluation_attempts = attempt
                            # Make sure to update session state with the new attempt count
                            st.session_state.workflow_state = updated_state
                    
                    # Complete the progress
                    progress_bar.progress(1.0)
                    
                    # Show final outcome
                    if quality_percentage == 100:
                        st.success(f"✅ {t('all_errors_implemented')}")
                    elif quality_percentage >= 80:
                        st.success(f"✅ {t('good_quality')} {quality_percentage:.1f}%")
                    else:
                        st.warning(f"⚠️ {t('partial_quality')} {quality_percentage:.1f}%")
                
        with col2:
            # Show statistics in the sidebar
            st.subheader(t("generation_stats"))
            
            if hasattr(updated_state, 'evaluation_result') and updated_state.evaluation_result:
                found = len(updated_state.evaluation_result.get("found_errors", []))
                missing = len(updated_state.evaluation_result.get("missing_errors", []))
                total = found + missing
                if total > 0:
                    quality_percentage = (found / total * 100)
                    st.metric(t("quality"), f"{quality_percentage:.1f}%")
                
                st.metric(t("errors_found"), f"{found}/{total}")
                
                if hasattr(updated_state, 'evaluation_attempts'):
                    st.metric(t("generation_attempts"), updated_state.evaluation_attempts)
        
        # Update session state with completed process
        updated_state.current_step = "review"
        st.session_state.workflow_state = updated_state
        st.session_state.active_tab = 1  # Move to the review tab
        st.session_state.error = None
        st.session_state.workflow_steps.append(t("code_generation_completed"))
        
        # Display the generated code
        if hasattr(updated_state, 'code_snippet') and updated_state.code_snippet:
            # Show the generated code in this tab for immediate feedback
            st.subheader(t("generated_java_code"))
            
            code_to_display = None
            if hasattr(updated_state.code_snippet, 'clean_code') and updated_state.code_snippet.clean_code:
                code_to_display = updated_state.code_snippet.clean_code
            elif hasattr(updated_state.code_snippet, 'code') and updated_state.code_snippet.code:
                code_to_display = updated_state.code_snippet.code
                
            if code_to_display:
                st.code(code_to_display, language="java")
        
        return True
        
    except Exception as e:
        logger.error(f"Error generating code problem: {str(e)}")
        import traceback
        traceback.print_exc()
        st.error(f"Error generating code problem: {str(e)}")
        return False

def render_generate_tab(workflow, error_selector_ui, code_display_ui, user_level=None):
    """
    Render the problem generation tab with enhanced workflow visualization.
    
    Args:
        workflow: JavaCodeReviewGraph workflow
        error_selector_ui: ErrorSelectorUI instance
        code_display_ui: CodeDisplayUI instance
        user_level: Optional user level from authentication (basic, medium, senior)
    """
    st.subheader(t("generate_problem"))

    force_regenerate = st.session_state.get("force_regeneration", False)

    if force_regenerate:
        st.session_state.force_regeneration = False
        st.info(t("starting_new_session"))
    
    # Initialize workflow steps if not present
    if not hasattr(st.session_state, 'workflow_steps'):
        st.session_state.workflow_steps = []
    
    # If we already have a code snippet, show the workflow process
    if hasattr(st.session_state, 'workflow_state') and hasattr(st.session_state.workflow_state, 'code_snippet') and st.session_state.workflow_state.code_snippet:
        # First display the workflow progress
        show_workflow_process()
        
        # Then display the generated code
        st.subheader(t("generated_java_code"))
        
        # Get known problems from multiple sources to ensure we have data for instructor view
        known_problems = []
        
        # First, try to get problems from evaluation_result['found_errors']
        if (hasattr(st.session_state.workflow_state, 'evaluation_result') and 
            st.session_state.workflow_state.evaluation_result and 
            'found_errors' in st.session_state.workflow_state.evaluation_result):
            found_errors = st.session_state.workflow_state.evaluation_result.get('found_errors', [])
            if found_errors:
                known_problems = found_errors
        
        # If we couldn't get known problems from evaluation, try to get from selected errors
        if not known_problems and hasattr(st.session_state.workflow_state, 'selected_specific_errors'):
            selected_errors = st.session_state.workflow_state.selected_specific_errors
            if selected_errors:
                # Format selected errors to match expected format
                known_problems = [
                    f"{error.get('type', '').upper()} - {error.get('name', '')}" 
                    for error in selected_errors
                ]
        
        # As a last resort, try to extract from raw_errors in code_snippet
        if not known_problems and hasattr(st.session_state.workflow_state.code_snippet, 'raw_errors'):
            raw_errors = st.session_state.workflow_state.code_snippet.raw_errors
            if isinstance(raw_errors, dict):
                for error_type, errors in raw_errors.items():
                    for error in errors:
                        if isinstance(error, dict):
                            error_type_str = error.get('type', error_type).upper()
                            error_name = error.get('name', error.get('error_name', error.get('check_name', 'Unknown')))
                            known_problems.append(f"{error_type_str} - {error_name}")
        
        # Always pass known_problems, the render_code_display function will handle showing
        # the instructor view based on session state and checkbox status
        code_display_ui.render_code_display(
            st.session_state.workflow_state.code_snippet,
            known_problems=known_problems
        )
        
        # Add button to regenerate code
        if st.button(t("generate_new"), type="primary"):
            # Reset the state for new generation
            st.session_state.workflow_state.code_snippet = None
            st.session_state.workflow_state.current_step = "generate"
            st.session_state.workflow_state.evaluation_attempts = 0
            st.session_state.workflow_steps = []
            # Rerun to update UI
            st.rerun()
    else:
        # Add custom CSS for the error category cards
        st.markdown("""
        <style>
        .problem-area-card {
            transition: transform 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
            cursor: pointer;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 16px;
        }
        .problem-area-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.1);
        }
        .problem-area-card.selected {
            background-color: rgba(76, 104, 215, 0.1);
            border-color: #4c68d7;
            box-shadow: 0 4px 8px rgba(76, 104, 215, 0.2);
        }
        .category-selection-container {
            background-color: #f9f9f9;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid #e0e0e0;
        }
        </style>
        """, unsafe_allow_html=True)
       
        selection_mode = error_selector_ui.render_mode_selector()
        
        # Set parameters automatically based on user level (no UI controls)
        params = error_selector_ui.get_code_params_for_level(user_level)
        
        # Show the auto-set parameters as read-only information
        difficulty_level = params["difficulty_level"].capitalize()
        code_length = params["code_length"].capitalize()
        
        # Create a nicer container for parameter display
        st.markdown(f"""
        <div style="background-color: rgba(76, 104, 215, 0.1); border-left: 4px solid #4c68d7; padding: 15px; margin: 15px 0; border-radius: 5px;">
          <strong>{t("code_params")}</strong>
          <div style="display: flex; margin-top: 10px;">
            <div style="flex: 1; padding: 10px; background-color: white; border-radius: 5px; margin-right: 10px; text-align: center;">
              <div style="font-weight: 500; color: #4c68d7;">{t("difficulty")}</div>
              <div style="font-size: 1.2rem; margin-top: 5px;">{difficulty_level}</div>
            </div>
            <div style="flex: 1; padding: 10px; background-color: white; border-radius: 5px; text-align: center;">
              <div style="font-weight: 500; color: #4c68d7;">{t("code_length")}</div>
              <div style="font-size: 1.2rem; margin-top: 5px;">{code_length}</div>
            </div>
          </div>
          <em style="font-size: 0.9rem; margin-top: 10px; display: block;">{t("params_based_on_level")} ({user_level or 'medium'}).</em>
        </div>
        """, unsafe_allow_html=True)
        
        # Display error selection interface based on mode within a container
        st.markdown('<div class="category-selection-container">', unsafe_allow_html=True)
        
        all_categories = workflow.get_all_error_categories()
        
        if selection_mode == "advanced":
            # Advanced mode - select categories
            selected_categories = error_selector_ui.render_category_selection(all_categories)
            specific_errors = []
        else:
            # Specific mode - select specific errors
            specific_errors = error_selector_ui.render_specific_error_selection(workflow.error_repository)
            # Initialize empty categories for this mode
            selected_categories = {"java_errors": []}
            
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Create a visually appealing generate button
        st.markdown("""
        <style>
        .generate-button-container {
            display: flex;
            justify-content: center;
            margin: 30px 0 10px 0;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="generate-button-container">', unsafe_allow_html=True)
        if st.button(t("generate_code_button"), type="primary", use_container_width=True):
            # Reset workflow steps for a fresh generation
            st.session_state.workflow_steps = [f"{t('start_process')}"]
            
            # Store parameters in state for generation
            if hasattr(st.session_state, 'workflow_state'):
                # Set basic parameters
                st.session_state.workflow_state.code_length = params["code_length"]
                st.session_state.workflow_state.difficulty_level = params["difficulty_level"]
                
                # Set selection based on mode
                if selection_mode == "advanced":
                    st.session_state.workflow_state.selected_error_categories = selected_categories
                    st.session_state.workflow_state.selected_specific_errors = []
                else:
                    st.session_state.workflow_state.selected_error_categories = {"java_errors": []}
                    st.session_state.workflow_state.selected_specific_errors = specific_errors
                
                # Initialize generation state
                st.session_state.workflow_state.current_step = "generate"
                st.session_state.workflow_state.evaluation_attempts = 0
                
                try:
                    # Run the full generate-evaluate-regenerate workflow
                    with st.spinner(t("generating_code")):
                        # Step 1: Generate initial code
                        state = workflow.generate_code_node(st.session_state.workflow_state)
                        st.session_state.workflow_steps.append(t("generated_initial_code"))
                        
                        if state.error:
                            st.error(f"Error: {state.error}")
                            return
                        
                        # Step 2: Evaluate code
                        st.session_state.workflow_state = state  # Update state
                        status_placeholder = st.empty()
                        status_placeholder.info(t("evaluating_code"))
                        state = workflow.evaluate_code_node(state)
                        st.session_state.workflow_steps.append(t("evaluated_code"))
                        
                        if state.error:
                            st.error(f"Error: {state.error}")
                            return
                        
                        # Step 3: Regenerate if needed
                        evaluation_attempts = 1
                        max_attempts = state.max_evaluation_attempts
                        
                        # Loop for regeneration attempts
                        while evaluation_attempts < max_attempts and workflow.should_regenerate_or_review(state) == "regenerate_code":
                            # Update steps and status
                            st.session_state.workflow_steps.append(f"{t('regenerating_code')} ({evaluation_attempts})")
                            status_placeholder.warning(f"{t('regenerating_code')} ({evaluation_attempts}/{max_attempts})...")
                            
                            # Regenerate code
                            state.current_step = "regenerate"
                            state = workflow.regenerate_code_node(state)
                            
                            if state.error:
                                st.error(f"Error: {state.error}")
                                return
                                
                            # Re-evaluate code
                            st.session_state.workflow_steps.append(t("reevaluated_code"))
                            status_placeholder.info(t("reevaluating_code"))
                            state = workflow.evaluate_code_node(state)
                            
                            if state.error:
                                st.error(f"Error: {state.error}")
                                return
                                
                            # Increment attempt counter
                            evaluation_attempts += 1
                        
                        # Update state and finalize
                        state.current_step = "review"
                        state.evaluation_attempts = evaluation_attempts
                        st.session_state.workflow_state = state
                        st.session_state.workflow_steps.append(t("code_generation_completed"))
                        
                        # Move to review tab
                        st.session_state.active_tab = 1
                        status_placeholder.success(t("code_generation_complete"))
                        
                        # Force UI refresh
                        st.rerun()
                        
                except Exception as e:
                    logger.error(f"Error in workflow: {str(e)}", exc_info=True)
                    st.session_state.workflow_steps.append(f"Error in code generation: {str(e)}")
                    st.error(f"Error: {str(e)}")
            else:
                # If workflow state doesn't exist yet
                st.error(t("workflow_not_initialized"))
        st.markdown('</div>', unsafe_allow_html=True)

def show_workflow_process():
    """Show a visual representation of the workflow process with improved styling."""
    # Check if we have the necessary state information
    if not hasattr(st.session_state, 'workflow_state'):
        return
    
    state = st.session_state.workflow_state
    
    # Get the current step and evaluation attempts
    current_step = getattr(state, 'current_step', 'generate')
    evaluation_attempts = getattr(state, 'evaluation_attempts', 0)
    max_evaluation_attempts = getattr(state, 'max_evaluation_attempts', 3)
    
    # Create a workflow visualization with improved style
    st.markdown("""
    <style>
    .workflow-container {
        margin: 20px 0;
    }
    .workflow-step {
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        text-align: center;
        font-weight: 500;
        transition: all 0.3s ease;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .workflow-step:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    .step-completed {
        background-color: #28a745;
        color: white;
    }
    .step-active {
        background-color: #4c68d7;
        color: white;
        animation: pulse 2s infinite;
    }
    .step-pending {
        background-color: #6c757d;
        color: white;
    }
    @keyframes pulse {
        0% {
            box-shadow: 0 0 0 0 rgba(76, 104, 215, 0.4);
        }
        70% {
            box-shadow: 0 0 0 10px rgba(76, 104, 215, 0);
        }
        100% {
            box-shadow: 0 0 0 0 rgba(76, 104, 215, 0);
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.subheader(t("code_generation_process"))
    
    st.markdown('<div class="workflow-container">', unsafe_allow_html=True)
    
    # Create columns for the process steps
    cols = st.columns(4)
    
    # Step 1: Generate Code - Always completed if we're showing workflow
    with cols[0]:
        st.markdown(f"<div class='workflow-step step-completed'>{t('step1')}</div>", unsafe_allow_html=True)
    
    # Step 2: Evaluate Code
    with cols[1]:
        evaluate_style = "step-completed" if current_step in ['evaluate', 'regenerate', 'review'] else "step-pending"
        st.markdown(f"<div class='workflow-step {evaluate_style}'>{t('step2')}</div>", unsafe_allow_html=True)
    
    # Step 3: Regenerate
    with cols[2]:
        # Set the text for regeneration step
        if evaluation_attempts > 0:
            regenerate_text = f"{t('step3')} ({evaluation_attempts} {t('attempts')})"
            regenerate_style = "step-completed"
        else:
            regenerate_text = t("step3")
            regenerate_style = "step-pending"
        
        # Set active class if this is the current step
        if current_step == 'regenerate':
            regenerate_style = "step-active"
            
        st.markdown(f"<div class='workflow-step {regenerate_style}'>{regenerate_text}</div>", unsafe_allow_html=True)
    
    # Step 4: Ready for Review
    with cols[3]:
        review_style = "step-active" if current_step == 'review' else "step-pending"
        st.markdown(f"<div class='workflow-step {review_style}'>{t('step4')}</div>", unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Show process details in an expander
    with st.expander(t("process_details"), expanded=False):
        if hasattr(st.session_state, 'workflow_steps') and st.session_state.workflow_steps:
            for i, step in enumerate(st.session_state.workflow_steps, 1):
                st.markdown(f"{i}. {step}")
        else:
            st.write(t("no_process_details"))

    # If we have evaluation results, show a summary card
    if (hasattr(state, 'evaluation_result') and state.evaluation_result and 
        'found_errors' in state.evaluation_result):
        
        found = len(state.evaluation_result.get("found_errors", []))
        missing = len(state.evaluation_result.get("missing_errors", []))
        total = found + missing
        if total > 0:
            quality_percentage = (found / total * 100)
            
            # Generate color based on quality percentage
            if quality_percentage >= 80:
                color = "#28a745"  # Green for good quality
                icon = "✅"
            elif quality_percentage >= 60:
                color = "#ffc107"  # Yellow for medium quality
                icon = "⚠️"
            else:
                color = "#dc3545"  # Red for low quality
                icon = "❌"
                
            st.markdown(f"""
            <div style="background-color: rgba({color.replace('#', '')}, 0.1); 
                        border-left: 4px solid {color}; 
                        padding: 15px; margin: 15px 0; border-radius: 5px;">
                <div style="display: flex; align-items: center;">
                    <div style="font-size: 24px; margin-right: 15px;">{icon}</div>
                    <div>
                        <div style="font-weight: 500; font-size: 1.1rem;">{t("code_quality")}: {quality_percentage:.1f}%</div>
                        <div>{t("found")} {found} {t("of")} {total} {t("requested_errors")}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)