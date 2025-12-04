"""
SALESBOT Training System - Telegram Bot
Connects to the FastAPI backend for Academy training functionality
"""
import os
import logging
import asyncio
from typing import Optional, List, Dict
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, MessageHandler, filters
)
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Backend URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8080")

# Conversation states
SELECTING_ROLE, SELECTING_MODULE, VIEWING_LESSON, TAKING_TEST, SELECTING_VOICE, AWAITING_PASSWORD = range(6)

# Maximum message length for Telegram
MAX_MESSAGE_LENGTH = 4000


def split_long_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> List[str]:
    """Split a long message into chunks"""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break
        
        # Find the last newline or space before max_length
        split_pos = text.rfind('\n', 0, max_length)
        if split_pos == -1:
            split_pos = text.rfind(' ', 0, max_length)
        if split_pos == -1:
            split_pos = max_length
        
        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip()
    
    return chunks


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler - now with password-based login"""
    user = update.effective_user
    user_id = str(user.id)
    
    # Check if user already has a role
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/academy/v1/users/{user_id}/role")
            
            if response.status_code == 200:
                role_data = response.json()
                user_role = role_data.get('role')
                
                if user_role and user_role != 'not_set':
                    # User already has a role, show welcome message
                    welcome_message = f"""
👋 Добро пожаловать в Академию обучения На Счастье, {user.first_name}!

Я ваш обучающий ассистент. Вот что я могу для вас сделать:

📚 /academy - Просмотр и изучение обучающих модулей
📊 /progress - Проверка вашего прогресса обучения
🔍 /search <запрос> - Поиск конкретного контента
❓ /help - Показать доступные команды

Давайте начнём ваше обучение! Наберите /academy чтобы увидеть доступные модули.
"""
                    await update.message.reply_text(welcome_message)
                    return
    except Exception as e:
        logger.error(f"Error checking user role: {e}")
    
    # User doesn't have a role, ask them to login
    welcome_message = f"""
👋 Добро пожаловать в Академию обучения На Счастье, {user.first_name}!

Для начала работы, пожалуйста, войдите в систему.

Используйте команду /login и введите пароль доступа.

Ваша роль (администратор или пользователь) будет определена на основе введённого пароля.
"""
    
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler"""
    help_text = """
🤖 *Академия обучения На Счастье*

Доступные команды:

📚 /academy - Просмотр обучающих модулей
   • Просмотр всех доступных модулей
   • Фильтрация по вашей роли
   • Начало изучения уроков

👤 /profile - Ваш личный кабинет
   • Роль и ID пользователя
   • Статистика обучения
   • Модули в процессе

📊 /progress - Просмотр вашего прогресса
   • Просмотр завершённых модулей
   • Отслеживание прохождения уроков
   • Просмотр результатов тестов

📈 /progress_daily - Дневной прогресс
   • Активность по дням
   • Статистика изучения

🏆 /badges - Ваши значки
   • Просмотр заработанных значков
   • Достижения в обучении

🔍 /search <запрос> - Поиск контента
   • Поиск конкретных модулей
   • Поиск контента уроков
   • Быстрый доступ к темам

🔐 /login - Вход в систему
   • Вход по паролю доступа
   • Автоматическое определение роли (admin/user)

🔐 /admin - Панель администратора (только для admin)
   • Статистика по сотрудникам
   • Управление модулями
   • Просмотр результатов

🔄 /reload - Перезагрузить модули (только для admin)

*🆕 V3 - Новые функции:*

⭐ /level - Ваш уровень и опыт
   • Просмотр текущего уровня
   • XP и ранг
   • Прогресс до следующего уровня

📋 /plan - Персональный план обучения
   • Рекомендуемые уроки
   • Адаптивный план на 7 дней

🔄 /plan_refresh - Обновить план обучения
   • Пересоздать план

🎯 /quests - Ежедневные задания
   • Активные квесты
   • Награды XP

🎙️ /tts_settings - Настройки озвучки
   • Выбор голоса
   • Скорость воспроизведения

❓ /help - Показать это справочное сообщение

💡 *Советы:*
• Не торопитесь с каждым уроком
• Проходите уроки по порядку
• Тесты помогают закрепить знания
• Зарабатывайте значки за достижения
• Вы можете в любое время вернуться к любому уроку

Готовы учиться? Начните с /academy!
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Login command - authenticate with password"""
    user = update.effective_user
    user_id = str(user.id)
    
    # Check if user already has a role
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/academy/v1/users/{user_id}/role")
            
            if response.status_code == 200:
                role_data = response.json()
                user_role = role_data.get('role')
                
                if user_role and user_role != 'not_set':
                    # User already has a role
                    role_display = "АДМИН" if user_role == "admin" else "ПОЛЬЗОВАТЕЛЬ"
                    message = f"""
✅ Вы уже вошли как *{role_display}*.

Если хотите сменить роль, введите новый пароль доступа ниже.
"""
                    await update.message.reply_text(message, parse_mode='Markdown')
                    return AWAITING_PASSWORD
    except Exception as e:
        logger.error(f"Error checking user role in login: {e}")
    
    # User doesn't have a role or wants to change it
    message = """
🔐 *Вход в систему*

Пожалуйста, введите пароль доступа.

Ваша роль будет определена на основе введённого пароля.
"""
    await update.message.reply_text(message, parse_mode='Markdown')
    return AWAITING_PASSWORD


async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle password input for login"""
    user = update.effective_user
    user_id = str(user.id)
    username = user.username
    password = update.message.text.strip()
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_URL}/academy/v1/auth/login",
                json={
                    "telegram_id": user_id,
                    "telegram_username": username,
                    "password": password
                }
            )
            
            if response.status_code == 200:
                login_data = response.json()
                role = login_data.get('role')
                
                # Store role in context
                context.user_data['role'] = role
                
                # Show success message based on role
                if role == "admin":
                    message = """
✅ *Вы вошли как АДМИН*

Вам доступны:
• Все обучающие модули
• Команды управления (/admin, /reload)
• Статистика и аналитика
• Мегастатистика (V3)

Начните с команды /academy или /admin
"""
                else:  # role == "user"
                    message = """
✅ *Вы вошли как ПОЛЬЗОВАТЕЛЬ*

Вам доступно:
• Все обучающие модули
• Система уровней и опыта
• Персональные планы обучения
• Ежедневные квесты

Начните с команды /academy
"""
                
                await update.message.reply_text(message, parse_mode='Markdown')
                return ConversationHandler.END
            
            elif response.status_code == 401:
                # Invalid password
                message = """
❌ *Неверный пароль*

Пожалуйста, проверьте пароль и попробуйте ещё раз.

Введите пароль доступа или используйте /cancel для отмены.
"""
                await update.message.reply_text(message, parse_mode='Markdown')
                return AWAITING_PASSWORD
            
            else:
                # Other error
                await update.message.reply_text(
                    "❌ Произошла ошибка при входе. Попробуйте позже или используйте /cancel."
                )
                return AWAITING_PASSWORD
    
    except Exception as e:
        logger.error(f"Error in handle_password: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Произошла ошибка при входе. Попробуйте позже или используйте /cancel."
        )
        return AWAITING_PASSWORD


async def cancel_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel login process"""
    await update.message.reply_text(
        "❌ Вход отменён.\n\nИспользуйте /login когда захотите войти в систему."
    )
    return ConversationHandler.END


async def academy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show academy modules menu"""
    user_id = str(update.effective_user.id)
    
    try:
        async with httpx.AsyncClient() as client:
            # Get modules filtered by user's role
            response = await client.get(f"{BACKEND_URL}/academy/v1/modules?user_id={user_id}")
            
            if response.status_code != 200:
                await update.message.reply_text("❌ Не удалось загрузить модули. Попробуйте позже.")
                return ConversationHandler.END
            
            modules = response.json()
            
            if not modules:
                await update.message.reply_text("📚 Обучающие модули пока недоступны. Заходите позже!")
                return ConversationHandler.END
            
            # Create keyboard with module buttons
            keyboard = []
            for module in modules:
                button_text = f"{module['title']} (Уровень {module['level']})"
                keyboard.append([InlineKeyboardButton(
                    button_text,
                    callback_data=f"module:{module['id']}"
                )])
            
            keyboard.append([InlineKeyboardButton("❌ Закрыть", callback_data="close")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = "📚 *Доступные обучающие модули*\n\n"
            message += "Выберите модуль для начала обучения:\n"
            
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return SELECTING_MODULE
    
    except Exception as e:
        logger.error(f"Error in academy_command: {e}", exc_info=True)
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
        return ConversationHandler.END


async def module_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle module selection"""
    query = update.callback_query
    await query.answer()
    
    module_id = query.data.split(':')[1]
    user_id = str(update.effective_user.id)
    
    try:
        async with httpx.AsyncClient() as client:
            # Get module details
            response = await client.get(f"{BACKEND_URL}/academy/v1/modules/{module_id}")
            
            if response.status_code != 200:
                await query.edit_message_text("❌ Module not found.")
                return ConversationHandler.END
            
            module = response.json()
            
            # Build module info message
            message = f"📘 *{module['title']}*\n\n"
            message += f"{module['description']}\n\n"
            message += f"📊 Уровень: {module['level']}\n"
            message += f"📚 Уроков: {len(module['lessons'])}\n"
            message += f"📝 Тестов: {len(module['tests'])}\n"
            
            if module.get('estimated_duration_minutes'):
                message += f"⏱ Длительность: ~{module['estimated_duration_minutes']} минут\n"
            
            # Create keyboard
            keyboard = []
            
            # Add lesson buttons
            for lesson in sorted(module['lessons'], key=lambda l: l['order']):
                keyboard.append([InlineKeyboardButton(
                    f"📖 {lesson['title']}",
                    callback_data=f"lesson:{module_id}:{lesson['id']}"
                )])
            
            # Add test buttons
            for test in module.get('tests', []):
                keyboard.append([InlineKeyboardButton(
                    f"📝 {test['title']}",
                    callback_data=f"test:{module_id}:{test['id']}"
                )])
            
            keyboard.append([InlineKeyboardButton("◀️ Назад к модулям", callback_data="back_to_modules")])
            keyboard.append([InlineKeyboardButton("❌ Закрыть", callback_data="close")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Store module context
            context.user_data['current_module'] = module_id
            
            await query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return VIEWING_LESSON
    
    except Exception as e:
        logger.error(f"Error in module_selected: {e}", exc_info=True)
        await query.edit_message_text("❌ An error occurred. Please try again.")
        return ConversationHandler.END


async def lesson_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle lesson selection"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(':')
    module_id = parts[1]
    lesson_id = parts[2]
    user_id = str(update.effective_user.id)
    
    try:
        async with httpx.AsyncClient() as client:
            # Get lesson details
            response = await client.get(
                f"{BACKEND_URL}/academy/v1/modules/{module_id}/lessons/{lesson_id}"
            )
            
            if response.status_code != 200:
                await query.edit_message_text("❌ Lesson not found.")
                return VIEWING_LESSON
            
            lesson = response.json()
            
            # Mark lesson as started
            await client.post(
                f"{BACKEND_URL}/academy/v1/progress/{user_id}/lessons/{module_id}/{lesson_id}/start"
            )
            
            # Store lesson context
            context.user_data['current_lesson'] = {
                'module_id': module_id,
                'lesson_id': lesson_id,
                'content': lesson['content']
            }
            
            # Split content into chunks if needed
            chunks = split_long_message(lesson['content'])
            context.user_data['lesson_chunks'] = chunks
            context.user_data['current_chunk'] = 0
            
            # Send first chunk
            message = f"📖 *{lesson['title']}*\n\n{chunks[0]}"
            
            # Create navigation keyboard
            keyboard = []
            
            if len(chunks) > 1:
                keyboard.append([InlineKeyboardButton("▶️ Next Part", callback_data="lesson_next")])
            
            keyboard.append([
                InlineKeyboardButton("✅ Отметить как пройденный", callback_data=f"complete:{module_id}:{lesson_id}"),
                InlineKeyboardButton("🔊 Послушать урок", callback_data=f"tts_menu:{module_id}:{lesson_id}")
            ])
            keyboard.append([InlineKeyboardButton("◀️ Назад к модулю", callback_data=f"module:{module_id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return VIEWING_LESSON
    
    except Exception as e:
        logger.error(f"Error in lesson_selected: {e}", exc_info=True)
        await query.edit_message_text("❌ An error occurred loading the lesson.")
        return VIEWING_LESSON


async def lesson_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle lesson navigation (next/previous)"""
    query = update.callback_query
    await query.answer()
    
    chunks = context.user_data.get('lesson_chunks', [])
    current_chunk = context.user_data.get('current_chunk', 0)
    lesson_data = context.user_data.get('current_lesson', {})
    
    if query.data == "lesson_next":
        current_chunk += 1
    elif query.data == "lesson_prev":
        current_chunk -= 1
    
    current_chunk = max(0, min(current_chunk, len(chunks) - 1))
    context.user_data['current_chunk'] = current_chunk
    
    # Build message
    message = f"📖 Урок (Часть {current_chunk + 1}/{len(chunks)})\n\n{chunks[current_chunk]}"
    
    # Create navigation keyboard
    keyboard = []
    nav_row = []
    
    if current_chunk > 0:
        nav_row.append(InlineKeyboardButton("◀️ Предыдущая", callback_data="lesson_prev"))
    if current_chunk < len(chunks) - 1:
        nav_row.append(InlineKeyboardButton("Следующая ▶️", callback_data="lesson_next"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    module_id = lesson_data.get('module_id')
    lesson_id = lesson_data.get('lesson_id')
    
    keyboard.append([
        InlineKeyboardButton("✅ Отметить как пройденный", callback_data=f"complete:{module_id}:{lesson_id}"),
        InlineKeyboardButton("🔊 Послушать урок", callback_data=f"tts_menu:{module_id}:{lesson_id}")
    ])
    keyboard.append([InlineKeyboardButton("◀️ Назад к модулю", callback_data=f"module:{module_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup)
    return VIEWING_LESSON


async def show_tts_voice_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show voice selection menu for TTS"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(':')
    module_id = parts[1]
    lesson_id = parts[2]
    
    # Store context for TTS request
    context.user_data['tts_context'] = {
        'module_id': module_id,
        'lesson_id': lesson_id
    }
    
    message = "🔊 *Выберите голос для озвучки урока:*"
    
    keyboard = [
        [InlineKeyboardButton("👩 Женский голос", callback_data=f"tts:{module_id}:{lesson_id}:ru_female")],
        [InlineKeyboardButton("👨 Мужской голос", callback_data=f"tts:{module_id}:{lesson_id}:ru_male")],
        [InlineKeyboardButton("◀️ Отмена", callback_data=f"lesson:{module_id}:{lesson_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    return VIEWING_LESSON


async def complete_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark lesson as completed"""
    query = update.callback_query
    await query.answer("✅ Урок отмечен как пройденный!")
    
    parts = query.data.split(':')
    module_id = parts[1]
    lesson_id = parts[2]
    user_id = str(update.effective_user.id)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_URL}/academy/v1/progress/{user_id}/lessons/{module_id}/{lesson_id}/complete"
            )
            
            if response.status_code == 200:
                # Return to module view
                context.user_data['callback_data'] = f"module:{module_id}"
                await module_selected(update, context)
                return VIEWING_LESSON
            else:
                await query.edit_message_text("❌ Failed to mark lesson as completed.")
                return VIEWING_LESSON
    
    except Exception as e:
        logger.error(f"Error completing lesson: {e}", exc_info=True)
        return VIEWING_LESSON


async def request_tts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Request TTS for lesson"""
    query = update.callback_query
    await query.answer("🔊 Генерирую аудио... Пожалуйста, подождите.")
    
    parts = query.data.split(':')
    if len(parts) < 3:
        await query.answer("❌ Неверный формат данных")
        return VIEWING_LESSON
    
    module_id = parts[1]
    lesson_id = parts[2]
    voice_type = parts[3] if len(parts) > 3 else 'ru_female'
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/academy/v1/lessons/{module_id}/{lesson_id}/tts",
                json={"voice_type": voice_type}
            )
            
            if response.status_code == 200:
                result = response.json()
                audio_url = result.get('audio_url')
                
                if audio_url:
                    voice_name = "Женский голос" if voice_type == "ru_female" else "Мужской голос"
                    # Download and send audio
                    audio_response = await client.get(audio_url)
                    if audio_response.status_code == 200:
                        # Send audio file
                        await context.bot.send_voice(
                            chat_id=update.effective_chat.id,
                            voice=audio_response.content,
                            caption=f"🔊 Аудио урока ({voice_name})"
                        )
                    else:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="✅ Аудио сгенерировано! Вы можете прослушать его здесь: " + audio_url
                        )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"❌ Не удалось сгенерировать аудио. Код ошибки: {response.status_code}"
                )
    
    except Exception as e:
        logger.error(f"Error requesting TTS: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Сервис озвучки временно недоступен."
        )
    
    return VIEWING_LESSON


async def test_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle test selection"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(':')
    module_id = parts[1]
    test_id = parts[2]
    
    try:
        async with httpx.AsyncClient() as client:
            # Get module to find test
            response = await client.get(f"{BACKEND_URL}/academy/v1/modules/{module_id}")
            
            if response.status_code != 200:
                await query.edit_message_text("❌ Test not found.")
                return VIEWING_LESSON
            
            module = response.json()
            test = None
            for t in module.get('tests', []):
                if t['id'] == test_id:
                    test = t
                    break
            
            if not test:
                await query.edit_message_text("❌ Тест не найден.")
                return VIEWING_LESSON
            
            # Store test context
            context.user_data['current_test'] = {
                'module_id': module_id,
                'test_id': test_id,
                'questions': test['questions'],
                'current_question': 0,
                'answers': []
            }
            
            # Show first question
            await show_test_question(query, context)
            return TAKING_TEST
    
    except Exception as e:
        logger.error(f"Error in test_selected: {e}", exc_info=True)
        await query.edit_message_text("❌ Произошла ошибка при загрузке теста.")
        return VIEWING_LESSON


async def show_test_question(query, context: ContextTypes.DEFAULT_TYPE):
    """Show current test question"""
    test_data = context.user_data.get('current_test', {})
    questions = test_data.get('questions', [])
    current_q = test_data.get('current_question', 0)
    
    if current_q >= len(questions):
        # Test complete - submit answers
        await submit_test_answers(query, context)
        return
    
    question = questions[current_q]
    
    message = f"📝 *Вопрос {current_q + 1} из {len(questions)}*\n\n"
    message += f"{question['question']}\n\n"
    
    # Create option buttons
    keyboard = []
    for idx, option in enumerate(question['options']):
        keyboard.append([InlineKeyboardButton(
            f"{chr(65 + idx)}. {option}",
            callback_data=f"answer:{idx}"
        )])
    
    keyboard.append([InlineKeyboardButton("❌ Отменить тест", callback_data=f"module:{test_data['module_id']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def test_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle test answer selection"""
    query = update.callback_query
    await query.answer()
    
    answer_idx = int(query.data.split(':')[1])
    
    test_data = context.user_data.get('current_test', {})
    test_data['answers'].append(answer_idx)
    test_data['current_question'] += 1
    context.user_data['current_test'] = test_data
    
    # Show next question
    await show_test_question(query, context)
    return TAKING_TEST


async def submit_test_answers(query, context: ContextTypes.DEFAULT_TYPE):
    """Submit test answers for evaluation"""
    test_data = context.user_data.get('current_test', {})
    user_id = str(query.from_user.id)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_URL}/academy/v1/modules/{test_data['module_id']}/tests/{test_data['test_id']}/submit",
                json={
                    "user_id": user_id,
                    "answers": test_data['answers']
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                
                message = "🎉 *Тест завершён!*\n\n"
                message += f"Балл: {result['score']}%\n"
                message += f"Правильно: {sum(1 for i, a in enumerate(result['user_answers']) if a == result['correct_answers'][i])}/{result['total_questions']}\n\n"
                
                if result['passed']:
                    message += "✅ *ПРОЙДЕН!* Поздравляем!\n\n"
                else:
                    message += "❌ *Не пройден.* Продолжайте учиться и попробуйте снова!\n\n"
                
                keyboard = [[InlineKeyboardButton("◀️ Назад к модулю", callback_data=f"module:{test_data['module_id']}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text("❌ Не удалось отправить тест.")
    
    except Exception as e:
        logger.error(f"Error submitting test: {e}", exc_info=True)
        await query.edit_message_text("❌ Произошла ошибка при отправке теста.")


async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user progress"""
    user_id = str(update.effective_user.id)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/academy/v1/progress/{user_id}")
            
            if response.status_code != 200:
                await update.message.reply_text("❌ Не удалось загрузить прогресс.")
                return
            
            progress = response.json()
            
            message = "📊 *Ваш прогресс обучения*\n\n"
            message += f"📚 Модулей: {progress['completed_modules']}/{progress['total_modules']} завершено\n"
            message += f"📖 Уроков: {progress['completed_lessons']}/{progress['total_lessons']} завершено\n"
            message += f"📝 Тестов: {progress['passed_tests']}/{progress['total_tests']} пройдено\n\n"
            
            if progress['completed_lessons'] == 0:
                message += "💡 Начните обучение с /academy!"
            elif progress['completed_modules'] == progress['total_modules']:
                message += "🎉 Потрясающе! Вы завершили все модули!"
            else:
                completion_rate = int((progress['completed_lessons'] / max(progress['total_lessons'], 1)) * 100)
                message += f"📈 Общий прогресс: {completion_rate}%\n"
                message += "Продолжайте в том же духе! 🚀"
            
            await update.message.reply_text(message, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error in progress_command: {e}", exc_info=True)
        await update.message.reply_text("❌ Произошла ошибка при загрузке прогресса.")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search for content"""
    if not context.args:
        await update.message.reply_text("Использование: /search <запрос>\n\nПример: /search воронка продаж")
        return
    
    query_text = ' '.join(context.args)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_URL}/academy/v1/search",
                params={"query": query_text}
            )
            
            if response.status_code != 200:
                await update.message.reply_text("❌ Поиск не удался.")
                return
            
            results = response.json()
            
            message = f"🔍 *Результаты поиска для '{query_text}'*\n\n"
            
            modules = results.get('modules', [])
            lessons = results.get('lessons', [])
            
            if modules:
                message += "*Модули:*\n"
                for module in modules[:5]:
                    message += f"📘 {module['title']}\n"
                message += "\n"
            
            if lessons:
                message += "*Уроки:*\n"
                for lesson_info in lessons[:5]:
                    message += f"📖 {lesson_info['lesson']['title']} (в {lesson_info['module_title']})\n"
                message += "\n"
            
            if not modules and not lessons:
                message += "Результатов не найдено. Попробуйте другой поисковый запрос."
            else:
                message += "Используйте /academy для доступа к этим модулям."
            
            await update.message.reply_text(message, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error in search_command: {e}", exc_info=True)
        await update.message.reply_text("❌ Произошла ошибка во время поиска.")


async def back_to_modules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to modules list"""
    query = update.callback_query
    await query.answer()
    
    # Re-trigger academy command by creating a fake update
    context.user_data['callback_query'] = query
    
    try:
        async with httpx.AsyncClient() as client:
            # Get user_id for role-based filtering
            user_id = str(query.from_user.id)
            response = await client.get(f"{BACKEND_URL}/academy/v1/modules?user_id={user_id}")
            
            if response.status_code != 200:
                await query.edit_message_text("❌ Не удалось загрузить модули.")
                return SELECTING_MODULE
            
            modules = response.json()
            
            # Create keyboard with module buttons
            keyboard = []
            for module in modules:
                button_text = f"{module['title']} (Уровень {module['level']})"
                keyboard.append([InlineKeyboardButton(
                    button_text,
                    callback_data=f"module:{module['id']}"
                )])
            
            keyboard.append([InlineKeyboardButton("❌ Закрыть", callback_data="close")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = "📚 *Доступные обучающие модули*\n\n"
            message += "Выберите модуль для начала обучения:\n"
            
            await query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return SELECTING_MODULE
    
    except Exception as e:
        logger.error(f"Error in back_to_modules: {e}", exc_info=True)
        await query.edit_message_text("❌ An error occurred.")
        return ConversationHandler.END


async def close_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Close the menu"""
    query = update.callback_query
    await query.answer()
    await query.delete_message()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation"""
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user profile"""
    user_id = str(update.effective_user.id)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/academy/v1/users/{user_id}/profile")
            
            if response.status_code != 200:
                await update.message.reply_text("❌ Не удалось загрузить профиль.")
                return
            
            profile = response.json()
            
            # Format role name
            role_names = {
                'sales_manager': 'Менеджер по продажам',
                'generator': 'Генератор / Продакшн',
                'admin': 'Руководитель / Админ',
                'other': 'Другое',
                'not_set': 'Не установлена'
            }
            role_display = role_names.get(profile.get('role', 'not_set'), profile.get('role', 'Не установлена'))
            
            message = f"👤 *Ваш профиль*\n\n"
            message += f"🆔 ID: `{user_id}`\n"
            message += f"👔 Роль: {role_display}\n"
            message += f"📅 Дата присоединения: {profile.get('joined_date', 'Не указана')}\n\n"
            
            message += f"📊 *Статистика обучения:*\n"
            message += f"📖 Завершено уроков: {profile['completed_lessons']}/{profile['total_lessons']}\n"
            message += f"📚 Завершено модулей: {profile['completed_modules']}/{profile['total_modules']}\n"
            message += f"📝 Пройдено тестов: {profile['passed_tests']}/{profile['total_tests']}\n"
            message += f"📈 Процент выполнения: {profile['completion_percentage']}%\n"
            message += f"⭐ Общий рейтинг: {profile['rating']}/100\n"
            message += f"🏆 Заработано значков: {profile['badges_count']}\n\n"
            
            # Modules in progress
            if profile.get('modules_in_progress'):
                message += f"📚 *Модули в процессе:*\n"
                for mod in profile['modules_in_progress'][:3]:  # Show max 3
                    message += f"  • {mod['title']}\n"
                message += "\n"
            
            message += "Продолжайте обучение! 🚀"
            
            await update.message.reply_text(message, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error in profile_command: {e}", exc_info=True)
        await update.message.reply_text("❌ Произошла ошибка при загрузке профиля.")


async def badges_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user badges"""
    user_id = str(update.effective_user.id)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/academy/v1/users/{user_id}/badges")
            
            if response.status_code != 200:
                await update.message.reply_text("❌ Не удалось загрузить значки.")
                return
            
            data = response.json()
            badges = data.get('badges', [])
            
            if not badges:
                message = "🏆 *Ваши значки*\n\n"
                message += "У вас пока нет заработанных значков.\n\n"
                message += "Продолжайте обучение, чтобы заработать:\n"
                message += "🎖 Первый модуль пройден\n"
                message += "🧠 Один тест на 100%\n"
                message += "🔥 3 дня подряд обучение\n"
                message += "🚀 Закрыт весь F-блок\n"
            else:
                message = f"🏆 *Ваши значки* ({len(badges)})\n\n"
                for badge in badges:
                    badge_date = badge.get('earned_at', '')[:10] if badge.get('earned_at') else ''
                    message += f"{badge['badge_name']}\n"
                    if badge.get('badge_description'):
                        message += f"  _{badge['badge_description']}_\n"
                    if badge_date:
                        message += f"  📅 {badge_date}\n"
                    message += "\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error in badges_command: {e}", exc_info=True)
        await update.message.reply_text("❌ Произошла ошибка при загрузке значков.")


async def progress_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show daily progress"""
    user_id = str(update.effective_user.id)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/academy/v1/users/{user_id}/daily-progress?days=14")
            
            if response.status_code != 200:
                await update.message.reply_text("❌ Не удалось загрузить дневной прогресс.")
                return
            
            data = response.json()
            progress = data.get('progress', [])
            
            if not progress:
                message = "📊 *Дневной прогресс*\n\n"
                message += "Пока нет записей о вашей активности.\n"
                message += "Начните обучение, чтобы отслеживать прогресс!"
            else:
                message = f"📊 *Дневной прогресс* (последние {len(progress)} дней)\n\n"
                
                total_lessons = 0
                total_minutes = 0
                total_tests = 0
                
                for day in progress[:10]:  # Show max 10 days
                    date = day.get('date', '')
                    lessons = day.get('lessons_completed', 0)
                    minutes = day.get('minutes_studied', 0)
                    tests = day.get('tests_passed', 0)
                    
                    total_lessons += lessons
                    total_minutes += minutes
                    total_tests += tests
                    
                    if lessons > 0 or minutes > 0 or tests > 0:
                        message += f"📅 *{date}*\n"
                        if lessons > 0:
                            message += f"  📖 Уроков: {lessons}\n"
                        if minutes > 0:
                            message += f"  ⏱ Минут: {minutes}\n"
                        if tests > 0:
                            message += f"  📝 Тестов: {tests}\n"
                        message += "\n"
                
                message += f"📈 *Итого за период:*\n"
                message += f"📖 Уроков: {total_lessons}\n"
                message += f"⏱ Минут: {total_minutes}\n"
                message += f"📝 Тестов: {total_tests}\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error in progress_daily_command: {e}", exc_info=True)
        await update.message.reply_text("❌ Произошла ошибка при загрузке дневного прогресса.")


async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reload modules (admin only)"""
    user_id = str(update.effective_user.id)
    
    # Check if user is admin
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/academy/v1/users/{user_id}/role")
            
            if response.status_code != 200:
                await update.message.reply_text("❌ Не удалось проверить права доступа.")
                return
            
            role_data = response.json()
            user_role = role_data.get('role')
            
            if user_role != 'admin':
                await update.message.reply_text("❌ Эта команда доступна только администраторам.")
                return
            
            # Get admin token from environment
            admin_token = os.getenv("ADMIN_API_KEY", "")
            
            # Reload modules
            headers = {}
            if admin_token:
                headers["X-Admin-Token"] = admin_token
            
            response = await client.post(
                f"{BACKEND_URL}/academy/v1/admin/reload",
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                message = "✅ *Модули успешно перезагружены*\n\n"
                message += f"Модулей до перезагрузки: {result.get('modules_before', 0)}\n"
                message += f"Модулей после перезагрузки: {result.get('modules_after', 0)}\n"
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ Ошибка при перезагрузке модулей. Код: {response.status_code}")
    
    except Exception as e:
        logger.error(f"Error in reload_command: {e}", exc_info=True)
        await update.message.reply_text("❌ Произошла ошибка при перезагрузке модулей.")


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin dashboard"""
    user_id = str(update.effective_user.id)
    
    # Check if user is admin
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/academy/v1/users/{user_id}/role")
            
            if response.status_code != 200:
                await update.message.reply_text("❌ Не удалось проверить права доступа.")
                return
            
            role_data = response.json()
            user_role = role_data.get('role')
            
            if user_role != 'admin':
                await update.message.reply_text("❌ Эта команда доступна только администраторам.")
                return
            
            # Show admin menu
            message = "🔐 *Панель администратора*\n\n"
            message += "Выберите действие:"
            
            keyboard = [
                [InlineKeyboardButton("📊 Статистика по сотрудникам", callback_data="admin:users_stats")],
                [InlineKeyboardButton("📚 Статистика по модулям", callback_data="admin:modules_stats")],
                [InlineKeyboardButton("🎯 Мегастатистика (V3)", callback_data="admin:mega_stats")],
                [InlineKeyboardButton("📝 Результаты тестов", callback_data="admin:test_results")],
                [InlineKeyboardButton("🔄 Перезагрузить модули", callback_data="admin:reload")],
                [InlineKeyboardButton("👥 Список пользователей", callback_data="admin:users_list")],
                [InlineKeyboardButton("❌ Закрыть", callback_data="close")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error in admin_command: {e}", exc_info=True)
        await update.message.reply_text("❌ Произошла ошибка при открытии панели администратора.")


async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin menu callbacks"""
    query = update.callback_query
    await query.answer()
    
    action = query.data.split(':')[1]
    user_id = str(update.effective_user.id)
    
    # Get admin token
    admin_token = os.getenv("ADMIN_API_KEY", "")
    headers = {}
    if admin_token:
        headers["X-Admin-Token"] = admin_token
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if action == "users_stats":
                response = await client.get(
                    f"{BACKEND_URL}/academy/v1/admin/stats/summary",
                    headers=headers
                )
                
                if response.status_code == 200:
                    stats = response.json()
                    message = "📊 *Статистика по сотрудникам*\n\n"
                    message += f"👥 Всего пользователей: {stats['total_users']}\n"
                    message += f"📈 Активных пользователей: {stats['users_with_progress']}\n"
                    message += f"📚 Всего модулей: {stats['total_modules']}\n"
                    message += f"📖 Всего уроков: {stats['total_lessons_available']}\n"
                    message += f"✅ Завершено уроков: {stats['total_lessons_completed']}\n"
                    message += f"📊 Средний % завершения: {stats['average_completion_rate']}%\n\n"
                    
                    if stats.get('top_modules'):
                        message += "*Топ модули:*\n"
                        for mod in stats['top_modules'][:3]:
                            message += f"  • {mod['title']}: {mod['completions']} завершений\n"
                    
                    await query.edit_message_text(message, parse_mode='Markdown')
                else:
                    await query.edit_message_text("❌ Не удалось загрузить статистику.")
            
            elif action == "modules_stats":
                response = await client.get(
                    f"{BACKEND_URL}/academy/v1/admin/modules/stats",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    module_stats = data.get('module_stats', [])
                    
                    message = f"📚 *Статистика по модулям* ({data['total_modules']} модулей)\n\n"
                    
                    for mod in module_stats[:5]:  # Show top 5
                        message += f"*{mod['module_title']}*\n"
                        message += f"  👥 Начали: {mod['users_started']}\n"
                        message += f"  ✅ Завершили: {mod['users_completed']}\n"
                        message += f"  📊 Средний %: {mod['average_completion_percentage']}%\n"
                        
                        if mod.get('top_users'):
                            top_user = mod['top_users'][0] if len(mod['top_users']) > 0 else None
                            if top_user:
                                message += f"  🏆 Топ: {top_user['user_id']} ({top_user['completion']:.0f}%)\n"
                        message += "\n"
                    
                    await query.edit_message_text(message, parse_mode='Markdown')
                else:
                    await query.edit_message_text("❌ Не удалось загрузить статистику по модулям.")
            
            elif action == "test_results":
                await query.edit_message_text("📝 *Результаты тестов*\n\nФункция в разработке. Используйте /admin для других опций.", parse_mode='Markdown')
            
            elif action == "mega_stats":
                # V3: Мегастатистика
                response = await client.get(
                    f"{BACKEND_URL}/academy/v1/admin/mega_stats",
                    headers=headers
                )
                
                if response.status_code == 200:
                    stats = response.json()
                    
                    message = "🎯 *МЕГАСТАТИСТИКА*\n\n"
                    
                    # Общие данные
                    message += "*📊 Общие данные:*\n"
                    message += f"👥 Всего пользователей: {stats['total_users']}\n"
                    message += f"✅ Активных сегодня: {stats['active_today']}\n"
                    message += f"📅 Активных за неделю: {stats['active_week']}\n"
                    message += f"📆 Активных за месяц: {stats['active_month']}\n\n"
                    
                    # По ролям
                    if stats.get('users_by_role'):
                        message += "*👔 По ролям:*\n"
                        role_names = {
                            'sales_manager': 'Менеджеры',
                            'generator': 'Генераторы',
                            'admin': 'Админы',
                            'other': 'Другие'
                        }
                        for role, count in stats['users_by_role'].items():
                            role_display = role_names.get(role, role)
                            message += f"  • {role_display}: {count}\n"
                        message += "\n"
                    
                    # Топ модули
                    if stats.get('top_modules'):
                        message += "*📚 Топ-5 изучаемых модулей:*\n"
                        for i, mod in enumerate(stats['top_modules'][:3], 1):
                            message += f"{i}. {mod.get('title', mod['module_id'])}: {mod['user_count']} чел.\n"
                        message += "\n"
                    
                    # Средний балл
                    message += f"*📊 Средний балл по тестам:* {stats['average_score']:.1f}%\n\n"
                    
                    # Сложные модули
                    if stats.get('hardest_modules'):
                        message += "*😰 Самые сложные модули:*\n"
                        for mod in stats['hardest_modules'][:3]:
                            message += f"  • {mod.get('title', mod['module_id'])}: {mod['avg_score']:.0f}%\n"
                    
                    await query.edit_message_text(message, parse_mode='Markdown')
                else:
                    await query.edit_message_text("❌ Не удалось загрузить мегастатистику.")
            
            elif action == "reload":
                response = await client.post(
                    f"{BACKEND_URL}/academy/v1/admin/reload",
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    message = "✅ *Модули перезагружены*\n\n"
                    message += f"До: {result.get('modules_before', 0)} модулей\n"
                    message += f"После: {result.get('modules_after', 0)} модулей\n"
                    await query.edit_message_text(message, parse_mode='Markdown')
                else:
                    await query.edit_message_text("❌ Ошибка при перезагрузке модулей.")
            
            elif action == "users_list":
                response = await client.get(
                    f"{BACKEND_URL}/academy/v1/admin/users",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    users = data.get('users', [])
                    
                    message = f"👥 *Список пользователей* ({data['total_users']})\n\n"
                    
                    for user in users[:10]:  # Show first 10
                        role_names = {
                            'sales_manager': 'Продажи',
                            'generator': 'Генератор',
                            'admin': 'Админ',
                            'other': 'Другое'
                        }
                        role_display = role_names.get(user.get('role', 'other'), 'Другое')
                        
                        message += f"🆔 `{user['user_id']}`\n"
                        message += f"  Роль: {role_display}\n"
                        message += f"  📖 Уроков: {user.get('completed_lessons', 0)}\n"
                        message += f"  📝 Тестов: {user.get('passed_tests', 0)}\n\n"
                    
                    if len(users) > 10:
                        message += f"\n_...и ещё {len(users) - 10} пользователей_"
                    
                    await query.edit_message_text(message, parse_mode='Markdown')
                else:
                    await query.edit_message_text("❌ Не удалось загрузить список пользователей.")
    
    except Exception as e:
        logger.error(f"Error in admin_callback_handler: {e}", exc_info=True)
        await query.edit_message_text("❌ Произошла ошибка.")


# ========================================
# V3 COMMANDS: Levels, Learning Plans, Quests, TTS Settings
# ========================================

async def level_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать уровень и опыт пользователя (V3)"""
    user_id = str(update.effective_user.id)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/academy/v1/user/{user_id}/level")
            
            if response.status_code == 200:
                level_data = response.json()
                
                message = "⭐ *Ваш уровень и опыт*\n\n"
                message += f"🏆 Ранг: *{level_data['rank_name']}*\n"
                message += f"📊 Уровень: {level_data['level']}/10\n"
                message += f"✨ Опыт: {level_data['xp']} XP\n"
                
                if level_data['level'] < 10:
                    message += f"🎯 До следующего уровня: {level_data['xp_to_next']} XP\n\n"
                else:
                    message += "\n🌟 *Вы достигли максимального уровня!* 🌟\n\n"
                
                message += "*Как получить опыт:*\n"
                message += "• Пройти урок: +10 XP\n"
                message += "• Пройти тест: +30 XP\n"
                message += "• Тест на 100%: +60 XP\n"
                message += "• Ежедневная активность: +5 XP\n"
                message += "• Выполнить квест: +10-50 XP\n"
                
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Не удалось загрузить информацию об уровне.")
    
    except Exception as e:
        logger.error(f"Error in level_command: {e}", exc_info=True)
        await update.message.reply_text("❌ Произошла ошибка при загрузке уровня.")


async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать персональный план обучения (V3)"""
    user_id = str(update.effective_user.id)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/academy/v1/plan/{user_id}")
            
            if response.status_code == 200:
                plan_data = response.json()
                items = plan_data.get('items', [])
                
                if not items:
                    message = "📋 *Персональный план обучения*\n\n"
                    message += "У вас пока нет активного плана.\n"
                    message += "Используйте /plan_refresh для генерации нового плана."
                else:
                    message = "📋 *Ваш персональный план обучения*\n\n"
                    message += f"📅 Создан: {plan_data['generated_at'][:10]}\n"
                    message += f"⏰ Действует до: {plan_data['valid_until'][:10]}\n\n"
                    
                    # Группировать по статусу
                    pending = [i for i in items if i['status'] == 'pending']
                    active = [i for i in items if i['status'] == 'active']
                    done = [i for i in items if i['status'] == 'done']
                    
                    if active:
                        message += "*🔄 В процессе:*\n"
                        for item in active[:3]:
                            message += f"  • {item['module_id']} → {item['lesson_id']}\n"
                        message += "\n"
                    
                    if pending:
                        message += f"*📝 Запланировано ({len(pending)}):*\n"
                        for item in pending[:5]:
                            priority_emoji = "🔴" if item['priority'] >= 8 else "🟡" if item['priority'] >= 5 else "🟢"
                            message += f"  {priority_emoji} {item['module_id']} → {item['lesson_id']}\n"
                        if len(pending) > 5:
                            message += f"  _...и ещё {len(pending) - 5}_\n"
                        message += "\n"
                    
                    if done:
                        message += f"✅ Завершено: {len(done)}\n"
                    
                    message += "\n💡 Используйте /plan_refresh для обновления плана"
                
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Не удалось загрузить план обучения.")
    
    except Exception as e:
        logger.error(f"Error in plan_command: {e}", exc_info=True)
        await update.message.reply_text("❌ Произошла ошибка при загрузке плана.")


async def plan_refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сгенерировать новый персональный план обучения (V3)"""
    user_id = str(update.effective_user.id)
    
    await update.message.reply_text("🔄 Генерирую персональный план обучения...\nЭто может занять несколько секунд.")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{BACKEND_URL}/academy/v1/plan/{user_id}/generate")
            
            if response.status_code == 200:
                plan_data = response.json()
                items = plan_data.get('items', [])
                
                message = "✅ *Новый план обучения создан!*\n\n"
                message += f"📚 Запланировано уроков: {len(items)}\n"
                message += f"📅 Действует 7 дней\n\n"
                message += "План создан на основе:\n"
                message += "• Вашей роли\n"
                message += "• Текущего прогресса\n"
                message += "• Результатов тестов\n"
                message += "• Незавершенных модулей\n\n"
                message += "Используйте /plan для просмотра плана"
                
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Не удалось создать план обучения.")
    
    except Exception as e:
        logger.error(f"Error in plan_refresh_command: {e}", exc_info=True)
        await update.message.reply_text("❌ Произошла ошибка при создании плана.")


async def quests_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать ежедневные квесты (V3)"""
    user_id = str(update.effective_user.id)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/academy/v1/quests/{user_id}")
            
            if response.status_code == 200:
                quests = response.json()
                
                if not quests:
                    message = "🎯 *Ежедневные задания*\n\n"
                    message += "На сегодня нет активных заданий.\n"
                    message += "Квесты обновляются каждый день!"
                else:
                    message = "🎯 *Ежедневные задания*\n\n"
                    
                    active_quests = [q for q in quests if q['status'] == 'active']
                    completed_quests = [q for q in quests if q['status'] == 'completed']
                    
                    if active_quests:
                        message += "*Активные:*\n"
                        for quest in active_quests:
                            type_emoji = {
                                "lesson": "📖",
                                "test": "📝",
                                "streak": "🔥",
                                "tts": "🔊",
                                "module": "📚"
                            }.get(quest['type'], "⭐")
                            
                            message += f"{type_emoji} {quest['description']}\n"
                            message += f"   Награда: +{quest['reward_xp']} XP\n\n"
                    
                    if completed_quests:
                        message += f"✅ *Выполнено сегодня: {len(completed_quests)}*\n\n"
                    
                    message += "💡 Квесты выполняются автоматически при совершении действий!"
                
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Не удалось загрузить квесты.")
    
    except Exception as e:
        logger.error(f"Error in quests_command: {e}", exc_info=True)
        await update.message.reply_text("❌ Произошла ошибка при загрузке квестов.")


async def tts_settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать и настроить параметры TTS (V3)"""
    user_id = str(update.effective_user.id)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/academy/v1/tts/settings/{user_id}")
            
            if response.status_code == 200:
                settings = response.json()
                
                voice_names = {
                    "female": "Женский",
                    "male": "Мужской",
                    "neutral": "Нейтральный"
                }
                
                message = "🎙️ *Настройки озвучки (TTS)*\n\n"
                message += f"🔊 Голос: {voice_names.get(settings['voice'], settings['voice'])}\n"
                message += f"⚡ Скорость: {settings['speed']}x\n"
                message += f"📁 Формат: {settings['format'].upper()}\n\n"
                message += "*Доступные настройки:*\n"
                message += "• Голоса: женский, мужской, нейтральный\n"
                message += "• Скорость: 1.0x, 1.25x, 1.5x\n"
                message += "• Форматы: MP3, OGG\n\n"
                message += "💡 Настройки применяются автоматически при генерации аудио"
                
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Не удалось загрузить настройки TTS.")
    
    except Exception as e:
        logger.error(f"Error in tts_settings_command: {e}", exc_info=True)
        await update.message.reply_text("❌ Произошла ошибка при загрузке настроек TTS.")


def main():
    """Main function to run the bot"""
    # Get bot token from environment variable
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        logger.info("Please set TELEGRAM_BOT_TOKEN before running the bot.")
        logger.info("For testing, you can use: export TELEGRAM_BOT_TOKEN='your-token-here'")
        return
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Login conversation handler
    login_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('login', login_command)],
        states={
            AWAITING_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password),
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_login),
        ],
    )
    
    # Conversation handler for academy flow
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('academy', academy_command)],
        states={
            SELECTING_MODULE: [
                CallbackQueryHandler(module_selected, pattern='^module:'),
                CallbackQueryHandler(back_to_modules, pattern='^back_to_modules$'),
                CallbackQueryHandler(close_menu, pattern='^close$'),
            ],
            VIEWING_LESSON: [
                CallbackQueryHandler(lesson_selected, pattern='^lesson:'),
                CallbackQueryHandler(test_selected, pattern='^test:'),
                CallbackQueryHandler(complete_lesson, pattern='^complete:'),
                CallbackQueryHandler(show_tts_voice_menu, pattern='^tts_menu:'),
                CallbackQueryHandler(request_tts, pattern='^tts:'),
                CallbackQueryHandler(lesson_navigation, pattern='^lesson_(next|prev)$'),
                CallbackQueryHandler(module_selected, pattern='^module:'),
                CallbackQueryHandler(back_to_modules, pattern='^back_to_modules$'),
                CallbackQueryHandler(close_menu, pattern='^close$'),
            ],
            TAKING_TEST: [
                CallbackQueryHandler(test_answer, pattern='^answer:'),
                CallbackQueryHandler(module_selected, pattern='^module:'),
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(close_menu, pattern='^close$'),
        ],
    )
    
    # Add handlers
    application.add_handler(login_conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("progress", progress_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("badges", badges_command))
    application.add_handler(CommandHandler("progress_daily", progress_daily_command))
    application.add_handler(CommandHandler("reload", reload_command))
    application.add_handler(CommandHandler("admin", admin_command))
    
    # V3 Commands
    application.add_handler(CommandHandler("level", level_command))
    application.add_handler(CommandHandler("plan", plan_command))
    application.add_handler(CommandHandler("plan_refresh", plan_refresh_command))
    application.add_handler(CommandHandler("quests", quests_command))
    application.add_handler(CommandHandler("tts_settings", tts_settings_command))
    
    application.add_handler(conv_handler)
    
    # Admin menu handler
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern='^admin:'))
    
    # Start bot
    logger.info("🤖 SALESBOT Training Bot starting...")
    logger.info(f"Backend URL: {BACKEND_URL}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
