"""
Notification Service for Academy
Sends notifications about new modules and important updates
"""
import os
import logging
import asyncio
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications to users"""
    
    def __init__(self):
        """Initialize notification service"""
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.notification_log_file = Path(__file__).parent.parent.parent / "data" / "notifications.log"
        self.notification_log_file.parent.mkdir(parents=True, exist_ok=True)
    
    async def notify_new_module(self, module_title: str, module_description: str, user_ids: List[str]):
        """
        Notify users about a new module
        
        Args:
            module_title: Title of the new module
            module_description: Description of the module
            user_ids: List of user IDs to notify
        """
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not set, cannot send notifications")
            return
        
        message = f"""
📚 *Новый обучающий модуль!*

*{module_title}*

{module_description}

Начните обучение прямо сейчас! Используйте команду /academy для доступа к модулю.
"""
        
        # Log notification
        self._log_notification("new_module", module_title, len(user_ids))
        
        # Send notifications asynchronously
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                tasks = []
                for user_id in user_ids[:100]:  # Limit to 100 users at once to avoid rate limits
                    task = self._send_telegram_message(client, user_id, message)
                    tasks.append(task)
                
                # Send in batches
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count successes
                success_count = sum(1 for r in results if r is True)
                logger.info(f"Sent {success_count}/{len(user_ids)} notifications for new module: {module_title}")
        
        except Exception as e:
            logger.error(f"Error sending notifications: {e}", exc_info=True)
    
    async def _send_telegram_message(self, client, user_id: str, message: str) -> bool:
        """
        Send a Telegram message to a user
        
        Args:
            client: httpx AsyncClient
            user_id: Telegram user ID
            message: Message to send
        
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": user_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = await client.post(url, json=data)
            
            if response.status_code == 200:
                return True
            else:
                logger.warning(f"Failed to send notification to {user_id}: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Error sending message to {user_id}: {e}")
            return False
    
    def _log_notification(self, notification_type: str, subject: str, recipient_count: int):
        """
        Log notification to file
        
        Args:
            notification_type: Type of notification
            subject: Subject/title of notification
            recipient_count: Number of recipients
        """
        try:
            from datetime import datetime
            
            log_entry = f"{datetime.now().isoformat()} | {notification_type} | {subject} | {recipient_count} recipients\n"
            
            with open(self.notification_log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        
        except Exception as e:
            logger.error(f"Error logging notification: {e}")


# Global notification service instance
notification_service = NotificationService()
