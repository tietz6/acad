# V3 Quick Start Guide - На Счастье Academy

## 🚀 Быстрый старт

### Что нового в V3?

5 главных функций:
1. ⭐ **Уровни и опыт** - система прогрессии с 10 уровнями
2. 📋 **Персональные планы** - адаптивное обучение на 7 дней
3. 🎯 **Ежедневные квесты** - задания с наградами XP
4. 📊 **Мегастатистика** - детальная аналитика для админов
5. 🎙️ **Настройки TTS** - персонализация озвучки

---

## 👤 Для пользователей

### Начало работы:

Для входа в систему используйте команду `/login` в Telegram боте.

Введите пароль доступа:
- **ADMIN_PASSWORD** - для доступа с правами администратора
- **USER_PASSWORD** - для обычного пользовательского доступа

Пароли настраиваются в `.env` файле.

### Команды бота:

```bash
/login          # Вход в систему по паролю
/level          # Посмотреть свой уровень, ранг и опыт
/plan           # Персональный план обучения
/plan_refresh   # Обновить план
/quests         # Ежедневные задания
/tts_settings   # Настройки озвучки уроков
```

### Как получать опыт (XP)?

| Действие | XP |
|----------|-----|
| 📖 Завершить урок | +10 |
| 📝 Пройти тест | +30 |
| 💯 Тест на 100% | +60 |
| 🎯 Выполнить квест | +10-50 |
| 📅 Ежедневная активность | +5 |

### Ранги:

1. Новичок (0 XP)
2. Стажер (100 XP)
3. Продвинутый (250 XP)
4. Специалист (500 XP)
5. Старший (1000 XP)
6. Эксперт (2000 XP)
7. Про (3500 XP)
8. Мастер (5500 XP)
9. Легенда (8000 XP)
10. Гуру (12000 XP)

---

## 🔐 Для администраторов

### Доступ к мегастатистике:

1. Используйте команду `/admin`
2. Выберите "🎯 Мегастатистика (V3)"

### Что показывает мегастатистика?

- 👥 **Активность пользователей** - сегодня, неделя, месяц
- 👔 **По ролям** - администраторы и пользователи
- 📚 **Топ модули** - самые изучаемые
- 😰 **Сложные модули** - низкий средний балл
- 📊 **Средний балл** - по всем тестам
- ⚠️ **Проблемные зоны** - модули с низкой успеваемостью

### API доступ:

```bash
GET /academy/v1/admin/mega_stats
Header: X-Admin-Token: ваш-ключ
```

---

## 🔧 Для разработчиков

### Новые API Endpoints:

```python
# Аутентификация
POST /academy/v1/auth/login
# Body: {"telegram_id": "123", "telegram_username": "user", "password": "..."}
# Returns: {"role": "admin" | "user"}

# Уровни
GET /academy/v1/user/{user_id}/level

# Планы обучения
GET /academy/v1/plan/{user_id}
POST /academy/v1/plan/{user_id}/generate

# Квесты
GET /academy/v1/quests/{user_id}
POST /academy/v1/quests/{user_id}/complete/{quest_id}

# Мегастатистика (требуется X-Admin-Token)
GET /academy/v1/admin/mega_stats

# Настройки TTS
GET /academy/v1/tts/settings/{user_id}
POST /academy/v1/tts/settings/{user_id}
```

### Новые таблицы в БД:

- `academy_levels` - уровни пользователей
- `academy_xp_history` - история начислений XP
- `academy_learning_plan` - персональные планы
- `academy_daily_quests` - ежедневные квесты
- `academy_tts_settings` - настройки TTS

### Автоматическая интеграция:

XP начисляется автоматически при:
- Завершении урока (через существующий endpoint)
- Прохождении теста (через существующий endpoint)
- Генерации TTS (если передан user_id)

Квесты завершаются автоматически при соответствующих действиях.

---

## 📖 Примеры использования

### Python (API):

```python
import httpx

# Получить уровень пользователя
async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:8080/academy/v1/user/12345/level"
    )
    level_data = response.json()
    print(f"Level: {level_data['level']}, XP: {level_data['xp']}")

# Сгенерировать план обучения
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8080/academy/v1/plan/12345/generate"
    )
    plan = response.json()
    print(f"Plan items: {len(plan['items'])}")

# Получить квесты
async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:8080/academy/v1/quests/12345"
    )
    quests = response.json()
    print(f"Active quests: {len([q for q in quests if q['status'] == 'active'])}")
```

### JavaScript (API):

```javascript
// Получить уровень пользователя
const response = await fetch('http://localhost:8080/academy/v1/user/12345/level');
const levelData = await response.json();
console.log(`Level: ${levelData.level}, XP: ${levelData.xp}`);

// Получить мегастатистику (с токеном)
const statsResponse = await fetch('http://localhost:8080/academy/v1/admin/mega_stats', {
    headers: {
        'X-Admin-Token': 'your-admin-token'
    }
});
const stats = await statsResponse.json();
console.log(`Total users: ${stats.total_users}`);
```

---

## ⚙️ Настройка

### .env файл:

```bash
# Обязательно
TELEGRAM_BOT_TOKEN=ваш-токен-бота
BACKEND_URL=http://127.0.0.1:8080
BACKEND_BASE_URL=http://127.0.0.1:8080

# Для админов
ADMIN_API_KEY=ваш-секретный-ключ

# Опционально для TTS
VOICE_API_KEY=ваш-api-ключ-assemblyai
```

---

## 🐛 Устранение неполадок

### Проблема: "База данных не создается"
**Решение:** Таблицы создаются автоматически при первом запуске. Убедитесь, что у вас есть права на запись в директорию `botfinal/`.

### Проблема: "Квесты не появляются"
**Решение:** Квесты генерируются автоматически при первом запросе дня. Используйте `/quests` в боте.

### Проблема: "XP не начисляется"
**Решение:** XP начисляется только при завершении уроков и тестов через API. Убедитесь, что используются правильные endpoints.

### Проблема: "Мегастатистика недоступна"
**Решение:** 
1. Убедитесь, что у пользователя роль `admin`
2. Проверьте, что `ADMIN_API_KEY` установлен в `.env`
3. Используйте заголовок `X-Admin-Token` в API запросах

---

## 📚 Дополнительная документация

- [V3_IMPLEMENTATION.md](./V3_IMPLEMENTATION.md) - Полная техническая документация
- [README.md](./README.md) - Общая документация системы
- [V2_IMPLEMENTATION.md](./V2_IMPLEMENTATION.md) - Документация V2

---

## 💡 Советы

### Для максимальной эффективности:

1. **Проверяйте уровень ежедневно** - `/level`
2. **Следуйте плану обучения** - `/plan`
3. **Выполняйте квесты** - `/quests`
4. **Настройте TTS под себя** - `/tts_settings`
5. **Учитесь регулярно** - получайте бонус за ежедневную активность

### Для администраторов:

1. **Мониторьте активность** - мегастатистика показывает тренды
2. **Анализируйте сложные модули** - возможно, их нужно улучшить
3. **Отслеживайте неиспользуемые модули** - они могут быть неактуальны
4. **Проверяйте средний балл** - индикатор качества обучения

---

## 🎉 Готово!

V3 готова к использованию. Все функции работают автоматически и не требуют дополнительной настройки.

**Начните с команды:** `/level`

---

© 2025 На Счастье Academy
