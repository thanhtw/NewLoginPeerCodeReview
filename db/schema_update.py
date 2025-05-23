import logging
from db.mysql_connection import MySQLConnection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_database_schema():
    """Apply schema updates to support multilingual fields and add badge and statistics support."""
    db = MySQLConnection()

    
    # Create users table with multilingual support if it doesn't exist
    users_table = """
    CREATE TABLE IF NOT EXISTS users (
        uid VARCHAR(36) PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,       
        display_name_en VARCHAR(255),
        display_name_zh VARCHAR(255),
        password VARCHAR(255) NOT NULL,       
        level_name_en VARCHAR(50),
        level_name_zh VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reviews_completed INT DEFAULT 0,
        score INT DEFAULT 0,
        last_activity DATE DEFAULT NULL,
        consecutive_days INT DEFAULT 0,
        total_points INT DEFAULT 0,
        tutorial_completed BOOLEAN DEFAULT FALSE,
        user_role ENUM('student', 'instructor', 'admin') DEFAULT 'student'
    )
    """
    
    # Create badges table with multilingual fields (if not exists)
    badges_table = """
    CREATE TABLE IF NOT EXISTS badges (
        badge_id VARCHAR(36) PRIMARY KEY,
        name_en VARCHAR(100) NOT NULL,
        name_zh VARCHAR(100) NOT NULL,
        description_en TEXT NOT NULL,
        description_zh TEXT NOT NULL,
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
        details_en TEXT,
        details_zh TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(uid)
    )
    """

    
    try:
        db.execute_query(users_table)
        db.execute_query(badges_table)
        db.execute_query(user_badges_table)
        db.execute_query(error_category_stats_table)
        db.execute_query(activity_log_table)      
        
        insert_default_badges(db)
        return True
    except Exception as e:
        logger.error(f"Error updating database schema: {str(e)}")
        return False

def insert_default_badges(db):
    """Insert default badges into the badges table with multilingual support."""
    # Check if badges already exist
    count_query = "SELECT COUNT(*) as badge_count FROM badges"
    result = db.execute_query(count_query, fetch_one=True)
    badge_count = result.get('badge_count', 0) if result else 0
    
    # Only proceed with insertion if no badges exist
    if badge_count > 0:
        logger.info(f"Badges already exist in the database ({badge_count} found). Skipping insertion.")
        return
    
    # Define default badges with English and Chinese translations
    # Format: (badge_id, name_en, name_zh, description_en, description_zh, icon, category, difficulty, points)
    default_badges = [
        # Achievement badges
        ("bug-hunter", "Bug Hunter", "錯誤獵人", "Found all errors in at least 5 reviews", "在至少 5 次審查中找到所有錯誤", "🐞", "achievement", "medium", 50),
        ("perfectionist", "Perfectionist", "完美主義者", "Achieved 100% accuracy in 3 consecutive reviews", "連續 3 次審查達到 100% 準確度", "✨", "achievement", "hard", 100),
        ("quick-eye", "Quick Eye", "敏銳之眼", "Found a Hard difficulty error in under 2 minutes", "2 分鐘內發現困難等級錯誤", "👁️", "achievement", "medium", 30),
        ("consistency-champ", "Consistency Champion", "持續冠軍", "Completed reviews on 5 consecutive days", "連續 5 天完成審查", "🏆", "achievement", "medium", 50),
        ("reviewer-novice", "Reviewer Novice", "審查新手", "Completed 5 code reviews", "完成 5 次代碼審查", "🔰", "progression", "easy", 10),
        ("reviewer-adept", "Reviewer Adept", "審查熟手", "Completed 25 code reviews", "完成 25 次代碼審查", "🥈", "progression", "medium", 30),
        ("reviewer-master", "Reviewer Master", "審查大師", "Completed 50 code reviews", "完成 50 次代碼審查", "🥇", "progression", "hard", 100),
        
        # Error category badges
        ("syntax-specialist", "Syntax Specialist", "語法專家", "Mastered Syntax error identification", "掌握語法錯誤識別", "📝", "category", "medium", 40),
        ("logic-guru", "Logic Guru", "邏輯大師", "Mastered Logical error identification", "掌握邏輯錯誤識別", "🧠", "category", "medium", 40),
        ("quality-inspector", "Quality Inspector", "品質檢查員", "Mastered Code Quality error identification", "掌握程式碼品質錯誤識別", "🔍", "category", "medium", 40),
        ("standards-expert", "Standards Expert", "標準專家", "Mastered Standard Violation identification", "掌握標準違規識別", "📏", "category", "medium", 40),
        ("java-maven", "Java Maven", "Java 專家", "Mastered Java Specific error identification", "掌握 Java 特定錯誤識別", "☕", "category", "medium", 40),
        
        # Special badges
        ("full-spectrum", "Full Spectrum", "全方位", "Identified at least one error in each category", "在每個類別中至少識別一個錯誤", "🌈", "special", "hard", 75),
        ("rising-star", "Rising Star", "冉冉新星", "Earned 500 points in your first week", "在第一週內獲得 500 點", "⭐", "special", "hard", 100),
        ("tutorial-master", "Tutorial Master", "教學大師", "Completed the interactive tutorial", "完成互動教學", "🎓", "tutorial", "easy", 25),

        #Peer review badges
        ("peer-reviewer", "Peer Reviewer", "同儕審查者", "Completed your first peer review", "完成了您的第一次同儕審查","👥", "peer_review", "easy", 20),
        ("helpful-reviewer", "Helpful Reviewer", "有用的審查者","Received 5-star ratings on 5 reviews", "在5次審查中獲得5星評價", "🌟", "peer_review", "medium", 50),
        ("collaborative", "Collaborative", "協作者","Participated in 10 peer review discussions", "參與了10次同儕審查討論","🤝", "peer_review", "medium", 40),
        ("submission-creator", "Submission Creator", "提交創建者","Created your first peer submission", "創建了您的第一次同儕提交","📝", "peer_review", "easy", 15),

         # Challenge participation badges
        ("challenge-newcomer", "Challenge Newcomer", "挑戰新手", "Participated in your first community challenge", "參與了你的第一個社群挑戰", "🎯", "challenge", "easy", 15),
        ("challenge-regular", "Challenge Regular", "挑戰常客", "Participated in 5 community challenges", "參與了 5 個社群挑戰", "🎪", "challenge", "medium", 30),
        ("challenge-enthusiast", "Challenge Enthusiast", "挑戰愛好者", "Participated in 15 community challenges", "參與了 15 個社群挑戰", "🎨", "challenge", "hard", 75),
        
        # Challenge performance badges
        ("challenge-winner", "Challenge Winner", "挑戰獲勝者", "Won 1st place in a community challenge", "在社群挑戰中獲得第一名", "🏆", "challenge", "hard", 100),
        ("podium-finisher", "Podium Finisher", "登台完賽者", "Finished in top 3 of a community challenge", "在社群挑戰中進入前三名", "🥉", "challenge", "medium", 50),
        ("top-performer", "Top Performer", "頂級表現者", "Finished in top 10% of participants in a challenge", "在挑戰中進入參與者前 10%", "⭐", "challenge", "medium", 40),
        
        # Challenge streak badges
        ("challenge-streak-3", "3-Challenge Streak", "三連挑戰", "Completed 3 challenges in a row", "連續完成 3 個挑戰", "🔥", "challenge", "medium", 45),
        ("challenge-streak-7", "Weekly Warrior", "每週戰士", "Completed 7 challenges in a row", "連續完成 7 個挑戰", "💪", "challenge", "hard", 80),
        
        # Speed and accuracy badges
        ("speed-demon", "Speed Demon", "速度惡魔", "Completed a challenge in under 10 minutes", "在 10 分鐘內完成挑戰", "⚡", "challenge", "medium", 35),
        ("perfectionist-challenger", "Perfectionist Challenger", "完美主義挑戰者", "Achieved 100% accuracy in a challenge", "在挑戰中達到 100% 準確率", "💎", "challenge", "hard", 60),
        
        # Challenge creation badges (for instructors)
        ("challenge-creator", "Challenge Creator", "挑戰創造者", "Created your first custom challenge", "創建了你的第一個自訂挑戰", "🎭", "challenge", "medium", 50),
        ("popular-creator", "Popular Creator", "受歡迎創造者", "Created a challenge with 50+ participants", "創建了有 50+ 參與者的挑戰", "🌟", "challenge", "hard", 100),
        
        # Community engagement badges
        ("early-bird", "Early Bird", "早起鳥", "Joined a challenge within first hour of launch", "在挑戰開始後一小時內參加", "🐦", "challenge", "easy", 20),
        ("last-minute-hero", "Last Minute Hero", "最後時刻英雄", "Completed a challenge in its final hour", "在挑戰的最後一小時完成", "⏰", "challenge", "medium", 35)
        
    ]
    
    # Insert each badge with error handling
    successfully_inserted = 0
    for badge_id, name_en, name_zh, desc_en, desc_zh, icon, category, difficulty, points in default_badges:
        try:
            # Check if this specific badge already exists
            check_query = "SELECT COUNT(*) as exists_count FROM badges WHERE badge_id = %s"
            result = db.execute_query(check_query, (badge_id,), fetch_one=True)
            badge_exists = result.get('exists_count', 0) > 0 if result else False
            
            if badge_exists:
                logger.debug(f"Badge {badge_id} already exists, skipping insertion")
                continue
                
            # Insert the badge with multilingual fields
            insert_query = """
            INSERT INTO badges (badge_id, name_en, name_zh, description_en, description_zh, icon, category, difficulty, points)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            db.execute_query(insert_query, (badge_id, name_en, name_zh, desc_en, desc_zh, icon, category, difficulty, points))
            successfully_inserted += 1
            
        except Exception as e:
            logger.warning(f"Error inserting badge {badge_id}: {str(e)}")
            # Continue with the next badge
            continue
    
    logger.info(f"Inserted {successfully_inserted} multilingual default badges")