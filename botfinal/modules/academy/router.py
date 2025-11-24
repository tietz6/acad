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
from .notification_service import notification_service

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
        Success message with XP award (V3)
    """
    success = service.complete_lesson(user_id, module_id, lesson_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Lesson {lesson_id} not found in module {module_id}"
        )
    
    # V3: Award XP for completing lesson
    try:
        xp_result = levels_service.award_xp(
            user_id=user_id,
            xp_amount=10,
            reason=f"Completed lesson {lesson_id} in {module_id}"
        )
        
        # V3: Check and complete quest
        quest_result = quests_service.check_and_complete_quest(user_id, "lesson")
        if quest_result.get("quest_completed"):
            # Award additional XP for quest
            quest_xp = levels_service.award_xp(
                user_id=user_id,
                xp_amount=quest_result["reward_xp"],
                reason=f"Completed daily quest: lesson"
            )
            xp_result["quest_xp"] = quest_xp
        
        # V3: Update learning plan status
        learning_plan_service.update_item_status(user_id, module_id, lesson_id, "done")
    except Exception as e:
        logger.warning(f"Error awarding XP or updating plan: {e}")
        xp_result = None
    
    return {
        "success": True,
        "message": "Lesson marked as completed",
        "user_id": user_id,
        "module_id": module_id,
        "lesson_id": lesson_id,
        "xp_awarded": xp_result
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
        Test result with score and pass/fail status (V3: includes XP awards)
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
    
    # V3: Award XP for test completion
    try:
        # Base XP for completing test
        xp_amount = 30
        
        # Bonus XP for perfect score
        if result.passed and result.score == result.total_questions:
            xp_amount = 60
        
        xp_result = levels_service.award_xp(
            user_id=submission.user_id,
            xp_amount=xp_amount,
            reason=f"Completed test {test_id} in {module_id}"
        )
        
        # V3: Check and complete quest
        quest_result = quests_service.check_and_complete_quest(submission.user_id, "test")
        if quest_result.get("quest_completed"):
            # Award additional XP for quest
            quest_xp = levels_service.award_xp(
                user_id=submission.user_id,
                xp_amount=quest_result["reward_xp"],
                reason=f"Completed daily quest: test"
            )
        
        # Add XP info to result (using dict conversion)
        result_dict = result.model_dump()
        result_dict["xp_awarded"] = xp_result
        
        return result_dict
    except Exception as e:
        logger.warning(f"Error awarding XP for test: {e}")
        return result


@router.post("/lessons/{module_id}/{lesson_id}/tts")
async def generate_lesson_tts(
    module_id: str,
    lesson_id: str,
    user_id: Optional[str] = None,
    tts_request: TTSRequest = Body(default=TTSRequest())
):
    """
    Generate text-to-speech audio for a lesson
    
    Args:
        module_id: Module identifier
        lesson_id: Lesson identifier
        user_id: Optional user ID (V3: for quest completion)
        tts_request: TTS configuration (voice_type: ru_female or ru_male)
    
    Returns:
        Audio URL and metadata (V3: includes quest completion if user_id provided)
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
        
        response = {
            "success": True,
            "lesson_id": lesson_id,
            "module_id": module_id,
            "audio_url": f"{BACKEND_BASE_URL}{tts_result['audio_url']}",
            "voice_type": tts_request.voice_type,
            "provider": tts_result.get("provider", "unknown"),
            "cached": tts_result.get("cached", False)
        }
        
        # V3: Check and complete TTS quest if user_id provided
        if user_id:
            try:
                quest_result = quests_service.check_and_complete_quest(user_id, "tts")
                if quest_result.get("quest_completed"):
                    # Award XP for quest
                    xp_result = levels_service.award_xp(
                        user_id=user_id,
                        xp_amount=quest_result["reward_xp"],
                        reason=f"Completed daily quest: tts"
                    )
                    response["quest_completed"] = True
                    response["xp_awarded"] = xp_result
            except Exception as e:
                logger.warning(f"Error checking TTS quest: {e}")
        
        return response
    
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
async def reload_modules(
    x_admin_token: Optional[str] = Header(None),
    notify_users: bool = False
):
    """
    Reload all modules from disk (admin only)
    
    Requires X-Admin-Token header
    
    Args:
        notify_users: If True, notify all users about new modules
    
    Returns:
        Reload status with list of new modules
    """
    verify_admin_token(x_admin_token)
    
    try:
        # Get module IDs before reload
        old_modules = {m.id: m for m in module_repo.list_modules()}
        old_count = len(old_modules)
        
        # Reload modules
        module_repo.reload()
        
        # Get module IDs after reload
        new_modules = {m.id: m for m in module_repo.list_modules()}
        new_count = len(new_modules)
        
        # Detect new modules
        new_module_ids = set(new_modules.keys()) - set(old_modules.keys())
        new_modules_info = []
        
        for module_id in new_module_ids:
            module = new_modules[module_id]
            new_modules_info.append({
                "id": module.id,
                "title": module.title,
                "description": module.description
            })
        
        # Send notifications if requested and there are new modules
        notifications_sent = False
        if notify_users and new_modules_info:
            try:
                # Get all users
                all_users = progress_repo.get_all_users()
                user_ids = [user['user_id'] for user in all_users]
                
                # Send notification for each new module
                for module_info in new_modules_info:
                    await notification_service.notify_new_module(
                        module_title=module_info['title'],
                        module_description=module_info['description'],
                        user_ids=user_ids
                    )
                
                notifications_sent = True
                logger.info(f"Sent notifications about {len(new_modules_info)} new modules to {len(user_ids)} users")
            
            except Exception as notif_error:
                logger.error(f"Error sending notifications: {notif_error}", exc_info=True)
        
        return {
            "success": True,
            "message": "Modules reloaded successfully",
            "modules_before": old_count,
            "modules_after": new_count,
            "new_modules": new_modules_info,
            "notifications_sent": notifications_sent
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


# ========================================
# V3 ENDPOINTS: Levels, Learning Plans, Quests, Mega Stats, Enhanced TTS
# ========================================

from .models import (
    UserLevel, LearningPlan, DailyQuest, QuestCompletion,
    TTSSettings, MegaStats
)
from .levels_service import LevelsService
from .learning_plan_service import LearningPlanService
from .quests_service import QuestsService
from .mega_stats_service import MegaStatsService
from .tts_settings_service import TTSSettingsService

# Initialize V3 services
levels_service = LevelsService()
learning_plan_service = LearningPlanService()
quests_service = QuestsService()
mega_stats_service = MegaStatsService()
tts_settings_service = TTSSettingsService()


@router.get("/user/{user_id}/level", response_model=UserLevel)
async def get_user_level(user_id: str):
    """
    Получить уровень и опыт пользователя
    
    Args:
        user_id: ID пользователя
    
    Returns:
        UserLevel с информацией об уровне, XP и ранге
    """
    try:
        level = levels_service.get_user_level(user_id)
        return level
    except Exception as e:
        logger.error(f"Error getting user level: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plan/{user_id}", response_model=LearningPlan)
async def get_learning_plan(user_id: str):
    """
    Получить персональный план обучения пользователя
    
    Args:
        user_id: ID пользователя
    
    Returns:
        LearningPlan с элементами плана
    """
    try:
        plan = learning_plan_service.get_user_plan(user_id)
        return plan
    except Exception as e:
        logger.error(f"Error getting learning plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plan/{user_id}/generate", response_model=LearningPlan)
async def generate_learning_plan(user_id: str):
    """
    Сгенерировать новый персональный план обучения
    
    Args:
        user_id: ID пользователя
    
    Returns:
        Новый LearningPlan
    """
    try:
        # Получить роль пользователя
        user_role = progress_repo.get_user_role(user_id) or "other"
        
        # Сгенерировать план
        plan = learning_plan_service.generate_plan(
            user_id=user_id,
            user_role=user_role,
            module_repo=module_repo,
            progress_repo=progress_repo
        )
        
        return plan
    except Exception as e:
        logger.error(f"Error generating learning plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quests/{user_id}", response_model=List[DailyQuest])
async def get_daily_quests(user_id: str):
    """
    Получить ежедневные квесты пользователя
    
    Args:
        user_id: ID пользователя
    
    Returns:
        Список активных квестов на сегодня
    """
    try:
        quests = quests_service.get_daily_quests(user_id)
        return quests
    except Exception as e:
        logger.error(f"Error getting daily quests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quests/{user_id}/complete/{quest_id}")
async def complete_quest(user_id: str, quest_id: str):
    """
    Отметить квест как выполненный
    
    Args:
        user_id: ID пользователя
        quest_id: ID квеста
    
    Returns:
        Результат выполнения с начисленным XP
    """
    try:
        # Завершить квест
        result = quests_service.complete_quest(user_id, quest_id)
        
        if result["success"]:
            # Начислить XP
            xp_result = levels_service.award_xp(
                user_id=user_id,
                xp_amount=result["reward_xp"],
                reason=f"Completed quest: {quest_id}"
            )
            
            result["xp_awarded"] = xp_result
        
        return result
    except Exception as e:
        logger.error(f"Error completing quest: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/mega_stats", response_model=MegaStats)
async def get_mega_stats(x_admin_token: Optional[str] = Header(None)):
    """
    Получить мегастатистику для администраторов
    Требуется X-Admin-Token
    
    Returns:
        MegaStats с полной статистикой по системе
    """
    # Проверить админский токен
    admin_token = os.getenv("ADMIN_API_KEY")
    if admin_token and x_admin_token != admin_token:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        stats = mega_stats_service.get_mega_stats(module_repo)
        return stats
    except Exception as e:
        logger.error(f"Error getting mega stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tts/settings/{user_id}", response_model=TTSSettings)
async def get_tts_settings(user_id: str):
    """
    Получить настройки TTS пользователя
    
    Args:
        user_id: ID пользователя
    
    Returns:
        TTSSettings с настройками голоса, скорости и формата
    """
    try:
        settings = tts_settings_service.get_user_settings(user_id)
        return settings
    except Exception as e:
        logger.error(f"Error getting TTS settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts/settings/{user_id}", response_model=TTSSettings)
async def update_tts_settings(
    user_id: str,
    voice: Optional[str] = Body(None),
    speed: Optional[str] = Body(None),
    format: Optional[str] = Body(None)
):
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
    try:
        settings = tts_settings_service.update_settings(
            user_id=user_id,
            voice=voice,
            speed=speed,
            format=format
        )
        return settings
    except Exception as e:
        logger.error(f"Error updating TTS settings: {e}", exc_info=True)
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
