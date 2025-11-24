"""
Levels Service - Управление уровнями и опытом пользователей (V3)
"""
import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
from .models import UserLevel, XPAward

logger = logging.getLogger(__name__)

# Названия рангов по уровням
RANK_NAMES = {
    1: "Новичок",
    2: "Стажер",
    3: "Продвинутый",
    4: "Специалист",
    5: "Старший",
    6: "Эксперт",
    7: "Про",
    8: "Мастер",
    9: "Легенда",
    10: "Гуру"
}

# Требуемый XP для каждого уровня
XP_REQUIREMENTS = {
    1: 0,      # Старт
    2: 100,    # Стажер
    3: 250,    # Продвинутый
    4: 500,    # Специалист
    5: 1000,   # Старший
    6: 2000,   # Эксперт
    7: 3500,   # Про
    8: 5500,   # Мастер
    9: 8000,   # Легенда
    10: 12000  # Гуру (максимальный уровень)
}

# Награды за действия
XP_REWARDS = {
    "lesson": 10,
    "test": 30,
    "test_perfect": 60,  # 100% на тесте
    "daily_active": 5
}


class LevelsService:
    """Сервис для управления уровнями и опытом"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Инициализация сервиса"""
        if db_path is None:
            base_dir = Path(__file__).parent.parent.parent
            db_path = base_dir / "academy_progress.db"
        
        self.db_path = Path(db_path)
        self._init_tables()
    
    def _init_tables(self):
        """Создание таблиц для уровней"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Таблица уровней пользователей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS academy_levels (
                user_id TEXT PRIMARY KEY,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                xp_to_next INTEGER DEFAULT 100,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица истории начислений XP
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS academy_xp_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                xp_amount INTEGER NOT NULL,
                reason TEXT NOT NULL,
                awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Индексы
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_levels_user
            ON academy_levels(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_xp_history_user
            ON academy_xp_history(user_id, awarded_at)
        """)
        
        conn.commit()
        conn.close()
        logger.info("Levels tables initialized")
    
    def get_user_level(self, user_id: str) -> UserLevel:
        """
        Получить уровень пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            UserLevel с информацией об уровне
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, level, xp, xp_to_next, updated_at
            FROM academy_levels
            WHERE user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return UserLevel(
                user_id=row["user_id"],
                level=row["level"],
                xp=row["xp"],
                xp_to_next=row["xp_to_next"],
                rank_name=RANK_NAMES.get(row["level"], "Неизвестно"),
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now()
            )
        else:
            # Создать новый уровень для пользователя
            return self._create_user_level(user_id)
    
    def _create_user_level(self, user_id: str) -> UserLevel:
        """Создать начальный уровень для нового пользователя"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR IGNORE INTO academy_levels (user_id, level, xp, xp_to_next)
            VALUES (?, 1, 0, 100)
        """, (user_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created level 1 for user {user_id}")
        
        return UserLevel(
            user_id=user_id,
            level=1,
            xp=0,
            xp_to_next=100,
            rank_name=RANK_NAMES[1],
            updated_at=datetime.now()
        )
    
    def award_xp(self, user_id: str, xp_amount: int, reason: str) -> Dict:
        """
        Начислить опыт пользователю
        
        Args:
            user_id: ID пользователя
            xp_amount: Количество XP
            reason: Причина начисления
        
        Returns:
            Dict с информацией о начислении и возможном повышении уровня
        """
        # Получить текущий уровень
        current_level = self.get_user_level(user_id)
        
        # Добавить XP
        new_xp = current_level.xp + xp_amount
        new_level = current_level.level
        leveled_up = False
        
        # Проверить повышение уровня
        while new_level < 10:
            next_level = new_level + 1
            required_xp = XP_REQUIREMENTS.get(next_level, float('inf'))
            
            if new_xp >= required_xp:
                new_level = next_level
                leveled_up = True
            else:
                break
        
        # Вычислить XP до следующего уровня
        if new_level < 10:
            xp_to_next = XP_REQUIREMENTS[new_level + 1] - new_xp
        else:
            xp_to_next = 0  # Максимальный уровень
        
        # Обновить в базе данных
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Обновить уровень
        cursor.execute("""
            UPDATE academy_levels
            SET level = ?, xp = ?, xp_to_next = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (new_level, new_xp, xp_to_next, user_id))
        
        # Записать в историю
        cursor.execute("""
            INSERT INTO academy_xp_history (user_id, xp_amount, reason)
            VALUES (?, ?, ?)
        """, (user_id, xp_amount, reason))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Awarded {xp_amount} XP to user {user_id} for {reason}")
        
        return {
            "success": True,
            "xp_awarded": xp_amount,
            "new_xp": new_xp,
            "new_level": new_level,
            "leveled_up": leveled_up,
            "old_level": current_level.level,
            "rank_name": RANK_NAMES.get(new_level, "Неизвестно"),
            "xp_to_next": xp_to_next
        }
    
    def get_xp_history(self, user_id: str, limit: int = 10):
        """Получить историю начислений XP"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT xp_amount, reason, awarded_at
            FROM academy_xp_history
            WHERE user_id = ?
            ORDER BY awarded_at DESC
            LIMIT ?
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "xp_amount": row["xp_amount"],
                "reason": row["reason"],
                "awarded_at": row["awarded_at"]
            }
            for row in rows
        ]
