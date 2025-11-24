"""
Module Repository - Loads training modules from YAML files
"""
import os
import logging
from pathlib import Path
from typing import List, Optional, Dict
import yaml
from .models import AcademyModule, AcademyLesson, AcademyTest, AcademyQuestion

logger = logging.getLogger(__name__)


class ModuleRepository:
    """Repository for loading and managing training modules"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize repository with data directory"""
        if data_dir is None:
            # Default to data/academy/modules relative to botfinal directory
            base_dir = Path(__file__).parent.parent.parent
            data_dir = base_dir / "data" / "academy" / "modules"
        
        self.data_dir = Path(data_dir)
        self.modules: Dict[str, AcademyModule] = {}
        self._load_modules()
    
    def _load_modules(self):
        """Load all modules from YAML files"""
        if not self.data_dir.exists():
            logger.warning(f"Modules data directory does not exist: {self.data_dir}")
            return
        
        yaml_files = list(self.data_dir.glob("*.yaml")) + list(self.data_dir.glob("*.yml"))
        
        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                if not data:
                    logger.warning(f"Empty YAML file: {yaml_file}")
                    continue
                
                # Parse lessons
                lessons = []
                for idx, lesson_data in enumerate(data.get('lessons', [])):
                    lesson_data['order'] = lesson_data.get('order', idx + 1)
                    lessons.append(AcademyLesson(**lesson_data))
                
                # Parse tests
                tests = []
                for test_data in data.get('tests', []):
                    questions = []
                    for q_data in test_data.get('questions', []):
                        questions.append(AcademyQuestion(**q_data))
                    test_data['questions'] = questions
                    tests.append(AcademyTest(**test_data))
                
                # Create module
                module_data = {
                    'id': data['id'],
                    'title': data['title'],
                    'description': data['description'],
                    'roles': data.get('roles', []),
                    'level': data.get('level', 1),
                    'lessons': lessons,
                    'tests': tests,
                    'estimated_duration_minutes': data.get('estimated_duration_minutes'),
                    'f_block': data.get('f_block'),
                    'products': data.get('products', [])
                }
                
                module = AcademyModule(**module_data)
                self.modules[module.id] = module
                logger.info(f"Loaded module: {module.id} - {module.title}")
                
            except Exception as e:
                logger.error(f"Failed to load module from {yaml_file}: {e}", exc_info=True)
        
        logger.info(f"Total modules loaded: {len(self.modules)}")
    
    def list_modules(self, role: Optional[str] = None) -> List[AcademyModule]:
        """
        List all modules, optionally filtered by role
        
        Args:
            role: Filter modules by role (e.g., "sales_manager", "generator")
        
        Returns:
            List of modules
        """
        modules = list(self.modules.values())
        
        if role:
            # Filter: include if role matches, or if module has "all" in roles, or if roles is empty
            modules = [m for m in modules if role in m.roles or "all" in m.roles or len(m.roles) == 0]
        
        return sorted(modules, key=lambda m: (m.level, m.title))
    
    def get_module(self, module_id: str) -> Optional[AcademyModule]:
        """
        Get a specific module by ID
        
        Args:
            module_id: Module identifier
        
        Returns:
            Module or None if not found
        """
        return self.modules.get(module_id)
    
    def get_lesson(self, module_id: str, lesson_id: str) -> Optional[AcademyLesson]:
        """
        Get a specific lesson from a module
        
        Args:
            module_id: Module identifier
            lesson_id: Lesson identifier
        
        Returns:
            Lesson or None if not found
        """
        module = self.get_module(module_id)
        if not module:
            return None
        
        for lesson in module.lessons:
            if lesson.id == lesson_id:
                return lesson
        
        return None
    
    def get_test(self, module_id: str, test_id: str) -> Optional[AcademyTest]:
        """
        Get a specific test from a module
        
        Args:
            module_id: Module identifier
            test_id: Test identifier
        
        Returns:
            Test or None if not found
        """
        module = self.get_module(module_id)
        if not module:
            return None
        
        for test in module.tests:
            if test.id == test_id:
                return test
        
        return None
    
    def search(self, query: str) -> Dict[str, List]:
        """
        Search modules and lessons by query string
        
        Args:
            query: Search query (substring match in titles/content)
        
        Returns:
            Dictionary with 'modules' and 'lessons' lists
        """
        query_lower = query.lower()
        results = {
            'modules': [],
            'lessons': []
        }
        
        for module in self.modules.values():
            # Search in module title and description
            if query_lower in module.title.lower() or query_lower in module.description.lower():
                results['modules'].append(module)
            
            # Search in lessons
            for lesson in module.lessons:
                if query_lower in lesson.title.lower() or query_lower in lesson.content.lower():
                    results['lessons'].append({
                        'module_id': module.id,
                        'module_title': module.title,
                        'lesson': lesson
                    })
        
        return results
    
    def reload(self):
        """Reload all modules from disk"""
        self.modules.clear()
        self._load_modules()
