"""
Text-to-Speech Service for Academy Lessons
Supports multiple TTS providers including AssemblyAI and gTTS
"""
import os
import logging
import uuid
import time
import httpx
from pathlib import Path
from typing import Optional, Literal
from gtts import gTTS

logger = logging.getLogger(__name__)

# TTS Configuration
VOICE_API_KEY = os.getenv("VOICE_API_KEY", "")
VOICE_API_BASE_URL = os.getenv("VOICE_API_BASE_URL", "https://api.assemblyai.com/v2")
TTS_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "tts"


class TTSService:
    """Text-to-Speech service with multiple provider support"""
    
    def __init__(self):
        """Initialize TTS service"""
        # Ensure TTS directory exists
        TTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Determine which TTS provider to use
        self.use_assemblyai = bool(VOICE_API_KEY)
        
        if self.use_assemblyai:
            logger.info("Using AssemblyAI for TTS")
        else:
            logger.info("Using gTTS for TTS (VOICE_API_KEY not set)")
    
    async def generate_tts(
        self,
        text: str,
        voice_type: Literal["ru_female", "ru_male"] = "ru_female",
        cache_key: Optional[str] = None
    ) -> dict:
        """
        Generate TTS audio from text with caching support
        
        Args:
            text: Text to convert to speech
            voice_type: Voice type (ru_female or ru_male)
            cache_key: Optional cache key for consistent file naming (e.g., lesson_id)
        
        Returns:
            Dictionary with audio_url, file_path, and metadata
        """
        if self.use_assemblyai:
            return await self._generate_assemblyai_tts(text, voice_type)
        else:
            return await self._generate_gtts(text, voice_type, cache_key)
    
    async def _generate_assemblyai_tts(
        self,
        text: str,
        voice_type: str
    ) -> dict:
        """
        Generate TTS using AssemblyAI API
        
        Note: As of 2024, AssemblyAI primarily focuses on speech-to-text (transcription).
        For text-to-speech, we would need to use their partner services or fallback to gTTS.
        This is a placeholder implementation that falls back to gTTS.
        """
        logger.warning("AssemblyAI TTS not fully implemented, falling back to gTTS")
        return await self._generate_gtts(text, voice_type)
        
        # If AssemblyAI adds TTS in the future, implementation would be:
        # try:
        #     async with httpx.AsyncClient() as client:
        #         headers = {
        #             "authorization": VOICE_API_KEY,
        #             "content-type": "application/json"
        #         }
        #         
        #         # Map voice types to AssemblyAI voices
        #         voice_map = {
        #             "ru_female": "ru-RU-DariyaNeural",
        #             "ru_male": "ru-RU-DmitryNeural"
        #         }
        #         
        #         data = {
        #             "text": text,
        #             "voice": voice_map.get(voice_type, voice_map["ru_female"]),
        #             "language": "ru"
        #         }
        #         
        #         response = await client.post(
        #             f"{VOICE_API_BASE_URL}/synthesize",
        #             headers=headers,
        #             json=data,
        #             timeout=60.0
        #         )
        #         
        #         if response.status_code == 200:
        #             # Save audio file
        #             filename = f"{uuid.uuid4()}.mp3"
        #             filepath = TTS_DATA_DIR / filename
        #             
        #             with open(filepath, 'wb') as f:
        #                 f.write(response.content)
        #             
        #             logger.info(f"Generated TTS audio via AssemblyAI: {filename}")
        #             
        #             return {
        #                 "success": True,
        #                 "audio_url": f"/data/tts/{filename}",
        #                 "file_path": str(filepath),
        #                 "voice_type": voice_type,
        #                 "provider": "assemblyai",
        #                 "language": "ru"
        #             }
        #         else:
        #             logger.error(f"AssemblyAI API error: {response.status_code}")
        #             raise Exception(f"TTS API error: {response.status_code}")
        # 
        # except Exception as e:
        #     logger.error(f"AssemblyAI TTS failed: {e}", exc_info=True)
        #     # Fallback to gTTS
        #     logger.info("Falling back to gTTS")
        #     return await self._generate_gtts(text, voice_type)
    
    async def _generate_gtts(
        self,
        text: str,
        voice_type: str,
        cache_key: Optional[str] = None
    ) -> dict:
        """
        Generate TTS using Google Text-to-Speech (gTTS) with caching support
        
        Args:
            text: Text to convert to speech
            voice_type: Voice type (ru_female or ru_male) - note: gTTS doesn't distinguish
            cache_key: Optional cache key (e.g., lesson_id) for consistent file naming
        
        Returns:
            Dictionary with audio_url, file_path, and metadata
        """
        try:
            # Generate filename with caching support
            if cache_key:
                # Use cache key for consistent naming
                filename = f"{cache_key}_{voice_type}.mp3"
            else:
                # Fallback to unique filename
                filename = f"{uuid.uuid4()}.mp3"
            
            filepath = TTS_DATA_DIR / filename
            
            # Check if cached file exists
            if filepath.exists():
                logger.info(f"Using cached TTS audio: {filename}")
                return {
                    "success": True,
                    "audio_url": f"/data/tts/{filename}",
                    "file_path": str(filepath),
                    "voice_type": voice_type,
                    "provider": "gtts",
                    "language": "ru",
                    "cached": True
                }
            
            # Generate TTS (gTTS doesn't have gender selection, but accepts the parameter)
            # We use Russian language with timeout protection
            try:
                tts = gTTS(text=text, lang='ru', slow=False, timeout=30)
                tts.save(str(filepath))
            except Exception as gtts_error:
                logger.error(f"gTTS timeout or error: {gtts_error}")
                # Retry once with shorter text if needed
                if len(text) > 5000:
                    logger.warning("Text too long, truncating for TTS")
                    text = text[:5000] + "..."
                    tts = gTTS(text=text, lang='ru', slow=False, timeout=30)
                    tts.save(str(filepath))
                else:
                    raise
            
            logger.info(f"Generated TTS audio via gTTS: {filename} (voice: {voice_type})")
            
            return {
                "success": True,
                "audio_url": f"/data/tts/{filename}",
                "file_path": str(filepath),
                "voice_type": voice_type,
                "provider": "gtts",
                "language": "ru",
                "cached": False
            }
        
        except Exception as e:
            logger.error(f"gTTS generation failed: {e}", exc_info=True)
            raise Exception(f"TTS generation failed: {str(e)}")
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """
        Clean up TTS files older than specified hours
        
        Args:
            max_age_hours: Maximum age of files to keep (default: 24 hours)
        """
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            deleted_count = 0
            for file_path in TTS_DATA_DIR.glob("*.mp3"):
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    file_path.unlink()
                    deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old TTS files")
        
        except Exception as e:
            logger.error(f"Error cleaning up TTS files: {e}", exc_info=True)


# Global TTS service instance
tts_service = TTSService()
