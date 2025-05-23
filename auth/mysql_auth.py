# auth/mysql_auth.py
"""
MySQL-based authentication for Java Peer Review Training System.
"""

import logging
import datetime
import hashlib
import uuid
from typing import Dict, Any, List, Optional
from db.mysql_connection import MySQLConnection
from auth.badge_manager import BadgeManager
from utils.language_utils import set_language, get_current_language, t

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MySQLAuthManager:
    """
    Manager for MySQL-based authentication and user management.
    """
    
    _instance = None
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super(MySQLAuthManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the MySQLAuthManager."""
        if self._initialized:
            return
            
        self.db = MySQLConnection()
        self._initialized = True
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    

    def update_tutorial_completion(self, user_id: str, completed: bool) -> Dict[str, Any]:
        """
        Update the tutorial completion status for a user.
        
        Args:
            user_id: User ID
            completed: True if tutorial is completed, False otherwise
            
        Returns:
            Dictionary with success status and any error messages
        """
        try:
            # Update tutorial completion status
            update_query = """
            UPDATE users 
            SET tutorial_completed = %s 
            WHERE uid = %s
            """
            
            affected_rows = self.db.execute_query(update_query, (completed, user_id))
            
            if affected_rows is not None and affected_rows > 0:
                logger.debug(f"Updated tutorial completion status for user {user_id} to {completed}")
                return {
                    "success": True,
                    "tutorial_completed": completed
                }
            else:
                logger.warning(f"No rows affected when updating tutorial completion for user {user_id}")
                return {
                    "success": False,
                    "error": "Failed to update tutorial completion status"
                }
                
        except Exception as e:
            logger.error(f"Error updating tutorial completion for user {user_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def register_user(self, email: str, password: str, display_name_en: str = None, display_name_zh: str = None,
                 level_name_en: str = None, 
                 level_name_zh: str = None) -> Dict[str, Any]:
        """Register a new user with multilingual support."""
        # Check if email is already in use
        check_query = "SELECT email FROM users WHERE email = %s"
        result = self.db.execute_query(check_query, (email,), fetch_one=True)
        
        if result:
            return {"success": False, "error": "Email already in use"}
        
        # Generate a unique user ID
        user_id = str(uuid.uuid4())
        
        # Hash the password
        hashed_password = self._hash_password(password)
            
        # If level names are not provided, get them from translation
        if not level_name_en or not level_name_zh:
            # Save current language
            current_lang = get_current_language()
            
            # Default level value
            default_level = "basic"
            
            # Get English level name
            if not level_name_en:
                set_language("en")
                level_name_en = t(default_level)
            
            # Get Chinese level name
            if not level_name_zh:
                set_language("zh")
                level_name_zh = t(default_level)
            
            # Restore original language
            set_language(current_lang)
        
        # Prepare the SQL query based on existing columns
        columns = ["uid", "email", "display_name_en", "display_name_zh", "password", "level_name_en", "level_name_zh"]
        values = [user_id, email, display_name_en, display_name_zh, hashed_password, level_name_en, level_name_zh]
        
        # Create the SQL query
        columns_str = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(values))
        insert_query = f"""
            INSERT INTO users 
            ({columns_str}) 
            VALUES ({placeholders})
        """
        
        # Execute the query
        affected_rows = self.db.execute_query(insert_query, tuple(values))
        
        if affected_rows:
            logger.debug(f"Registered new user: {email} (ID: {user_id})")
            return {
                "success": True,
                "user_id": user_id,
                "email": email,
                "display_name_en": display_name_en,
                "display_name_zh": display_name_zh,
                "level_name_en": level_name_en,
                "level_name_zh": level_name_zh
            }
        else:
            return {"success": False, "error": "Error saving user data"}
    
    def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user with email and password.
        Updated to include tutorial completion status.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Dictionary with authentication result
        """
        try:
            # Get user by email with tutorial completion status
            query = """
            SELECT uid, email, password, display_name_en, display_name_zh, 
                level_name_en, level_name_zh,
                reviews_completed, score, tutorial_completed
            FROM users 
            WHERE email = %s
            """
            
            user_data = self.db.execute_query(query, (email,), fetch_one=True)
            
            if not user_data:
                logger.warning(f"Authentication failed: User not found for email {email}")
                return {
                    "success": False,
                    "error": "Invalid email or password"
                }
            
           
            return {
                    "success": True,
                    "user_id": user_data["uid"],
                    "email": user_data["email"],
                    "display_name_en": user_data["display_name_en"],
                    "display_name_zh": user_data["display_name_zh"],
                    "level_name_en": user_data["level_name_en"],
                    "level_name_zh": user_data["level_name_zh"],                    
                    "reviews_completed": user_data["reviews_completed"],
                    "score": user_data["score"],
                    "tutorial_completed": user_data["tutorial_completed"]
                }
            
                
        except Exception as e:
            logger.error(f"Error during authentication for email {email}: {str(e)}")
            return {
                "success": False,
                "error": "Authentication failed due to system error"
            }
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get complete user profile including tutorial completion status.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with user profile data
        """
        try:
            # Get user profile with tutorial completion status
            query = """
            SELECT uid, email, display_name_en, display_name_zh, 
                level_name_en, level_name_zh,
                reviews_completed, score, tutorial_completed,
                created_at, last_activity, consecutive_days, total_points
            FROM users 
            WHERE uid = %s
            """
            
            user_data = self.db.execute_query(query, (user_id,), fetch_one=True)
            
            if user_data:
                return {
                    "success": True,
                    "user_id": user_data["uid"],
                    "email": user_data["email"],
                    "display_name_en": user_data["display_name_en"],
                    "display_name_zh": user_data["display_name_zh"],
                    "level_name_en": user_data["level_name_en"],
                    "level_name_zh": user_data["level_name_zh"],                   
                    "reviews_completed": user_data["reviews_completed"],
                    "score": user_data["score"],
                    "tutorial_completed": user_data["tutorial_completed"],
                    "created_at": user_data["created_at"],
                    "last_activity": user_data["last_activity"],
                    "consecutive_days": user_data["consecutive_days"],
                    "total_points": user_data["total_points"]
                }
            else:
                return {
                    "success": False,
                    "error": "User not found"
                }
                
        except Exception as e:
            logger.error(f"Error getting user profile for {user_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a user's profile."""
        # Ensure we don't update sensitive fields
        safe_updates = {k: v for k, v in updates.items() if k in [
            "display_name_en", "display_name_zh", 
            "level_name_en", "level_name_zh", "reviews_completed"
        ]}
        
        if not safe_updates:
            return {"success": True}  # Nothing to update
        
        # Build the UPDATE query dynamically
        set_clauses = []
        values = []
        
        for key, value in safe_updates.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)
        
        # Add the user_id to the values
        values.append(user_id)
        
        query = f"""
            UPDATE users 
            SET {', '.join(set_clauses)} 
            WHERE uid = %s
        """
        
        affected_rows = self.db.execute_query(query, tuple(values))
        
        if affected_rows is not None:
            return {"success": True}
        else:
            return {"success": False, "error": "Error updating user data"}
    
    def update_review_stats(self, user_id: str, accuracy: float, score: int = 0) -> Dict[str, Any]:
        """
        Update a user's review statistics with score and automatically upgrade user level based on score.
        Now also updates badges and point rewards.
            
        Args:
            user_id: The user's ID
            accuracy: The accuracy of the review (0-100 percentage)
            score: Number of errors detected in the review
                
        Returns:
            Dict containing success status and updated statistics
        """
        # Validate connection
        if not self.db:
            logger.error("Database connection not initialized")
            return {"success": False, "error": "Database connection not initialized"}
        
        # Get current stats
        query = """
            SELECT reviews_completed, score, level_name_en, level_name_zh 
            FROM users 
            WHERE uid = %s
        """
        
        logger.debug(f"Executing query to get current stats for user {user_id}")
        result = self.db.execute_query(query, (user_id,), fetch_one=True)
        
        if not result:
            logger.error(f"User {user_id} not found in database")
            return {"success": False, "error": "User not found"}
        
        # Calculate new stats
        current_reviews = result["reviews_completed"]
        current_score = result.get("score", 0)
        current_level_en = result.get("level_name_en", "basic")  # Default to basic if not set
        current_level_zh = result.get("level_name_zh", "基礎")   # Default to Chinese equivalent of basic
        
        new_reviews = current_reviews + 1
        new_score = current_score + score
        
        # Determine if level upgrade is needed based on new score
        new_level_en = current_level_en
        new_level_zh = current_level_zh
        
        if new_score > 200:
            # Senior level
            if current_level_en != "Senior" and current_level_en != "senior":
                new_level_en = "Senior"
                new_level_zh = "高級"
        elif new_score > 100 and (current_level_en == "Basic" or current_level_en == "basic"):
            # Medium level
            new_level_en = "Medium"
            new_level_zh = "中級"
        
        # Only update level if it changed
        level_changed = (new_level_en != current_level_en)
        
        # Update the database
        if level_changed:
            update_query = """
                UPDATE users 
                SET reviews_completed = %s, score = %s, 
                level_name_en = %s, level_name_zh = %s 
                WHERE uid = %s
            """
            
            affected_rows = self.db.execute_query(
                update_query, 
                (new_reviews, new_score, new_level_en, new_level_zh, user_id)
            )
        else:
            update_query = """
                UPDATE users 
                SET reviews_completed = %s, score = %s 
                WHERE uid = %s
            """
            
            affected_rows = self.db.execute_query(
                update_query, 
                (new_reviews, new_score, user_id)
            )
        
        if affected_rows is not None and affected_rows >= 0:
            result = {
                "success": True,
                "reviews_completed": new_reviews,
                "score": new_score
            }
            
            # Add level information if it changed
            if level_changed:
                result["level_changed"] = True
                result["old_level"] = current_level_en
                result["new_level"] = new_level_en
            
            # Initialize badge manager
            badge_manager = BadgeManager()

            # Award points for the review
            base_points = 10  # Base points for completing a review
            accuracy_bonus = int(accuracy / 10)  # 0-10 bonus points based on accuracy
            total_points = base_points + accuracy_bonus + score  # Add points for each error found
            
            badge_manager.award_points(
                user_id, 
                total_points,
                "review_completion",
                f"Review completion with {accuracy:.1f}% accuracy, found {score} errors"
            )
            
            # Update consecutive days
            badge_manager.update_consecutive_days(user_id)
            
            # Check for review completion badges
            all_errors_found = accuracy >= 100.0
            badge_manager.check_review_completion_badges(user_id, new_reviews, all_errors_found)
            
            return result
        else:
            logger.error("Database update failed or returned None")
            return {"success": False, "error": "Error updating review stats"}
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get a list of all users with proper language support."""
        # Get current language for field selection
        current_lang = get_current_language()
        
        query = """
            SELECT uid, email, display_name_en, display_name_zh,
            level_name_en, level_name_zh,
            created_at, reviews_completed, total_points
            FROM users
        """
        
        users = self.db.execute_query(query)
        
        if users is None:
            return []
        
        # Process each user to select language-appropriate fields
        for user in users:
            # Choose display name based on current language
            display_name = user.get(f"display_name_{current_lang}") if current_lang in ["en", "zh"] else user.get("display_name_en", "")
            user["display_name"] = display_name
            
            # Choose level based on current language
            level_name = user.get(f"level_name_{current_lang}") if current_lang in ["en", "zh"] else user.get("level_name_en", "Basic")
            user["level"] = level_name
            
            # Rename uid to user_id for consistency with the rest of the app
            user["user_id"] = user.pop("uid")
        
        return users