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
from utils.language_utils import get_current_language

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
        print('self.current_language', self.current_language)
        # Determine file path based on language
        if java_errors_path is None:
            self.java_errors_path = f"{self.current_language}_Java_code_review_errors.json"
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
        
        # If loading fails, try loading the English version as a fallback
        if not java_loaded and self.current_language != "en":
            logger.warning(f"Failed to load {self.current_language} Java errors, trying English version")
            old_path = self.java_errors_path
            self.java_errors_path = "en_Java_code_review_errors.json"
            java_loaded = self._load_java_errors()
            if not java_loaded:
                logger.warning(f"Failed to load both {old_path} and {self.java_errors_path}")
        
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
            # Try different paths to find the Java errors file
            file_paths = self._get_potential_file_paths(self.java_errors_path)
            
            for file_path in file_paths:
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            self.java_errors = json.load(file)
                            self.java_error_categories = list(self.java_errors.keys())
                            logger.info(f"Loaded Java errors from {file_path} with {len(self.java_error_categories)} categories")
                            return True
                    except Exception as file_error:
                        logger.error(f"Error reading or parsing file {file_path}: {str(file_error)}")
                        continue  # Try the next path
            
            # If we get here, none of the paths worked
            logger.warning(f"Could not find or load Java errors file: {self.java_errors_path}")
            return False
                
        except Exception as e:
            logger.error(f"Error loading Java errors: {str(e)}")
            return False
    
    def _get_potential_file_paths(self, file_name: str) -> List[str]:
        """
        Get potential file paths to look for the error files.
        
        Args:
            file_name: Base file name to search for
            
        Returns:
            List of potential file paths
        """
        # Get the current directory
        current_dir = os.path.dirname(os.path.realpath(__file__))
        
        # Get the parent directory (project root)
        parent_dir = os.path.dirname(current_dir)
        
        # Try various potential locations
        return [
            file_name,  # Direct file name (if it's in the working directory)
            os.path.join(current_dir, file_name),  # In the same directory as this file
            os.path.join(parent_dir, file_name),  # In the parent directory (project root)
            os.path.join(parent_dir, "data", file_name),  # In a data subdirectory
            os.path.join(parent_dir, "resources", file_name),  # In a resources subdirectory
            os.path.join(parent_dir, "assets", file_name),  # In an assets subdirectory
            # Additional paths
            os.path.join(os.getcwd(), file_name),  # Current working directory 
            os.path.join(os.getcwd(), "data", file_name),  # Data folder in current working directory
            os.path.join(os.path.expanduser("~"), file_name),  # User's home directory
        ]
    
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
            errors = self.java_errors[category_name]
            
            # Check if we need field name mapping (for non-English languages)
            needs_mapping = False
            if errors and isinstance(errors, list) and len(errors) > 0:
                # Check the first error to see if it uses localized field names
                first_error = errors[0]
                if '錯誤名稱' in first_error and 'error_name' not in first_error:
                    needs_mapping = True
            
            # Return the original list if no mapping needed
            if not needs_mapping:
                return errors
            
            # Map field names for each error
            mapped_errors = []
            for error in errors:
                mapped_error = {}
                
                # Map Chinese field names to English field names
                if '錯誤名稱' in error:
                    mapped_error['error_name'] = error['錯誤名稱']
                if '描述' in error:
                    mapped_error['description'] = error['描述']
                if '實作範例' in error:
                    mapped_error['implementation_guide'] = error['實作範例']
                    
                # Add any other fields directly
                for key, value in error.items():
                    if key not in ['錯誤名稱', '描述', '實作範例']:
                        mapped_error[key] = value
                        
                mapped_errors.append(mapped_error)
                
            return mapped_errors
                
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
                    if error.get("error_name") == error_name:
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
                        "name": error["error_name"],
                        "description": error["description"],
                        "implementation_guide": error.get("implementation_guide", "")
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
            "easy": max(2, count - 2),
            "medium": count,
            "hard": count + 2
        }
        adjusted_count = error_counts.get(difficulty.lower(), count)
        
        # If specific errors are provided, use those
        if specific_errors and len(specific_errors) > 0:
            
            # Format problem descriptions
            problem_descriptions = []
            selected_errors = []
            
            # Process each selected error to ensure it has all required fields
            for error in specific_errors:
                processed_error = error.copy()
                error_type = processed_error.get("type", "Unknown")
                name = processed_error.get("name", "Unknown")
                description = processed_error.get("description", "")
                category = processed_error.get("category", "")
                
                # Add implementation guide if available
                implementation_guide = self._get_implementation_guide(error_type, name, category)
                if implementation_guide:
                    processed_error["implementation_guide"] = implementation_guide
                
                # Create problem description
                problem_descriptions.append(f"Java Error - {name}: {description} (Category: {category})")
                
                selected_errors.append(processed_error)
            
            # If we don't have exactly the adjusted count, log a notice but proceed
            if len(selected_errors) != adjusted_count:
                print(f"Note: Using {len(selected_errors)} specific errors instead of adjusted count {adjusted_count}")
            
            return selected_errors, problem_descriptions
        
        # Otherwise use category-based selection
        elif selected_categories:
            print("Selection Method: Using category-based selection")
            print(f"Selected Categories: {selected_categories}")
            
            # Check if any categories are actually selected
            java_error_categories = selected_categories.get("java_errors", [])
            
            print(f"Java Error Categories: {java_error_categories}")
            
            if not java_error_categories:
                # Use default categories if none specified
                print("WARNING: No categories specified, using defaults")
                selected_categories = {
                    "java_errors": ["LogicalErrors", "SyntaxErrors", "CodeQualityErrors"]
                }
            
            # Collect errors from each selected category
            all_errors = []
            
            for category in selected_categories.get("java_errors", []):
                if category in self.java_errors:
                    # Use get_category_errors to get language-mapped errors
                    category_errors = self.get_category_errors(category)
                    # For each selected category, randomly select 1-2 errors
                    num_to_select = min(len(category_errors), random.randint(1, 2))
                    if num_to_select > 0:
                        selected_from_category = random.sample(category_errors, num_to_select)
                        print(f"Selected {num_to_select} errors from Java error category '{category}'")
                        for error in selected_from_category:
                            all_errors.append({
                                "type": "java_error",
                                "category": category,
                                "name": error["error_name"],  # Now this will work with any language
                                "description": error["description"],
                                "implementation_guide": error.get("implementation_guide", "")
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
                error_type = error.get("type", "Unknown")
                name = error.get("name", "Unknown")
                description = error.get("description", "")
                category = error.get("category", "")
                
                problem_descriptions.append(f"Java Error - {name}: {description} (Category: {category})")
            
            # Print final selected errors
            print("\n--- FINAL SELECTED ERRORS ---")
            for i, error in enumerate(selected_errors, 1):
                print(f"  {i}. {error.get('type', 'Unknown')} - {error.get('name', 'Unknown')} ({error.get('category', 'Unknown')})")
            print("======================================")
            
            return selected_errors, problem_descriptions
        
        # If no selection method was provided, return empty lists
        print("WARNING: No selection method provided, returning empty error list")
        return [], []
    
    def _get_implementation_guide(self, error_type: str, error_name: str, category: str) -> Optional[str]:
        """
        Get implementation guide for a specific error.
        
        Args:
            error_type: Type of error
            error_name: Name of the error
            category: Category of the error
            
        Returns:
            Implementation guide string or None if not found
        """
        if error_type == "java_error":
            if category in self.java_errors:
                for error in self.java_errors[category]:
                    if error.get("error_name") == error_name:
                        return error.get("implementation_guide")
        return None

    def search_errors(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Search for errors containing the search term.
        
        Args:
            search_term: Term to search for in error names and descriptions
            
        Returns:
            List of matching errors with type and category information
        """
        results = []
        search_term = search_term.lower()
        
        # Search java errors
        for category in self.java_errors:
            for error in self.java_errors[category]:
                name = error.get("error_name", "").lower()
                description = error.get("description", "").lower()
                
                if search_term in name or search_term in description:
                    results.append({
                        "type": "java_error",
                        "category": category,
                        "name": error["error_name"],
                        "description": error["description"]
                    })
        
        return results
    
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
                    if error.get("error_name") == error_name:
                        return {
                            "type": "java_error",
                            "category": category,
                            "name": error["error_name"],
                            "description": error["description"]
                        }
        return None