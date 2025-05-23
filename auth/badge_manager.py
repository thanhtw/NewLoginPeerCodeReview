"""
Badge and rewards manager for the Java Peer Review Training System.
"""

import logging
import datetime
import uuid
from typing import Dict, Any, List, Optional, Tuple
from db.mysql_connection import MySQLConnection
from utils.language_utils import get_current_language, t

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BadgeManager:
    """Manager for badges, points and user progress tracking."""
    
    _instance = None
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super(BadgeManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the BadgeManager."""
        if self._initialized:
            return
            
        self.db = MySQLConnection()
        self._initialized = True
        # Get current language on initialization and update when needed
        self.current_language = get_current_language()
    

    def award_points(self, user_id: str, points: int, activity_type: str, details: str = None) -> Dict[str, Any]:
        """
        Award points to a user and log the activity.
        
        Args:
            user_id: The user's ID
            points: Number of points to award
            activity_type: Type of activity (e.g., review_completion, error_found)
            details: Optional details about the activity
            
        Returns:
            Dict containing success status and updated point total
        """
        if not user_id:
            return {"success": False, "error": t("invalid_user_id")}
        
        # Update current language whenever a method is called
        self.current_language = get_current_language()
        
        try:
            # First, update the user's total points
            update_query = """
                UPDATE users 
                SET total_points = total_points + %s 
                WHERE uid = %s
            """
            
            self.db.execute_query(update_query, (points, user_id))
           
            log_query = """
                    INSERT INTO activity_log 
                    (user_id, activity_type, points, details_en, details_zh) 
                    VALUES (%s, %s, %s, %s, %s)
                """
            self.db.execute_query(log_query, (user_id, activity_type, points, details, details))
         
            
            # Get the updated total points
            points_query = "SELECT total_points FROM users WHERE uid = %s"
            result = self.db.execute_query(points_query, (user_id,), fetch_one=True)
            
            if result:
                total_points = result.get("total_points", 0)
                
                # Check for any point-based badges
                self._check_point_badges(user_id, total_points)
                
                return {"success": True, "total_points": total_points}
            else:
                return {"success": False, "error": t("user_not_found")}
                
        except Exception as e:
            logger.error(f"{t('error_awarding_points')}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def award_badge(self, user_id: str, badge_id: str) -> Dict[str, Any]:
        """
        Award a badge to a user.
        
        Args:
            user_id: The user's ID
            badge_id: The badge ID to award
            
        Returns:
            Dict containing success status and badge information
        """
        if not user_id or not badge_id:
            return {"success": False, "error": t("invalid_user_id_or_badge_id")}
        
        # Update current language
        self.current_language = get_current_language()
        
        try:
            # Check if the badge exists
            # Use language-specific field based on current language
            name_field = f"name_{self.current_language}" if self.current_language == "en" or self.current_language == "zh" else "name_en"
            desc_field = f"description_{self.current_language}" if self.current_language == "en" or self.current_language == "zh" else "description_en"
            
            badge_query = f"SELECT badge_id, {name_field} as name, {desc_field} as description, points FROM badges WHERE badge_id = %s"
            badge = self.db.execute_query(badge_query, (badge_id,), fetch_one=True)
            
            if not badge:
                return {"success": False, "error": t("badge_not_found")}
            
            # Check if the user already has this badge
            has_badge_query = """
                SELECT * FROM user_badges 
                WHERE user_id = %s AND badge_id = %s
            """
            
            existing = self.db.execute_query(has_badge_query, (user_id, badge_id), fetch_one=True)
            
            if existing:
                return {"success": True, "badge": badge, "message": t("badge_already_awarded")}
            
            # Award the badge
            award_query = """
                INSERT INTO user_badges 
                (user_id, badge_id) 
                VALUES (%s, %s)
            """
            
            self.db.execute_query(award_query, (user_id, badge_id))
            
            # Award points for earning the badge
            badge_points = badge.get("points", 10)
            self.award_points(
                user_id, 
                badge_points,
                "badge_earned",
                f"{t('earned_badge')}: {badge.get('name')}"
            )
            
            return {
                "success": True, 
                "badge": badge,
                "message": t("badge_awarded_successfully").format(badge_name=badge.get('name'))
            }
                
        except Exception as e:
            logger.error(f"{t('error_awarding_badge')}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_user_badges(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all badges earned by a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of badge dictionaries with badge details
        """
        if not user_id:
            return []
        
        # Update current language
        self.current_language = get_current_language()
        
        try:
            # Use language-specific field based on current language
            name_field = f"name_{self.current_language}" if self.current_language == "en" or self.current_language == "zh" else "name_en"
            desc_field = f"description_{self.current_language}" if self.current_language == "en" or self.current_language == "zh" else "description_en"
            
            query = f"""
                SELECT b.badge_id, b.{name_field} as name, b.{desc_field} as description, 
                       b.icon, b.category, b.difficulty, b.points, ub.awarded_at
                FROM badges b
                JOIN user_badges ub ON b.badge_id = ub.badge_id
                WHERE ub.user_id = %s
                ORDER BY ub.awarded_at DESC
            """
            
            badges = self.db.execute_query(query, (user_id,))
            return badges or []
                
        except Exception as e:
            logger.error(f"{t('error_getting_user_badges')}: {str(e)}")
            return []
    
    def update_category_stats(self, user_id: str, category: str, 
                           encountered: int = 0, identified: int = 0) -> Dict[str, Any]:
        """
        Update a user's error category statistics.
        
        Args:
            user_id: The user's ID
            category: The error category
            encountered: Number of errors encountered
            identified: Number of errors identified
            
        Returns:
            Dict containing success status and updated statistics
        """
        if not user_id or not category:
            return {"success": False, "error": t("invalid_user_id_or_category")}
        
        try:
            # Check if the stats exist
            check_query = """
                SELECT * FROM error_category_stats 
                WHERE user_id = %s AND category = %s
            """
            
            stats = self.db.execute_query(check_query, (user_id, category), fetch_one=True)
            
            if stats:
                # Update existing stats
                update_query = """
                    UPDATE error_category_stats 
                    SET encountered = encountered + %s,
                        identified = identified + %s,
                        mastery_level = CASE 
                            WHEN (encountered + %s) > 0 THEN (identified + %s) / (encountered + %s) 
                            ELSE 0 
                        END
                    WHERE user_id = %s AND category = %s
                """
                
                self.db.execute_query(
                    update_query, 
                    (encountered, identified, encountered, identified, encountered, user_id, category)
                )
            else:
                # Insert new stats
                insert_query = """
                    INSERT INTO error_category_stats 
                    (user_id, category, encountered, identified, mastery_level) 
                    VALUES (%s, %s, %s, %s, %s)
                """
                
                mastery = identified / encountered if encountered > 0 else 0
                self.db.execute_query(insert_query, (user_id, category, encountered, identified, mastery))
            
            # Get the updated stats
            updated_query = """
                SELECT * FROM error_category_stats 
                WHERE user_id = %s AND category = %s
            """
            
            updated_stats = self.db.execute_query(updated_query, (user_id, category), fetch_one=True)
            
            # Check for category mastery badges
            self._check_category_mastery(user_id, category, updated_stats)
            
            return {"success": True, "stats": updated_stats}
                
        except Exception as e:
            logger.error(f"{t('error_updating_category_stats')}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_category_stats(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all category statistics for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of category statistics
        """
        if not user_id:
            return []
        
        try:
            query = """
                SELECT * FROM error_category_stats 
                WHERE user_id = %s
                ORDER BY mastery_level DESC
            """
            
            stats = self.db.execute_query(query, (user_id,))
            return stats or []
                
        except Exception as e:
            logger.error(f"{t('error_getting_category_stats')}: {str(e)}")
            return []
    
    def update_consecutive_days(self, user_id: str) -> Dict[str, Any]:
        """
        Update a user's consecutive days of activity.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Dict containing success status and updated statistics
        """
        if not user_id:
            return {"success": False, "error": t("invalid_user_id")}
        
        try:
            # Get current last_activity and consecutive_days
            query = """
                SELECT last_activity, consecutive_days 
                FROM users 
                WHERE uid = %s
            """
            
            result = self.db.execute_query(query, (user_id,), fetch_one=True)
            
            if not result:
                return {"success": False, "error": t("user_not_found")}
            
            today = datetime.date.today()
            last_activity = result.get("last_activity")
            consecutive_days = result.get("consecutive_days", 0)
            
            # Calculate new consecutive days
            new_consecutive_days = consecutive_days
            
            if not last_activity:
                # First activity
                new_consecutive_days = 1
            elif last_activity == today:
                # Already logged today, no change
                pass
            elif last_activity == today - datetime.timedelta(days=1):
                # Activity on consecutive day
                new_consecutive_days += 1
            else:
                # Break in streak
                new_consecutive_days = 1
            
            # Update user record
            update_query = """
                UPDATE users 
                SET last_activity = %s,
                    consecutive_days = %s
                WHERE uid = %s
            """
            
            self.db.execute_query(update_query, (today, new_consecutive_days, user_id))
            
            # Check for consistency badges
            if new_consecutive_days >= 5:
                self.award_badge(user_id, "consistency-champ")
            
            return {
                "success": True, 
                "consecutive_days": new_consecutive_days
            }
                
        except Exception as e:
            logger.error(f"{t('error_updating_consecutive_days')}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the user leaderboard by total points with multilingual support.
        
        Args:
            limit: Maximum number of users to return
            
        Returns:
            List of user dictionaries with score and ranking
        """
        try:
            # Update current language
            self.current_language = get_current_language()
            
            # Set display name and level fields based on language
            display_name_field = f"display_name_{self.current_language}" if self.current_language in ["en", "zh"] else "display_name_en"
            level_field = f"level_name_{self.current_language}" if self.current_language in ["en", "zh"] else "level_name_en"
            
            
            # Build query with appropriate fields
            query = f"""
                SELECT uid, {display_name_field} as display_name, total_points, {level_field} as level,
                    (SELECT COUNT(*) FROM user_badges WHERE user_id = uid) AS badge_count
                FROM users
                ORDER BY total_points DESC
                LIMIT %s
            """
            
            leaders = self.db.execute_query(query, (limit,))
            
            # Add rank
            for i, leader in enumerate(leaders, 1):
                leader["rank"] = i
                    
            return leaders or []
                
        except Exception as e:
            logger.error(f"{t('error_getting_leaderboard')}: {str(e)}")
            return []
    
    def get_user_rank(self, user_id: str) -> Dict[str, Any]:
        """
        Get a user's rank on the leaderboard.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Dict containing rank and total users
        """
        if not user_id:
            return {"rank": 0, "total_users": 0}
        
        try:
            # Get the user's points
            points_query = "SELECT total_points FROM users WHERE uid = %s"
            result = self.db.execute_query(points_query, (user_id,), fetch_one=True)
            
            if not result:
                return {"rank": 0, "total_users": 0}
            
            points = result.get("total_points", 0)
            
            # Get the user's rank
            rank_query = """
                SELECT COUNT(*) AS rank_pos
                FROM users
                WHERE total_points > %s
            """
            
            rank_result = self.db.execute_query(rank_query, (points,), fetch_one=True)
            
            # Get total users
            total_query = "SELECT COUNT(*) AS total FROM users"
            total_result = self.db.execute_query(total_query, fetch_one=True)
            
            return {
                "rank": rank_result.get("rank_pos", 0) + 1,
                "total_users": total_result.get("total", 0)
            }
                
        except Exception as e:
            logger.error(f"{t('error_getting_user_rank')}: {str(e)}")
            return {"rank": 0, "total_users": 0}
    
    def _check_point_badges(self, user_id: str, total_points: int) -> None:
        """
        Check if a user qualifies for any point-based badges.
        
        Args:
            user_id: The user's ID
            total_points: The user's total points
        """
        # Rising Star badge - 500 points in first week
        if total_points >= 500:
            # Check when the user joined
            query = "SELECT created_at FROM users WHERE uid = %s"
            result = self.db.execute_query(query, (user_id,), fetch_one=True)
            
            if result:
                created_at = result.get("created_at")
                now = datetime.datetime.now()
                
                if created_at and (now - created_at).days <= 7:
                    self.award_badge(user_id, "rising-star")
    
    def _check_category_mastery(self, user_id: str, category: str, stats: Dict[str, Any]) -> None:
        """
        Check if a user qualifies for category mastery badges.
        
        Args:
            user_id: The user's ID
            category: The error category
            stats: Category statistics
        """
        # Required mastery level and minimum encounters to earn the badge
        MASTERY_THRESHOLD = 0.85
        MIN_ENCOUNTERS = 10
        
        if stats and stats.get("mastery_level", 0) >= MASTERY_THRESHOLD and stats.get("encountered", 0) >= MIN_ENCOUNTERS:
            # Update current language before mapping categories
            self.current_language = get_current_language()
            
            # Map categories to badge IDs - support both English and Chinese categories
            # Categories are not translated with t() because they need to match exactly what's in the database
            category_badges = {
                t("logical"): "logic-guru",
                "Logical": "logic-guru",
                "邏輯錯誤": "logic-guru",  # Chinese equivalent
                t("syntax"): "syntax-specialist",
                "Syntax": "syntax-specialist",
                "語法錯誤": "syntax-specialist",  # Chinese equivalent
                t("code_quality"): "quality-inspector",
                "Code Quality": "quality-inspector",
                "程式碼品質": "quality-inspector",  # Chinese equivalent
                t("standard_violation"): "standards-expert",
                "Standard Violation": "standards-expert",
                "標準違規": "standards-expert",  # Chinese equivalent
                t("java_specific"): "java-maven",
                "Java Specific": "java-maven",
                "Java 特定錯誤": "java-maven"  # Chinese equivalent
            }
            
            # Award the appropriate badge if available
            badge_id = category_badges.get(category)
            if badge_id:
                self.award_badge(user_id, badge_id)
            
        # Check for "Full Spectrum" badge - at least one error in each category
        query = """
            SELECT COUNT(DISTINCT category) AS category_count
            FROM error_category_stats
            WHERE user_id = %s AND identified > 0
        """
        
        result = self.db.execute_query(query, (user_id,), fetch_one=True)
        
        if result and result.get("category_count", 0) >= 5:  # Assuming 5 main categories
            self.award_badge(user_id, "full-spectrum")
    
    def check_review_completion_badges(self, user_id: str, reviews_completed: int, 
                                    all_errors_found: bool) -> None:
        """
        Check if a user qualifies for review completion badges.
        
        Args:
            user_id: The user's ID
            reviews_completed: Number of reviews completed
            all_errors_found: Whether all errors were found in the review
        """
        # Review progression badges
        if reviews_completed >= 5:
            self.award_badge(user_id, "reviewer-novice")
        
        if reviews_completed >= 25:
            self.award_badge(user_id, "reviewer-adept")
        
        if reviews_completed >= 50:
            self.award_badge(user_id, "reviewer-master")
        
        # Bug Hunter badge - find all errors in at least 5 reviews
        if all_errors_found:
            # Count how many perfect reviews the user has
            query = """
                SELECT COUNT(*) AS perfect_count
                FROM activity_log
                WHERE user_id = %s AND activity_type = 'perfect_review'
            """
            
            result = self.db.execute_query(query, (user_id,), fetch_one=True)
            
            if result and result.get("perfect_count", 0) >= 5:
                self.award_badge(user_id, "bug-hunter")            
          
                self.db.execute_query(
                    "INSERT INTO activity_log (user_id, activity_type, points, details_en, details_zh) VALUES (%s, %s, %s, %s, %s)",
                    (user_id, "perfect_review", 0, t("completed_perfect_review"), t("completed_perfect_review"))
                )
          
            
            # Perfectionist badge - 3 consecutive perfect reviews
            query = """
                SELECT activity_type
                FROM activity_log
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 3
            """
            
            result = self.db.execute_query(query, (user_id,))
            
            if result and len(result) >= 3:
                all_perfect = all(r.get("activity_type") == "perfect_review" for r in result)
                if all_perfect:
                    self.award_badge(user_id, "perfectionist")

    def get_leaderboard_with_badges(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the user leaderboard with badge icons for display.
        
        Args:
            limit: Maximum number of users to return
            
        Returns:
            List of user dictionaries with badge icons and ranking
        """
        try:
            # Update current language
            self.current_language = get_current_language()
            
            # Set display name and level fields based on language
            display_name_field = f"display_name_{self.current_language}" if self.current_language in ["en", "zh"] else "display_name_en"
            level_field = f"level_name_{self.current_language}" if self.current_language in ["en", "zh"] else "level_name_en"
            
            # Build query with appropriate fields
            query = f"""
                SELECT uid, {display_name_field} as display_name, total_points, {level_field} as level,
                    (SELECT COUNT(*) FROM user_badges WHERE user_id = uid) AS badge_count
                FROM users
                WHERE total_points > 0
                ORDER BY total_points DESC
                LIMIT %s
            """
            
            leaders = self.db.execute_query(query, (limit,))
            
            if not leaders:
                return []
            
            # Add rank and get top badges for each user
            for i, leader in enumerate(leaders, 1):
                leader["rank"] = i
                
                # Get top 3 badges for this user
                badge_query = f"""
                    SELECT b.icon, b.{f"name_{self.current_language}" if self.current_language in ["en", "zh"] else "name_en"} as name,
                        b.category, b.difficulty
                    FROM badges b
                    JOIN user_badges ub ON b.badge_id = ub.badge_id
                    WHERE ub.user_id = %s
                    ORDER BY 
                        CASE b.difficulty 
                            WHEN 'hard' THEN 3 
                            WHEN 'medium' THEN 2 
                            WHEN 'easy' THEN 1 
                            ELSE 0 
                        END DESC,
                        ub.awarded_at DESC
                    LIMIT 3
                """
                
                badges = self.db.execute_query(badge_query, (leader["uid"],))
                leader["top_badges"] = badges or []
                    
            return leaders
                
        except Exception as e:
            logger.error(f"{t('error_getting_leaderboard')}: {str(e)}")
            return []