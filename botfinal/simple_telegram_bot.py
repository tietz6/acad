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
SELECTING_ROLE, SELECTING_MODULE, VIEWING_LESSON, TAKING_TEST, SELECTING_VOICE = range(5)

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
    """Start command handler - with role selection"""
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
    
    # User doesn't have a role, ask for it
    welcome_message = f"""
👋 Добро пожаловать в Академию обучения На Счастье, {user.first_name}!

Для начала, пожалуйста, выберите вашу роль в компании:
"""
    
    keyboard = [
        [InlineKeyboardButton("👔 Менеджер по продажам", callback_data="role:sales_manager")],
        [InlineKeyboardButton("🎨 Генератор / Продакшн", callback_data="role:generator")],
        [InlineKeyboardButton("⭐ Руководитель / Админ", callback_data="role:admin")],
        [InlineKeyboardButton("👤 Другое", callback_data="role:other")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)


async def role_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle role selection"""
    query = update.callback_query
    await query.answer()
    
    role = query.data.split(':')[1]
    user_id = str(update.effective_user.id)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_URL}/academy/v1/users/{user_id}/role",
                json={"role": role}
            )
            
            if response.status_code == 200:
                role_names = {
                    'sales_manager': 'Менеджер по продажам',
                    'generator': 'Генератор / Продакшн',
                    'admin': 'Руководитель / Админ',
                    'other': 'Другое'
                }
                
                message = f"""
✅ Роль сохранена: *{role_names.get(role, role)}*

Теперь вам будут показываться нужные обучающие модули.

Наберите /academy, чтобы начать обучение!
"""
                await query.edit_message_text(message, parse_mode='Markdown')
            else:
                await query.edit_message_text("❌ Ошибка при сохранении роли. Попробуйте снова.")
    
    except Exception as e:
        logger.error(f"Error setting role: {e}", exc_info=True)
        await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler"""
    help_text = """
🤖 *Академия обучения На Счастье*

Доступные команды:

📚 /academy - Просмотр обучающих модулей
   • Просмотр всех доступных модулей
   • Фильтрация по вашей роли
   • Начало изучения уроков

📊 /progress - Просмотр вашего прогресса
   • Просмотр завершённых модулей
   • Отслеживание прохождения уроков
   • Просмотр результатов тестов

🔍 /search <запрос> - Поиск контента
   • Поиск конкретных модулей
   • Поиск контента уроков
   • Быстрый доступ к темам

❓ /help - Показать это справочное сообщение

💡 *Советы:*
• Не торопитесь с каждым уроком
• Проходите уроки по порядку
• Тесты помогают закрепить знания
• Вы можете в любое время вернуться к любому уроку

Готовы учиться? Начните с /academy!
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


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
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("progress", progress_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(conv_handler)
    
    # Role selection handler (separate from academy flow)
    application.add_handler(CallbackQueryHandler(role_selected, pattern='^role:'))
    
    # Start bot
    logger.info("🤖 SALESBOT Training Bot starting...")
    logger.info(f"Backend URL: {BACKEND_URL}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
