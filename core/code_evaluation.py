"""
Unified Code Evaluation Agent for Java Peer Review Training System.

This module provides the CodeEvaluationAgent class which evaluates 
generated Java code to ensure it contains the required errors.
Incorporates enhanced evaluation methods for more accurate analysis.
"""

import re
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from langchain_core.language_models import BaseLanguageModel

from utils.llm_logger import LLMInteractionLogger
from utils.code_utils import create_evaluation_prompt, create_regeneration_prompt, process_llm_response
from utils.language_utils import t

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CodeEvaluationAgent:
    """
    Agent for evaluating generated Java code to ensure it meets error requirements.
    
    This agent provides detailed feedback on how well the generated code
    implements the required errors, and suggests improvements for the
    code generator. Can use an LLM for more accurate evaluation.
    """
    
    def __init__(self, llm: BaseLanguageModel = None, llm_logger = None):
        """
        Initialize the CodeEvaluationAgent.
        
        Args:
            llm: Language model for evaluation
            llm_logger: Logger for tracking LLM interactions
        """
        self.llm = llm
        self.llm_logger = llm_logger
    
    def evaluate_code(self, code: str, requested_errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate Java code to check for requested errors.
        
        Args:
            code: The Java code to evaluate
            requested_errors: List of errors that should be included in the code
            
        Returns:
            Evaluation results with found and missing errors
        """
        
        if not self.llm:
            logger.warning("No LLM available for code evaluation, using fallback evaluation")
            return "// Error: No LLM available for code generation"

        # Create evaluation prompt
        prompt = create_evaluation_prompt(code, requested_errors)
        
        try:
            # Generate the evaluation using the LLM
            logger.debug(t("sending_code_to_llm_for_evaluation"))
            response = self.llm.invoke(prompt)
            # Process response to ensure it's properly formatted
            processed_response = process_llm_response(response)
            
            # Log the evaluation
            if self.llm_logger:
                metadata = {
                    t("code_length"): len(code.splitlines()),
                    t("requested_errors_count"): len(requested_errors)
                }
                self.llm_logger.log_code_evaluation(prompt, processed_response, metadata)
            
            # Extract JSON from the response
            evaluation_result = self._extract_json_from_response(processed_response)
            
            # Process the evaluation result
            processed_result = self._process_evaluation_result(evaluation_result, requested_errors)
            
            return processed_result
            
        except Exception as e:
            logger.error(f"{t('error_evaluating_code')}: {str(e)}")
            return ""
    
    def generate_improved_prompt(self, code: str, requested_errors: List[Dict[str, Any]], 
                          evaluation: Dict[str, Any]) -> str:
        """
        Generate an improved prompt for the code generator based on evaluation results.
        
        Args:
            code: The previously generated code
            requested_errors: List of errors that should be implemented
            evaluation: Evaluation results from evaluate_code method
            
        Returns:
            Improved prompt string for the code generator
        """       
        
        # Determine domain from existing code
        domain = self._infer_domain_from_code(code)
        
        # Extract missing and found errors
        missing_errors = []
        found_errors = []
        
        # Process missing errors - handle both string and dictionary formats
        if evaluation.get(t("missing_errors"), None):
            for error in evaluation.get(t("missing_errors"), []):
                if isinstance(error, dict):
                    error_type = error[t("error_type")]
                    error_name = error[t("error_name")]
                    missing_errors.append(f"{error_type} - {error_name}")
                elif isinstance(error, str):
                    missing_errors.append(error)
        
        # Process found errors - handle both string and dictionary formats
        if evaluation.get(t("found_errors"), None):
            for error in evaluation.get(t("found_errors"), None):
                if isinstance(error, dict):
                    error_type = error[t("error_type")]
                    error_name = error[t("error_name")]
                    found_errors.append(f"{error_type} - {error_name}")
                elif isinstance(error, str):
                    found_errors.append(error)
        
        # Use the optimized prompt function
        prompt = create_regeneration_prompt(
            code=code,
            domain=domain,
            missing_errors=missing_errors,
            found_errors=found_errors,
            requested_errors=requested_errors
        )
        
        # Log the regeneration prompt
        metadata = {
             t("requested_errors"): [f"{error.get(t('type'), '').upper()} - {error.get(t('name'), '')}" for error in requested_errors],
             t("missing_errors"): missing_errors,
             t("found_errors"): found_errors,
             t("domain"): domain,
             t("attempt"): self.llm_logger.get_attempt_count("code_generation") + 1
        }
        
        self.llm_logger.log_interaction("regeneration_prompt", prompt, "N/A - Prompt Only", metadata)
        
        return prompt

    def _infer_domain_from_code(self, code: str) -> str:
        """
        Infer the domain of the code based on class and variable names.
        
        Args:
            code: The Java code
            
        Returns:
            Inferred domain string
        """
        code_lower = code.lower()
        
        # Check for common domains
        domains = {
            "student_management": ["student", "course", "enroll", "grade", "academic"],
            "file_processing": ["file", "read", "write", "path", "directory"],
            "data_validation": ["validate", "input", "check", "valid", "sanitize"],
            "calculation": ["calculate", "compute", "math", "formula", "result"],
            "inventory_system": ["inventory", "product", "stock", "item", "quantity"],
            "notification_service": ["notify", "message", "alert", "notification", "send"],
            "banking": ["account", "bank", "transaction", "balance", "deposit"],
            "e-commerce": ["cart", "product", "order", "payment", "customer"]
        }
        
        # Count domain-related terms
        domain_scores = {}
        for domain, terms in domains.items():
            score = sum(code_lower.count(term) for term in terms)
            domain_scores[domain] = score
        
        # Return the highest scoring domain, or a default
        if domain_scores:
            max_domain = max(domain_scores.items(), key=lambda x: x[1])
            if max_domain[1] > 0:
                return max_domain[0]
        
        return "general_application"  # Default domain
    
    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON data from LLM response with improved handling for Groq responses.
        
        Args:
            response: LLM response text
            
        Returns:
            Extracted JSON data or None if extraction fails
        """
        # Check if response is None or empty
        if not response:
            return None
        
        # Ensure response is a string
        if not isinstance(response, str):
            try:
                response = str(response)
            except:
                logger.error(t("could_not_convert_response_to_string"))
                return None
        
        # Log first part of response for debugging
        logger.debug(f"{t('extracting_json_from_response')}: {response[:200]}...")
        
        # First try direct JSON parsing if the response looks like JSON
        if response.strip().startswith('{') and response.strip().endswith('}'):
            try:
                # Clean the response to fix common JSON issues
                json_str = response.strip()
                # Fix trailing commas which are invalid in JSON
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
                # Try to parse as JSON directly
                return json.loads(json_str)
            except json.JSONDecodeError:
                # If direct parsing fails, continue with regex extraction
                pass
        
        # Try to find JSON block with various patterns
        patterns = [
            r'```json\s*([\s\S]*?)```',  # JSON in code block
            r'```\s*({[\s\S]*?})\s*```',  # Any JSON in code block
            r'({[\s\S]*?"Found Errors"[\s\S]*?})',  # JSON with found_errors field
            r'({[\s\S]*?"已找到錯誤"[\s\S]*?})',  # JSON with Chinese found_errors field
            r'({[\s\S]*?"Valid"[\s\S]*?})',  # JSON with valid field
            r'({[\s\S]*?"有效"[\s\S]*?})',  # JSON with Chinese valid field
            r'({[\s\S]*?"Missing Errors"[\s\S]*?})',  # JSON with missing_errors field
            r'({[\s\S]*?"遺漏錯誤"[\s\S]*?})',  # JSON with Chinese missing_errors field
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                try:
                    # Clean the match to fix common JSON issues
                    json_str = match.strip()
                    # Fix trailing commas which are invalid in JSON
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    # Try to parse as JSON
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
        
        # If regex extraction fails, try to find JSON-like structure with looser matching
        try:
            opening_bracket = response.find('{')
            closing_bracket = response.rfind('}')
            
            if opening_bracket != -1 and closing_bracket != -1 and opening_bracket < closing_bracket:
                json_str = response[opening_bracket:closing_bracket + 1]
                # Fix trailing commas
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
                # Try to parse as JSON
                return json.loads(json_str)
        except:
            pass
        
        # For Groq responses, if all extraction methods fail, try a more aggressive approach
        # to build a structured result manually
        missing_errors = []
        found_errors = []
        
        # Try to extract found_errors section - support both English and Chinese field names
        found_match = re.search(r'(found_errors|已找到錯誤):?\s*\n(.*?)(?:(missing_errors|遺漏錯誤)|\n\n)', response, re.DOTALL)
        if found_match:
            found_section = found_match.group(2)
            # Extract individual errors
            for line in found_section.splitlines():
                if line.strip() and ":" in line:
                    found_errors.append(line.strip())
        
        # Try to extract missing_errors section - support both English and Chinese field names
        missing_match = re.search(r'(missing_errors|遺漏錯誤):?\s*\n(.*?)(?:\n\n|$)', response, re.DOTALL)
        if missing_match:
            missing_section = missing_match.group(2)
            # Extract individual errors
            for line in missing_section.splitlines():
                if line.strip() and ":" in line:
                    missing_errors.append(line.strip())
        
        # If we extracted at least some structured data, return a constructed result
        if found_errors or missing_errors:
            logger.debug(f"{t('using_manually_extracted_errors')}: {len(found_errors)} {t('found')}, {len(missing_errors)} {t('missing')}")
            return {
                t("found_errors"): found_errors,
                t("missing_errors"): missing_errors,
                t("valid"): len(missing_errors) == 0,
                t("feedback"): f"{t('found')} {len(found_errors)} {t('errors')}, {len(missing_errors)} {t('missing')}."
            }
        
        # If all extraction methods fail, return a default result structure
        logger.warning(t("could_not_extract_json_from_response"))
        # Include all requested errors as missing to force regeneration
        return {
            t("found_errors"): [],
            t("missing_errors"): [t("extraction_failed")],  # This will force regeneration
            t("valid"): False,
            t("feedback"): t("could_not_extract_proper_analysis")
        }
    
    def _process_evaluation_result(self, result: Dict[str, Any], 
                        requested_errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process and enhance the evaluation result with improved type safety.
        
        Args:
            result: Raw evaluation result from LLM
            requested_errors: List of requested errors
            
        Returns:
            Processed evaluation result
        """
        # Handle None result
        if result is None:
            logger.warning(t("received_none_result"))
            result = {
                t("found_errors"): [],
                t("missing_errors"): [],
                t("valid"): False,
                t("feedback"): t("failed_to_process_evaluation_result")
            }
        
        # Ensure result is a dictionary
        if not isinstance(result, dict):
            logger.error(f"{t('expected_dict_for_result')}, {t('got')} {type(result)}")
            result = {
                t("found_errors"): [],
                t("missing_errors"): [],
                t("valid"): False,
                t("feedback"): f"{t('invalid_evaluation_result_type')}: {type(result)}"
            }
        
        # Ensure all expected fields exist with proper defaults
        if result.get(t("found_errors")) is None:
            result[t("found_errors")] = []
        if result.get(t("missing_errors")) is None:
            result[t("missing_errors")] = []
        
        # Ensure found_errors is a list
        if not isinstance(result.get(t("found_errors"), []), list):
            logger.warning(f"{t('found_errors')} {t('is_not_a_list')}, {t('got')} {type(result.get(t('found_errors'), []))}")
            result[t("found_errors")] = []
        
        # Ensure missing_errors is a list
        if not isinstance(result.get(t("missing_errors"), []), list):
            logger.warning(f"{t('missing_errors')} {t('is_not_a_list')}, {t('got')} {type(result.get(t('missing_errors'), []))}")
            result[t("missing_errors")] = []
        
        # Convert requested errors to keys for easier lookup
        requested_keys = {}
        for error in requested_errors:
            if not isinstance(error, dict):
                logger.warning(f"{t('skipping_non_dict_error')}: {error}")
                continue
                
            error_type = error.get(t("type"), "").upper()
            error_name = error.get(t("name"), "")
            key = f"{error_type} - {error_name}"
            requested_keys[key] = error
        
        # Process found errors to make sure they're in the right format for regeneration
        processed_found_errors = []
        
        for error in result.get(t("found_errors"), []):
            # Skip non-dict errors with warning
            if not isinstance(error, dict):
                try:
                    error_str = str(error)
                    # Try to extract error type and name from string
                    match = re.search(r'([A-Z]+)\s*-\s*([^:]+)', error_str)
                    if match:
                        error_type = match.group(1).strip()
                        error_name = match.group(2).strip()
                        processed_found_errors.append(f"{error_type} - {error_name}")
                    else:
                        logger.warning(f"{t('could_not_process_non_dict_error')}: {error_str}")
                except:
                    logger.warning(f"{t('could_not_process_non_dict_error')}: {error}")
                continue
                
            error_type = error[t('error_type')]
            error_name = error[t('error_name')]
            
            if error_type and error_name:
                processed_found_errors.append(f"{error_type} - {error_name}")
        
        # Process missing errors to ensure they're in the right format for regeneration
        processed_missing_errors = []
        
        for error in result.get(t("missing_errors"), []):
            # Skip non-dict errors with warning
            if not isinstance(error, dict):
                try:
                    error_str = str(error)
                    # Try to extract error type and name from string
                    match = re.search(r'([A-Z]+)\s*-\s*([^:]+)', error_str)
                    if match:
                        error_type = match.group(1).strip()
                        error_name = match.group(2).strip()
                        processed_missing_errors.append(f"{error_type} - {error_name}")
                    else:
                        logger.warning(f"{t('could_not_process_non_dict_error')}: {error_str}")
                except:
                    logger.warning(f"{t('could_not_process_non_dict_error')}: {error}")
                continue
                
            error_type =  error[t('error_type')]
            error_name =  error[t('error_name')]
            
            if error_type and error_name:
                processed_missing_errors.append(f"{error_type} - {error_name}")
        
        # Update the result with processed data
        result[t("found_errors")] = processed_found_errors
        result[t("missing_errors")] = processed_missing_errors
        
        # Validate the "valid" field based on found vs requested errors
        result[t("valid")] = len(processed_missing_errors) == 0 and len(processed_found_errors) == len(requested_errors)
        
        # Store the original requested error count
        result[t("original_error_count")] = len(requested_errors)
        
        # Generate a feedback message
        if result.get(t("valid"), False):
            result[t("feedback")] = f"{t('all')} {len(requested_errors)} {t('requested_errors_are_properly_implemented')}."
        else:
            result[t("feedback")] = (f"{t('found')} {len(processed_found_errors)} {t('out_of')} {len(requested_errors)} "
                            f"{t('requested_errors')}. {t('missing')} {len(processed_missing_errors)} {t('errors')}.")
        
        return result