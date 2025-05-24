import re
import os
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from langchain_core.language_models import BaseLanguageModel

from utils.code_utils import create_review_analysis_prompt, create_feedback_prompt, create_comparison_report_prompt, process_llm_response
from utils.llm_logger import LLMInteractionLogger
from utils.language_utils import t
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StudentResponseEvaluator:
    """
    Evaluates student code reviews against known problems in the code.
    
    This class analyzes how thoroughly and accurately a student identified 
    issues in a code snippet, providing detailed feedback and metrics.
    """    
    def __init__(self, llm: BaseLanguageModel = None,                 
                 llm_logger: LLMInteractionLogger = None):
        """
        Initialize the StudentResponseEvaluator.
        
        Args:
            llm: Language model to use for evaluation           
            llm_logger: Logger for tracking LLM interactions
        """
        self.llm = llm
        self.llm_logger = llm_logger or LLMInteractionLogger()

        # Load meaningful score threshold from environment variable with default fallback to 0.6
        try:
            self.meaningful_score_threshold = float(os.getenv("MEANINGFUL_SCORE", "0.6"))
            self.accuracy_score_threshold = float(os.getenv("ACCURACY_SCORE", "0.7"))
            logger.debug(f"Using meaningful score threshold: {self.meaningful_score_threshold}")
            logger.debug(f"Using accuracy score threshold: {self.accuracy_score_threshold}")
        except (ValueError, TypeError):
            logger.warning("Invalid MEANINGFUL_SCORE in environment, defaulting to 0.6")
            logger.warning("Invalid ACCURACY_SCORE in environment, defaulting to 0.7")
            self.meaningful_score_threshold = 0.6
            self.accuracy_score_threshold = 0.7
    
    def evaluate_review(self, code_snippet: str, known_problems: List[str], student_review: str) -> Dict[str, Any]:
        """
        Evaluate a student's review against known problems.
        Uses the create_review_analysis_prompt function from code_utils.
        
        Args:
            code_snippet: The original code snippet with injected errors
            known_problems: List of known problems in the code
            student_review: The student's review comments
            
        Returns:
            Dictionary with detailed analysis results
        """
        if not self.llm:
            logger.warning("No LLM available for review evaluation, using fallback evaluation")
            return "// Error: No LLM available for code generation"

        try:
            logger.debug("Evaluating student review with code_utils prompt")
            
            if not self.llm:
                logger.warning(t("no_llm_provided_for_evaluation"))
                return ""
            
            # Create a review analysis prompt using the utility function
            prompt = create_review_analysis_prompt(
                code=code_snippet,
                known_problems=known_problems,
                student_review=student_review
            )
            
            try:
                # Metadata for logging
                metadata = {
                    t("code_length"): len(code_snippet.splitlines()),
                    t("known_problems_count"): len(known_problems),
                    t("student_review_length"): len(student_review.splitlines())
                }
                # Get the evaluation from the LLM
                logger.debug("Sending student review to LLM for evaluation")
                response = self.llm.invoke(prompt)
                processed_response = process_llm_response(response)

                # Log the interaction
                self.llm_logger.log_review_analysis(prompt, processed_response, metadata)
                
                # Make sure we have a response
                if not response:
                    logger.error(t("empty_response_from_llm"))
                    return ""
                
                # Extract JSON data from the response
                analysis_data = self._extract_json_from_text(processed_response)   
                # Process the analysis data
                enhanced_analysis = self._process_enhanced_analysis(analysis_data, known_problems)               
                return enhanced_analysis
                
            except Exception as e:
                logger.error(f"{t('error')} {t('evaluating_review_with_llm')}: {str(e)}")                
                # Log the error
                error_metadata = {**metadata, "error": str(e)}
                self.llm_logger.log_review_analysis(prompt, f"{t('error')}: {str(e)}", error_metadata)                
                return ""
            
        except Exception as e:
            logger.error(f"{t('exception_in_evaluate_review')}: {str(e)}")
            return ""
            
    def _process_enhanced_analysis(self, analysis_data: Dict[str, Any], known_problems: List[str]) -> Dict[str, Any]:
        """
        Process and enhance the analysis data from the LLM.
        
        Args:
            analysis_data: Raw analysis data from LLM
            known_problems: List of known problems for reference
            
        Returns:
            Enhanced analysis data
        """

        if not analysis_data:
            return ""
        
        # Extract core metrics with defaults
        identified_count = analysis_data.get(f"{t('identified_count')}",0)
        total_problems = analysis_data.get(f"{t('total_problems')}",len(known_problems))

        # Track meaningful comments separately
        identified_problems = analysis_data.get(f"{t('identified_problems')}", [])

        # Calculate percentages
        if total_problems > 0:
            identified_percentage = (identified_count / total_problems) * 100
        else:
            identified_percentage = 100.0

        # Calculate percentages
        if total_problems > 0:
            identified_percentage = (identified_count / total_problems) * 100
        else:
            identified_percentage = 100.0

        # Check if review is sufficient based on meaningful comments
        review_sufficient = analysis_data.get(f"{'review_sufficient'}", False)
        identified_problems =  analysis_data.get(f"{t('identified_problems')}", False)
        missed_problems = analysis_data.get(f"{t('missed_problems')}", False)
        
        # Construct enhanced result using t() function for keys
        enhanced_result = {
            t("identified_problems"): identified_problems,
            t("missed_problems"): missed_problems,
            t("identified_count"): identified_count,
            t("total_problems"): total_problems,
            t("identified_percentage"): identified_percentage,
            t("review_sufficient"): review_sufficient
        }
        
        return enhanced_result
         
    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON data from LLM response text with improved robustness for malformed responses.
        
        Args:
            text: Text containing JSON data
            
        Returns:
            Extracted JSON data
        """
        # Handle None or empty text
        if not text:
            return {t("error"): t("empty_response_from_llm")}
        
        try:
            # First try direct JSON parsing if the response looks like JSON
            if text.strip().startswith('{') and text.strip().endswith('}'):
                try:
                    # Clean the response to fix common JSON issues
                    json_str = text.strip()
                    # Fix trailing commas which are invalid in JSON
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    # Try to parse as JSON directly
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # If direct parsing fails, continue with regex extraction
                    pass
                    
            # For the specific broken format in the example
            # Look for key JSON fields and try to reconstruct a valid JSON
            identified_problems_match = re.search(r'"(已識別的問題|Identified Problems)"\s*:\s*\[(.*?)\]', text, re.DOTALL)
            
            # Fallback manual extraction when JSON is severely malformed
            analysis = {}
            
            # Extract identified problems with either Chinese or English field names
            if identified_problems_match:
                identified_problems_text = identified_problems_match.group(2)
                # Try to extract individual problem objects
                problem_objects = []
                current_problem = {}
                lines = identified_problems_text.strip().split('\n')
                
                for line in lines:
                    line = line.strip()
                    
                    # Skip empty lines or just containing brackets/braces
                    if not line or line in ['{', '}', '[', ']']:
                        continue
                    
                    # Check for key-value pairs
                    key_value_match = re.search(r'"([^"]+)"\s*:\s*(.+)', line)
                    if key_value_match:
                        key = key_value_match.group(1)
                        value = key_value_match.group(2).strip()
                        
                        # Remove trailing comma if present
                        if value.endswith(','):
                            value = value[:-1].strip()
                        
                        # Handle string values (quoted)
                        if value.startswith('"') and value.endswith('"'):
                            current_problem[key] = value[1:-1]
                        # Handle numeric values
                        elif value.replace('.', '', 1).isdigit():
                            current_problem[key] = float(value) if '.' in value else int(value)
                        # Handle boolean values
                        elif value.lower() in ['true', 'false']:
                            current_problem[key] = value.lower() == 'true'
                        else:
                            current_problem[key] = value
                    
                    # If we see a closing brace, add the current problem to the list
                    if '}' in line and current_problem:
                        problem_objects.append(current_problem)
                        current_problem = {}
                
                # Add any remaining problem
                if current_problem:
                    problem_objects.append(current_problem)
                    
                # Add the extracted problems to the analysis
                analysis[t("identified_problems")] = problem_objects
            
            # Extract other fields similarly (missed problems, counts, etc.)
            # Example for identified count
            identified_count_match = re.search(r'"(已識別數量|Identified Count)"\s*:\s*(\d+)', text)
            if identified_count_match:
                analysis[t("identified_count")] = int(identified_count_match.group(2))
                
            # Example for total problems
            total_problems_match = re.search(r'"(總問題數|Total Problems)"\s*:\s*(\d+)', text)
            if total_problems_match:
                analysis[t("total_problems")] = int(total_problems_match.group(2))
                
            # Example for identified percentage
            percentage_match = re.search(r'"(識別百分比|Identified Percentage)"\s*:\s*([0-9.]+)', text)
            if percentage_match:
                analysis[t("identified_percentage")] = float(percentage_match.group(2))
                
            # Example for review sufficient
            sufficient_match = re.search(r'"(審查足夠|Review Sufficient)"\s*:\s*(true|false)', text, re.IGNORECASE)
            if sufficient_match:
                analysis[t("review_sufficient")] = sufficient_match.group(2).lower() == "true"
            
            # Try to extract missed problems array separately
            missed_problems_match = re.search(r'"(遺漏的問題|Missed Problems)"\s*:\s*\[(.*?)\]', text, re.DOTALL)
            if missed_problems_match:
               
                # Parse the missed_text to extract problem objects
                #analysis[t("missed_problems")] = missed_problems
                missed_text = missed_problems_match.group(2).strip()
                missed_problems = []
                current_problem = {}
                lines = missed_text.strip().split('\n')

                for line in lines:
                    line = line.strip()
                    # Skip empty lines or just containing brackets/braces
                    if not line or line in ['{', '}', '[', ']']:
                        continue
                    
                    # Check for key-value pairs
                    key_value_match = re.search(r'"([^"]+)"\s*:\s*(.+)', line)
                    if key_value_match:
                        key = key_value_match.group(1)
                        value = key_value_match.group(2).strip()
                        
                        # Remove trailing comma if present
                        if value.endswith(','):
                            value = value[:-1].strip()
                        
                        # Handle string values (quoted)
                        if value.startswith('"') and value.endswith('"'):
                            current_problem[key] = value[1:-1]
                        # Handle numeric values
                        elif value.replace('.', '', 1).isdigit():
                            current_problem[key] = float(value) if '.' in value else int(value)
                        # Handle boolean values
                        elif value.lower() in ['true', 'false']:
                            current_problem[key] = value.lower() == 'true'
                        else:
                            current_problem[key] = value
                    
                    # If we see a closing brace, add the current problem to the list
                    if '}' in line and current_problem:
                        missed_problems.append(current_problem)
                        current_problem = {}

                # Add any remaining problem
                if current_problem:
                    missed_problems.append(current_problem)
                
                # Add the parsed missed problems to the analysis
                analysis[t("missed_problems")] = missed_problems
            else:
                analysis[t("missed_problems")] = []
            
            # If we extracted enough fields to form a valid analysis, return it
            if t("identified_problems") in analysis or t("missed_problems") in analysis:
                return analysis
                
            # If all else fails, return a minimal valid structure
            logger.warning(t("could_not_extract_json_from_response"))
            return {
                t("identified_problems"): [],
                t("missed_problems"): [],
                t("identified_count"): 0,
                t("total_problems"): 0,
                t("identified_percentage"): 0,
                t("review_sufficient"): False,
                t("feedback"): t("analysis_could_not_extract_feedback")
            }
            
        except Exception as e:
            logger.error(f"{t('error_extracting_json')}: {str(e)}")
            return {
                t("error"): f"{t('error_extracting_json')}: {str(e)}",
                t("raw_text"): text[:500] + ("..." if len(text) > 500 else "")
            }

    def generate_targeted_guidance(self, code_snippet: str, known_problems: List[str], student_review: str, review_analysis: Dict[str, Any], iteration_count: int, max_iterations: int) -> str:
        """
        Generate targeted guidance for the student to improve their review.
        Ensures guidance is concise and focused with proper language support.
        
        Args:
            code_snippet: The original code snippet with injected errors
            known_problems: List of known problems in the code
            student_review: The student's review comments
            review_analysis: Analysis of the student review
            iteration_count: Current iteration number
            max_iterations: Maximum number of iterations
            
        Returns:
            Targeted guidance text
        """        
        if not self.llm:
            logger.warning(t("no_llm_provided_for_guidance"))
            return ""
        
        try:
            # Get iteration information to add to review_analysis for context
            review_context = review_analysis.copy()
            review_context.update({
                t("iteration_count"): iteration_count,
                t("max_iterations"): max_iterations,
                t("remaining_attempts"): max_iterations - iteration_count
            })

            identified_count = review_context.get(t("identified_count"), 0)

            # Use the utility function to create the prompt
            prompt = create_feedback_prompt(
                code=code_snippet,
                known_problems=known_problems,
                review_analysis=review_context
            )

            #prompt += "\n\nIMPORTANT: Focus on helping the student make more meaningful comments. A good comment should clearly explain WHAT the issue is and WHY it's a problem, not just identify where it is. For example, instead of just 'Line 11: null issue', guide them to write 'Line 11: Object is accessed before null check, which could cause NullPointerException'."

            metadata = {
                t("iteration"): iteration_count,
                t("max_iterations"): max_iterations,
                t("identified_count"):  review_analysis[t('identified_count')],
                t("total_problems"): review_analysis[t('total_problems')],
                t("accuracy_percentage"): review_analysis[t('accuracy_percentage')]
            }

            logger.debug(t("generating_concise_targeted_guidance").format(iteration_count=iteration_count))
            response = self.llm.invoke(prompt)
            guidance = process_llm_response(response)
            
            
            # Ensure response is concise - trim if needed
            if len(guidance.split()) > 100:
                # Split into sentences and take the first 3-4
                sentences = re.split(r'(?<=[.!?])\s+', guidance)
                guidance = ' '.join(sentences[:4])
                logger.debug(t("trimmed_guidance_words").format(
                    before=len(guidance.split()), 
                    after=len(guidance.split())
                ))
            
            # Log the interaction
            self.llm_logger.log_summary_generation(prompt, guidance, metadata)            
            return guidance
            
        except Exception as e:
            logger.error(f"{t('error_generating_guidance')}: {str(e)}")            
            
            # Create error metadata with translated keys
            error_metadata = {
                t("iteration"): iteration_count,
                t("max_iterations"): max_iterations,
                t("identified_count"): review_analysis[t('identified_count')],
                t("total_problems"): review_analysis[t('total_problems')],
                t("error"): str(e)
            }
            
            # Log the error
            self.llm_logger.log_interaction(
                t('targeted_guidance'), 
                prompt,
                f"{t('error')}: {str(e)}", 
                error_metadata
            )
                
            # Fallback to concise guidance
            return ""
        
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
   
    def generate_comparison_report(self, evaluation_errors: List[str], review_analysis: Dict[str, Any], 
                                  review_history: List[Dict[str, Any]] = None) -> str:
        """
        Generate a comparison report showing progress across review attempts.
        Uses the LLM instance that's already available in the class.
        
        Args:
            evaluation_errors: List of errors found by the evaluation
            review_analysis: Analysis of the latest student review
            review_history: History of all review attempts
            
        Returns:
            Formatted comparison report
        """
        try:
            # Check if LLM is available
            if not self.llm:
                logger.error(f"{t('error')} generating comparison report: No LLM available")
                return ""
                
            # Create the prompt for the LLM
            prompt = create_comparison_report_prompt(evaluation_errors, review_analysis, review_history)
            
            # Generate the report with the LLM
            response = self.llm.invoke(prompt)
            
            # Process the response
            if hasattr(response, 'content'):
                report = response.content
            elif isinstance(response, dict) and 'content' in response:
                report = response['content']
            else:
                report = str(response)
            
            # Clean up the report
            report = report.replace('\\n', '\n')
            
            # Log the report generation
            self.llm_logger.log_interaction("comparison_report", prompt, report, {
                t("evaluation_errors_count"): len(evaluation_errors),
                t("review_analysis"): review_analysis,
                t("review_history_count"): len(review_history) if review_history else 0
            })
            
            return report
        except Exception as e:
            # Log the error
            logger.error(f"Error generating comparison report with LLM: {str(e)}")
            # Return an empty string
            return ""
    