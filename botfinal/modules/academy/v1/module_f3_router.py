"""
FastAPI Router для модуля F3 (Эмоциональная связь с клиентом)
Предоставляет REST API для работы с модулем F3
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from . import module_f3_service

logger = logging.getLogger(__name__)

# Создаём роутер
router = APIRouter(
    prefix="/academy/v1/modules/module_f3",
    tags=["academy_modules"]
)


class TestSubmissionRequest(BaseModel):
    """Модель запроса для отправки теста"""
    user_id: str
    answers: List[int]


class TestResultResponse(BaseModel):
    """Модель ответа с результатами теста"""
    score: int
    passed: bool
    correct_answers: List[int]
    user_answers: List[int]
    total_questions: int


@router.get("/")
async def get_module():
    """
    Получить метаданные модуля F3
    
    Returns:
        Полная информация о модуле: id, title, description, lessons, tests и т.д.
    """
    try:
        module_data = module_f3_service.get_module()
        return module_data
    except Exception as e:
        logger.exception("Ошибка при получении модуля F3: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при загрузке модуля: {str(e)}"
        )


@router.get("/lessons/{lesson_id}")
async def get_lesson(lesson_id: str):
    """
    Получить конкретный урок модуля F3
    
    Args:
        lesson_id: идентификатор урока
        
    Returns:
        Данные урока: title, content_ru, order
    """
    try:
        lesson = module_f3_service.get_lesson("module_f3_emotion", lesson_id)
        
        if not lesson:
            raise HTTPException(
                status_code=404,
                detail=f"Урок {lesson_id} не найден в модуле F3"
            )
        
        return lesson
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Ошибка при получении урока %s: %s", lesson_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при загрузке урока: {str(e)}"
        )


@router.post("/progress/{user_id}/lessons/{lesson_id}/start")
async def start_lesson(user_id: str, lesson_id: str):
    """
    Начать прохождение урока для пользователя
    
    Args:
        user_id: идентификатор пользователя
        lesson_id: идентификатор урока
        
    Returns:
        Статус операции
    """
    try:
        result = module_f3_service.start_lesson_for_user(
            user_id=user_id,
            module_id_param="module_f3_emotion",
            lesson_id=lesson_id
        )
        return result
        
    except Exception as e:
        logger.exception(
            "Ошибка при старте урока %s для пользователя %s: %s",
            lesson_id, user_id, e
        )
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при старте урока: {str(e)}"
        )


@router.post("/tests/{test_id}/submit", response_model=TestResultResponse)
async def submit_test(
    test_id: str,
    submission: TestSubmissionRequest = Body(...)
):
    """
    Отправить ответы на тест
    
    Args:
        test_id: идентификатор теста
        submission: JSON с user_id и answers
        
    Returns:
        Результат теста: score, passed, correct_answers, user_answers, total_questions
    """
    try:
        result = module_f3_service.submit_test(
            user_id=submission.user_id,
            module_id_param="module_f3_emotion",
            test_id=test_id,
            answers=submission.answers
        )
        
        # Проверяем на ошибку
        if result.get("error"):
            raise HTTPException(
                status_code=404,
                detail=result["error"]
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Ошибка при проверке теста %s для пользователя %s: %s",
            test_id, submission.user_id, e
        )
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при проверке теста: {str(e)}"
        )
