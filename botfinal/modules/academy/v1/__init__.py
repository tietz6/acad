"""
Пакет v1 для модулей Academy
Экспортирует роутеры модулей для интеграции с FastAPI
"""

from .module_f3_router import router as module_f3_router

__all__ = ["module_f3_router"]
