"""
Сервис для работы с пользователями
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import User, UserRole


class UserService:
    """Сервис для работы с пользователями"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Получение пользователя по ID"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получение пользователя по Telegram ID"""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    
    async def search_users(
        self,
        query: str,
        limit: int = 20
    ) -> List[User]:
        """Поиск пользователей"""
        search_pattern = f"%{query}%"
        result = await self.session.execute(
            select(User)
            .where(
                or_(
                    User.username.ilike(search_pattern),
                    User.full_name.ilike(search_pattern),
                    User.first_name.ilike(search_pattern),
                    User.last_name.ilike(search_pattern),
                    User.group_name.ilike(search_pattern),
                    User.student_id.ilike(search_pattern)
                )
            )
            .limit(limit)
        )
        return result.scalars().all()
    
    async def update_profile(
        self,
        user_id: int,
        full_name: Optional[str] = None,
        course: Optional[int] = None,
        group_name: Optional[str] = None,
        student_id: Optional[str] = None,
        faculty: Optional[str] = None,
        is_onboarded: Optional[bool] = None
    ) -> Optional[User]:
        """Обновление профиля пользователя"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            if full_name is not None:
                user.full_name = full_name
            if course is not None:
                user.course = course
            if group_name is not None:
                user.group_name = group_name
            if student_id is not None:
                user.student_id = student_id
            if faculty is not None:
                user.faculty = faculty
            if is_onboarded is not None:
                user.is_onboarded = is_onboarded
            
            await self.session.flush()
        
        return user
    
    async def complete_onboarding(self, user_id: int) -> Optional[User]:
        """Завершение онбординга пользователя"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.is_onboarded = True
            await self.session.flush()
        
        return user
    
    async def set_role(self, user_id: int, role: UserRole) -> Optional[User]:
        """Установка роли пользователя"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.role = role
            await self.session.flush()
        
        return user
    
    async def set_verified(self, user_id: int, verified: bool = True) -> Optional[User]:
        """Верификация пользователя"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.is_verified = verified
            await self.session.flush()
        
        return user
    
    async def toggle_notifications(self, user_id: int) -> Optional[bool]:
        """Переключение уведомлений"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.notifications_enabled = not user.notifications_enabled
            await self.session.flush()
            return user.notifications_enabled
        
        return None
    
    async def get_users_by_role(
        self, 
        role: UserRole, 
        active_only: bool = True
    ) -> List[User]:
        """Получение пользователей по роли"""
        query = select(User).where(User.role == role)
        
        if active_only:
            query = query.where(User.is_active == True)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_users_by_group(self, group_name: str) -> List[User]:
        """Получение пользователей по группе"""
        result = await self.session.execute(
            select(User)
            .where(User.group_name == group_name, User.is_active == True)
        )
        return result.scalars().all()
    
    async def get_users_by_course(self, course: int) -> List[User]:
        """Получение пользователей по курсу"""
        result = await self.session.execute(
            select(User)
            .where(User.course == course, User.is_active == True)
        )
        return result.scalars().all()
    
    async def get_users_with_notifications(
        self,
        role: Optional[UserRole] = None,
        group_name: Optional[str] = None,
        course: Optional[int] = None,
        faculty: Optional[str] = None
    ) -> List[User]:
        """Получение пользователей для рассылки"""
        query = select(User).where(
            User.is_active == True,
            User.notifications_enabled == True
        )
        
        if role:
            query = query.where(User.role == role)
        if group_name:
            query = query.where(User.group_name == group_name)
        if course:
            query = query.where(User.course == course)
        if faculty:
            query = query.where(User.faculty == faculty)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def deactivate_user(self, user_id: int) -> bool:
        """Деактивация пользователя"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.is_active = False
            await self.session.flush()
            return True
        return False
    
    # === Статистика ===
    
    async def get_stats(self) -> dict:
        """Получение статистики пользователей"""
        # Общее количество
        total = await self.session.execute(
            select(func.count(User.id))
        )
        
        # Активные
        active = await self.session.execute(
            select(func.count(User.id))
            .where(User.is_active == True)
        )
        
        # По ролям
        stats_by_role = {}
        for role in UserRole:
            count = await self.session.execute(
                select(func.count(User.id))
                .where(User.role == role)
            )
            stats_by_role[role.value] = count.scalar() or 0
        
        # Верифицированные
        verified = await self.session.execute(
            select(func.count(User.id))
            .where(User.is_verified == True)
        )
        
        # Новые за сегодня
        today = datetime.utcnow().date()
        new_today = await self.session.execute(
            select(func.count(User.id))
            .where(func.date(User.created_at) == today)
        )
        
        return {
            "total": total.scalar() or 0,
            "active": active.scalar() or 0,
            "verified": verified.scalar() or 0,
            "new_today": new_today.scalar() or 0,
            "by_role": stats_by_role
        }

