"""
Mega Stats Service - Расширенная статистика для администраторов (V3)
"""
import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from .models import MegaStats

logger = logging.getLogger(__name__)


class MegaStatsService:
    """Сервис для сбора мегастатистики"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Инициализация сервиса"""
        if db_path is None:
            base_dir = Path(__file__).parent.parent.parent
            db_path = base_dir / "academy_progress.db"
        
        self.db_path = Path(db_path)
    
    def get_mega_stats(self, module_repo) -> MegaStats:
        """
        Собрать мегастатистику по всей системе
        
        Args:
            module_repo: Репозиторий модулей
        
        Returns:
            MegaStats со всеми данными
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Общие данные о пользователях
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM users")
        total_users = cursor.fetchone()[0] or 0
        
        # Активные пользователи
        now = datetime.now()
        today = now.date().isoformat()
        week_ago = (now - timedelta(days=7)).isoformat()
        month_ago = (now - timedelta(days=30)).isoformat()
        
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) 
            FROM academy_daily_progress 
            WHERE date = ?
        """, (today,))
        active_today = cursor.fetchone()[0] or 0
        
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) 
            FROM academy_daily_progress 
            WHERE date >= ?
        """, (week_ago[:10],))
        active_week = cursor.fetchone()[0] or 0
        
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) 
            FROM academy_daily_progress 
            WHERE date >= ?
        """, (month_ago[:10],))
        active_month = cursor.fetchone()[0] or 0
        
        # 2. Распределение по ролям
        cursor.execute("""
            SELECT role, COUNT(*) as count
            FROM users
            GROUP BY role
        """)
        users_by_role = {row["role"]: row["count"] for row in cursor.fetchall()}
        
        # 3. Статистика по модулям
        
        # Топ-5 самых изучаемых модулей
        cursor.execute("""
            SELECT module_id, COUNT(DISTINCT user_id) as user_count
            FROM user_progress
            WHERE status IN ('in_progress', 'completed')
            GROUP BY module_id
            ORDER BY user_count DESC
            LIMIT 5
        """)
        top_modules = [
            {
                "module_id": row["module_id"],
                "user_count": row["user_count"],
                "title": self._get_module_title(module_repo, row["module_id"])
            }
            for row in cursor.fetchall()
        ]
        
        # Топ-5 самых сложных модулей (по результатам тестов)
        cursor.execute("""
            SELECT module_id, AVG(score * 100.0 / total_questions) as avg_score
            FROM test_results
            GROUP BY module_id
            HAVING COUNT(*) >= 3
            ORDER BY avg_score ASC
            LIMIT 5
        """)
        hardest_modules = [
            {
                "module_id": row["module_id"],
                "avg_score": round(row["avg_score"], 2),
                "title": self._get_module_title(module_repo, row["module_id"])
            }
            for row in cursor.fetchall()
        ]
        
        # Модули, которые никто не изучает
        all_modules = module_repo.list_modules()
        studied_modules = set()
        
        cursor.execute("SELECT DISTINCT module_id FROM user_progress")
        for row in cursor.fetchall():
            studied_modules.add(row["module_id"])
        
        unused_modules = [
            {
                "module_id": m.id,
                "title": m.title,
                "description": m.description
            }
            for m in all_modules
            if m.id not in studied_modules
        ]
        
        # 4. Статистика по тестам
        
        # Средний балл по системе
        cursor.execute("""
            SELECT AVG(score * 100.0 / total_questions) as avg_score
            FROM test_results
        """)
        avg_score_row = cursor.fetchone()
        average_score = round(avg_score_row["avg_score"], 2) if avg_score_row["avg_score"] else 0.0
        
        # Самые провальные вопросы (модули с низкой успеваемостью)
        cursor.execute("""
            SELECT module_id, test_id, 
                   COUNT(*) as attempts,
                   SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) as passes,
                   AVG(score * 100.0 / total_questions) as avg_score
            FROM test_results
            GROUP BY module_id, test_id
            HAVING attempts >= 3
            ORDER BY avg_score ASC
            LIMIT 10
        """)
        failing_questions = [
            {
                "module_id": row["module_id"],
                "test_id": row["test_id"],
                "attempts": row["attempts"],
                "passes": row["passes"],
                "pass_rate": round((row["passes"] / row["attempts"]) * 100, 2),
                "avg_score": round(row["avg_score"], 2),
                "title": self._get_module_title(module_repo, row["module_id"])
            }
            for row in cursor.fetchall()
        ]
        
        # Модули с низкой успеваемостью
        cursor.execute("""
            SELECT module_id, 
                   COUNT(*) as test_count,
                   AVG(score * 100.0 / total_questions) as avg_score,
                   SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as pass_rate
            FROM test_results
            GROUP BY module_id
            HAVING test_count >= 3 AND avg_score < 70
            ORDER BY avg_score ASC
            LIMIT 5
        """)
        low_performance_modules = [
            {
                "module_id": row["module_id"],
                "test_count": row["test_count"],
                "avg_score": round(row["avg_score"], 2),
                "pass_rate": round(row["pass_rate"], 2),
                "title": self._get_module_title(module_repo, row["module_id"])
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return MegaStats(
            total_users=total_users,
            active_today=active_today,
            active_week=active_week,
            active_month=active_month,
            users_by_role=users_by_role,
            top_modules=top_modules,
            hardest_modules=hardest_modules,
            unused_modules=unused_modules,
            average_score=average_score,
            failing_questions=failing_questions,
            low_performance_modules=low_performance_modules,
            generated_at=datetime.now()
        )
    
    def _get_module_title(self, module_repo, module_id: str) -> str:
        """Получить название модуля по ID"""
        try:
            module = module_repo.get_module(module_id)
            return module.title if module else module_id
        except Exception:
            return module_id
