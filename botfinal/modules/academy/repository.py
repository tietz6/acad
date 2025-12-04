"""
Module Repository - Loads training modules from YAML files and Python modules
"""
import os
import sys
import logging
import importlib.util
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
        self.modules_dir = Path(__file__).parent  # Directory containing Python modules
        self.modules: Dict[str, AcademyModule] = {}
        self._module_keywords: Dict[str, List[str]] = {}  # Store keywords separately
        self._load_modules()
    
    def _load_modules(self):
        """Load all modules from YAML files and Python module files"""
        # Load YAML modules from data directory
        self._load_yaml_modules()
        
        # Load Python modules from modules/academy directory
        self._load_python_modules()
        
        logger.info(f"Total modules loaded: {len(self.modules)}")
    
    def _load_yaml_modules(self):
        """Load modules from YAML files"""
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
    
    def _load_python_modules(self):
        """Load modules from Python module files matching module*.py pattern"""
        if not self.modules_dir.exists():
            logger.warning(f"Modules directory does not exist: {self.modules_dir}")
            return
        
        # Find all module*.py files (includes module4.py, module_p1.py, etc.)
        module_files = list(self.modules_dir.glob("module*.py"))
        
        # Exclude module7_tech.py from loading (F7 module removed from system)
        module_files = [f for f in module_files if f.stem != "module7_tech"]
        
        for module_file in module_files:
            try:
                # Dynamically import the module
                module_name = module_file.stem
                spec = importlib.util.spec_from_file_location(module_name, module_file)
                if spec and spec.loader:
                    py_module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = py_module
                    spec.loader.exec_module(py_module)
                    
                    # Check if module has required attributes
                    if not hasattr(py_module, 'module_id'):
                        logger.warning(f"Module {module_name} missing 'module_id' attribute")
                        continue
                    
                    # Extract module data
                    module_id = py_module.module_id
                    title = getattr(py_module, 'title', 'Untitled')
                    description = getattr(py_module, 'description', '')
                    role_visibility = getattr(py_module, 'role_visibility', [])
                    estimated_duration_minutes = getattr(py_module, 'estimated_duration_minutes', None)
                    keywords = getattr(py_module, 'keywords', [])
                    
                    # Parse lessons with content_ru support
                    lessons = []
                    for idx, lesson_data in enumerate(getattr(py_module, 'lessons', [])):
                        # Support both 'content' and 'content_ru'
                        if 'content_ru' in lesson_data and 'content' not in lesson_data:
                            lesson_data['content'] = lesson_data['content_ru']
                        lesson_data['order'] = lesson_data.get('order', idx + 1)
                        lessons.append(AcademyLesson(**lesson_data))
                    
                    # Parse tests
                    tests = []
                    for test_data in getattr(py_module, 'tests', []):
                        questions = []
                        for q_data in test_data.get('questions', []):
                            questions.append(AcademyQuestion(**q_data))
                        test_data['questions'] = questions
                        tests.append(AcademyTest(**test_data))
                    
                    # Create module
                    module_data = {
                        'id': module_id,
                        'title': title,
                        'description': description,
                        'roles': role_visibility,
                        'level': getattr(py_module, 'level', 1),
                        'lessons': lessons,
                        'tests': tests,
                        'estimated_duration_minutes': estimated_duration_minutes,
                        'f_block': getattr(py_module, 'f_block', None),
                        'products': getattr(py_module, 'products', [])
                    }
                    
                    module = AcademyModule(**module_data)
                    self.modules[module.id] = module
                    
                    # Store keywords in a separate dictionary for search
                    if not hasattr(self, '_module_keywords'):
                        self._module_keywords = {}
                    self._module_keywords[module.id] = keywords
                    
                    logger.info(f"Loaded Python module: {module.id} - {module.title}")
                    
            except Exception as e:
                logger.error(f"Failed to load Python module from {module_file}: {e}", exc_info=True)
    
    def list_modules(self, role: Optional[str] = None) -> List[AcademyModule]:
        """
        List all modules, optionally filtered by role
        
        Args:
            role: Filter modules by role (only "admin" or "user")
        
        Returns:
            List of modules
        """
        modules = list(self.modules.values())
        
        if role:
            # Simplified role system: admin sees all, user sees all non-admin-only modules
            # Modules with old roles (sales_manager, generator, etc.) are treated as visible to all users
            if role == "admin":
                # Admin sees everything
                pass
            else:
                # User (non-admin) sees all modules except admin-only ones
                # Filter out modules that have only "admin" in their roles list
                modules = [m for m in modules if "admin" not in m.roles or len(m.roles) == 0 or len(m.roles) > 1 or "all" in m.roles]
        
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
        Search modules and lessons by query string (enhanced global search)
        
        Args:
            query: Search query (substring match in titles/content/tests/keywords)
        
        Returns:
            Dictionary with 'modules' and 'lessons' lists
        """
        query_lower = query.lower()
        results = {
            'modules': [],
            'lessons': []
        }
        
        for module in self.modules.values():
            module_matched = False
            
            # Search in module title and description
            if query_lower in module.title.lower() or query_lower in module.description.lower():
                module_matched = True
            
            # Search in keywords if available
            keywords = self._module_keywords.get(module.id, [])
            if isinstance(keywords, list):
                for keyword in keywords:
                    if query_lower in str(keyword).lower():
                        module_matched = True
                        break
            
            # Search in tests
            if not module_matched:
                for test in module.tests:
                    if query_lower in test.title.lower():
                        module_matched = True
                        break
                    # Search in test questions
                    for question in test.questions:
                        if query_lower in question.question.lower():
                            module_matched = True
                            break
                        # Search in answer options
                        for option in question.options:
                            if query_lower in option.lower():
                                module_matched = True
                                break
                    if module_matched:
                        break
            
            if module_matched:
                results['modules'].append(module)
            
            # Search in lessons (title and content)
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
        self._module_keywords.clear()
        self._load_modules()
