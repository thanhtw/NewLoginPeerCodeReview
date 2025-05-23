"""
Utility functions for code generation and processing in the Java Code Review System.

This module provides shared functionality for generating prompts, 
extracting code from responses, and handling error comments.
"""

import re
import random
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from langchain_core.language_models import BaseLanguageModel
from utils.language_utils import t, get_llm_prompt_instructions, get_current_language

# Import prompt templates
from prompts import get_prompt_template, format_prompt_safely

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_line_numbers(code: str) -> str:
    """
    Add line numbers to code snippet.
    
    Args:
        code: The code snippet to add line numbers to
        
    Returns:
        Code with line numbers
    """
    lines = code.splitlines()
    max_line_num = len(lines)
    padding = len(str(max_line_num))
    
    # Create a list of lines with line numbers
    numbered_lines = []
    for i, line in enumerate(lines, 1):
        # Format line number with consistent padding
        line_num = str(i).rjust(padding)
        numbered_lines.append(f"{line_num} | {line}")
    
    return "\n".join(numbered_lines)

def create_code_generation_prompt(code_length: str, difficulty_level: str, selected_errors: list, domain: str = None, include_error_annotations: bool = True) -> str:
    """
    Create a concise prompt for generating Java code with intentional errors.
    Enhanced to emphasize the exact number of errors required and ensure one per error type.
    Now uses language-specific templates based on current language.
    
    Args:
        code_length: Length of code (short, medium, long)
        difficulty_level: Difficulty level (easy, medium, hard)
        selected_errors: List of errors to include in the code
        domain: Domain context for the code
        include_error_annotations: Whether to include error annotations
        
    Returns:
        Optimized prompt string for LLM
    """
    # Define code complexity by length
    complexity = {
        "short": "1 simple class with 1-2 basic methods (15-30 lines total)",
        "medium": "1 class with 3-5 methods of moderate complexity (40-80 lines total)",
        "long": "1-2 classes with 4-8 methods and clear relationships (100-150 lines total)"
    }.get(str(code_length).lower(), "1 class with methods")
    
    # Count the number of errors
    error_count = len(selected_errors)
    
    # Format errors concisely with only essential information
    error_list = []
    for i, error in enumerate(selected_errors, 1):
        error_type = error.get(t("category"), "unknown").upper()
        name = error.get(t("error_name_variable"), "unknown")
        description = error.get(t("description"), "")
        implementation_guide = error.get(t("implementation_guide"), "")
        
        error_entry = f"{i}. {error_type} - {name}: {description}"
        if implementation_guide:
            error_entry += f"\n{t('implementation_guide')}: {implementation_guide}"
        
        error_list.append(error_entry)
    
    # Join errors with clear separation
    error_instructions = "\n\n".join(error_list)
    
    # Get language-specific difficulty instructions template
    if difficulty_level.lower() == t("easy"):
        difficulty_instructions = get_prompt_template("beginner_instructions")
    elif difficulty_level.lower() == t("medium"):
        difficulty_instructions = get_prompt_template("intermediate_instructions")
    else:  # hard
        difficulty_instructions = get_prompt_template("advanced_instructions")
    
    domain_str = domain or "general"
    
    # Get language-specific instructions
    language_instructions = get_llm_prompt_instructions(get_current_language())
    
    # Get language-specific template
    template = get_prompt_template("code_generation_template")
    
    # Create the prompt by filling in the template safely
    prompt = f"{language_instructions}. " + format_prompt_safely(
        template,
        code_length=code_length,
        domain_str=domain_str,
        error_count=error_count,
        complexity=complexity,
        difficulty_instructions=difficulty_instructions,
        error_instructions=error_instructions,
        difficulty_level=difficulty_level
    )

    return prompt

def create_evaluation_prompt(code: str, requested_errors: list) -> str:
    """
    Create a clear and concise prompt for evaluating whether code contains required errors.
    Improved with detailed evaluation criteria and structured output format.
    Now uses language-specific templates based on current language.
    
    Args:
        code: The code to evaluate
        requested_errors: List of errors that should be in the code
        
    Returns:
        Evaluation prompt string
    """
    # Count the exact number of requested errors
    error_count = len(requested_errors)
    
    # Format requested errors clearly with language-aware field access
    error_list = []
    for i, error in enumerate(requested_errors, 1):
        # Get error type and name with fallbacks for different field names
        error_type = error.get(t("category"), "").upper()

        # Handle language variations for field names
        name = None
        if t("error_name_variable") in error:
            name = error.get(t("error_name_variable"), "")
            
        # Get description with language variations
        description = ""
        if t("description") in error:
            description = error.get(t("description"), "")

        implementation_guide = ""
        if t("implementation_guide") in error:
            implementation_guide = error.get(t("implementation_guide"), "")
        
        error_list.append(f"{i}. {error_type} - {name}: {description} ({t('example')}: {implementation_guide})")

    error_instructions = "\n".join(error_list)

    # Get language-specific instructions
    language_instructions = get_llm_prompt_instructions(get_current_language())

    # Get language-specific template
    template = get_prompt_template("evaluation_template")
    
    # Create the prompt by filling in the template safely
    prompt = f"{language_instructions}. " + format_prompt_safely(
        template,
        code=add_line_numbers(code),
        error_count=error_count,
        error_instructions=error_instructions
    )
    
    return prompt

def create_regeneration_prompt(code: str, domain: str, missing_errors: list, found_errors: list, requested_errors: list) -> str:
    """
    Create a focused prompt for regenerating code with missing errors and removing extra errors.
    Enhanced to provide clear instructions for exact error requirements.
    Now uses language-specific templates based on current language.
    
    Args:
        code: The original code
        domain: Domain of the code
        missing_errors: List of errors that need to be added
        found_errors: List of errors that are already in the code
        requested_errors: List of all requested errors
        
    Returns:
        Regeneration prompt string
    """
    # Total requested errors count
    total_requested = len(requested_errors)
    
    # Format missing and found errors
    missing_text = "\n".join(f"- {instr}" for instr in missing_errors) if missing_errors else "No missing errors - all requested errors are already implemented."
    found_text = "\n".join(f"- {err}" for err in found_errors) if found_errors else "No correctly implemented errors found."
    
    # Get language-specific instructions
    language_instructions = get_llm_prompt_instructions(get_current_language())
    
    # Get language-specific template
    template = get_prompt_template("regeneration_template")

    # Create the prompt by filling in the template safely
    prompt = f"{language_instructions}. " + format_prompt_safely(
        template,
        code=code,
        domain=domain,
        missing_text=missing_text,
        found_text=found_text,
        total_requested=total_requested
    )
    
    return prompt

def create_review_analysis_prompt(code: str, known_problems: list, student_review: str) -> str:
    """
    Create an optimized prompt for analyzing student code reviews.
    Enhanced with educational assessment focus and better structured output requirements.
    Now uses language-specific templates based on current language.
    
    Args:
        code: The code being reviewed
        known_problems: List of known problems in the code
        student_review: Student's review text
        
    Returns:
        Review analysis prompt string
    """
    # Count known problems
    problem_count = len(known_problems)
    
    # Format known problems clearly
    problems_text = "\n".join(f"- {problem}" for problem in known_problems)

    # Get threshold values from environment variables
    meaningful_score_threshold = float(os.getenv("MEANINGFUL_SCORE", "0.6"))
    accuracy_score_threshold = float(os.getenv("ACCURACY_SCORE", "0.7"))

    # Get language-specific instructions
    language_instructions = get_llm_prompt_instructions(get_current_language())

    # Get language-specific template
    template = get_prompt_template("review_analysis_template")
   
    # Create the prompt by filling in the template safely
    prompt = f"{language_instructions}. " + format_prompt_safely(
        template,
        code=code,
        problem_count=problem_count,
        problems_text=problems_text,
        student_review=student_review,
        meaningful_score_threshold=meaningful_score_threshold,
        accuracy_score_threshold=accuracy_score_threshold
    )
    
    return prompt

def create_feedback_prompt(code: str, known_problems: list, review_analysis: dict) -> str:
    """
    Create an optimized prompt for generating concise, focused guidance on student reviews.
    Enhanced with clearer educational goals and example output.
    Now uses language-specific templates based on current language.
    
    Args:
        code: The code being reviewed
        known_problems: List of known problems in the code
        review_analysis: Analysis of the student's review
        
    Returns:
        Feedback prompt string
    """
    # Extract data from review analysis using direct access
    identified = review_analysis.get(t("identified_count"), 0)
    total = review_analysis.get(t("total_problems"), len(known_problems))
    accuracy = review_analysis.get(t("identified_percentage"), 0)
    iteration = review_analysis.get(t("iteration_count"), 1)
    max_iterations = review_analysis.get(t("max_iterations"), 3)
    remaining = review_analysis.get(t("remaining_attempts"), max_iterations - iteration)
    
    # Format identified problems with direct access
    identified_problems = review_analysis.get(t("identified_problems"), [])
    identified_text = ""
    for problem in identified_problems:
        if isinstance(problem, dict):
            problem_text = problem.get(t("problem"), "")
            identified_text += f"- {problem_text}\n"
        else:
            identified_text += f"- {problem}\n"
    
    # Format missed problems with direct access
    missed_problems = review_analysis.get(t("missed_problems"), [])
    missed_text = ""
    for problem in missed_problems:
        if isinstance(problem, dict):
            problem_text = problem.get(t("problem"), "")
            missed_text += f"- {problem_text}\n"
        else:
            missed_text += f"- {problem}\n"

    # Get language-specific instructions
    language_instructions = get_llm_prompt_instructions(get_current_language())

    # Get language-specific template
    template = get_prompt_template("feedback_template")

    # Create the prompt by filling in the template safely
    prompt = f"{language_instructions}. " + format_prompt_safely(
        template,
        iteration=iteration,
        max_iterations=max_iterations,
        identified=identified,
        total=total,
        accuracy=accuracy,
        remaining=remaining,
        identified_text=identified_text,
        missed_text=missed_text
    )
    
    return prompt

def create_comparison_report_prompt(evaluation_errors: List[str], review_analysis: Dict[str, Any], review_history: List[Dict[str, Any]] = None) -> str:
    """
    Create a prompt for generating a comparison report with an LLM.
    Now uses language-specific templates based on current language.
    
    Args:
        evaluation_errors: List of errors found by the evaluation
        review_analysis: Analysis of the latest student review
        review_history: History of all review attempts
        
    Returns:
        Comparison report prompt string
    """
    # Extract performance metrics from latest review using direct access
    identified_problems = review_analysis.get(t("identified_problems"), [])
    missed_problems = review_analysis.get(t("missed_problems"), [])

    
    # Get total problems count using direct access
    total_problems = (review_analysis.get(t("total_problems"), 0) or 
                      review_analysis.get(t("original_error_count"), 0) or 
                      len(evaluation_errors))
    
    # Calculate metrics
    identified_count = len(identified_problems)
    accuracy = (identified_count / total_problems * 100) if total_problems > 0 else 0
    
    # Format the problems for the prompt
    identified_str = []
    for problem in identified_problems:
        if isinstance(problem, dict) and t("problem") in problem:
            identified_str.append(problem.get(t("problem"), ""))
        elif isinstance(problem, str):
            identified_str.append(problem)
    
    missed_str = []
    for problem in missed_problems:
        if isinstance(problem, dict) and t("problem") in problem:
            missed_str.append(problem.get(t("problem"), ""))
        elif isinstance(problem, str):
            missed_str.append(problem)
    
    
    # Format identified problems for the prompt
    identified_text = "\n".join(f"- {p}" for p in identified_str)
    missed_text = "\n".join(f"- {p}" for p in missed_str)
    
    # Create progress tracking info if multiple attempts exist
    progress_info = ""

    # Get language-specific instructions
    language_instructions = get_llm_prompt_instructions(get_current_language())

    # Get language-specific template
    template = get_prompt_template("comparison_report_template")
    
    # Create the prompt by filling in the template safely
    prompt = f"{language_instructions}. " + format_prompt_safely(
        template,
        total_problems=total_problems,
        identified_count=identified_count,
        accuracy=accuracy,
        len_missed_str=len(missed_str),
        identified_text=identified_text,
        missed_text=missed_text,
        progress_info=progress_info
    )

    return prompt

def extract_both_code_versions(response) -> Tuple[str, str]:
    """
    Extract both annotated and clean code versions from LLM response.
    Enhanced to better handle Groq response format differences.
    
    Args:
        response: Text response from LLM or AIMessage/ChatMessage object
        
    Returns:
        Tuple of (annotated_code, clean_code)
    """
    # Check for None or empty response
    if not response:
        return "", ""
    
    # Handle AIMessage or similar objects (from LangChain)
    if hasattr(response, 'content'):
        # Extract the content from the message object
        response_text = response.content
    elif isinstance(response, dict) and 'content' in response:
        # Handle dictionary-like response
        response_text = response['content']
    else:
        # Assume it's already a string
        response_text = str(response)
    
    # Handle Groq-specific response format
    # Groq often wraps content differently, so check for that pattern
    if "content=" in response_text and not response_text.startswith("```"):
        # Extract just the content part
        response_text = response_text.replace("content=", "")
        # Remove any leading/trailing quotes if present
        if (response_text.startswith('"') and response_text.endswith('"')) or \
           (response_text.startswith("'") and response_text.endswith("'")):
            response_text = response_text[1:-1]
    
    # Extract annotated version with java-annotated tag
    annotated_pattern = r'```java-annotated\s*(.*?)\s*```'
    annotated_matches = re.findall(annotated_pattern, response_text, re.DOTALL)
    annotated_code = annotated_matches[0] if annotated_matches else ""
    
    # Extract clean version with java-clean tag
    clean_pattern = r'```java-clean\s*(.*?)\s*```'
    clean_matches = re.findall(clean_pattern, response_text, re.DOTALL)
    clean_code = clean_matches[0] if clean_matches else ""
    
    # Fallbacks if specific tags aren't found
    if not annotated_code:
        # Try to find any java code block for annotated version
        java_pattern = r'```java\s*(.*?)\s*```'
        java_matches = re.findall(java_pattern, response_text, re.DOTALL)
        if java_matches:
            annotated_code = java_matches[0]
        else:
            # Last resort: look for any code block
            any_code_pattern = r'```\s*(.*?)\s*```'
            any_matches = re.findall(any_code_pattern, response_text, re.DOTALL)
            if any_matches:
                # Use the largest code block
                annotated_code = max(any_matches, key=len)
    
    # For Groq responses: If we found annotated but no clean code, create clean code by removing error comments
    if annotated_code and not clean_code:
        # Process line by line to remove only the error comments, not the entire line
        clean_lines = []
        for line in annotated_code.splitlines():
            if "// ERROR:" in line:
                # Remove only the error comment part, keep the code
                error_comment_index = line.find("// ERROR:")
                # Only take the part before the error comment
                cleaned_line = line[:error_comment_index].rstrip()
                # Only add non-empty lines
                if cleaned_line:
                    clean_lines.append(cleaned_line)
            else:
                # Line doesn't have an error comment, keep it as is
                clean_lines.append(line)
        clean_code = "\n".join(clean_lines)
    
    # Log detailed information if extraction failed
    if not annotated_code:
        logger.warning(f"Failed to extract annotated code from response text: {response_text[:200]}...")
    if not clean_code:
        logger.warning(f"Failed to extract clean code from response text: {response_text[:200]}...")
    
    return annotated_code, clean_code

def process_llm_response(response):
    """
    Process LLM response to handle different formats from different providers
    with improved error handling and type safety.
    
    Args:
        response: Response from LLM (string, AIMessage, or dict)
        
    Returns:
        Cleaned string content
    """
    # Handle None case
    if response is None:
        return ""
    
    try:
        # Extract content based on response type
        if hasattr(response, 'content'):
            # AIMessage or similar object from LangChain
            content = response.content
        elif isinstance(response, dict) and 'content' in response:
            # Dictionary with content key
            content = response['content']
        else:
            # Assume it's already a string
            content = str(response)
        
        # Fix common formatting issues:
        
        # 1. Remove any 'content=' prefix if present (common in Groq debug output)
        if content.startswith('content='):
            content = content.replace('content=', '', 1)
        
        # 2. Fix escaped newlines and quotes
        content = content.replace('\\n', '\n')
        content = content.replace('\\"', '"')
        content = content.replace('\\\'', '\'')
        
        # 3. Remove any surrounding quotes that might have been added
        if (content.startswith('"') and content.endswith('"')) or \
           (content.startswith("'") and content.endswith("'")):
            content = content[1:-1]
        
        # 4. Fix markdown formatting issues
        content = re.sub(r'\*\*(.+?)\*\*', r'**\1**', content)  # Fix bold formatting
        
        # 5. Clean up any raw escape sequences for newlines
        content = re.sub(r'(?<!\\)\\n', '\n', content)
        content = re.sub(r'\\\\n', '\\n', content)  # Preserve intentional \n in code
        
        # 6. Fix any metadata that might have leaked into the content
        content = re.sub(r'response_metadata=\{.*\}', '', content)
        content = re.sub(r'additional_kwargs=\{.*\}', '', content)
        
        return content
    except Exception as e:
        logger.error(f"Error processing LLM response: {str(e)}")
        # Return a safe default
        if response is not None:
            try:
                return str(response)
            except:
                pass
        return ""

def get_error_count_from_state(state: Any, difficulty_level: str = "medium") -> int:
    """
    Get error count from the state object or parameters.
    Uses direct attribute access.
    
    Args:
        state: State object that might contain error count info
        difficulty_level: Fallback difficulty level if state doesn't have count
        
    Returns:
        Number of errors to use
    """
    # First try to get error count from selected_specific_errors if available
    specific_errors = getattr(state, 'selected_specific_errors', None)
    if specific_errors:
        return len(specific_errors)
    
    # Next try to get from original_error_count if it's been set
    original_error_count = getattr(state, 'original_error_count', 0)
    if original_error_count > 0:
        return original_error_count
    
    # If we have selected error categories, use their count
    selected_categories = getattr(state, 'selected_error_categories', None)
    if selected_categories:
        java_errors = selected_categories.get("java_errors", [])
        category_count = len(java_errors)
        if category_count > 0:
            return max(category_count, 2)
    
    # Finally fall back to difficulty-based default if all else fails
    difficulty_map = {
        t("easy"): 2,
        t("medium"): 4,
        t("hard"): 6
    }
    return difficulty_map.get(str(difficulty_level).lower(), 4)