"""
Сервис для модуля F3 (Эмоциональная связь с клиентом)
Предоставляет функции для работы с контентом модуля F3

# TODO: В будущем добавить сохранение прогресса в БД
"""

import logging
from typing import Dict, List, Optional, Any

# Импортируем данные модуля F3
from ..module_f3_emotion import (
    module_id,
    title,
    description,
    level,
    estimated_duration_minutes,
    keywords,
    lessons,
    tests,
    role_visibility,
    f_block,
    products
)

logger = logging.getLogger(__name__)


def get_module() -> Dict[str, Any]:
    """
    Возвращает метаданные модуля F3
    
    Returns:
        Словарь с полной информацией о модуле:
        - id: идентификатор модуля
        - title: название
        - description: описание
        - level: уровень сложности
        - estimated_duration_minutes: примерное время прохождения
        - keywords: ключевые слова
        - lessons: список уроков
        - tests: список тестов
        - role_visibility: роли, которым доступен модуль
        - f_block: блок F
        - products: связанные продукты
    """
    try:
        return {
            "id": module_id,
            "title": title,
            "description": description,
            "level": level,
            "estimated_duration_minutes": estimated_duration_minutes,
            "keywords": keywords,
            "lessons": lessons,
            "tests": tests,
            "role_visibility": role_visibility,
            "f_block": f_block,
            "products": products
        }
    except Exception as e:
        logger.exception("Ошибка при получении данных модуля F3: %s", e)
        raise


def get_lesson(module_id_param: str, lesson_id: str) -> Optional[Dict[str, Any]]:
    """
    Возвращает один урок по его ID
    
    Args:
        module_id_param: идентификатор модуля (для проверки)
        lesson_id: идентификатор урока
        
    Returns:
        Словарь с данными урока (title, content_ru, order) или None
    """
    try:
        # Проверяем, что запрашивается наш модуль
        if module_id_param != module_id:
            logger.warning("Запрошен урок для неправильного модуля: %s", module_id_param)
            return None
        
        for lesson in lessons:
            if lesson.get("id") == lesson_id:
                return {
                    "id": lesson.get("id"),
                    "title": lesson.get("title"),
                    "content_ru": lesson.get("content_ru"),
                    "order": lesson.get("order"),
                    "type": lesson.get("type", "text"),
                    "duration_minutes": lesson.get("duration_minutes")
                }
        
        logger.warning("Урок не найден: %s", lesson_id)
        return None
        
    except Exception as e:
        logger.exception("Ошибка при получении урока %s: %s", lesson_id, e)
        raise


def start_lesson_for_user(user_id: str, module_id_param: str, lesson_id: str) -> Dict[str, Any]:
    """
    Отмечает начало прохождения урока пользователем
    
    Args:
        user_id: идентификатор пользователя
        module_id_param: идентификатор модуля
        lesson_id: идентификатор урока
        
    Returns:
        Словарь со статусом операции
        
    # TODO: Добавить реальное сохранение прогресса в БД
    """
    try:
        logger.info(
            "Пользователь %s начал урок %s в модуле %s",
            user_id, lesson_id, module_id_param
        )
        
        return {
            "success": True,
            "message": "Урок успешно начат",
            "user_id": user_id,
            "module_id": module_id_param,
            "lesson_id": lesson_id
        }
        
    except Exception as e:
        logger.exception(
            "Ошибка при старте урока для пользователя %s: %s",
            user_id, e
        )
        raise


def submit_test(
    user_id: str,
    module_id_param: str,
    test_id: str,
    answers: List[int]
) -> Dict[str, Any]:
    """
    Валидирует ответы пользователя на тест
    
    Args:
        user_id: идентификатор пользователя
        module_id_param: идентификатор модуля
        test_id: идентификатор теста
        answers: список индексов выбранных ответов
        
    Returns:
        Словарь с результатами теста:
        - score: набранный балл (процент)
        - passed: пройден ли тест (>= 70%)
        - correct_answers: список правильных ответов
        - user_answers: список ответов пользователя
        - total_questions: общее количество вопросов
    """
    try:
        # Проверяем, что запрашивается наш модуль
        if module_id_param != module_id:
            logger.warning("Отправка теста для неправильного модуля: %s", module_id_param)
            return {
                "score": 0,
                "passed": False,
                "correct_answers": [],
                "user_answers": answers,
                "total_questions": 0,
                "error": "Модуль не найден"
            }
        
        # Ищем тест
        test_data = None
        for test in tests:
            if test.get("id") == test_id:
                test_data = test
                break
        
        if not test_data:
            logger.warning("Тест не найден: %s", test_id)
            return {
                "score": 0,
                "passed": False,
                "correct_answers": [],
                "user_answers": answers,
                "total_questions": 0,
                "error": "Тест не найден"
            }
        
        questions = test_data.get("questions", [])
        total_questions = len(questions)
        
        if total_questions == 0:
            logger.warning("Тест %s не содержит вопросов", test_id)
            return {
                "score": 0,
                "passed": False,
                "correct_answers": [],
                "user_answers": answers,
                "total_questions": 0,
                "error": "Тест не содержит вопросов"
            }
        
        # Получаем правильные ответы
        correct_answers = [q.get("correct_index", 0) for q in questions]
        
        # Считаем правильные ответы
        correct_count = 0
        for i, correct_idx in enumerate(correct_answers):
            if i < len(answers) and answers[i] == correct_idx:
                correct_count += 1
        
        # Вычисляем процент
        score = int((correct_count / total_questions) * 100)
        
        # Проходной балл 70%
        passing_score = test_data.get("passing_score", 70)
        passed = score >= passing_score
        
        logger.info(
            "Пользователь %s завершил тест %s: %d%% (%s)",
            user_id, test_id, score, "пройден" if passed else "не пройден"
        )
        
        return {
            "score": score,
            "passed": passed,
            "correct_answers": correct_answers,
            "user_answers": answers,
            "total_questions": total_questions
        }
        
    except Exception as e:
        logger.exception(
            "Ошибка при проверке теста для пользователя %s: %s",
            user_id, e
        )
        raise
