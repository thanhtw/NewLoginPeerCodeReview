"""
JSON Error Repository module for Java Peer Review Training System.

This module provides direct access to error data from JSON files,
eliminating the need for intermediate data transformation.
"""

import os
import json
import logging
import random
from typing import Dict, List, Any, Optional, Set, Union, Tuple
from utils.language_utils import get_current_language, t

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class JsonErrorRepository:
    """
    Repository for accessing Java error data directly from JSON files.
    
    This class handles loading, categorizing, and providing access to
    error data from Java_code_review_errors.json file.
    """
    
    
    def __init__(self, java_errors_path: str = None):
        """
        Initialize the JSON Error Repository.
        
        Args:
            java_errors_path: Path to the Java code review errors JSON file
        """
        # Get current language
        self.current_language = get_current_language()
        self.java_errors_path = java_errors_path
        self.DATA_DIR = os.path.join(os.path.dirname(__file__))
        # Determine file path based on language
        if java_errors_path is None:
            self.java_errors_path = f"{self.DATA_DIR}/{self.current_language}_Java_code_review_errors.json"
        else:
            self.java_errors_path = java_errors_path     
        # Initialize data
        self.java_errors = {}
        self.java_error_categories = []
        
        # Load error data from JSON files
        self.load_error_data()
       
    def load_error_data(self) -> bool:
        """
        Load error data from JSON files.
        
        Returns:
            True if files are loaded successfully, False otherwise
        """
        java_loaded = self._load_java_errors()
        if not java_loaded and self.current_language != "en":
            logger.warning(f"Failed to load {self.current_language} Java errors, trying English version")
            self.java_errors_path = os.path.join(self.DATA_DIR, "en_Java_code_review_errors.json")
            java_loaded = self._load_java_errors()
        
        # If still not loaded, use hardcoded fallback categories
        if not java_loaded:
            logger.warning("Using fallback error categories")
            # Provide fallback error categories to ensure UI doesn't break
            self.java_errors = {
                "Logical": [],
                "Syntax": [],
                "Code Quality": [],
                "Standard Violation": [],
                "Java Specific": []
            }
            self.java_error_categories = list(self.java_errors.keys())
        
        return java_loaded

    def _load_java_errors(self) -> bool:
        """
        Load Java errors from JSON file.
        
        Returns:
            True if file is loaded successfully, False otherwise
        """
        try:                    
           if os.path.exists(self.java_errors_path):
            with open(self.java_errors_path, 'r', encoding='utf-8') as file:
                self.java_errors = json.load(file)
                self.java_error_categories = list(self.java_errors.keys())
                logger.debug(f"Loaded Java errors from {self.java_errors_path} with {len(self.java_error_categories)} categories")
                return True
        
            logger.warning(f"Could not find Java errors file: {self.java_errors_path}")
            return False
                    
        except Exception as e:
            logger.error(f"Error loading Java errors: {str(e)}")
            return False
    
    def get_all_categories(self) -> Dict[str, List[str]]:
        """
        Get all error categories.
        
        Returns:
            Dictionary with 'java_errors' categories
        """
        return {
            "java_errors": self.java_error_categories
        }
    
    def get_category_errors(self, category_name: str) -> List[Dict[str, str]]:
        """
        Get errors for a specific category with language-aware field mapping.
        
        Args:
            category_name: Name of the category
            
        Returns:
            List of error dictionaries for the category
        """
        if category_name in self.java_errors:
             return self.java_errors[category_name]
                
        return []
    
    def get_errors_by_categories(self, selected_categories: Dict[str, List[str]]) -> Dict[str, List[Dict[str, str]]]:
        """
        Get errors for selected categories.
        
        Args:
            selected_categories: Dictionary with 'java_errors' key
                              containing a list of selected categories
            
        Returns:
            Dictionary with selected errors by category type
        """
        selected_errors = {
            "java_errors": []
        }
        
        # Get Java errors
        if "java_errors" in selected_categories:
            for category in selected_categories["java_errors"]:
                if category in self.java_errors:
                    selected_errors["java_errors"].extend(self.java_errors[category])
        
        return selected_errors
    
    def get_error_details(self, error_type: str, error_name: str) -> Optional[Dict[str, str]]:
        """
        Get details for a specific error.
        
        Args:
            error_type: Type of error ('java_error')
            error_name: Name of the error
            
        Returns:
            Error details dictionary or None if not found
        """
        if error_type == "java_error":
            for category in self.java_errors:
                for error in self.java_errors[category]:
                    if error.get(t("error_name")) == error_name:
                        return error
        return None
    
    def get_random_errors_by_categories(self, selected_categories: Dict[str, List[str]], 
                                  count: int = 4) -> List[Dict[str, Any]]:
        """
        Get random errors from selected categories.
        
        Args:
            selected_categories: Dictionary with 'java_errors' key
                            containing a list of selected categories
            count: Number of errors to select
            
        Returns:
            List of selected errors with type and category information
        """
        all_errors = []
        java_error_categories = selected_categories.get("java_errors", [])
        
        # Java errors
        for category in java_error_categories:
            if category in self.java_errors:
                for error in self.java_errors[category]:
                    all_errors.append({
                        "type": "java_error",
                        "category": category,
                        "name": error.get(t("error_name")),
                        "description": error.get(t("description")),
                        "implementation_guide": error.get(t("implementation_guide"), "")
                    })
        
        # Select random errors
        if all_errors:
            # If we have fewer errors than requested, return all
            if len(all_errors) <= count:
                return all_errors
            
            # Otherwise select random errors
            return random.sample(all_errors, count)
        
        return []
    
    def get_errors_for_llm(self, 
                 selected_categories: Dict[str, List[str]] = None, 
                 specific_errors: List[Dict[str, Any]] = None,
                 count: int = 4, 
                 difficulty: str = "medium") -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Get errors suitable for sending to the LLM for code generation.
        Can use either category-based selection or specific errors.
        
        Args:
            selected_categories: Dictionary with selected error categories
            specific_errors: List of specific errors to include
            count: Number of errors to select if using categories
            difficulty: Difficulty level to adjust error count
            
        Returns:
            Tuple of (list of error objects, list of problem descriptions)
        """       
        # Adjust count based on difficulty
        error_counts = {
            t("easy"): max(2, count - 2),
            t("medium"): count,
            t("hard"): count + 2
        }

        adjusted_count = error_counts.get(difficulty.lower(), count)
       
        # If specific errors are provided, use those
        if specific_errors and len(specific_errors) > 0:
            problem_descriptions = []
            selected_errors = []
            # Process each selected error to ensure it has all required fields
            for error in specific_errors:
                processed_error = error.copy()               
                name = processed_error.get(t("error_name_variable"), "Unknown")
                description = processed_error.get(t("description"), "")
                category = processed_error.get(t("category"), "")
                
                # Add implementation guide if available
                implementation_guide = self._get_implementation_guide(name, category)
                if implementation_guide:
                    processed_error[t("implementation_guide")] = implementation_guide
                
                # Create problem description
                problem_descriptions.append(f"{category}: {name} - {description}")
                selected_errors.append(processed_error)
            
            # If we don't have exactly the adjusted count, log a notice but proceed
            if len(selected_errors) != adjusted_count:
                print(f"Note: Using {len(selected_errors)} specific errors instead of adjusted count {adjusted_count}")
            return selected_errors, problem_descriptions
        
        # Otherwise use category-based selection
        elif selected_categories:          
            print(f"Selected Categories: {selected_categories}")
            # Check if any categories are actually selected
            java_error_categories = selected_categories.get("java_errors", [])
            print(f"Java Error Categories: {java_error_categories}")
        
            if not java_error_categories:
                print("WARNING: No categories specified, using defaults")
                selected_categories = {
                    "java_errors": ["LogicalErrors", "SyntaxErrors", "CodeQualityErrors"]
                }

            error_selection_ranges = {
                t("easy"): (1, 2),    # Easy: 1-2 errors per category
                t("medium"): (1, 3),  # Medium: 1-3 errors per category
                t("hard"): (1, 4)     # Hard: 1-4 errors per category
            }

            min_errors, max_errors = error_selection_ranges.get(
                difficulty.lower(), 
                (1, 2)  # Default to 1-2 if difficulty not recognized
            )
            
            # Collect errors from each selected category
            all_errors = []
          
            for category in selected_categories.get("java_errors", []):
                if category in self.java_errors:
                    # Use get_category_errors to get language-mapped errors
                    category_errors = self.get_category_errors(category)

                    # For each selected category, randomly select 1-2 errors
                    num_to_select = min(len(category_errors), random.randint(min_errors, max_errors))

                    if num_to_select > 0:
                        selected_from_category = random.sample(category_errors, num_to_select)
                        print(f"Selected {num_to_select} errors from Java error category '{category}'")                        
                        for error in selected_from_category:
                            all_errors.append({                                
                                t("category"): category,
                                t("error_name_variable"): error.get(t("error_name_variable")),
                                t("description"): error.get(t("description")),
                                t("implementation_guide"): error.get(t("implementation_guide"), "")
                            })                       
            # If we have more errors than needed, randomly select the required number
            if len(all_errors) > adjusted_count:
                print(f"Too many errors ({len(all_errors)}), selecting {adjusted_count} randomly")
                selected_errors = random.sample(all_errors, adjusted_count)
            else:
                print(f"Using all {len(all_errors)} errors from categories")
                selected_errors = all_errors
            
            # Format problem descriptions
            problem_descriptions = []
            for error in selected_errors:
                category = error.get(t("category"), "")                
                name = error.get(t("error_name_variable"), "Unknown")
                description = error.get(t("description"), "")

                problem_descriptions.append(f"{category} - {name}: {description}")

            
            return selected_errors, problem_descriptions
        
        # If no selection method was provided, return empty lists
        print("WARNING: No selection method provided, returning empty error list")
        return [], []
    
    def _get_implementation_guide(self, error_name: str, category: str) -> Optional[str]:
        """
        Get implementation guide for a specific error.
        
        Args:
            error_type: Type of error
            error_name: Name of the error
            category: Category of the error
            
        Returns:
            Implementation guide string or None if not found
        """
      
        if category in self.java_errors:
            for error in self.java_errors[category]:
                if error.get(t("error_name")) == error_name:
                    return error.get(t("implementation_guide"))
        return None

    def get_error_by_name(self, error_type: str, error_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific error by name.
        
        Args:
            error_type: Type of error ('java_error')
            error_name: Name of the error
            
        Returns:
            Error dictionary with added type and category, or None if not found
        """
        if error_type == "java_error":
            for category, errors in self.java_errors.items():
                for error in errors:
                    if error.get(t("error_name_variable")) == error_name:
                        return {                            
                            t("category"): category,
                            t("error_name_variable"): error.get(t("error_name_variable")),
                            t("description"): error.get(t("description"))
                        }
        return None