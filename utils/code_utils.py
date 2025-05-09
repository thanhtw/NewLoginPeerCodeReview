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
from utils.language_utils import get_llm_instructions, get_current_language

# Import prompt templates
from prompts import get_prompt_template

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
        error_type = error.get("type", "unknown").upper()
        name = error.get("name", "unknown")
        description = error.get("description", "")
        implementation_guide = error.get("implementation_guide", "")
        
        error_entry = f"{i}. {error_type} - {name}: {description}"
        if implementation_guide:
            error_entry += f"\nImplementation: {implementation_guide}"
        
        error_list.append(error_entry)
    
    # Join errors with clear separation
    error_instructions = "\n\n".join(error_list)
    
    # Get language-specific difficulty instructions template
    if difficulty_level.lower() == "easy":
        difficulty_instructions = get_prompt_template("beginner_instructions")
    elif difficulty_level.lower() == "medium":
        difficulty_instructions = get_prompt_template("intermediate_instructions")
    else:  # hard
        difficulty_instructions = get_prompt_template("advanced_instructions")
    
    domain_str = domain or "general"
    
    # Get language-specific instructions
    language_instructions = get_llm_instructions()
    
    # Get language-specific template
    template = get_prompt_template("code_generation_template")
    
    # Create the prompt by filling in the template safely
    prompt = f"{language_instructions}. " + format_template_safely(
        template,
        code_length=code_length,
        domain_str=domain_str,
        error_count=len(selected_errors),
        complexity=complexity,
        difficulty_instructions=difficulty_instructions,
        error_instructions=error_instructions,
        difficulty_level=difficulty_level
    )

    return prompt

def format_template_safely(template: str, **kwargs) -> str:
    """
    Format a template string safely, handling potential formatting errors.
    
    Args:
        template: Template string with {placeholders}
        **kwargs: Key-value pairs to substitute into the template
        
    Returns:
        Formatted string
    """
    try:
        # First attempt: use standard string formatting
        return template.format(**kwargs)
    except KeyError as e:
        # If we get a KeyError, log it and try a fallback approach
        logger.warning(f"Template formatting error: missing key {e}")
        # Replace problematic placeholders with their string values
        for key, value in kwargs.items():
            placeholder = "{" + key + "}"
            template = template.replace(placeholder, str(value))
        return template
    except Exception as e:
        # For any other error, log and return a basic formatted string
        logger.error(f"Template formatting error: {str(e)}")
        # Create a basic output with the key information
        return (f"Code evaluation for {kwargs.get('error_count', '?')} errors:\n\n"
                f"Code to evaluate:\n{kwargs.get('code', '')}\n\n"
                f"Errors to find:\n{kwargs.get('error_instructions', '')}")

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
        error_type = error.get("type", "").upper()
        
        # Handle language variations for field names
        name = None
        if "name" in error:
            name = error.get("name", "")
        elif "error_name" in error:
            name = error.get("error_name", "")
        elif "錯誤名稱" in error:  # Traditional Chinese field name
            name = error.get("錯誤名稱", "")
            
        # Get description with language variations
        description = ""
        if "description" in error:
            description = error.get("description", "")
        elif "描述" in error:  # Traditional Chinese field name
            description = error.get("描述", "")
        
        # If we still don't have a name, use a fallback
        if not name:
            name = "Unknown Error"
            
        error_list.append(f"{i}. {error_type} - {name}: {description}")
    
    error_instructions = "\n".join(error_list)

    # Get language-specific instructions
    language_instructions = get_llm_instructions()

    # Get language-specific template
    template = get_prompt_template("evaluation_template")
    
    # Create the prompt by filling in the template safely
    prompt = f"{language_instructions}. " + format_template_safely(
        template,
        code=code,
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
    language_instructions = get_llm_instructions()
    
    # Get language-specific template
    template = get_prompt_template("regeneration_template")

    # Create the prompt by filling in the template safely
    prompt = f"{language_instructions}. " + format_template_safely(
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

    # Get language-specific instructions
    language_instructions = get_llm_instructions()

    # Get language-specific template
    template = get_prompt_template("review_analysis_template")
   
    # Create the prompt by filling in the template safely
    prompt = f"{language_instructions}. " + format_template_safely(
        template,
        code=code,
        problem_count=problem_count,
        problems_text=problems_text,
        student_review=student_review
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
    # Extract data from review analysis
    identified = review_analysis.get("identified_count", 0)
    total = review_analysis.get("total_problems", len(known_problems))
    accuracy = review_analysis.get("identified_percentage", 0)
    iteration = review_analysis.get("iteration_count", 1)
    max_iterations = review_analysis.get("max_iterations", 3)
    remaining = review_analysis.get("remaining_attempts", max_iterations - iteration)
    
    # Format identified problems
    identified_problems = review_analysis.get("identified_problems", [])
    identified_text = ""
    for problem in identified_problems:
        if isinstance(problem, dict):
            problem_text = problem.get("problem", "")
            identified_text += f"- {problem_text}\n"
        else:
            identified_text += f"- {problem}\n"
    
    # Format missed problems
    missed_problems = review_analysis.get("missed_problems", [])
    missed_text = ""
    for problem in missed_problems:
        if isinstance(problem, dict):
            problem_text = problem.get("problem", "")
            missed_text += f"- {problem_text}\n"
        else:
            missed_text += f"- {problem}\n"

    # Get language-specific instructions
    language_instructions = get_llm_instructions()

    # Get language-specific template
    template = get_prompt_template("feedback_template")

    # Create the prompt by filling in the template safely
    prompt = f"{language_instructions}. " + format_template_safely(
        template,
        iteration=iteration,
        max_iterations=max_iterations,
        identified=identified,
        total=total,
        accuracy=accuracy,
        remaining=remaining,
        identified_text=identified_text or "None",
        missed_text=missed_text or "None - great job!"
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
    # Extract performance metrics from latest review
    identified_problems = review_analysis.get("identified_problems", [])
    missed_problems = review_analysis.get("missed_problems", [])
    false_positives = review_analysis.get("false_positives", [])
    
    # Get total problems count
    total_problems = (review_analysis.get("total_problems", 0) or 
                       review_analysis.get("original_error_count", 0) or 
                       len(evaluation_errors))
    
    # Calculate metrics
    identified_count = len(identified_problems)
    accuracy = (identified_count / total_problems * 100) if total_problems > 0 else 0
    
    # Format the problems for the prompt
    identified_str = []
    for problem in identified_problems:
        if isinstance(problem, dict) and "problem" in problem:
            identified_str.append(problem["problem"])
        elif isinstance(problem, str):
            identified_str.append(problem)
    
    missed_str = []
    for problem in missed_problems:
        if isinstance(problem, dict) and "problem" in problem:
            missed_str.append(problem["problem"])
        elif isinstance(problem, str):
            missed_str.append(problem)
    
    false_str = []
    for problem in false_positives:
        if isinstance(problem, dict) and "student_comment" in problem:
            false_str.append(problem["student_comment"])
        elif isinstance(problem, str):
            false_str.append(problem)
    
    # Format identified problems for the prompt
    identified_text = "\n".join(f"- {p}" for p in identified_str)
    missed_text = "\n".join(f"- {p}" for p in missed_str)
    false_positive_text = "\n".join(f"- {p}" for p in false_str)
    
    # Create progress tracking info if multiple attempts exist
    progress_info = ""
    if review_history and len(review_history) > 1:
        progress_info = "## Progress Across Attempts\n\n"
        
        for i, review in enumerate(review_history, 1):
            analysis = review.get("review_analysis", {})
            found = analysis.get("identified_count", 0)
            acc = analysis.get("identified_percentage", 0)
            progress_info += f"Attempt {i}: Found {found}/{total_problems} issues ({acc:.1f}%)\n"
        
        # Compare first vs. latest attempt
        first = review_history[0].get("review_analysis", {})
        first_found = first.get("identified_count", 0)
        first_acc = first.get("identified_percentage", 0)
        
        if accuracy > first_acc:
            improvement = accuracy - first_acc
            progress_info += f"\nImprovement: +{improvement:.1f}% from first attempt\n"

    # Get language-specific instructions
    language_instructions = get_llm_instructions()

    # Get language-specific template
    template = get_prompt_template("comparison_report_template")
    
    # Create the prompt by filling in the template safely
    prompt = f"{language_instructions}. " + format_template_safely(
        template,
        total_problems=total_problems,
        identified_count=identified_count,
        accuracy=accuracy,
        len_missed_str=len(missed_str),
        len_false_str=len(false_str),
        identified_text=identified_text or "None - the student didn't identify any correct issues.",
        missed_text=missed_text or "None - the student identified all issues correctly!",
        false_positive_text=false_positive_text or "None - the student didn't identify any false issues.",
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
        # Remove lines with error comments
        clean_lines = []
        for line in annotated_code.splitlines():
            if "// ERROR:" not in line:
                clean_lines.append(line)
        clean_code = "\n".join(clean_lines)
    
    # Log detailed information if extraction failed
    if not annotated_code:
        logger.warning(f"Failed to extract annotated code from response text: {response_text[:200]}...")
    if not clean_code:
        logger.warning(f"Failed to extract clean code from response text: {response_text[:200]}...")
    
    return annotated_code, clean_code

def generate_comparison_report(evaluation_errors: List[str], review_analysis: Dict[str, Any], 
                              review_history: List[Dict[str, Any]] = None, llm = None) -> str:
    """
    Generate a comparison report showing progress across review attempts.
    Uses an LLM when available, with fallback to static generation.
    
    Args:
        evaluation_errors: List of errors found by the evaluation
        review_analysis: Analysis of the latest student review
        review_history: History of all review attempts
        llm: Optional language model to generate the report
        
    Returns:
        Formatted comparison report
    """
    # If LLM is provided, use it to generate the report
    if llm:
        try:
            # Create the prompt for the LLM
            prompt = create_comparison_report_prompt(evaluation_errors, review_analysis, review_history)
            
            # Generate the report with the LLM
            response = llm.invoke(prompt)
            
            # Process the response
            if hasattr(response, 'content'):
                report = response.content
            elif isinstance(response, dict) and 'content' in response:
                report = response['content']
            else:
                report = str(response)
            
            # Clean up the report
            report = report.replace('\\n', '\n')
            
            return report
        except Exception as e:
            # Log the error
            logger.error(f"Error generating comparison report with LLM: {str(e)}")
            # Fall back to static generation
            return generate_comparison_report_fallback(evaluation_errors, review_analysis, review_history)
    else:
        # If no LLM is provided, use static generation
        return generate_comparison_report_fallback(evaluation_errors, review_analysis, review_history)

def generate_comparison_report_fallback(evaluation_errors: List[str], review_analysis: Dict[str, Any], 
                              review_history: List[Dict[str, Any]] = None) -> str:
    """
    Generate a static comparison report showing progress across review attempts.
    Used as a fallback when LLM generation is not available.
    
    Args:
        evaluation_errors: List of errors found by the evaluation
        review_analysis: Analysis of the latest student review
        review_history: History of all review attempts
        
    Returns:
        Formatted comparison report
    """
    # Extract performance metrics from latest review
    identified_problems = review_analysis.get("identified_problems", [])
    missed_problems = review_analysis.get("missed_problems", [])
    false_positives = review_analysis.get("false_positives", [])
    
    # Get total problems count
    total_problems = (review_analysis.get("total_problems", 0) or 
                     review_analysis.get("original_error_count", 0) or 
                     len(evaluation_errors))
    
    # Calculate metrics
    identified_count = len(identified_problems)
    accuracy = (identified_count / total_problems * 100) if total_problems > 0 else 0
    
    # Convert all problems to strings
    identified_str = [str(p) if not isinstance(p, str) else p for p in identified_problems]
    missed_str = [str(p) if not isinstance(p, str) else p for p in missed_problems]
    false_str = [str(p) if not isinstance(p, str) else p for p in false_positives]
    
    # Build report with markdown
    report = "# Code Review Assessment\n\n"
    
    # Add progress tracking if multiple attempts exist
    if review_history and len(review_history) > 1:
        report += "## Progress Across Attempts\n\n"
        report += "| Attempt | Issues Found | Accuracy |\n"
        report += "|---------|--------------|----------|\n"
        
        for i, review in enumerate(review_history, 1):
            analysis = review.get("review_analysis", {})
            found = analysis.get("identified_count", 0)
            acc = analysis.get("identified_percentage", 0)
            report += f"| {i} | {found}/{total_problems} | {acc:.1f}% |\n"
        
        # Compare first vs. latest attempt
        first = review_history[0].get("review_analysis", {})
        first_found = first.get("identified_count", 0)
        first_acc = first.get("identified_percentage", 0)
        
        if accuracy > first_acc:
            improvement = accuracy - first_acc
            report += f"\n📈 **Improvement**: +{improvement:.1f}% from first attempt\n\n"
    
    # Performance summary
    report += f"## Final Review Performance\n\n"
    report += f"**Score:** {identified_count}/{total_problems} issues identified ({accuracy:.1f}%)\n\n"
    
    # Issues identified in latest attempt
    if identified_str:
        report += "## Issues Correctly Identified\n\n"
        for i, problem in enumerate(identified_str, 1):
            report += f"✅ **{i}.** {problem}\n\n"
    
    # Issues missed in latest attempt
    if missed_str:
        report += "## Issues Missed\n\n"
        for i, problem in enumerate(missed_str, 1):
            report += f"❌ **{i}.** {problem}\n\n"
            
            # Add specific guidance for missed issues
            problem_lower = problem.lower()
            if "null" in problem_lower:
                report += "*Tip: Check for null pointer handling before method calls*\n\n"
            elif "name" in problem_lower or "convention" in problem_lower:
                report += "*Tip: Verify variable/class naming conventions (camelCase, PascalCase)*\n\n"
            elif "equals" in problem_lower or "==" in problem_lower:
                report += "*Tip: Look for object equality issues (.equals() vs ==)*\n\n"
    
    # False positives
    if false_str:
        report += "## False Positives\n\n"
        for i, problem in enumerate(false_str, 1):
            report += f"⚠️ **{i}.** {problem}\n\n"
    
    # New knowledge gained (if multiple attempts)
    if review_history and len(review_history) > 1:
        # Get identified issues from first attempt
        first_review = review_history[0].get("review_analysis", {})
        first_identified = first_review.get("identified_problems", [])
        first_identified_str = [str(p) if not isinstance(p, str) else p for p in first_identified]
        
        # Find newly identified issues in the latest attempt
        new_findings = [p for p in identified_str if p not in first_identified_str]
        
        if new_findings:
            report += "## New Issues Found\n\n"
            report += "*Issues you identified in your latest attempt that you missed initially:*\n\n"
            for i, problem in enumerate(new_findings, 1):
                report += f"🔍 **{i}.** {problem}\n\n"
    
    # Quick tip
    report += "\n**Tip for next time:** Use format `Line X: [Error Type] - Description` in your reviews.\n"
    
    return report

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
    Replaces the fixed get_error_count_for_difficulty function.
    
    Args:
        state: State object that might contain error count info
        difficulty_level: Fallback difficulty level if state doesn't have count
        
    Returns:
        Number of errors to use
    """
    # First try to get error count from selected_specific_errors if available
    if hasattr(state, 'selected_specific_errors') and state.selected_specific_errors:
        return len(state.selected_specific_errors)
    
    # Next try to get from original_error_count if it's been set
    if hasattr(state, 'original_error_count') and state.original_error_count > 0:
        return state.original_error_count
    
    # If we have selected error categories, use their count
    if hasattr(state, 'selected_error_categories'):
        selected_categories = state.selected_error_categories
        if selected_categories:
            java_errors = selected_categories.get("java_errors", [])
            # Use at least one error per selected category
            category_count = len(java_errors)
            if category_count > 0:
                return max(category_count, 2)  # Ensure at least 2 errors
    
    # Finally fall back to difficulty-based default if all else fails
    difficulty_map = {
        "easy": 2,
        "medium": 4,
        "hard": 6
    }
    return difficulty_map.get(str(difficulty_level).lower(), 4)