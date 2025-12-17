"""
Middleware антиспама (throttling)
"""
import time
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware для защиты от спама.
    Ограничивает частоту сообщений от пользователя.
    """
    
    def __init__(
        self, 
        rate_limit: float = 0.5,  # Минимальный интервал между сообщениями (сек)
        warning_limit: int = 3    # После скольких нарушений показывать предупреждение
    ):
        self.rate_limit = rate_limit
        self.warning_limit = warning_limit
        self.user_timestamps: Dict[int, float] = defaultdict(float)
        self.user_violations: Dict[int, int] = defaultdict(int)
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)
        
        user_id = event.from_user.id if event.from_user else None
        
        if user_id is None:
            return await handler(event, data)
        
        current_time = time.time()
        last_time = self.user_timestamps[user_id]
        
        if current_time - last_time < self.rate_limit:
            self.user_violations[user_id] += 1
            
            if self.user_violations[user_id] >= self.warning_limit:
                await event.answer(
                    "⏳ Пожалуйста, не отправляйте сообщения слишком часто.\n"
                    "Подождите немного и попробуйте снова."
                )
                self.user_violations[user_id] = 0
            
            return None
        
        self.user_timestamps[user_id] = current_time
        self.user_violations[user_id] = 0
        
        return await handler(event, data)

