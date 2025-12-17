"""
Сервис уведомлений
"""
from datetime import datetime
from typing import List, Optional

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from loguru import logger
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Notification, User, UserRole


class NotificationService:
    """Сервис для отправки уведомлений"""
    
    def __init__(self, session: AsyncSession, bot: Optional[Bot] = None):
        self.session = session
        self.bot = bot
    
    async def create_notification(
        self,
        title: str,
        message: str,
        target_role: Optional[str] = None,
        target_group: Optional[str] = None,
        target_course: Optional[int] = None,
        target_faculty: Optional[str] = None,
        scheduled_at: Optional[datetime] = None
    ) -> Notification:
        """Создание уведомления"""
        notification = Notification(
            title=title,
            message=message,
            target_role=target_role,
            target_group=target_group,
            target_course=target_course,
            target_faculty=target_faculty,
            scheduled_at=scheduled_at
        )
        self.session.add(notification)
        await self.session.flush()
        return notification
    
    async def get_pending_notifications(self) -> List[Notification]:
        """Получение уведомлений для отправки"""
        now = datetime.utcnow()
        
        result = await self.session.execute(
            select(Notification)
            .where(
                and_(
                    Notification.is_active == True,
                    Notification.is_sent == False,
                    (Notification.scheduled_at == None) | (Notification.scheduled_at <= now)
                )
            )
        )
        return result.scalars().all()
    
    async def get_target_users(self, notification: Notification) -> List[User]:
        """Получение списка пользователей для уведомления"""
        query = select(User).where(
            User.is_active == True,
            User.notifications_enabled == True
        )
        
        if notification.target_role:
            try:
                role = UserRole(notification.target_role)
                query = query.where(User.role == role)
            except ValueError:
                pass
        
        if notification.target_group:
            query = query.where(User.group_name == notification.target_group)
        
        if notification.target_course:
            query = query.where(User.course == notification.target_course)
        
        if notification.target_faculty:
            query = query.where(User.faculty == notification.target_faculty)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def send_notification(self, notification: Notification) -> int:
        """Отправка уведомления"""
        if not self.bot:
            raise ValueError("Bot instance not provided")
        
        users = await self.get_target_users(notification)
        sent_count = 0
        
        text = f"📢 <b>{notification.title}</b>\n\n{notification.message}"
        
        for user in users:
            try:
                await self.bot.send_message(
                    chat_id=user.telegram_id,
                    text=text,
                    parse_mode="HTML"
                )
                sent_count += 1
            except TelegramForbiddenError:
                # Пользователь заблокировал бота
                user.is_active = False
                logger.warning(f"User {user.telegram_id} blocked the bot")
            except TelegramBadRequest as e:
                logger.error(f"Failed to send to {user.telegram_id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error sending to {user.telegram_id}: {e}")
        
        # Обновляем статус уведомления
        notification.is_sent = True
        notification.sent_at = datetime.utcnow()
        notification.sent_count = sent_count
        await self.session.flush()
        
        return sent_count
    
    async def send_to_user(
        self,
        user_id: int,
        text: str,
        parse_mode: str = "HTML"
    ) -> bool:
        """Отправка сообщения конкретному пользователю"""
        if not self.bot:
            raise ValueError("Bot instance not provided")
        
        # Получаем telegram_id
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        try:
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode=parse_mode
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send to user {user_id}: {e}")
            return False
    
    async def send_to_moderators(self, text: str) -> int:
        """Отправка сообщения всем модераторам"""
        if not self.bot:
            raise ValueError("Bot instance not provided")
        
        result = await self.session.execute(
            select(User)
            .where(
                User.role.in_([UserRole.ADMIN, UserRole.MODERATOR]),
                User.is_active == True
            )
        )
        moderators = result.scalars().all()
        
        sent_count = 0
        for mod in moderators:
            try:
                await self.bot.send_message(
                    chat_id=mod.telegram_id,
                    text=text,
                    parse_mode="HTML"
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to notify moderator {mod.telegram_id}: {e}")
        
        return sent_count
    
    async def notify_new_ticket(self, ticket_number: str, subject: str):
        """Уведомление о новом тикете"""
        text = (
            f"🎫 <b>Новое обращение!</b>\n\n"
            f"Номер: <code>{ticket_number}</code>\n"
            f"Тема: {subject}\n\n"
            f"Используйте /admin для просмотра"
        )
        await self.send_to_moderators(text)
    
    async def notify_ticket_response(
        self,
        user_telegram_id: int,
        ticket_number: str,
        response_preview: str
    ):
        """Уведомление пользователя об ответе на тикет"""
        if not self.bot:
            return
        
        text = (
            f"💬 <b>Ответ на ваше обращение</b>\n\n"
            f"Номер: <code>{ticket_number}</code>\n\n"
            f"{response_preview[:200]}{'...' if len(response_preview) > 200 else ''}\n\n"
            f"Используйте /tickets для подробностей"
        )
        
        try:
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=text,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to notify user about ticket response: {e}")
    
    async def get_all_notifications(
        self,
        limit: int = 50,
        include_sent: bool = True
    ) -> List[Notification]:
        """Получение всех уведомлений"""
        query = (
            select(Notification)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        
        if not include_sent:
            query = query.where(Notification.is_sent == False)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def delete_notification(self, notification_id: int) -> bool:
        """Удаление уведомления"""
        result = await self.session.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        notification = result.scalar_one_or_none()
        
        if notification:
            await self.session.delete(notification)
            return True
        return False

