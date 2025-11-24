"""
Quests Service - Ежедневные задания (V3)
"""
import sqlite3
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime, date
import uuid
from .models import DailyQuest

logger = logging.getLogger(__name__)

# Типы квестов и их награды
QUEST_TYPES = {
    "lesson": {
        "description": "Пройти 1 урок",
        "reward_xp": 15
    },
    "test": {
        "description": "Пройти тест",
        "reward_xp": 40
    },
    "streak": {
        "description": "Учиться 20 минут",
        "reward_xp": 25
    },
    "tts": {
        "description": "Получить аудиоверсию урока",
        "reward_xp": 10
    },
    "module": {
        "description": "Завершить модуль",
        "reward_xp": 50
    }
}


class QuestsService:
    """Сервис для управления ежедневными заданиями"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Инициализация сервиса"""
        if db_path is None:
            base_dir = Path(__file__).parent.parent.parent
            db_path = base_dir / "academy_progress.db"
        
        self.db_path = Path(db_path)
        self._init_tables()
    
    def _init_tables(self):
        """Создание таблиц для квестов"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Таблица ежедневных квестов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS academy_daily_quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quest_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT NOT NULL,
                reward_xp INTEGER NOT NULL,
                status TEXT DEFAULT 'active',
                date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        
        # Индексы
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quests_user_date
            ON academy_daily_quests(user_id, date, status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quests_quest_id
            ON academy_daily_quests(quest_id)
        """)
        
        conn.commit()
        conn.close()
        logger.info("Quests tables initialized")
    
    def get_daily_quests(self, user_id: str) -> List[DailyQuest]:
        """
        Получить ежедневные квесты пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Список активных квестов на сегодня
        """
        today = date.today().isoformat()
        
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получить квесты на сегодня
        cursor.execute("""
            SELECT quest_id, user_id, type, description, reward_xp, status, date, created_at
            FROM academy_daily_quests
            WHERE user_id = ? AND date = ?
            ORDER BY created_at ASC
        """, (user_id, today))
        
        rows = cursor.fetchall()
        conn.close()
        
        quests = []
        for row in rows:
            quests.append(DailyQuest(
                quest_id=row["quest_id"],
                user_id=row["user_id"],
                type=row["type"],
                description=row["description"],
                reward_xp=row["reward_xp"],
                status=row["status"],
                date=row["date"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now()
            ))
        
        # Если квестов нет, создать новые
        if not quests:
            quests = self._generate_daily_quests(user_id)
        
        return quests
    
    def _generate_daily_quests(self, user_id: str) -> List[DailyQuest]:
        """
        Сгенерировать ежедневные квесты для пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Список новых квестов
        """
        today = date.today().isoformat()
        
        # Выбрать 3 случайных типа квестов
        import random
        quest_types = random.sample(list(QUEST_TYPES.keys()), min(3, len(QUEST_TYPES)))
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        quests = []
        
        for quest_type in quest_types:
            quest_config = QUEST_TYPES[quest_type]
            quest_id = str(uuid.uuid4())
            
            cursor.execute("""
                INSERT INTO academy_daily_quests 
                (quest_id, user_id, type, description, reward_xp, status, date)
                VALUES (?, ?, ?, ?, ?, 'active', ?)
            """, (
                quest_id,
                user_id,
                quest_type,
                quest_config["description"],
                quest_config["reward_xp"],
                today
            ))
            
            quests.append(DailyQuest(
                quest_id=quest_id,
                user_id=user_id,
                type=quest_type,
                description=quest_config["description"],
                reward_xp=quest_config["reward_xp"],
                status="active",
                date=today,
                created_at=datetime.now()
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Generated {len(quests)} daily quests for user {user_id}")
        
        return quests
    
    def complete_quest(self, user_id: str, quest_id: str) -> dict:
        """
        Отметить квест как выполненный
        
        Args:
            user_id: ID пользователя
            quest_id: ID квеста
        
        Returns:
            Dict с результатом выполнения
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получить квест
        cursor.execute("""
            SELECT quest_id, user_id, type, reward_xp, status
            FROM academy_daily_quests
            WHERE quest_id = ? AND user_id = ?
        """, (quest_id, user_id))
        
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {
                "success": False,
                "message": "Quest not found"
            }
        
        if row["status"] == "completed":
            conn.close()
            return {
                "success": False,
                "message": "Quest already completed"
            }
        
        # Обновить статус квеста
        cursor.execute("""
            UPDATE academy_daily_quests
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE quest_id = ?
        """, (quest_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"User {user_id} completed quest {quest_id}")
        
        return {
            "success": True,
            "quest_id": quest_id,
            "reward_xp": row["reward_xp"],
            "message": "Quest completed!"
        }
    
    def check_and_complete_quest(self, user_id: str, quest_type: str) -> dict:
        """
        Проверить и автоматически выполнить квест определенного типа
        
        Args:
            user_id: ID пользователя
            quest_type: Тип квеста (lesson, test, tts, module, streak)
        
        Returns:
            Dict с результатом
        """
        today = date.today().isoformat()
        
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Найти активный квест этого типа на сегодня
        cursor.execute("""
            SELECT quest_id, reward_xp
            FROM academy_daily_quests
            WHERE user_id = ? AND type = ? AND date = ? AND status = 'active'
            LIMIT 1
        """, (user_id, quest_type, today))
        
        row = cursor.fetchone()
        
        if row:
            # Обновить статус
            cursor.execute("""
                UPDATE academy_daily_quests
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE quest_id = ?
            """, (row["quest_id"],))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Auto-completed {quest_type} quest for user {user_id}")
            
            return {
                "success": True,
                "quest_completed": True,
                "quest_id": row["quest_id"],
                "reward_xp": row["reward_xp"]
            }
        
        conn.close()
        
        return {
            "success": True,
            "quest_completed": False
        }
    
    def expire_old_quests(self):
        """Пометить старые квесты как просроченные"""
        today = date.today().isoformat()
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE academy_daily_quests
            SET status = 'expired'
            WHERE date < ? AND status = 'active'
        """, (today,))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if rows_affected > 0:
            logger.info(f"Expired {rows_affected} old quests")
