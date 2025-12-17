"""
Middleware логирования запросов
"""
import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from loguru import logger


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware для логирования всех входящих запросов
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        start_time = time.time()
        
        # Логируем входящее событие
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else "unknown"
            text = event.text[:100] if event.text else "[no text]"
            logger.info(f"📩 Message from {user_id}: {text}")
            
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else "unknown"
            callback_data = event.data[:100] if event.data else "[no data]"
            logger.info(f"🔘 Callback from {user_id}: {callback_data}")
        
        try:
            result = await handler(event, data)
            
            # Логируем время выполнения
            elapsed = (time.time() - start_time) * 1000
            logger.debug(f"⏱️ Handler completed in {elapsed:.2f}ms")
            
            return result
            
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"❌ Handler error after {elapsed:.2f}ms: {e}")
            raise

