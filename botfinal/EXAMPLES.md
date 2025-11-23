# SALESBOT Training System - API Examples

This document provides practical examples of using the Academy API endpoints.

## Base URL

```
http://localhost:8080
```

## Authentication

Currently, no authentication is required. In production, you should add authentication middleware.

## API Examples

### 1. List All Training Modules

**Request:**
```bash
curl http://localhost:8080/academy/v1/modules
```

**Response:**
```json
[
  {
    "id": "module1_intro",
    "title": "Module 1 — Introduction to На Счастье",
    "description": "Welcome module introducing our company culture, values, and mission",
    "roles": ["sales", "production", "marketing", "support"],
    "level": 1,
    "lessons_count": 3,
    "tests_count": 1
  }
]
```

### 2. Filter Modules by Role

**Request:**
```bash
curl "http://localhost:8080/academy/v1/modules?role=sales"
```

**Response:**
Returns only modules relevant to the sales role.

### 3. Get Module Details

**Request:**
```bash
curl http://localhost:8080/academy/v1/modules/module1_intro
```

**Response:**
```json
{
  "id": "module1_intro",
  "title": "Module 1 — Introduction to На Счастье",
  "description": "...",
  "roles": ["sales", "production", "marketing", "support"],
  "level": 1,
  "lessons": [
    {
      "id": "m1_l1",
      "title": "Welcome to На Счастье",
      "type": "text",
      "content": "...",
      "duration_minutes": 15,
      "order": 1
    }
  ],
  "tests": [...]
}
```

### 4. Get Specific Lesson

**Request:**
```bash
curl http://localhost:8080/academy/v1/modules/module1_intro/lessons/m1_l1
```

**Response:**
```json
{
  "id": "m1_l1",
  "title": "Welcome to На Счастье",
  "type": "text",
  "content": "Full lesson content...",
  "duration_minutes": 15,
  "order": 1
}
```

### 5. Mark Lesson as Completed

**Request:**
```bash
curl -X POST \
  http://localhost:8080/academy/v1/progress/user123/lessons/module1_intro/m1_l1/complete
```

**Response:**
```json
{
  "success": true,
  "message": "Lesson marked as completed",
  "user_id": "user123",
  "module_id": "module1_intro",
  "lesson_id": "m1_l1"
}
```

### 6. Get User Progress

**Request:**
```bash
curl http://localhost:8080/academy/v1/progress/user123
```

**Response:**
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
      "module_id": "module1_intro",
      "lesson_id": "m1_l1",
      "status": "completed",
      "score": null,
      "updated_at": "2025-11-23T21:26:00"
    }
  ]
}
```

### 7. Submit Test Answers

**Request:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "answers": [1, 2, 2, 2]
  }' \
  http://localhost:8080/academy/v1/modules/module1_intro/tests/m1_test1/submit
```

**Response:**
```json
{
  "test_id": "m1_test1",
  "user_id": "user123",
  "score": 100,
  "total_questions": 4,
  "passed": true,
  "correct_answers": [1, 2, 2, 2],
  "user_answers": [1, 2, 2, 2]
}
```

### 8. Generate TTS Audio for Lesson

**Request:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"voice_type": "russian"}' \
  http://localhost:8080/academy/v1/lessons/module1_intro/m1_l1/tts
```

**Response:**
```json
{
  "success": true,
  "lesson_id": "m1_l1",
  "module_id": "module1_intro",
  "audio_url": "http://127.0.0.1:8080/voice/v1/audio/abc123.mp3",
  "voice_type": "russian"
}
```

### 9. Search Content

**Request:**
```bash
curl "http://localhost:8080/academy/v1/search?query=sales"
```

**Response:**
```json
{
  "modules": [
    {
      "id": "module3_sales_f1",
      "title": "Module 3 — Sales (F1)",
      "...": "..."
    }
  ],
  "lessons": [
    {
      "module_id": "module3_sales_f1",
      "module_title": "Module 3 — Sales (F1)",
      "lesson": {
        "id": "m3_l1",
        "title": "Sales Funnel S0–S9",
        "...": "..."
      }
    }
  ]
}
```

### 10. Get Next Uncompleted Lesson

**Request:**
```bash
curl http://localhost:8080/academy/v1/modules/module1_intro/next-lesson/user123
```

**Response (when there's a next lesson):**
```json
{
  "completed": false,
  "lesson": {
    "id": "m1_l2",
    "title": "Our Company History",
    "type": "text",
    "content": "...",
    "duration_minutes": 15,
    "order": 2
  }
}
```

**Response (when all completed):**
```json
{
  "completed": true,
  "message": "All lessons in this module are completed",
  "module_id": "module1_intro"
}
```

## Telegram Bot Examples

### Bot Commands

```
/start          - Welcome message and introduction
/help           - Show all available commands
/academy        - Browse training modules
/progress       - View your learning progress
/search sales   - Search for content about "sales"
```

### Typical User Flow

1. User sends `/academy`
2. Bot shows list of available modules
3. User selects a module (e.g., "Module 1 — Introduction")
4. Bot shows module details with lessons and tests
5. User selects a lesson
6. Bot displays lesson content in chunks with navigation
7. User can:
   - Navigate through lesson parts
   - Mark lesson as completed
   - Request audio (TTS) version
   - Return to module
8. User can take tests after completing lessons
9. User checks progress with `/progress`

## Core System Endpoints

### Health Check

```bash
curl http://localhost:8080/api/public/v1/health
```

Response:
```json
{
  "status": "healthy",
  "service": "SALESBOT"
}
```

### Academy Module Health

```bash
curl http://localhost:8080/academy/v1/health
```

Response:
```json
{
  "status": "healthy",
  "module": "academy",
  "modules_loaded": 3
}
```

## Tips for Integration

1. **User IDs**: Use Telegram user IDs or your internal user system IDs
2. **Progress Tracking**: Call progress endpoints after each lesson/test completion
3. **Caching**: Consider caching module data on the client side
4. **Error Handling**: Always check response status codes
5. **Long Content**: Use the pagination/chunking for long lessons
6. **TTS**: Pre-generate audio for frequently accessed lessons

## Rate Limiting

Currently, there are no rate limits. Consider adding them for production use.

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message here"
}
```

Common HTTP status codes:
- `200` - Success
- `404` - Resource not found
- `500` - Internal server error
