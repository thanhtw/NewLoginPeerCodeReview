import re
import logging
import json
from typing import List, Dict, Any
from langchain_core.language_models import BaseLanguageModel

from utils.code_utils import create_review_analysis_prompt, create_feedback_prompt, process_llm_response
from utils.llm_logger import LLMInteractionLogger
from utils.language_utils import t, get_field_value, get_current_language

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
                 min_identified_percentage: float = 60.0,
                 llm_logger: LLMInteractionLogger = None):
        """
        Initialize the StudentResponseEvaluator.
        
        Args:
            llm: Language model to use for evaluation
            min_identified_percentage: Minimum percentage of problems that
                                     should be identified for a sufficient review
            llm_logger: Logger for tracking LLM interactions
        """
        self.llm = llm
        self.min_identified_percentage = min_identified_percentage
        self.llm_logger = llm_logger or LLMInteractionLogger()
    
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
        try:
            logger.info("Evaluating student review with code_utils prompt")
            
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
                logger.info("Sending student review to LLM for evaluation")
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

        # Calculate percentages
        if total_problems > 0:
            identified_percentage = (identified_count / total_problems) * 100
        else:
            identified_percentage = 100.0


        review_sufficient = analysis_data.get(f"{t('review_sufficient')}", False)
        identified_problems =  analysis_data.get(f"{t('identified_problems')}", False)
        missed_problems = analysis_data.get(f"{t('missed_problems')}", False)
        # Construct enhanced result using t() function for keys

        enhanced_result = {
            t("identified_problems"): identified_problems,  # Keep the detailed version
            t("missed_problems"): missed_problems,  # Keep the detailed version
            t("identified_count"): identified_count,
            t("total_problems"): total_problems,
            t("identified_percentage"): identified_percentage,  # For backward compatibility
            t("review_sufficient"): review_sufficient
        }
        
        return enhanced_result
         
    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON data from LLM response text with full internationalization support.
        
        Args:
            text: Text containing JSON data
            
        Returns:
            Extracted JSON data
        """
        # Handle None or empty text
        if not text:
            return {t("error"): t("empty_response_from_llm")}
        
        try:
            # Try to find JSON block with regex
            patterns = [
                r'```json\s*([\s\S]*?)```',  # JSON code block
                r'```\s*({[\s\S]*?})\s*```',  # Any JSON object in code block
                r'({[\s\S]*"Identified Problems"[\s\S]*"Missed Problems"[\s\S]*})',  # Look for our expected fields
                r'({[\s\S]*"已識別的問題"[\s\S]*"遺漏的問題"[\s\S]*})',  # Look for Chinese field names
                r'({[\s\S]*})',  # Any JSON-like structure
            ]
            
            # Try each pattern
            for pattern in patterns:
                matches = re.findall(pattern, text, re.DOTALL)
                for match in matches:
                    try:
                        # Clean up the match
                        json_str = match.strip()
                        # Fix trailing commas which are invalid in JSON
                        json_str = re.sub(r',\s*}', '}', json_str)
                        json_str = re.sub(r',\s*]', ']', json_str)
                        # Try to parse as JSON
                        parsed_json = json.loads(json_str)
                        
                        # Convert to standardized format with translated keys
                        result = {}
                        
                        # Map keys to translated versions
                        key_mappings = {
                            "issues_identified": t("issues_identified"),
                            "missed_problems": t("missed_problems"),
                            "identified_count": t("identified_count"),
                            "total_problems": t("total_problems"),
                            "accuracy_percentage": t("accuracy_percentage"),
                            "review_sufficient": t("review_sufficient"),
                            
                            # Chinese key mappings
                            "已識別問題": t("issues_identified"),
                            "遺漏問題": t("missed_problems"),
                            "已識別數量": t("identified_count"),
                            "總問題數": t("total_problems"),
                            "準確率百分比": t("accuracy_percentage"),
                            "審查充分": t("review_sufficient"),
                        }
                        
                        # Map all keys to translated versions
                        for key, value in parsed_json.items():
                            translated_key = key_mappings.get(key, key)
                            result[translated_key] = value
                        
                        return result
                    except json.JSONDecodeError:
                        continue
            
            # If standard methods fail, try to manually extract fields
            logger.warning(t("could_not_extract_json"))
            analysis = {}
            
            # Try to extract identified problems - support both English and Chinese field names
            identified_match = re.search(r'"(Identified Problems|已識別的問題)"\s*:\s*(\[.*?\])', text, re.DOTALL)
            if identified_match:
                try:
                    identified_str = identified_match.group(2)
                    # Clean up the JSON string
                    identified_str = re.sub(r',\s*]', ']', identified_str)
                    analysis[t("identified_problems")] = json.loads(identified_str)
                except Exception as e:
                    logger.warning(f"{t('json_parse_error')}: {str(e)}")
                    analysis[t("identified_problems")] = []
            else:
                analysis[t("identified_problems")] = []
            
            # Try to extract missed problems - support both English and Chinese field names
            missed_match = re.search(r'"(Missed Problems|遺漏的問題)"\s*:\s*(\[.*?\])', text, re.DOTALL)
            if missed_match:
                try:
                    missed_str = missed_match.group(2)
                    # Clean up the JSON string
                    missed_str = re.sub(r',\s*]', ']', missed_str)
                    analysis[t("missed_problems")] = json.loads(missed_str)
                except Exception as e:
                    logger.warning(f"{t('json_parse_error')}: {str(e)}")
                    analysis[t("missed_problems")] = []
            else:
                analysis[t("missed_problems")] = []
            
            # Try to extract identified count - support both English and Chinese field names
            count_match = re.search(r'"(Identified Count|已識別數量)"\s*:\s*([0-9]+)', text)
            if count_match:
                try:
                    analysis[t("identified_count")] = int(count_match.group(2))
                except:
                    analysis[t("identified_count")] = 0
            else:
                analysis[t("identified_count")] = 0
            
            # Try to extract total problems - support both English and Chinese field names
            total_match = re.search(r'"(Total Problems|總問題數)"\s*:\s*([0-9]+)', text)
            if total_match:
                try:
                    analysis[t("total_problems")] = int(total_match.group(2))
                except:
                    analysis[t("total_problems")] = 0
            else:
                analysis[t("total_problems")] = 0
            
            # Try to extract accuracy percentage - support both English and Chinese field names
            accuracy_match = re.search(r'"(Identified Percentage|識別百分比)"\s*:\s*([0-9.]+)', text)
            if accuracy_match:
                try:
                    analysis[t("identified_percentage")] = float(accuracy_match.group(2))
                except:
                    analysis[t("identified_percentage")] = 0.0
            else:
                analysis[t("identified_percentage")] = 0.0
            
            # Try to extract review_sufficient - support both English and Chinese field names
            sufficient_match = re.search(r'"(Review Sufficient|審查足夠)"\s*:\s*(true|false)', text, re.IGNORECASE)
            if sufficient_match:
                analysis[t("review_sufficient")] = sufficient_match.group(2).lower() == "true"
            else:
                analysis[t("review_sufficient")] = False
            
            # Try to extract feedback - support both English and Chinese field names
            feedback_match = re.search(r'"(Feedback|反饋)"\s*:\s*"(.*?)"', text)
            if feedback_match:
                analysis[t("feedback")] = feedback_match.group(2)
            else:
                analysis[t("feedback")] = t("analysis_could_not_extract_feedback")
            
            if analysis:
                # Add consistency check - ensure we have the basic required fields
                required_fields = [
                    t("identified_problems"),
                    t("missed_problems"),
                    t("identified_count"),
                    t("total_problems"),
                    t("accuracy_percentage"),
                    t("review_sufficient"),
                    t("feedback")
                ]
                
                # Fill in any missing required fields with defaults
                for field in required_fields:
                    if field not in analysis:
                        if field == t("identified_count") or field == t("total_problems"):
                            analysis[field] = 0
                        elif field == t("accuracy_percentage"):
                            analysis[field] = 0.0
                        elif field == t("review_sufficient"):
                            analysis[field] = False
                
                return analysis
            
            # If all else fails, return an error object
            logger.error(t("could_not_extract_analysis_data"))
            return {
                t("error"): t("could_not_parse_json_response"),
                t("raw_text"): text[:500] + ("..." if len(text) > 500 else "")
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

            # Use the utility function to create the prompt
            prompt = create_feedback_prompt(
                code=code_snippet,
                known_problems=known_problems,
                review_analysis=review_context
            )

            metadata = {
                t("iteration"): iteration_count,
                t("max_iterations"): max_iterations,
                t("identified_count"):  review_analysis[t('identified_count')],
                t("total_problems"): review_analysis[t('total_problems')],
                t("accuracy_percentage"): review_analysis[t('accuracy_percentage')]
            }

            # Generate the guidance using the LLM
            logger.info(t("generating_concise_targeted_guidance").format(iteration_count=iteration_count))
            response = self.llm.invoke(prompt)
            guidance = process_llm_response(response)
            
            # Ensure response is concise - trim if needed
            if len(guidance.split()) > 100:
                # Split into sentences and take the first 3-4
                sentences = re.split(r'(?<=[.!?])\s+', guidance)
                guidance = ' '.join(sentences[:4])
                logger.info(t("trimmed_guidance_words").format(
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