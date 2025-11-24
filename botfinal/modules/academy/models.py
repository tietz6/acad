"""
Pydantic models for Academy module
"""
from typing import List, Optional, Literal, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class AcademyQuestion(BaseModel):
    """Question model for tests"""
    id: str
    type: Literal["single", "multiple"] = "single"
    question: str
    options: List[str]
    correct_index: Optional[int] = None  # For single choice
    correct_indices: Optional[List[int]] = None  # For multiple choice
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "q1",
                "type": "single",
                "question": "What is S0 in the funnel?",
                "options": ["Lead created / new lead", "Sending demo", "Final payment"],
                "correct_index": 0
            }
        }


class AcademyTest(BaseModel):
    """Test model for module assessment"""
    id: str
    title: str
    questions: List[AcademyQuestion]
    passing_score: int = 70  # Percentage
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "m3_test1",
                "title": "Mini-test: sales funnel S0–S9",
                "questions": [],
                "passing_score": 70
            }
        }


class AcademyLesson(BaseModel):
    """Lesson model"""
    id: str
    title: str
    type: Literal["text", "video", "audio"] = "text"
    content: str
    duration_minutes: Optional[int] = None
    order: int = 0
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "m3_l1",
                "title": "Sales funnel S0–S9",
                "type": "text",
                "content": "Full lesson content here...",
                "order": 1
            }
        }


class AcademyModule(BaseModel):
    """Module model - main training unit"""
    id: str
    title: str
    description: str
    roles: List[str] = Field(default_factory=list)
    level: int = Field(default=1, ge=1, le=5)
    lessons: List[AcademyLesson] = Field(default_factory=list)
    tests: List[AcademyTest] = Field(default_factory=list)
    estimated_duration_minutes: Optional[int] = None
    f_block: Optional[str] = None  # F1-F7 блок
    products: List[str] = Field(default_factory=list)  # P1-P5 продукты
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "module3_sales_f1",
                "title": "Module 3 — Sales (F1)",
                "description": "How we sell with warmth and without pressure.",
                "roles": ["sales"],
                "level": 1,
                "lessons": [],
                "tests": []
            }
        }


class ModuleListItem(BaseModel):
    """Simplified module info for list views"""
    id: str
    title: str
    description: str
    roles: List[str]
    level: int
    lessons_count: int
    tests_count: int
    f_block: Optional[str] = None
    products: List[str] = Field(default_factory=list)


class LessonListItem(BaseModel):
    """Simplified lesson info for list views"""
    id: str
    title: str
    type: str
    order: int
    duration_minutes: Optional[int] = None


# Progress tracking models
class UserModuleProgress(BaseModel):
    """User progress for a specific lesson"""
    user_id: str
    module_id: str
    lesson_id: str
    status: Literal["not_started", "in_progress", "completed"] = "not_started"
    score: Optional[int] = None
    updated_at: datetime = Field(default_factory=datetime.now)


class UserProgressSummary(BaseModel):
    """Summary of user's progress"""
    user_id: str
    total_modules: int
    completed_modules: int
    total_lessons: int
    completed_lessons: int
    total_tests: int
    passed_tests: int
    progress_details: List[UserModuleProgress] = Field(default_factory=list)


class TestSubmission(BaseModel):
    """Test submission request"""
    user_id: str
    answers: List[int]  # List of selected option indices


class TestResult(BaseModel):
    """Test evaluation result"""
    test_id: str
    user_id: str
    score: int
    total_questions: int
    passed: bool
    correct_answers: List[int]
    user_answers: List[int]


class LessonCompletionRequest(BaseModel):
    """Request to mark lesson as completed"""
    user_id: str


class TTSRequest(BaseModel):
    """Request for text-to-speech generation"""
    voice_type: str = "ru_female"  # ru_female or ru_male


# ========================================
# V3 Models: Levels, Learning Plans, Quests, Enhanced TTS
# ========================================

class UserLevel(BaseModel):
    """Модель уровня и опыта пользователя"""
    user_id: str
    level: int = Field(default=1, ge=1, le=10)
    xp: int = Field(default=0, ge=0)
    xp_to_next: int
    rank_name: str
    updated_at: datetime = Field(default_factory=datetime.now)


class XPAward(BaseModel):
    """Начисление опыта"""
    user_id: str
    xp_amount: int
    reason: str
    awarded_at: datetime = Field(default_factory=datetime.now)


class LearningPlanItem(BaseModel):
    """Элемент персонального плана обучения"""
    user_id: str
    module_id: str
    lesson_id: str
    status: Literal["pending", "active", "done"] = "pending"
    priority: int = Field(default=1, ge=1, le=10)
    generated_at: datetime = Field(default_factory=datetime.now)


class LearningPlan(BaseModel):
    """Персональный план обучения"""
    user_id: str
    items: List[LearningPlanItem]
    generated_at: datetime
    valid_until: datetime


class DailyQuest(BaseModel):
    """Ежедневное задание"""
    quest_id: str
    user_id: str
    type: Literal["lesson", "test", "streak", "tts", "module"]
    description: str
    reward_xp: int
    status: Literal["active", "completed", "expired"] = "active"
    date: str  # YYYY-MM-DD
    created_at: datetime = Field(default_factory=datetime.now)


class QuestCompletion(BaseModel):
    """Завершение квеста"""
    user_id: str
    quest_id: str


class TTSSettings(BaseModel):
    """Настройки TTS для пользователя"""
    user_id: str
    voice: Literal["female", "male", "neutral"] = "female"
    speed: Literal["1.0", "1.25", "1.5"] = "1.0"
    format: Literal["ogg", "mp3"] = "mp3"
    updated_at: datetime = Field(default_factory=datetime.now)


class MegaStats(BaseModel):
    """Мега-статистика для администраторов"""
    # Общие данные
    total_users: int
    active_today: int
    active_week: int
    active_month: int
    
    # По ролям
    users_by_role: Dict[str, int]
    
    # По модулям
    top_modules: List[Dict[str, any]]
    hardest_modules: List[Dict[str, any]]
    unused_modules: List[Dict[str, any]]
    
    # По тестам
    average_score: float
    failing_questions: List[Dict[str, any]]
    low_performance_modules: List[Dict[str, any]]
    
    generated_at: datetime = Field(default_factory=datetime.now)
