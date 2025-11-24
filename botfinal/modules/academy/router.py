"""
FastAPI Router for Academy Module
"""
import os
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Body, Header
from fastapi.responses import JSONResponse
import httpx

from .models import (
    AcademyModule, AcademyLesson, ModuleListItem, LessonListItem,
    UserProgressSummary, TestSubmission, TestResult, TTSRequest
)
from .repository import ModuleRepository
from .progress_repository import ProgressRepository
from .service import AcademyService
from .tts_service import tts_service

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
async def list_modules(role: Optional[str] = None, user_id: Optional[str] = None):
    """
    List all available training modules
    
    Args:
        role: Optional filter by role (e.g., 'sales_manager', 'generator')
        user_id: Optional user ID to filter by user's role
    
    Returns:
        List of modules
    """
    try:
        # If user_id provided, get their role
        if user_id and not role:
            role = progress_repo.get_user_role(user_id)
        
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
        tts_request: TTS configuration (voice_type: ru_female or ru_male)
    
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
    
    # Generate TTS using the TTS service with caching
    try:
        # Use lesson_id as cache key for consistent file naming
        cache_key = f"{module_id}_{lesson_id}"
        
        tts_result = await tts_service.generate_tts(
            text=lesson.content,
            voice_type=tts_request.voice_type,
            cache_key=cache_key
        )
        
        return {
            "success": True,
            "lesson_id": lesson_id,
            "module_id": module_id,
            "audio_url": f"{BACKEND_BASE_URL}{tts_result['audio_url']}",
            "voice_type": tts_request.voice_type,
            "provider": tts_result.get("provider", "unknown"),
            "cached": tts_result.get("cached", False)
        }
    
    except Exception as e:
        logger.error(f"TTS generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


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


# User role management endpoints
@router.post("/users/{user_id}/role")
async def set_user_role(user_id: str, role_data: dict = Body(...)):
    """
    Set or update user's role
    
    Args:
        user_id: User identifier
        role_data: JSON with 'role' field
    
    Returns:
        Success message with role
    """
    role = role_data.get('role')
    if not role:
        raise HTTPException(status_code=400, detail="Role is required")
    
    valid_roles = ['sales_manager', 'generator', 'admin', 'other']
    if role not in valid_roles:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )
    
    progress_repo.set_user_role(user_id, role)
    
    return {
        "success": True,
        "user_id": user_id,
        "role": role,
        "message": f"Role set to {role}"
    }


@router.get("/users/{user_id}/role")
async def get_user_role(user_id: str):
    """
    Get user's current role
    
    Args:
        user_id: User identifier
    
    Returns:
        User role information
    """
    role = progress_repo.get_user_role(user_id)
    
    return {
        "user_id": user_id,
        "role": role if role else "not_set"
    }


# Admin analytics endpoints
def verify_admin_token(x_admin_token: Optional[str] = Header(None)):
    """Verify admin API key"""
    admin_key = os.getenv("ADMIN_API_KEY")
    if not admin_key:
        # If no admin key is set in production, this is a misconfiguration
        # In development, we allow access for testing
        import sys
        if 'pytest' not in sys.modules and os.getenv("ENVIRONMENT") == "production":
            raise HTTPException(
                status_code=500,
                detail="Server misconfiguration: ADMIN_API_KEY not set"
            )
        return True
    
    if not x_admin_token or x_admin_token != admin_key:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid or missing X-Admin-Token header"
        )
    return True


@router.get("/admin/users")
async def get_all_users(x_admin_token: Optional[str] = Header(None)):
    """
    Get list of all users with their progress
    
    Requires X-Admin-Token header
    
    Returns:
        List of users with stats
    """
    verify_admin_token(x_admin_token)
    
    try:
        users = progress_repo.get_all_users()
        return {
            "total_users": len(users),
            "users": users
        }
    except Exception as e:
        logger.error(f"Error getting all users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/users/{user_id}/progress")
async def get_admin_user_progress(user_id: str, x_admin_token: Optional[str] = Header(None)):
    """
    Get detailed progress for a specific user (admin view)
    
    Requires X-Admin-Token header
    
    Args:
        user_id: User identifier
    
    Returns:
        Detailed user progress
    """
    verify_admin_token(x_admin_token)
    
    try:
        # Get user role
        role = progress_repo.get_user_role(user_id)
        
        # Get progress summary
        summary = service.get_user_progress_summary(user_id)
        
        # Get test results
        test_results = progress_repo.get_test_results(user_id)
        
        return {
            "user_id": user_id,
            "role": role,
            "summary": summary,
            "test_results": test_results
        }
    except Exception as e:
        logger.error(f"Error getting admin user progress: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/stats/summary")
async def get_admin_stats_summary(x_admin_token: Optional[str] = Header(None)):
    """
    Get aggregated statistics across all users
    
    Requires X-Admin-Token header
    
    Returns:
        Summary statistics
    """
    verify_admin_token(x_admin_token)
    
    try:
        users = progress_repo.get_all_users()
        all_modules = module_repo.list_modules()
        
        # Calculate aggregate stats
        total_users = len(users)
        users_with_progress = sum(1 for u in users if u['completed_lessons'] > 0)
        
        # Module completion stats
        module_completions = {}
        for user in users:
            progress = progress_repo.get_user_progress(user['user_id'])
            for module in all_modules:
                module_lessons = {lesson.id for lesson in module.lessons}
                completed_lessons = {
                    p.lesson_id for p in progress 
                    if p.module_id == module.id and p.status == 'completed'
                }
                
                if module_lessons and module_lessons.issubset(completed_lessons):
                    module_completions[module.id] = module_completions.get(module.id, 0) + 1
        
        # Top modules
        top_modules = sorted(
            module_completions.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:3]
        
        # Average completion rate
        total_lessons = sum(len(m.lessons) for m in all_modules)
        total_completed = sum(u['completed_lessons'] for u in users)
        avg_completion = (total_completed / (total_users * total_lessons * 1.0) * 100) if total_users > 0 and total_lessons > 0 else 0
        
        return {
            "total_users": total_users,
            "users_with_progress": users_with_progress,
            "total_modules": len(all_modules),
            "average_completion_rate": round(avg_completion, 2),
            "top_modules": [
                {
                    "module_id": mid,
                    "completions": count,
                    "title": next((m.title for m in all_modules if m.id == mid), mid)
                }
                for mid, count in top_modules
            ],
            "total_lessons_available": total_lessons,
            "total_lessons_completed": total_completed
        }
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Badge endpoints
@router.get("/users/{user_id}/badges")
async def get_user_badges(user_id: str):
    """
    Get all badges earned by a user
    
    Args:
        user_id: User identifier
    
    Returns:
        List of badges
    """
    try:
        badges = progress_repo.get_user_badges(user_id)
        return {
            "user_id": user_id,
            "total_badges": len(badges),
            "badges": badges
        }
    except Exception as e:
        logger.error(f"Error getting user badges: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Daily progress endpoints
@router.get("/users/{user_id}/daily-progress")
async def get_user_daily_progress(user_id: str, days: int = 30):
    """
    Get daily progress for a user
    
    Args:
        user_id: User identifier
        days: Number of days to retrieve (default: 30)
    
    Returns:
        Daily progress records
    """
    try:
        daily_progress = progress_repo.get_daily_progress(user_id, days)
        return {
            "user_id": user_id,
            "days": days,
            "progress": daily_progress
        }
    except Exception as e:
        logger.error(f"Error getting daily progress: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# User profile endpoint
@router.get("/users/{user_id}/profile")
async def get_user_profile(user_id: str):
    """
    Get comprehensive user profile
    
    Args:
        user_id: User identifier
    
    Returns:
        User profile with role, progress, badges, and stats
    """
    try:
        # Get role
        role = progress_repo.get_user_role(user_id)
        
        # Get progress summary
        summary = service.get_user_progress_summary(user_id)
        
        # Get badges
        badges = progress_repo.get_user_badges(user_id)
        
        # Get user info from database
        conn = progress_repo._get_connection() if hasattr(progress_repo, '_get_connection') else None
        import sqlite3
        conn = sqlite3.connect(str(progress_repo.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT created_at FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        created_at = row['created_at'] if row else None
        
        # Calculate completion percentage
        completion_percentage = 0
        if summary.total_lessons > 0:
            completion_percentage = int((summary.completed_lessons / summary.total_lessons) * 100)
        
        # Calculate rating (0-100 based on multiple factors)
        rating = 0
        if summary.total_lessons > 0:
            lessons_weight = (summary.completed_lessons / summary.total_lessons) * 50
            modules_weight = (summary.completed_modules / summary.total_modules) * 30 if summary.total_modules > 0 else 0
            tests_weight = (summary.passed_tests / summary.total_tests) * 20 if summary.total_tests > 0 else 0
            rating = int(lessons_weight + modules_weight + tests_weight)
        
        # Get modules in progress
        in_progress_modules = []
        progress_list = progress_repo.get_user_progress(user_id)
        module_status = {}
        for p in progress_list:
            if p.module_id not in module_status:
                module_status[p.module_id] = {'started': False, 'completed': False}
            if p.status == 'in_progress':
                module_status[p.module_id]['started'] = True
            elif p.status == 'completed':
                module_status[p.module_id]['completed'] = True
        
        for module_id, status in module_status.items():
            if status['started'] and not status['completed']:
                module = module_repo.get_module(module_id)
                if module:
                    in_progress_modules.append({
                        'id': module.id,
                        'title': module.title
                    })
        
        return {
            "user_id": user_id,
            "role": role if role else "not_set",
            "completed_lessons": summary.completed_lessons,
            "total_lessons": summary.total_lessons,
            "completion_percentage": completion_percentage,
            "modules_in_progress": in_progress_modules,
            "joined_date": created_at,
            "rating": rating,
            "badges_count": len(badges),
            "completed_modules": summary.completed_modules,
            "total_modules": summary.total_modules,
            "passed_tests": summary.passed_tests,
            "total_tests": summary.total_tests
        }
    except Exception as e:
        logger.error(f"Error getting user profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Reload modules endpoint
@router.post("/admin/reload")
async def reload_modules(x_admin_token: Optional[str] = Header(None)):
    """
    Reload all modules from disk (admin only)
    
    Requires X-Admin-Token header
    
    Returns:
        Reload status
    """
    verify_admin_token(x_admin_token)
    
    try:
        # Get modules count before reload
        old_count = len(module_repo.list_modules())
        
        # Reload modules
        module_repo.reload()
        
        # Get modules count after reload
        new_count = len(module_repo.list_modules())
        
        return {
            "success": True,
            "message": "Modules reloaded successfully",
            "modules_before": old_count,
            "modules_after": new_count
        }
    except Exception as e:
        logger.error(f"Error reloading modules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Module statistics for admin
@router.get("/admin/modules/stats")
async def get_module_stats(x_admin_token: Optional[str] = Header(None)):
    """
    Get statistics for each module (admin only)
    
    Requires X-Admin-Token header
    
    Returns:
        Module statistics with completion data
    """
    verify_admin_token(x_admin_token)
    
    try:
        all_modules = module_repo.list_modules()
        all_users = progress_repo.get_all_users()
        
        module_stats = []
        
        for module in all_modules:
            users_started = 0
            users_completed = 0
            total_completion = 0
            
            user_scores = []  # For calculating top users
            
            for user in all_users:
                user_progress = progress_repo.get_user_progress(user['user_id'], module.id)
                
                if user_progress:
                    users_started += 1
                    
                    # Check if module is completed
                    module_lesson_ids = {lesson.id for lesson in module.lessons}
                    completed_lesson_ids = {p.lesson_id for p in user_progress if p.status == 'completed'}
                    
                    if module_lesson_ids and module_lesson_ids.issubset(completed_lesson_ids):
                        users_completed += 1
                    
                    # Calculate completion percentage for this user
                    if module_lesson_ids:
                        user_completion = (len(completed_lesson_ids) / len(module_lesson_ids)) * 100
                        total_completion += user_completion
                        user_scores.append({
                            'user_id': user['user_id'],
                            'completion': user_completion
                        })
            
            # Calculate average completion
            avg_completion = (total_completion / users_started) if users_started > 0 else 0
            
            # Get top 3 users
            top_users = sorted(user_scores, key=lambda x: x['completion'], reverse=True)[:3]
            
            module_stats.append({
                "module_id": module.id,
                "module_title": module.title,
                "users_started": users_started,
                "users_completed": users_completed,
                "average_completion_percentage": round(avg_completion, 2),
                "top_users": top_users
            })
        
        return {
            "total_modules": len(all_modules),
            "module_stats": module_stats
        }
    except Exception as e:
        logger.error(f"Error getting module stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
