"""
FastAPI Router for Academy Module
"""
import os
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse
import httpx

from .models import (
    AcademyModule, AcademyLesson, ModuleListItem, LessonListItem,
    UserProgressSummary, TestSubmission, TestResult, TTSRequest
)
from .repository import ModuleRepository
from .progress_repository import ProgressRepository
from .service import AcademyService

logger = logging.getLogger(__name__)

# Configuration
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8080")

# Initialize repositories and service
module_repo = ModuleRepository()
progress_repo = ProgressRepository()
service = AcademyService(module_repo, progress_repo)

# Create router
router = APIRouter(
    prefix="/academy/v1",
    tags=["academy"],
    responses={404: {"description": "Not found"}}
)


@router.get("/modules", response_model=List[ModuleListItem])
async def list_modules(role: Optional[str] = None):
    """
    List all available training modules
    
    Args:
        role: Optional filter by role (e.g., 'sales', 'production')
    
    Returns:
        List of modules
    """
    try:
        modules = service.get_modules_list(role)
        return modules
    except Exception as e:
        logger.error(f"Error listing modules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modules/{module_id}", response_model=AcademyModule)
async def get_module(module_id: str):
    """
    Get full details of a specific module
    
    Args:
        module_id: Module identifier
    
    Returns:
        Complete module with lessons and tests
    """
    module = service.get_module_detail(module_id)
    if not module:
        raise HTTPException(status_code=404, detail=f"Module {module_id} not found")
    return module


@router.get("/modules/{module_id}/lessons", response_model=List[LessonListItem])
async def list_lessons(module_id: str):
    """
    List all lessons in a module
    
    Args:
        module_id: Module identifier
    
    Returns:
        List of lessons
    """
    lessons = service.get_lessons_list(module_id)
    if lessons is None:
        raise HTTPException(status_code=404, detail=f"Module {module_id} not found")
    return lessons


@router.get("/modules/{module_id}/lessons/{lesson_id}", response_model=AcademyLesson)
async def get_lesson(module_id: str, lesson_id: str):
    """
    Get a specific lesson
    
    Args:
        module_id: Module identifier
        lesson_id: Lesson identifier
    
    Returns:
        Lesson details
    """
    lesson = service.get_lesson(module_id, lesson_id)
    if not lesson:
        raise HTTPException(
            status_code=404, 
            detail=f"Lesson {lesson_id} not found in module {module_id}"
        )
    return lesson


@router.post("/progress/{user_id}/lessons/{module_id}/{lesson_id}/complete")
async def complete_lesson(user_id: str, module_id: str, lesson_id: str):
    """
    Mark a lesson as completed for a user
    
    Args:
        user_id: User identifier
        module_id: Module identifier
        lesson_id: Lesson identifier
    
    Returns:
        Success message
    """
    success = service.complete_lesson(user_id, module_id, lesson_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Lesson {lesson_id} not found in module {module_id}"
        )
    
    return {
        "success": True,
        "message": "Lesson marked as completed",
        "user_id": user_id,
        "module_id": module_id,
        "lesson_id": lesson_id
    }


@router.post("/progress/{user_id}/lessons/{module_id}/{lesson_id}/start")
async def start_lesson(user_id: str, module_id: str, lesson_id: str):
    """
    Mark a lesson as in progress for a user
    
    Args:
        user_id: User identifier
        module_id: Module identifier
        lesson_id: Lesson identifier
    
    Returns:
        Success message
    """
    success = service.start_lesson(user_id, module_id, lesson_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Lesson {lesson_id} not found in module {module_id}"
        )
    
    return {
        "success": True,
        "message": "Lesson started",
        "user_id": user_id,
        "module_id": module_id,
        "lesson_id": lesson_id
    }


@router.get("/progress/{user_id}", response_model=UserProgressSummary)
async def get_user_progress(user_id: str):
    """
    Get comprehensive progress summary for a user
    
    Args:
        user_id: User identifier
    
    Returns:
        Progress summary
    """
    try:
        summary = service.get_user_progress_summary(user_id)
        return summary
    except Exception as e:
        logger.error(f"Error getting user progress: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/modules/{module_id}/tests/{test_id}/submit", response_model=TestResult)
async def submit_test(
    module_id: str,
    test_id: str,
    submission: TestSubmission = Body(...)
):
    """
    Submit test answers for evaluation
    
    Args:
        module_id: Module identifier
        test_id: Test identifier
        submission: Test submission with user_id and answers
    
    Returns:
        Test result with score and pass/fail status
    """
    result = service.evaluate_test(
        module_id=module_id,
        test_id=test_id,
        user_id=submission.user_id,
        answers=submission.answers
    )
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Test {test_id} not found in module {module_id}"
        )
    
    return result


@router.post("/lessons/{module_id}/{lesson_id}/tts")
async def generate_lesson_tts(
    module_id: str,
    lesson_id: str,
    tts_request: TTSRequest = Body(default=TTSRequest())
):
    """
    Generate text-to-speech audio for a lesson
    
    Args:
        module_id: Module identifier
        lesson_id: Lesson identifier
        tts_request: TTS configuration (voice_type)
    
    Returns:
        Audio URL and metadata
    """
    # Get lesson content
    lesson = service.get_lesson(module_id, lesson_id)
    if not lesson:
        raise HTTPException(
            status_code=404,
            detail=f"Lesson {lesson_id} not found in module {module_id}"
        )
    
    # Call internal TTS endpoint
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_BASE_URL}/voice/v1/tts",
                params={
                    "text": lesson.content,
                    "voice_type": tts_request.voice_type
                }
            )
            
            if response.status_code == 200:
                tts_result = response.json()
                return {
                    "success": True,
                    "lesson_id": lesson_id,
                    "module_id": module_id,
                    "audio_url": f"{BACKEND_BASE_URL}{tts_result['audio_url']}",
                    "voice_type": tts_request.voice_type
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="TTS generation failed"
                )
    except httpx.RequestError as e:
        logger.error(f"TTS request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"TTS service unavailable: {str(e)}")


@router.get("/search")
async def search_content(query: str):
    """
    Search for modules and lessons
    
    Args:
        query: Search query string
    
    Returns:
        Search results
    """
    if not query or len(query) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
    
    try:
        results = service.search_content(query)
        return results
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modules/{module_id}/next-lesson/{user_id}")
async def get_next_lesson(module_id: str, user_id: str):
    """
    Get the next uncompleted lesson for a user in a module
    
    Args:
        module_id: Module identifier
        user_id: User identifier
    
    Returns:
        Next lesson or message if all completed
    """
    lesson = service.get_next_lesson(user_id, module_id)
    
    if not lesson:
        # Check if module exists
        module = service.get_module_detail(module_id)
        if not module:
            raise HTTPException(status_code=404, detail=f"Module {module_id} not found")
        
        return {
            "completed": True,
            "message": "All lessons in this module are completed",
            "module_id": module_id
        }
    
    return {
        "completed": False,
        "lesson": lesson
    }


# Health check for the academy module
@router.get("/health")
async def academy_health():
    """Academy module health check"""
    modules_count = len(module_repo.list_modules())
    return {
        "status": "healthy",
        "module": "academy",
        "modules_loaded": modules_count
    }
