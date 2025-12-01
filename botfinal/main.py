"""
SALESBOT Training System - Main FastAPI Application
"""
import os
import sys
import logging
import tempfile
import uuid
from pathlib import Path
from typing import List
import importlib.util
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from gtts import gTTS
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SALESBOT Training System",
    description="Internal training and academy system",
    version="1.0.0"
)

# Global storage for loaded modules
loaded_module_commands = []
loaded_module_routers = []

# Create TTS data directory if it doesn't exist
tts_data_dir = Path(__file__).parent / "data" / "tts"
tts_data_dir.mkdir(parents=True, exist_ok=True)

# Mount static files for TTS audio
app.mount("/data/tts", StaticFiles(directory=str(tts_data_dir)), name="tts_audio")


def initialize_database():
    """Initialize database connections and tables"""
    logger.info("Database initialized")
    # Database initialization logic would go here
    # For now, we'll use SQLite through the modules


def discover_and_load_modules():
    """
    Auto-loader: Scan modules/ folder and dynamically include routers
    This mechanism loads any router.py files found in subdirectories of modules/
    """
    global loaded_module_commands, loaded_module_routers
    
    modules_dir = Path(__file__).parent / "modules"
    logger.info(f"FS-scan modules folder: {modules_dir}")
    
    if not modules_dir.exists():
        logger.warning(f"Modules directory does not exist: {modules_dir}")
        logger.info(f"Discovered module commands: {loaded_module_commands}")
        logger.info(f"Loaded {len(loaded_module_routers)} module routers")
        return
    
    # Scan for module directories
    for module_path in modules_dir.iterdir():
        if not module_path.is_dir():
            continue
        
        if module_path.name.startswith("_"):
            continue
        
        # Look for router.py in each module
        router_file = module_path / "router.py"
        if router_file.exists():
            try:
                # Dynamically import the module
                module_name = f"modules.{module_path.name}.router"
                spec = importlib.util.spec_from_file_location(module_name, router_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    
                    # Look for 'router' attribute in the module
                    if hasattr(module, "router"):
                        app.include_router(module.router)
                        loaded_module_routers.append(module_path.name)
                        logger.info(f"✓ Loaded router from module: {module_path.name}")
                    
                    # Look for commands (for future extension)
                    if hasattr(module, "commands"):
                        loaded_module_commands.extend(module.commands)
                        
            except Exception as e:
                logger.error(f"Failed to load module {module_path.name}: {e}", exc_info=True)
    
    # Загрузка модуля F3 из v1 пакета
    # F3 router находится в отдельной структуре v1/ и требует явной регистрации.
    # Контент модуля F3 автоматически загружается через repository.py (autodiscovery),
    # но роутер регистрируется явно для предоставления дополнительных эндпоинтов.
    try:
        from modules.academy.v1.module_f3_router import router as module_f3_router
        app.include_router(module_f3_router)
        loaded_module_routers.append("module_f3_emotion")
        logger.info("✓ Loaded router from module: module_f3_emotion")
    except Exception as e:
        logger.exception("Failed to load module_f3 router: %s", e)
    
    logger.info(f"Discovered module commands: {loaded_module_commands}")
    logger.info(f"Loaded {len(loaded_module_routers)} module routers")


# Core endpoints (existing SALESBOT system)
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "SALESBOT Training System",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/public/v1/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "SALESBOT"}


# Voice/TTS endpoints (existing core functionality)
@app.post("/voice/v1/tts")
async def text_to_speech(text: str, voice_type: str = "ru_female"):
    """
    Text-to-speech endpoint
    Converts text to audio file and returns the file path or audio data
    
    Args:
        text: Text to convert to speech
        voice_type: Voice type (ru_female, ru_male, default)
    
    Returns:
        Audio URL and metadata
    """
    try:
        # Create audio directory if it doesn't exist
        audio_dir = Path(__file__).parent / "audio_cache"
        audio_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        filename = f"{uuid.uuid4()}.mp3"
        filepath = audio_dir / filename
        
        # Determine language and settings based on voice_type
        # Note: gTTS doesn't support different Russian voices, but we accept the parameter
        # for future extensibility
        if voice_type.startswith('ru_') or voice_type == 'russian':
            lang = 'ru'
            slow = False
        else:
            lang = 'en'
            slow = False
        
        # Generate TTS
        tts = gTTS(text=text, lang=lang, slow=slow)
        tts.save(str(filepath))
        
        logger.info(f"Generated TTS audio: {filename} (voice: {voice_type}, lang: {lang})")
        
        return {
            "success": True,
            "audio_url": f"/voice/v1/audio/{filename}",
            "file_path": str(filepath),
            "voice_type": voice_type,
            "language": lang
        }
    except Exception as e:
        logger.error(f"TTS generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


@app.get("/voice/v1/audio/{filename}")
async def get_audio_file(filename: str):
    """Serve generated audio files"""
    audio_dir = Path(__file__).parent / "audio_cache"
    filepath = audio_dir / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(filepath, media_type="audio/mpeg")


@app.get("/voice/v1/chat/status")
async def chat_status():
    """Voice chat status endpoint (placeholder)"""
    return {"status": "available", "chat_sessions": 0}


# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("=== SALESBOT Starting ===")
    initialize_database()
    discover_and_load_modules()
    logger.info("=== SALESBOT Ready ===")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("=== SALESBOT Shutting Down ===")


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info"
    )
