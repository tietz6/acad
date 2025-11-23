"""
Academy Service - Business logic for the training system
"""
import logging
from typing import List, Optional, Dict, Tuple
from .models import (
    AcademyModule, AcademyLesson, AcademyTest, 
    UserModuleProgress, UserProgressSummary,
    TestResult, ModuleListItem, LessonListItem
)
from .repository import ModuleRepository
from .progress_repository import ProgressRepository

logger = logging.getLogger(__name__)


class AcademyService:
    """Service layer for Academy business logic"""
    
    def __init__(self, module_repo: ModuleRepository, progress_repo: ProgressRepository):
        """Initialize service with repositories"""
        self.module_repo = module_repo
        self.progress_repo = progress_repo
    
    def get_modules_list(self, role: Optional[str] = None) -> List[ModuleListItem]:
        """
        Get simplified list of modules
        
        Args:
            role: Optional role filter
        
        Returns:
            List of module summaries
        """
        modules = self.module_repo.list_modules(role)
        
        return [
            ModuleListItem(
                id=m.id,
                title=m.title,
                description=m.description,
                roles=m.roles,
                level=m.level,
                lessons_count=len(m.lessons),
                tests_count=len(m.tests),
                f_block=m.f_block,
                products=m.products
            )
            for m in modules
        ]
    
    def get_module_detail(self, module_id: str) -> Optional[AcademyModule]:
        """Get full module details"""
        return self.module_repo.get_module(module_id)
    
    def get_lessons_list(self, module_id: str) -> Optional[List[LessonListItem]]:
        """
        Get list of lessons for a module
        
        Args:
            module_id: Module identifier
        
        Returns:
            List of lesson summaries or None if module not found
        """
        module = self.module_repo.get_module(module_id)
        if not module:
            return None
        
        return [
            LessonListItem(
                id=lesson.id,
                title=lesson.title,
                type=lesson.type,
                order=lesson.order,
                duration_minutes=lesson.duration_minutes
            )
            for lesson in sorted(module.lessons, key=lambda l: l.order)
        ]
    
    def get_lesson(self, module_id: str, lesson_id: str) -> Optional[AcademyLesson]:
        """Get a specific lesson"""
        return self.module_repo.get_lesson(module_id, lesson_id)
    
    def complete_lesson(self, user_id: str, module_id: str, lesson_id: str) -> bool:
        """
        Mark a lesson as completed
        
        Args:
            user_id: User identifier
            module_id: Module identifier
            lesson_id: Lesson identifier
        
        Returns:
            True if successful
        """
        # Verify lesson exists
        lesson = self.module_repo.get_lesson(module_id, lesson_id)
        if not lesson:
            return False
        
        self.progress_repo.mark_lesson_completed(user_id, module_id, lesson_id)
        return True
    
    def start_lesson(self, user_id: str, module_id: str, lesson_id: str) -> bool:
        """
        Mark a lesson as in progress
        
        Args:
            user_id: User identifier
            module_id: Module identifier
            lesson_id: Lesson identifier
        
        Returns:
            True if successful
        """
        # Verify lesson exists
        lesson = self.module_repo.get_lesson(module_id, lesson_id)
        if not lesson:
            return False
        
        self.progress_repo.mark_lesson_in_progress(user_id, module_id, lesson_id)
        return True
    
    def get_user_progress_summary(self, user_id: str) -> UserProgressSummary:
        """
        Get comprehensive progress summary for a user
        
        Args:
            user_id: User identifier
        
        Returns:
            Progress summary
        """
        progress = self.progress_repo.get_user_progress(user_id)
        test_results = self.progress_repo.get_test_results(user_id)
        
        # Count completed lessons
        completed_lessons = sum(1 for p in progress if p.status == 'completed')
        
        # Count unique completed modules (modules where all lessons are completed)
        modules = self.module_repo.list_modules()
        completed_modules = 0
        
        for module in modules:
            module_progress = [p for p in progress if p.module_id == module.id]
            module_lesson_ids = {lesson.id for lesson in module.lessons}
            completed_lesson_ids = {p.lesson_id for p in module_progress if p.status == 'completed'}
            
            if module_lesson_ids and module_lesson_ids.issubset(completed_lesson_ids):
                completed_modules += 1
        
        # Count passed tests
        passed_tests = sum(1 for t in test_results if t['passed'])
        
        return UserProgressSummary(
            user_id=user_id,
            total_modules=len(modules),
            completed_modules=completed_modules,
            total_lessons=sum(len(m.lessons) for m in modules),
            completed_lessons=completed_lessons,
            total_tests=sum(len(m.tests) for m in modules),
            passed_tests=passed_tests,
            progress_details=progress
        )
    
    def evaluate_test(self, module_id: str, test_id: str, user_id: str, 
                     answers: List[int]) -> Optional[TestResult]:
        """
        Evaluate a test submission
        
        Args:
            module_id: Module identifier
            test_id: Test identifier
            user_id: User identifier
            answers: List of answer indices selected by user
        
        Returns:
            Test result or None if test not found
        """
        test = self.module_repo.get_test(module_id, test_id)
        if not test:
            return None
        
        if len(answers) != len(test.questions):
            logger.warning(f"Answer count mismatch: expected {len(test.questions)}, got {len(answers)}")
            return None
        
        # Evaluate answers
        correct_answers = []
        correct_count = 0
        
        for i, question in enumerate(test.questions):
            if question.type == "single":
                correct_answer = question.correct_index
                if correct_answer is not None:
                    correct_answers.append(correct_answer)
                    if i < len(answers) and answers[i] == correct_answer:
                        correct_count += 1
            elif question.type == "multiple" and question.correct_indices:
                # For multiple choice, we'll just take the first correct index for simplicity
                correct_answers.append(question.correct_indices[0] if question.correct_indices else 0)
                if i < len(answers) and answers[i] in question.correct_indices:
                    correct_count += 1
        
        # Calculate score percentage
        score = int((correct_count / len(test.questions)) * 100) if test.questions else 0
        passed = score >= test.passing_score
        
        # Save result
        self.progress_repo.save_test_result(
            user_id=user_id,
            module_id=module_id,
            test_id=test_id,
            score=score,
            total_questions=len(test.questions),
            passed=passed
        )
        
        return TestResult(
            test_id=test_id,
            user_id=user_id,
            score=score,
            total_questions=len(test.questions),
            passed=passed,
            correct_answers=correct_answers,
            user_answers=answers
        )
    
    def search_content(self, query: str) -> Dict:
        """
        Search for modules and lessons
        
        Args:
            query: Search query
        
        Returns:
            Search results
        """
        return self.module_repo.search(query)
    
    def get_next_lesson(self, user_id: str, module_id: str) -> Optional[AcademyLesson]:
        """
        Get the next incomplete lesson for a user in a module
        
        Args:
            user_id: User identifier
            module_id: Module identifier
        
        Returns:
            Next lesson or None
        """
        module = self.module_repo.get_module(module_id)
        if not module:
            return None
        
        progress = self.progress_repo.get_user_progress(user_id, module_id)
        completed_lesson_ids = {p.lesson_id for p in progress if p.status == 'completed'}
        
        # Find first uncompleted lesson
        for lesson in sorted(module.lessons, key=lambda l: l.order):
            if lesson.id not in completed_lesson_ids:
                return lesson
        
        return None  # All lessons completed
