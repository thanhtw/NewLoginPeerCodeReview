import logging
from db.mysql_connection import MySQLConnection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_database_schema():
    """Apply schema updates to add badge and enhanced statistics support."""
    db = MySQLConnection()
    
    # Create badges table
    badges_table = """
    CREATE TABLE IF NOT EXISTS badges (
        badge_id VARCHAR(36) PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        description TEXT NOT NULL,
        icon VARCHAR(50) NOT NULL,
        category VARCHAR(50) NOT NULL,
        difficulty ENUM('easy', 'medium', 'hard') DEFAULT 'medium',
        points INT DEFAULT 10,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    # Create user_badges table
    user_badges_table = """
    CREATE TABLE IF NOT EXISTS user_badges (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id VARCHAR(36) NOT NULL,
        badge_id VARCHAR(36) NOT NULL,
        awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(uid),
        FOREIGN KEY (badge_id) REFERENCES badges(badge_id),
        UNIQUE KEY (user_id, badge_id)
    )
    """
    
    # Create error_category_stats table
    error_category_stats_table = """
    CREATE TABLE IF NOT EXISTS error_category_stats (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id VARCHAR(36) NOT NULL,
        category VARCHAR(50) NOT NULL,
        encountered INT DEFAULT 0,
        identified INT DEFAULT 0,
        mastery_level FLOAT DEFAULT 0.0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(uid),
        UNIQUE KEY (user_id, category)
    )
    """
    
    # Create activity_log table for detailed point history
    activity_log_table = """
    CREATE TABLE IF NOT EXISTS activity_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id VARCHAR(36) NOT NULL,
        activity_type VARCHAR(50) NOT NULL,
        points INT NOT NULL,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(uid)
    )
    """
    
    # Update users table to add last_activity field for tracking consecutive days
    users_table_update = """
    ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS last_activity DATE DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS consecutive_days INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_points INT DEFAULT 0
    """
    
    # Execute all schema updates
    try:
        db.execute_query(badges_table)
        db.execute_query(user_badges_table)
        db.execute_query(error_category_stats_table)
        db.execute_query(activity_log_table)
        db.execute_query(users_table_update)
        logger.info("Database schema updated successfully")
        
        # Insert default badges
        insert_default_badges(db)
        
        return True
    except Exception as e:
        logger.error(f"Error updating database schema: {str(e)}")
        return False

def insert_default_badges(db):
    """Insert default badges into the badges table."""
    # Delete existing badges to avoid duplicates
    db.execute_query("DELETE FROM badges")
    
    # Define default badges
    default_badges = [
        # Achievement badges
        ("bug-hunter", "Bug Hunter", "Found all errors in at least 5 reviews", "🐞", "achievement", "medium", 50),
        ("perfectionist", "Perfectionist", "Achieved 100% accuracy in 3 consecutive reviews", "✨", "achievement", "hard", 100),
        ("quick-eye", "Quick Eye", "Found a Hard difficulty error in under 2 minutes", "👁️", "achievement", "medium", 30),
        ("consistency-champ", "Consistency Champion", "Completed reviews on 5 consecutive days", "🏆", "achievement", "medium", 50),
        ("reviewer-novice", "Reviewer Novice", "Completed 5 code reviews", "🔰", "progression", "easy", 10),
        ("reviewer-adept", "Reviewer Adept", "Completed 25 code reviews", "🥈", "progression", "medium", 30),
        ("reviewer-master", "Reviewer Master", "Completed 50 code reviews", "🥇", "progression", "hard", 100),
        
        # Error category badges
        ("syntax-specialist", "Syntax Specialist", "Mastered Syntax error identification", "📝", "category", "medium", 40),
        ("logic-guru", "Logic Guru", "Mastered Logical error identification", "🧠", "category", "medium", 40),
        ("quality-inspector", "Quality Inspector", "Mastered Code Quality error identification", "🔍", "category", "medium", 40),
        ("standards-expert", "Standards Expert", "Mastered Standard Violation identification", "📏", "category", "medium", 40),
        ("java-maven", "Java Maven", "Mastered Java Specific error identification", "☕", "category", "medium", 40),
        
        # Special badges
        ("full-spectrum", "Full Spectrum", "Identified at least one error in each category", "🌈", "special", "hard", 75),
        ("rising-star", "Rising Star", "Earned 500 points in your first week", "⭐", "special", "hard", 100),
    ]
    
    # Insert each badge
    for badge_id, name, description, icon, category, difficulty, points in default_badges:
        query = """
        INSERT INTO badges (badge_id, name, description, icon, category, difficulty, points)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        db.execute_query(query, (badge_id, name, description, icon, category, difficulty, points))
    
    logger.info(f"Inserted {len(default_badges)} default badges")