"""
TTS Settings Service - Управление настройками TTS пользователей (V3)
Расширяет существующий tts_service.py новыми функциями
"""
import sqlite3
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
from .models import TTSSettings

logger = logging.getLogger(__name__)


class TTSSettingsService:
    """Сервис для управления персональными настройками TTS"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Инициализация сервиса"""
        if db_path is None:
            base_dir = Path(__file__).parent.parent.parent
            db_path = base_dir / "academy_progress.db"
        
        self.db_path = Path(db_path)
        self._init_tables()
    
    def _init_tables(self):
        """Создание таблицы настроек TTS"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Таблица настроек TTS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS academy_tts_settings (
                user_id TEXT PRIMARY KEY,
                voice TEXT DEFAULT 'female',
                speed TEXT DEFAULT '1.0',
                format TEXT DEFAULT 'mp3',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Индекс
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tts_settings_user
            ON academy_tts_settings(user_id)
        """)
        
        conn.commit()
        conn.close()
        logger.info("TTS settings tables initialized")
    
    def get_user_settings(self, user_id: str) -> TTSSettings:
        """
        Получить настройки TTS пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            TTSSettings с настройками пользователя
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, voice, speed, format, updated_at
            FROM academy_tts_settings
            WHERE user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return TTSSettings(
                user_id=row["user_id"],
                voice=row["voice"],
                speed=row["speed"],
                format=row["format"],
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now()
            )
        else:
            # Вернуть настройки по умолчанию
            return TTSSettings(
                user_id=user_id,
                voice="female",
                speed="1.0",
                format="mp3",
                updated_at=datetime.now()
            )
    
    def update_settings(
        self,
        user_id: str,
        voice: Optional[str] = None,
        speed: Optional[str] = None,
        format: Optional[str] = None
    ) -> TTSSettings:
        """
        Обновить настройки TTS пользователя
        
        Args:
            user_id: ID пользователя
            voice: Голос (female, male, neutral)
            speed: Скорость (1.0, 1.25, 1.5)
            format: Формат (ogg, mp3)
        
        Returns:
            Обновленные TTSSettings
        """
        # Получить текущие настройки
        current = self.get_user_settings(user_id)
        
        # Обновить только указанные параметры
        new_voice = voice if voice is not None else current.voice
        new_speed = speed if speed is not None else current.speed
        new_format = format if format is not None else current.format
        
        # Валидация значений
        if new_voice not in ["female", "male", "neutral"]:
            new_voice = "female"
        if new_speed not in ["1.0", "1.25", "1.5"]:
            new_speed = "1.0"
        if new_format not in ["ogg", "mp3"]:
            new_format = "mp3"
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO academy_tts_settings 
            (user_id, voice, speed, format, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, new_voice, new_speed, new_format))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Updated TTS settings for user {user_id}: voice={new_voice}, speed={new_speed}, format={new_format}")
        
        return TTSSettings(
            user_id=user_id,
            voice=new_voice,
            speed=new_speed,
            format=new_format,
            updated_at=datetime.now()
        )
    
    def apply_settings_to_audio(self, audio_path: Path, settings: TTSSettings) -> Path:
        """
        PLACEHOLDER: Применить настройки скорости и формата к аудио
        
        ⚠️ ВНИМАНИЕ: Эта функция является заглушкой и не применяет настройки в текущей версии.
        
        Для полной реализации потребуется:
        - Библиотека pydub для изменения скорости воспроизведения
        - Библиотека для конвертации между форматами (mp3 <-> ogg)
        
        В будущих версиях эта функция будет реализована.
        
        Args:
            audio_path: Путь к исходному аудиофайлу
            settings: Настройки TTS
        
        Returns:
            Путь к исходному файлу (без изменений)
        """
        # TODO: Реализовать изменение скорости и конвертацию формата
        # Требуется: pip install pydub
        logger.info(f"TTS settings placeholder: speed={settings.speed}, format={settings.format} (not applied)")
        return audio_path
