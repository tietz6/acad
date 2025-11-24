# SALESBOT Training System - Примеры использования API

Этот документ содержит практические примеры использования эндпоинтов Academy API.

## Базовый URL

```
http://localhost:8080
```

## Аутентификация

Обычные эндпоинты не требуют аутентификации. Админ-эндпоинты требуют заголовок `X-Admin-Token`.

## Примеры API

### 1. Список всех обучающих модулей

**Запрос:**
```bash
curl http://localhost:8080/academy/v1/modules
```

**Ответ:**
```json
[
  {
    "id": "module1_intro",
    "title": "Модуль 1 — Введение в компанию На Счастье",
    "description": "Приветственный модуль: культура компании, ценности и миссия",
    "roles": ["all"],
    "level": 1,
    "lessons_count": 3,
    "tests_count": 1,
    "f_block": "F1",
    "products": ["P1", "P2", "P3", "P4", "P5"]
  }
]
```

### 2. Фильтрация модулей по роли

**Запрос:**
```bash
curl "http://localhost:8080/academy/v1/modules?role=sales_manager"
```

**Ответ:**
Возвращает только модули, относящиеся к роли sales_manager (менеджер по продажам).

### 3. Фильтрация модулей по user_id (автоматическая по роли)

**Запрос:**
```bash
curl "http://localhost:8080/academy/v1/modules?user_id=123456789"
```

Автоматически загрузит роль пользователя и отфильтрует модули.

### 4. Получить детали модуля

**Запрос:**
```bash
curl http://localhost:8080/academy/v1/modules/module3_sales_f1
```

**Ответ:**
```json
{
  "id": "module3_sales_f1",
  "title": "Модуль 3 — Продажи (F1)",
  "description": "Как мы продаём с теплотой и без давления...",
  "roles": ["sales_manager"],
  "level": 1,
  "f_block": "F1",
  "products": ["P1", "P2", "P3", "P4"],
  "lessons": [
    {
      "id": "m3_l1",
      "title": "Воронка продаж S0–S9",
      "type": "text",
      "content": "...",
      "duration_minutes": 30,
      "order": 1
    }
  ],
  "tests": [...]
}
```

### 5. Получить конкретный урок

**Запрос:**
```bash
curl http://localhost:8080/academy/v1/modules/module3_sales_f1/lessons/m3_l1
```

**Ответ:**
```json
{
  "id": "m3_l1",
  "title": "Воронка продаж S0–S9",
  "type": "text",
  "content": "Полный контент урока на русском...",
  "duration_minutes": 30,
  "order": 1
}
```

### 6. Отметить урок как завершённый

**Запрос:**
```bash
curl -X POST \
  http://localhost:8080/academy/v1/progress/user123/lessons/module3_sales_f1/m3_l1/complete
```

**Ответ:**
```json
{
  "success": true,
  "message": "Lesson marked as completed",
  "user_id": "user123",
  "module_id": "module3_sales_f1",
  "lesson_id": "m3_l1"
}
```

### 7. Получить прогресс пользователя

**Запрос:**
```bash
curl http://localhost:8080/academy/v1/progress/user123
```

**Ответ:**
```json
{
  "user_id": "user123",
  "total_modules": 3,
  "completed_modules": 0,
  "total_lessons": 9,
  "completed_lessons": 1,
  "total_tests": 3,
  "passed_tests": 0,
  "progress_details": [
    {
      "user_id": "user123",
      "module_id": "module3_sales_f1",
      "lesson_id": "m3_l1",
      "status": "completed",
      "score": null,
      "updated_at": "2025-11-23T22:30:00"
    }
  ]
}
```

### 8. Отправить ответы на тест

**Запрос:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "answers": [1, 2, 2, 2, 1]
  }' \
  http://localhost:8080/academy/v1/modules/module3_sales_f1/tests/m3_test1/submit
```

**Ответ:**
```json
{
  "test_id": "m3_test1",
  "user_id": "user123",
  "score": 100,
  "total_questions": 5,
  "passed": true,
  "correct_answers": [1, 2, 2, 2, 1],
  "user_answers": [1, 2, 2, 2, 1]
}
```

### 9. Генерация TTS аудио для урока (женский голос)

**Запрос:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"voice_type": "ru_female"}' \
  http://localhost:8080/academy/v1/lessons/module3_sales_f1/m3_l1/tts
```

**Ответ:**
```json
{
  "success": true,
  "lesson_id": "m3_l1",
  "module_id": "module3_sales_f1",
  "audio_url": "http://127.0.0.1:8080/voice/v1/audio/abc123.mp3",
  "voice_type": "ru_female"
}
```

### 10. Генерация TTS аудио (мужской голос)

**Запрос:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"voice_type": "ru_male"}' \
  http://localhost:8080/academy/v1/lessons/module3_sales_f1/m3_l1/tts
```

### 11. Поиск контента

**Запрос:**
```bash
curl "http://localhost:8080/academy/v1/search?query=продажи"
```

**Ответ:**
```json
{
  "modules": [
    {
      "id": "module3_sales_f1",
      "title": "Модуль 3 — Продажи (F1)",
      "...": "..."
    }
  ],
  "lessons": [
    {
      "module_id": "module3_sales_f1",
      "module_title": "Модуль 3 — Продажи (F1)",
      "lesson": {
        "id": "m3_l1",
        "title": "Воронка продаж S0–S9",
        "...": "..."
      }
    }
  ]
}
```

## Управление ролями пользователей

### 12. Установить роль пользователя

**Запрос:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"role": "sales_manager"}' \
  http://localhost:8080/academy/v1/users/123456789/role
```

**Ответ:**
```json
{
  "success": true,
  "user_id": "123456789",
  "role": "sales_manager",
  "message": "Role set to sales_manager"
}
```

**Доступные роли:**
- `sales_manager` - Менеджер по продажам
- `generator` - Генератор / Продакшн
- `admin` - Руководитель / Админ
- `other` - Другое

### 13. Получить роль пользователя

**Запрос:**
```bash
curl http://localhost:8080/academy/v1/users/123456789/role
```

**Ответ:**
```json
{
  "user_id": "123456789",
  "role": "sales_manager"
}
```

## Админ-аналитика (требуется X-Admin-Token)

### 14. Получить список всех пользователей

**Запрос:**
```bash
curl -H "X-Admin-Token: your-secret-key" \
  http://localhost:8080/academy/v1/admin/users
```

**Ответ:**
```json
{
  "total_users": 5,
  "users": [
    {
      "user_id": "123456789",
      "role": "sales_manager",
      "created_at": "2025-11-23 20:00:00",
      "updated_at": "2025-11-23 22:00:00",
      "completed_modules": 1,
      "completed_lessons": 3,
      "passed_tests": 1,
      "last_activity": "2025-11-23 22:00:00"
    }
  ]
}
```

### 15. Получить детальный прогресс пользователя (админ)

**Запрос:**
```bash
curl -H "X-Admin-Token: your-secret-key" \
  http://localhost:8080/academy/v1/admin/users/123456789/progress
```

**Ответ:**
```json
{
  "user_id": "123456789",
  "role": "sales_manager",
  "summary": {
    "user_id": "123456789",
    "total_modules": 2,
    "completed_modules": 1,
    "total_lessons": 6,
    "completed_lessons": 3,
    "total_tests": 2,
    "passed_tests": 1,
    "progress_details": [...]
  },
  "test_results": [
    {
      "user_id": "123456789",
      "module_id": "module3_sales_f1",
      "test_id": "m3_test1",
      "score": 100,
      "total_questions": 5,
      "passed": 1,
      "submitted_at": "2025-11-23 21:30:00"
    }
  ]
}
```

### 16. Получить сводную статистику

**Запрос:**
```bash
curl -H "X-Admin-Token: your-secret-key" \
  http://localhost:8080/academy/v1/admin/stats/summary
```

**Ответ:**
```json
{
  "total_users": 5,
  "users_with_progress": 3,
  "total_modules": 3,
  "average_completion_rate": 45.67,
  "top_modules": [
    {
      "module_id": "module1_intro",
      "completions": 2,
      "title": "Модуль 1 — Введение в компанию На Счастье"
    },
    {
      "module_id": "module3_sales_f1",
      "completions": 1,
      "title": "Модуль 3 — Продажи (F1)"
    }
  ],
  "total_lessons_available": 9,
  "total_lessons_completed": 7
}
```

## Примеры Telegram Bot

### Команды бота

```
/start          - Приветственное сообщение и выбор роли (при первом запуске)
/help           - Показать все доступные команды
/academy        - Просмотр обучающих модулей (фильтруется по роли)
/progress       - Просмотр вашего прогресса обучения
/search воронка - Поиск контента со словом "воронка"
```

### Типичный пользовательский поток

1. Пользователь отправляет `/start`
2. Если роль не установлена:
   - Бот показывает кнопки выбора роли
   - Пользователь выбирает: "👔 Менеджер по продажам"
   - Бот подтверждает: "✅ Роль сохранена: Менеджер по продажам"
3. Пользователь отправляет `/academy`
4. Бот показывает список доступных модулей для его роли
5. Пользователь выбирает "Модуль 3 — Продажи (F1)"
6. Бот показывает детали модуля с уроками
7. Пользователь выбирает "📖 Воронка продаж S0–S9"
8. Бот отображает содержимое урока с кнопками:
   - "✅ Отметить как пройденный"
   - "🔊 Послушать урок"
   - "◀️ Назад к модулю"
9. Пользователь нажимает "🔊 Послушать урок"
10. Бот показывает выбор голоса:
    - "👩 Женский голос"
    - "👨 Мужской голос"
11. Пользователь выбирает голос, бот генерирует и отправляет аудио
12. Пользователь нажимает "✅ Отметить как пройденный"
13. Пользователь может пройти тест по модулю
14. Пользователь проверяет прогресс с `/progress`

## Основные системные эндпоинты

### Проверка здоровья

```bash
curl http://localhost:8080/api/public/v1/health
```

Ответ:
```json
{
  "status": "healthy",
  "service": "SALESBOT"
}
```

### Проверка здоровья модуля Academy

```bash
curl http://localhost:8080/academy/v1/health
```

Ответ:
```json
{
  "status": "healthy",
  "module": "academy",
  "modules_loaded": 3
}
```

## Примеры структуры YAML модулей

### Модуль с ролями и метаданными

```yaml
id: "module3_sales_f1"
title: "Модуль 3 — Продажи (F1)"
description: "Как мы продаём с теплотой и без давления"
roles: ["sales_manager"]  # Доступен только менеджерам
f_block: "F1"  # Блок F1 - Продажи
products: ["P1", "P2", "P3", "P4"]  # Продукты: песня, фото, мультик, кавер
level: 1
estimated_duration_minutes: 90

lessons:
  - id: "m3_l1"
    title: "Воронка продаж S0–S9"
    type: "text"
    content: |
      Понимание нашей воронки продаж...
    duration_minutes: 30
    order: 1

tests:
  - id: "m3_test1"
    title: "Тест по воронке продаж"
    passing_score: 80
    questions:
      - id: "q1"
        type: "single"
        question: "Что такое S0 в воронке продаж?"
        options:
          - "Первый контакт с клиентом"
          - "Лид создан / новый лид"
          - "Отправка демо"
          - "Финальный платёж"
        correct_index: 1
```

### Модуль для всех ролей

```yaml
id: "module1_intro"
title: "Модуль 1 — Введение в компанию На Счастье"
description: "Приветственный модуль"
roles: ["all"]  # Доступен всем
f_block: "F1"
products: ["P1", "P2", "P3", "P4", "P5"]
level: 1
estimated_duration_minutes: 45
```

## Советы по интеграции

1. **User ID**: Используйте Telegram user ID или ID вашей внутренней системы
2. **Отслеживание прогресса**: Вызывайте эндпоинты прогресса после каждого завершения урока/теста
3. **Кеширование**: Рассмотрите кеширование данных модулей на стороне клиента
4. **Обработка ошибок**: Всегда проверяйте статус коды ответов
5. **Длинный контент**: Используйте пагинацию/чанкинг для длинных уроков
6. **TTS**: Предварительно генерируйте аудио для часто запрашиваемых уроков

## Ограничения скорости

В настоящее время ограничений скорости нет. Рассмотрите их добавление для производственного использования.

## Формат ответов об ошибках

Все ответы об ошибках следуют этому формату:

```json
{
  "detail": "Сообщение об ошибке здесь"
}
```

Распространённые HTTP статус коды:
- `200` - Успех
- `400` - Неверный запрос
- `401` - Не авторизован (для админ-эндпоинтов)
- `404` - Ресурс не найден
- `500` - Внутренняя ошибка сервера
