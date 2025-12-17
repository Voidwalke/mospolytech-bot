"""
Middleware авторизации и управления пользователями
"""
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, User, UserRole
from app.config import settings


class AuthMiddleware(BaseMiddleware):
    """
    Middleware для авторизации пользователей.
    Создаёт/обновляет пользователя в БД и добавляет его в контекст.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем пользователя из события
        user_data = None
        
        if isinstance(event, Message):
            user_data = event.from_user
        elif isinstance(event, CallbackQuery):
            user_data = event.from_user
        
        if user_data is None:
            return await handler(event, data)
        
        # Получаем или создаём пользователя
        async with async_session() as session:
            user = await self._get_or_create_user(session, user_data)
            
            # Обновляем активность
            user.last_activity = datetime.utcnow()
            await session.commit()
            
            # Добавляем в контекст
            data["user"] = user
            data["db_session"] = session
            data["is_admin"] = user.telegram_id in settings.ADMIN_IDS or user.role == UserRole.ADMIN
            
            return await handler(event, data)
    
    async def _get_or_create_user(
        self, 
        session: AsyncSession, 
        tg_user
    ) -> User:
        """Получение или создание пользователя"""
        result = await session.execute(
            select(User).where(User.telegram_id == tg_user.id)
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            # Создаём нового пользователя
            user = User(
                telegram_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                role=UserRole.ADMIN if tg_user.id in settings.ADMIN_IDS else UserRole.STUDENT
            )
            session.add(user)
            await session.flush()
        else:
            # Обновляем данные
            user.username = tg_user.username
            user.first_name = tg_user.first_name
            user.last_name = tg_user.last_name
            
            # Проверяем админа
            if tg_user.id in settings.ADMIN_IDS and user.role != UserRole.ADMIN:
                user.role = UserRole.ADMIN
        
        return user


def role_required(*allowed_roles: UserRole):
    """
    Декоратор для проверки роли пользователя
    
    Использование:
        @role_required(UserRole.ADMIN, UserRole.MODERATOR)
        async def admin_handler(message: Message, user: User):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            user: User = kwargs.get("user")
            
            if user is None:
                return None
            
            if user.role not in allowed_roles:
                # Определяем тип события для отправки ответа
                event = args[0] if args else None
                if isinstance(event, Message):
                    await event.answer(
                        "⛔ У вас нет доступа к этой функции.\n"
                        "Если считаете, что это ошибка, обратитесь к администратору."
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "⛔ Нет доступа к этой функции",
                        show_alert=True
                    )
                return None
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(func):
    """Декоратор для проверки прав администратора"""
    return role_required(UserRole.ADMIN)(func)


def moderator_required(func):
    """Декоратор для проверки прав модератора или выше"""
    return role_required(UserRole.ADMIN, UserRole.MODERATOR)(func)


def staff_required(func):
    """Декоратор для проверки прав сотрудника (преподаватель и выше)"""
    return role_required(UserRole.ADMIN, UserRole.MODERATOR, UserRole.TEACHER)(func)

