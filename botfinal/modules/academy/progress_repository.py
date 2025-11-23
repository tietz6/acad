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
        
        # Create indices for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_progress 
            ON user_progress(user_id, module_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_test_results 
            ON test_results(user_id, module_id, test_id)
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
