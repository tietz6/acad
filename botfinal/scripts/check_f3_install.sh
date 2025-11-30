#!/bin/bash
# Скрипт проверки установки модуля F3
# Проверяет синтаксис и импорт модуля

set -e

echo "=== Проверка модуля F3 ==="
echo ""

# Переход в корневую директорию botfinal
cd "$(dirname "$0")/.."

echo "1. Проверка синтаксиса Python файлов..."
python3 -m py_compile modules/academy/module_f3_emotion.py
echo "   ✓ module_f3_emotion.py"

python3 -m py_compile modules/academy/v1/module_f3_service.py
echo "   ✓ module_f3_service.py"

python3 -m py_compile modules/academy/v1/module_f3_router.py
echo "   ✓ module_f3_router.py"

python3 -m py_compile modules/academy/v1/__init__.py
echo "   ✓ v1/__init__.py"

echo ""
echo "2. Проверка импорта модуля..."
python3 -c "
import sys
sys.path.insert(0, '.')
from modules.academy.v1.module_f3_service import get_module
module = get_module()
print(f'   ✓ Модуль загружен: {module[\"id\"]}')
print(f'   ✓ Название: {module[\"title\"]}')
print(f'   ✓ Уроков: {len(module[\"lessons\"])}')
print(f'   ✓ Тестов: {len(module[\"tests\"])}')
"

echo ""
echo "=== Все проверки пройдены успешно! ==="
