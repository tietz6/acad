"""
Learning Plan Service - Персональный план обучения (V3)
"""
import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from .models import LearningPlanItem, LearningPlan

logger = logging.getLogger(__name__)


class LearningPlanService:
    """Сервис для управления персональными планами обучения"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Инициализация сервиса"""
        if db_path is None:
            base_dir = Path(__file__).parent.parent.parent
            db_path = base_dir / "academy_progress.db"
        
        self.db_path = Path(db_path)
        self._init_tables()
    
    def _init_tables(self):
        """Создание таблиц для планов обучения"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Таблица планов обучения
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS academy_learning_plan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                module_id TEXT NOT NULL,
                lesson_id TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 1,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, module_id, lesson_id)
            )
        """)
        
        # Индексы
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_learning_plan_user
            ON academy_learning_plan(user_id, status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_learning_plan_priority
            ON academy_learning_plan(user_id, priority DESC)
        """)
        
        conn.commit()
        conn.close()
        logger.info("Learning plan tables initialized")
    
    def get_user_plan(self, user_id: str) -> LearningPlan:
        """
        Получить текущий план обучения пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            LearningPlan с элементами плана
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, module_id, lesson_id, status, priority, generated_at
            FROM academy_learning_plan
            WHERE user_id = ?
            ORDER BY priority DESC, generated_at ASC
        """, (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        items = []
        generated_at = datetime.now()
        
        for row in rows:
            items.append(LearningPlanItem(
                user_id=row["user_id"],
                module_id=row["module_id"],
                lesson_id=row["lesson_id"],
                status=row["status"],
                priority=row["priority"],
                generated_at=datetime.fromisoformat(row["generated_at"]) if row["generated_at"] else datetime.now()
            ))
            if row["generated_at"]:
                generated_at = datetime.fromisoformat(row["generated_at"])
        
        # План действителен 7 дней
        valid_until = generated_at + timedelta(days=7)
        
        return LearningPlan(
            user_id=user_id,
            items=items,
            generated_at=generated_at,
            valid_until=valid_until
        )
    
    def generate_plan(
        self, 
        user_id: str, 
        user_role: str,
        module_repo,
        progress_repo
    ) -> LearningPlan:
        """
        Сгенерировать новый персональный план обучения
        
        Args:
            user_id: ID пользователя
            user_role: Роль пользователя
            module_repo: Репозиторий модулей
            progress_repo: Репозиторий прогресса
        
        Returns:
            Новый LearningPlan
        """
        # Очистить старый план
        self._clear_plan(user_id)
        
        # Получить прогресс пользователя
        user_progress = progress_repo.get_user_progress(user_id)
        completed_lessons = {
            (p.module_id, p.lesson_id) 
            for p in user_progress 
            if p.status == "completed"
        }
        
        # Получить результаты тестов для анализа слабых зон
        test_results = progress_repo.get_test_results(user_id)
        weak_modules = self._identify_weak_modules(test_results)
        
        # Получить доступные модули для роли
        modules = module_repo.list_modules(user_role)
        
        # Формировать план
        plan_items = []
        
        for module in modules:
            module_priority = 5  # Базовый приоритет
            
            # Повысить приоритет для слабых модулей
            if module.id in weak_modules:
                module_priority = 10
            
            # Добавить незавершенные уроки
            for lesson in sorted(module.lessons, key=lambda l: l.order):
                if (module.id, lesson.id) not in completed_lessons:
                    plan_items.append({
                        "module_id": module.id,
                        "lesson_id": lesson.id,
                        "priority": module_priority
                    })
        
        # Сортировать по приоритету и ограничить до разумного количества (например, 20)
        plan_items.sort(key=lambda x: x["priority"], reverse=True)
        plan_items = plan_items[:20]
        
        # Сохранить в базу данных
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        for item in plan_items:
            cursor.execute("""
                INSERT OR REPLACE INTO academy_learning_plan 
                (user_id, module_id, lesson_id, status, priority, generated_at)
                VALUES (?, ?, ?, 'pending', ?, CURRENT_TIMESTAMP)
            """, (user_id, item["module_id"], item["lesson_id"], item["priority"]))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Generated learning plan for user {user_id} with {len(plan_items)} items")
        
        # Вернуть созданный план
        return self.get_user_plan(user_id)
    
    def _clear_plan(self, user_id: str):
        """Очистить текущий план пользователя"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM academy_learning_plan
            WHERE user_id = ?
        """, (user_id,))
        
        conn.commit()
        conn.close()
    
    def _identify_weak_modules(self, test_results) -> set:
        """
        Определить модули со слабыми результатами
        
        Args:
            test_results: Результаты тестов пользователя
        
        Returns:
            Множество ID модулей с низкими результатами
        """
        weak_modules = set()
        
        # Группировать результаты по модулям
        module_scores = {}
        for result in test_results:
            module_id = result["module_id"]
            score = result["score"]
            
            if module_id not in module_scores:
                module_scores[module_id] = []
            module_scores[module_id].append(score)
        
        # Найти модули со средним баллом < 70%
        for module_id, scores in module_scores.items():
            avg_score = sum(scores) / len(scores)
            if avg_score < 70:
                weak_modules.add(module_id)
        
        return weak_modules
    
    def update_item_status(self, user_id: str, module_id: str, lesson_id: str, status: str) -> bool:
        """
        Обновить статус элемента плана
        
        Args:
            user_id: ID пользователя
            module_id: ID модуля
            lesson_id: ID урока
            status: Новый статус (pending, active, done)
        
        Returns:
            True если успешно
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE academy_learning_plan
            SET status = ?
            WHERE user_id = ? AND module_id = ? AND lesson_id = ?
        """, (status, user_id, module_id, lesson_id))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return rows_affected > 0
