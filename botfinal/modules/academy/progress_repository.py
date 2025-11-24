"""
Progress Repository - Tracks user progress through modules and lessons
"""
import sqlite3
import logging
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
from .models import UserModuleProgress

logger = logging.getLogger(__name__)


class ProgressRepository:
    """Repository for managing user progress data"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize repository with database path"""
        if db_path is None:
            # Default to academy_progress.db in botfinal directory
            base_dir = Path(__file__).parent.parent.parent
            db_path = base_dir / "academy_progress.db"
        
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                role TEXT DEFAULT 'other',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create progress table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                module_id TEXT NOT NULL,
                lesson_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'not_started',
                score INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, module_id, lesson_id)
            )
        """)
        
        # Create test results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                module_id TEXT NOT NULL,
                test_id TEXT NOT NULL,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                passed BOOLEAN NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create badges table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS academy_badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                badge_type TEXT NOT NULL,
                badge_name TEXT NOT NULL,
                badge_description TEXT,
                earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, badge_type)
            )
        """)
        
        # Create daily progress table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS academy_daily_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                date DATE NOT NULL,
                lessons_completed INTEGER DEFAULT 0,
                minutes_studied INTEGER DEFAULT 0,
                tests_passed INTEGER DEFAULT 0,
                UNIQUE(user_id, date)
            )
        """)
        
        # Create indices for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_progress 
            ON user_progress(user_id, module_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_test_results 
            ON test_results(user_id, module_id, test_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_badges 
            ON academy_badges(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_daily_progress 
            ON academy_daily_progress(user_id, date)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Progress database initialized: {self.db_path}")
    
    def get_user_progress(self, user_id: str, module_id: Optional[str] = None) -> List[UserModuleProgress]:
        """
        Get user progress, optionally filtered by module
        
        Args:
            user_id: User identifier
            module_id: Optional module filter
        
        Returns:
            List of progress records
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if module_id:
            cursor.execute("""
                SELECT * FROM user_progress 
                WHERE user_id = ? AND module_id = ?
                ORDER BY updated_at DESC
            """, (user_id, module_id))
        else:
            cursor.execute("""
                SELECT * FROM user_progress 
                WHERE user_id = ?
                ORDER BY updated_at DESC
            """, (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        progress_list = []
        for row in rows:
            progress_list.append(UserModuleProgress(
                user_id=row['user_id'],
                module_id=row['module_id'],
                lesson_id=row['lesson_id'],
                status=row['status'],
                score=row['score'],
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else datetime.now()
            ))
        
        return progress_list
    
    def mark_lesson_completed(self, user_id: str, module_id: str, lesson_id: str):
        """
        Mark a lesson as completed
        
        Args:
            user_id: User identifier
            module_id: Module identifier
            lesson_id: Lesson identifier
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_progress 
            (user_id, module_id, lesson_id, status, updated_at)
            VALUES (?, ?, ?, 'completed', CURRENT_TIMESTAMP)
        """, (user_id, module_id, lesson_id))
        
        conn.commit()
        conn.close()
        logger.info(f"Marked lesson completed: user={user_id}, module={module_id}, lesson={lesson_id}")
    
    def mark_lesson_in_progress(self, user_id: str, module_id: str, lesson_id: str):
        """
        Mark a lesson as in progress
        
        Args:
            user_id: User identifier
            module_id: Module identifier
            lesson_id: Lesson identifier
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Only insert if not exists (don't overwrite completed status)
        cursor.execute("""
            INSERT OR IGNORE INTO user_progress 
            (user_id, module_id, lesson_id, status, updated_at)
            VALUES (?, ?, ?, 'in_progress', CURRENT_TIMESTAMP)
        """, (user_id, module_id, lesson_id))
        
        conn.commit()
        conn.close()
    
    def save_test_result(self, user_id: str, module_id: str, test_id: str, 
                        score: int, total_questions: int, passed: bool):
        """
        Save test result
        
        Args:
            user_id: User identifier
            module_id: Module identifier
            test_id: Test identifier
            score: Score achieved
            total_questions: Total number of questions
            passed: Whether the test was passed
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO test_results 
            (user_id, module_id, test_id, score, total_questions, passed)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, module_id, test_id, score, total_questions, passed))
        
        conn.commit()
        conn.close()
        logger.info(f"Saved test result: user={user_id}, test={test_id}, score={score}/{total_questions}, passed={passed}")
    
    def get_test_results(self, user_id: str, module_id: Optional[str] = None) -> List[Dict]:
        """
        Get user's test results
        
        Args:
            user_id: User identifier
            module_id: Optional module filter
        
        Returns:
            List of test results
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if module_id:
            cursor.execute("""
                SELECT * FROM test_results 
                WHERE user_id = ? AND module_id = ?
                ORDER BY submitted_at DESC
            """, (user_id, module_id))
        else:
            cursor.execute("""
                SELECT * FROM test_results 
                WHERE user_id = ?
                ORDER BY submitted_at DESC
            """, (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_module_completion_status(self, user_id: str, module_id: str) -> Dict:
        """
        Get completion status for a module
        
        Args:
            user_id: User identifier
            module_id: Module identifier
        
        Returns:
            Dictionary with completion statistics
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_lessons,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_lessons
            FROM user_progress
            WHERE user_id = ? AND module_id = ?
        """, (user_id, module_id))
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            'total_lessons': row[0] if row else 0,
            'completed_lessons': row[1] if row else 0
        }
    
    def get_user_role(self, user_id: str) -> Optional[str]:
        """
        Get user's role
        
        Args:
            user_id: User identifier
        
        Returns:
            User role or None if not set
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        return row['role'] if row else None
    
    def set_user_role(self, user_id: str, role: str):
        """
        Set user's role
        
        Args:
            user_id: User identifier
            role: User role (sales_manager, generator, admin, other)
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Use INSERT ... ON CONFLICT to preserve other user data
        cursor.execute("""
            INSERT INTO users (user_id, role, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                role = excluded.role,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, role))
        
        conn.commit()
        conn.close()
        logger.info(f"Set role for user {user_id}: {role}")
    
    def get_all_users(self) -> List[Dict]:
        """
        Get all users with their roles and stats
        
        Returns:
            List of user dictionaries
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                u.user_id,
                u.role,
                u.created_at,
                u.updated_at,
                COUNT(DISTINCT CASE WHEN up.status = 'completed' THEN up.module_id END) as completed_modules,
                COUNT(DISTINCT CASE WHEN up.status = 'completed' THEN up.lesson_id END) as completed_lessons,
                COUNT(DISTINCT CASE WHEN tr.passed = 1 THEN tr.test_id END) as passed_tests,
                MAX(COALESCE(up.updated_at, tr.submitted_at)) as last_activity
            FROM users u
            LEFT JOIN user_progress up ON u.user_id = up.user_id
            LEFT JOIN test_results tr ON u.user_id = tr.user_id
            GROUP BY u.user_id, u.role, u.created_at, u.updated_at
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # Badge methods
    def award_badge(self, user_id: str, badge_type: str, badge_name: str, badge_description: str = ""):
        """
        Award a badge to a user
        
        Args:
            user_id: User identifier
            badge_type: Badge type identifier
            badge_name: Display name of the badge
            badge_description: Description of achievement
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR IGNORE INTO academy_badges 
            (user_id, badge_type, badge_name, badge_description)
            VALUES (?, ?, ?, ?)
        """, (user_id, badge_type, badge_name, badge_description))
        
        conn.commit()
        conn.close()
        logger.info(f"Awarded badge: user={user_id}, badge={badge_name}")
    
    def get_user_badges(self, user_id: str) -> List[Dict]:
        """
        Get all badges for a user
        
        Args:
            user_id: User identifier
        
        Returns:
            List of badge dictionaries
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM academy_badges 
            WHERE user_id = ?
            ORDER BY earned_at DESC
        """, (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def check_and_award_badges(self, user_id: str):
        """
        Check user's progress and award appropriate badges
        
        Args:
            user_id: User identifier
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Check for "first module completed" badge
        cursor.execute("""
            SELECT COUNT(DISTINCT module_id) as completed_count
            FROM user_progress
            WHERE user_id = ? AND status = 'completed'
        """, (user_id,))
        row = cursor.fetchone()
        if row and row[0] >= 1:
            self.award_badge(
                user_id, 
                "first_module", 
                "🎖 Первый модуль пройден",
                "Завершён первый обучающий модуль"
            )
        
        # Check for "perfect test" badge (100% score)
        cursor.execute("""
            SELECT COUNT(*) as perfect_count
            FROM test_results
            WHERE user_id = ? AND score = 100
        """, (user_id,))
        row = cursor.fetchone()
        if row and row[0] >= 1:
            self.award_badge(
                user_id,
                "perfect_test",
                "🧠 Один тест на 100%",
                "Получена оценка 100% в тесте"
            )
        
        # Check for "streak" badge (3 consecutive days of activity)
        cursor.execute("""
            SELECT COUNT(DISTINCT date) as days_count
            FROM academy_daily_progress
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT 3
        """, (user_id,))
        row = cursor.fetchone()
        if row and row[0] >= 3:
            self.award_badge(
                user_id,
                "three_day_streak",
                "🔥 3 дня подряд обучение",
                "Активность в течение 3 дней подряд"
            )
        
        conn.close()
    
    # Daily progress methods
    def update_daily_progress(self, user_id: str, lessons_completed: int = 0, 
                             minutes_studied: int = 0, tests_passed: int = 0):
        """
        Update daily progress for a user
        
        Args:
            user_id: User identifier
            lessons_completed: Number of lessons completed today
            minutes_studied: Minutes spent studying today
            tests_passed: Number of tests passed today
        """
        from datetime import date
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        
        cursor.execute("""
            INSERT INTO academy_daily_progress 
            (user_id, date, lessons_completed, minutes_studied, tests_passed)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, date) DO UPDATE SET
                lessons_completed = lessons_completed + excluded.lessons_completed,
                minutes_studied = minutes_studied + excluded.minutes_studied,
                tests_passed = tests_passed + excluded.tests_passed
        """, (user_id, today, lessons_completed, minutes_studied, tests_passed))
        
        conn.commit()
        conn.close()
    
    def get_daily_progress(self, user_id: str, days: int = 30) -> List[Dict]:
        """
        Get daily progress for a user
        
        Args:
            user_id: User identifier
            days: Number of days to retrieve
        
        Returns:
            List of daily progress records
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM academy_daily_progress 
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT ?
        """, (user_id, days))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
