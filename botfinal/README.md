# SALESBOT Training System

Internal training and academy system for "На Счастье" company.

## Overview

This is a comprehensive training platform that combines:
- **FastAPI Backend**: RESTful API for managing training modules, lessons, and user progress
- **Telegram Bot**: Interactive learning interface for employees
- **Modular Architecture**: Easy to extend with new training modules

## Features

- 📚 **Training Modules**: Organized courses for different roles (sales, production, marketing, etc.)
- 📖 **Interactive Lessons**: Step-by-step learning with progress tracking
- 📝 **Tests & Assessments**: Verify knowledge with quizzes
- 🔊 **Text-to-Speech**: Listen to lessons as audio
- 📊 **Progress Tracking**: Monitor learning progress across modules
- 🔍 **Search**: Find specific content quickly

## Architecture

### Backend (FastAPI)
- **Main Application**: `main.py` - FastAPI server with auto-loader for modules
- **Modules System**: Dynamically loads routers from `modules/` directory
- **Academy Module**: Complete training system under `modules/academy/`
  - `models.py` - Pydantic models
  - `repository.py` - Module data loader
  - `progress_repository.py` - User progress tracking
  - `service.py` - Business logic
  - `router.py` - API endpoints

### Data Layer
- **Training Content**: YAML files in `data/academy/modules/`
- **Progress Database**: SQLite for tracking user completion

### Telegram Bot
- **Interactive Interface**: `simple_telegram_bot.py`
- Built with `python-telegram-bot` 20.x
- Conversational flow for browsing and learning

## Installation

1. **Install Dependencies**:
```bash
cd botfinal
pip install -r requirements.txt
```

2. **Set Up Environment**:
```bash
# For Telegram bot (optional)
export TELEGRAM_BOT_TOKEN="your-bot-token"
```

3. **Start Backend**:
```bash
python main.py
```

The backend will start on `http://0.0.0.0:8080`

4. **Start Telegram Bot** (optional):
```bash
python simple_telegram_bot.py
```

## API Endpoints

### Academy Module (`/academy/v1`)

- `GET /academy/v1/modules` - List all modules
- `GET /academy/v1/modules/{module_id}` - Get module details
- `GET /academy/v1/modules/{module_id}/lessons` - List lessons
- `GET /academy/v1/modules/{module_id}/lessons/{lesson_id}` - Get lesson
- `POST /academy/v1/progress/{user_id}/lessons/{module_id}/{lesson_id}/complete` - Mark completed
- `GET /academy/v1/progress/{user_id}` - Get user progress
- `POST /academy/v1/modules/{module_id}/tests/{test_id}/submit` - Submit test
- `POST /academy/v1/lessons/{module_id}/{lesson_id}/tts` - Generate audio
- `GET /academy/v1/search?query=...` - Search content

### Core Endpoints

- `GET /` - Service info
- `GET /api/public/v1/health` - Health check
- `POST /voice/v1/tts` - Text-to-speech generation
- `GET /voice/v1/audio/{filename}` - Get audio file

## Adding Training Content

Create a YAML file in `data/academy/modules/`:

```yaml
id: "module_id"
title: "Module Title"
description: "Module description"
roles: ["sales", "production"]
level: 1
estimated_duration_minutes: 60

lessons:
  - id: "lesson1"
    title: "Lesson Title"
    type: "text"
    content: |
      Lesson content here...
    duration_minutes: 20
    order: 1

tests:
  - id: "test1"
    title: "Test Title"
    passing_score: 70
    questions:
      - id: "q1"
        type: "single"
        question: "Question text?"
        options:
          - "Option A"
          - "Option B"
          - "Option C"
        correct_index: 0
```

The module will be automatically loaded on backend startup.

## Telegram Bot Commands

- `/start` - Welcome message
- `/help` - Show help
- `/academy` - Browse training modules
- `/progress` - View your progress
- `/search <query>` - Search content

## Development

### Project Structure
```
botfinal/
├── main.py                 # FastAPI application
├── simple_telegram_bot.py  # Telegram bot
├── requirements.txt        # Dependencies
├── modules/               # Modular components
│   └── academy/          # Academy module
│       ├── __init__.py
│       ├── models.py
│       ├── repository.py
│       ├── progress_repository.py
│       ├── service.py
│       └── router.py
└── data/
    └── academy/
        └── modules/       # Training content (YAML)
```

### Extending the System

1. **Add New Modules**: Create a new directory in `modules/` with a `router.py`
2. **Add Training Content**: Create YAML files in `data/academy/modules/`
3. **Customize Bot**: Modify `simple_telegram_bot.py` for new features

## Logging

The system logs:
- Module discovery and loading
- API requests and errors
- User progress updates
- TTS generation

Check console output for operational status.

## License

Internal use for "На Счастье" company.
