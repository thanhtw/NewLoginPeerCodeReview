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
        total_points INT DEFAULT 0
    )
    """

    db.execute_query(users_table)
    # Check if columns exist before adding
    result = db.execute_query(check_column_exists, ('users', 'display_name_en'), fetch_one=True)
    has_display_name_en = result and result.get('column_exists', 0) > 0

    if has_display_name_en:
        logger.info("Users table already has multilingual support")
    else:
        # Users table exists but needs multilingual columns
        logger.info("Adding multilingual support to users table")
        
        # Add multilingual columns if they don't exist
        try:
            db.execute_query("ALTER TABLE users ADD COLUMN display_name_en VARCHAR(255)")
            db.execute_query("ALTER TABLE users ADD COLUMN display_name_zh VARCHAR(255)")
            db.execute_query("ALTER TABLE users ADD COLUMN level_name_en VARCHAR(50)")
            db.execute_query("ALTER TABLE users ADD COLUMN level_name_zh VARCHAR(50)")
            
            # Populate new columns with data from existing columns
            db.execute_query("UPDATE users SET display_name_en = display_name, display_name_zh = display_name")
            
            # Populate level names based on the level enum value
            db.execute_query("UPDATE users SET level_name_en = level")
            
            # Set Chinese level names
            db.execute_query("UPDATE users SET level_name_zh = CASE level " +
                            "WHEN 'basic' THEN '基礎' " +
                            "WHEN 'medium' THEN '中級' " +
                            "WHEN 'senior' THEN '高級' " +
                            "ELSE level END")
            
            logger.info("Multilingual columns added and populated in users table")
        except Exception as e:
            logger.error(f"Error adding multilingual columns to users table: {str(e)}")
    
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
    
    # Check if columns exist in users table
    check_column_exists = """
    SELECT COUNT(*) as column_exists 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE() 
    AND table_name = %s 
    AND column_name = %s
    """
    # Add multilingual fields to users table

    users_multilingual_update = """
    ALTER TABLE users
    ADD COLUMN display_name_en VARCHAR(255),
    ADD COLUMN display_name_zh VARCHAR(255),
    ADD COLUMN level_name_en VARCHAR(50),
    ADD COLUMN level_name_zh VARCHAR(50)
    """

    

    if not has_display_name_en:
        # The table exists but doesn't have multilingual columns
        # Need to migrate data from old format to new format
        logger.info("Migrating users table to support multiple languages...")
        
        # Create temporary columns
        db.execute_query("ALTER TABLE users ADD COLUMN display_name_backup VARCHAR(255)")
        db.execute_query("ALTER TABLE users ADD COLUMN level_backup VARCHAR(50)")
        
        # Backup current data
        db.execute_query("UPDATE users SET display_name_backup = display_name, level_backup = level")
        
        # Add multilingual columns
        db.execute_query(users_multilingual_update)
        
        # Copy data to new columns
        db.execute_query("UPDATE users SET display_name_en = display_name_backup, display_name_zh = display_name_backup")
        db.execute_query("UPDATE users SET level_name_en = level_backup, level_name_zh = level_backup")
        
        # Clean up backup columns
        db.execute_query("ALTER TABLE users DROP COLUMN display_name_backup")
        db.execute_query("ALTER TABLE users DROP COLUMN level_backup")
        
        logger.info("Added multilingual support to users table")
    else:
        logger.info("Users table already has multilingual support")

    
    # Execute all schema updates
    try:
        # Check if badges table exists
        result = db.execute_query(check_column_exists, ('badges', 'badge_id'), fetch_one=True)
        badges_exist = result and result.get('column_exists', 0) > 0
        
        # If badges table exists but doesn't have multilingual fields, modify it
        if badges_exist:
            # Check if name_en and name_zh exist
            result = db.execute_query(check_column_exists, ('badges', 'name_en'), fetch_one=True)
            has_name_en = result and result.get('column_exists', 0) > 0
            
            if not has_name_en:
                # The table exists but doesn't have multilingual columns
                # Need to migrate data from old format to new format
                logger.info("Migrating badges table to support multiple languages...")
                
                # Create temporary column name_backup and description_backup
                db.execute_query("ALTER TABLE badges ADD COLUMN name_backup VARCHAR(100)")
                db.execute_query("ALTER TABLE badges ADD COLUMN description_backup TEXT")
                
                # Backup current data
                db.execute_query("UPDATE badges SET name_backup = name, description_backup = description")
                
                # Check if the columns exist and modify or add them
                for column in ['name', 'description']:
                    # First try to modify existing columns
                    try:
                        result = db.execute_query(check_column_exists, ('badges', column), fetch_one=True)
                        if result and result.get('column_exists', 0) > 0:
                            # Rename the existing column to columnname_en
                            db.execute_query(f"ALTER TABLE badges CHANGE {column} {column}_en {column}_en VARCHAR(100) NOT NULL")
                            logger.info(f"Renamed {column} to {column}_en")
                        
                        # Add the new *_zh column
                        db.execute_query(f"ALTER TABLE badges ADD COLUMN {column}_zh {column}_zh VARCHAR(100) NOT NULL")
                        
                        # Copy the English content to the zh column as a temporary measure
                        db.execute_query(f"UPDATE badges SET {column}_zh = {column}_backup")
                        logger.info(f"Added {column}_zh and copied English content as placeholder")
                    except Exception as e:
                        logger.error(f"Error modifying {column} column: {str(e)}")
                
                # Clean up temporary columns
                try:
                    db.execute_query("ALTER TABLE badges DROP COLUMN name_backup")
                    db.execute_query("ALTER TABLE badges DROP COLUMN description_backup")
                except Exception as e:
                    logger.error(f"Error dropping backup columns: {str(e)}")
            else:
                logger.info("Badges table already has multilingual support")
        else:
            # Create the badges table with multilingual fields
            db.execute_query(badges_table)
            logger.info("Created badges table with multilingual support")
        
        # Create other tables if they don't exist
        db.execute_query(user_badges_table)       
        db.execute_query(error_category_stats_table)
        
        # Check if activity log table exists
        result = db.execute_query(check_column_exists, ('activity_log', 'id'), fetch_one=True)
        activity_log_exists = result and result.get('column_exists', 0) > 0
        
        if activity_log_exists:
            # Check if it has multilingual fields
            result = db.execute_query(check_column_exists, ('activity_log', 'details_en'), fetch_one=True)
            has_details_en = result and result.get('column_exists', 0) > 0
            
            if not has_details_en:
                # Migrate details to details_en and details_zh
                logger.info("Migrating activity_log table to support multiple languages...")
                db.execute_query("ALTER TABLE activity_log ADD COLUMN details_backup TEXT")
                db.execute_query("UPDATE activity_log SET details_backup = details")
                
                # Rename details to details_en and add details_zh
                try:
                    db.execute_query("ALTER TABLE activity_log CHANGE details details_en TEXT")
                    db.execute_query("ALTER TABLE activity_log ADD COLUMN details_zh TEXT")
                    db.execute_query("UPDATE activity_log SET details_zh = details_backup")
                    logger.info("Updated activity_log table with multilingual fields")
                except Exception as e:
                    logger.error(f"Error modifying activity_log table: {str(e)}")
                
                # Clean up
                try:
                    db.execute_query("ALTER TABLE activity_log DROP COLUMN details_backup")
                except Exception as e:
                    logger.error(f"Error dropping backup column: {str(e)}")
        else:
            # Create the activity_log table
            db.execute_query(activity_log_table)
            logger.info("Created activity_log table with multilingual support")
        
        # Check and add columns to users table
        columns_to_add = [
            ('last_activity', 'DATE DEFAULT NULL'),
            ('consecutive_days', 'INT DEFAULT 0'),
            ('total_points', 'INT DEFAULT 0')
        ]
        
        for column_name, column_def in columns_to_add:
            # Check if column exists
            result = db.execute_query(check_column_exists, ('users', column_name), fetch_one=True)
            column_exists = result and result.get('column_exists', 0) > 0
            
            if not column_exists:
                # Add column if it doesn't exist
                add_column_query = f"ALTER TABLE users ADD COLUMN {column_name} {column_def}"
                db.execute_query(add_column_query)
                logger.info(f"Added column {column_name} to users table")
        
        logger.info("Database schema updated successfully")
        
        # Insert default badges with multilingual support
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