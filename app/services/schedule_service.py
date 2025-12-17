"""
Сервис для работы с расписанием
"""
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Schedule


class ScheduleService:
    """Сервис для работы с расписанием"""
    
    EVENT_TYPES = {
        "lesson": "📚 Занятие",
        "exam": "📝 Экзамен",
        "consultation": "💬 Консультация",
        "event": "🎉 Мероприятие",
        "holiday": "🎄 Праздник/Каникулы",
        "deadline": "⏰ Дедлайн"
    }
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_schedule_for_group(
        self,
        group_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Schedule]:
        """Получение расписания для группы"""
        if start_date is None:
            start_date = datetime.utcnow()
        if end_date is None:
            end_date = start_date + timedelta(days=7)
        
        result = await self.session.execute(
            select(Schedule)
            .where(
                and_(
                    Schedule.group_name == group_name,
                    Schedule.start_time >= start_date,
                    Schedule.start_time <= end_date,
                    Schedule.is_cancelled == False
                )
            )
            .order_by(Schedule.start_time)
        )
        return result.scalars().all()
    
    async def get_schedule_for_date(
        self,
        group_name: str,
        date: datetime
    ) -> List[Schedule]:
        """Получение расписания на конкретную дату"""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        result = await self.session.execute(
            select(Schedule)
            .where(
                and_(
                    Schedule.group_name == group_name,
                    Schedule.start_time >= start_of_day,
                    Schedule.start_time < end_of_day,
                    Schedule.is_cancelled == False
                )
            )
            .order_by(Schedule.start_time)
        )
        return result.scalars().all()
    
    async def get_today_schedule(self, group_name: str) -> List[Schedule]:
        """Расписание на сегодня"""
        return await self.get_schedule_for_date(group_name, datetime.utcnow())
    
    async def get_tomorrow_schedule(self, group_name: str) -> List[Schedule]:
        """Расписание на завтра"""
        tomorrow = datetime.utcnow() + timedelta(days=1)
        return await self.get_tomorrow_schedule(group_name)
    
    async def get_upcoming_exams(
        self,
        group_name: Optional[str] = None,
        course: Optional[int] = None,
        limit: int = 10
    ) -> List[Schedule]:
        """Получение предстоящих экзаменов"""
        query = (
            select(Schedule)
            .where(
                and_(
                    Schedule.event_type == "exam",
                    Schedule.start_time >= datetime.utcnow(),
                    Schedule.is_cancelled == False
                )
            )
            .order_by(Schedule.start_time)
            .limit(limit)
        )
        
        if group_name:
            query = query.where(Schedule.group_name == group_name)
        if course:
            query = query.where(Schedule.course == course)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_upcoming_events(self, limit: int = 10) -> List[Schedule]:
        """Получение предстоящих мероприятий"""
        result = await self.session.execute(
            select(Schedule)
            .where(
                and_(
                    Schedule.event_type.in_(["event", "holiday"]),
                    Schedule.start_time >= datetime.utcnow(),
                    Schedule.is_cancelled == False
                )
            )
            .order_by(Schedule.start_time)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def create_event(
        self,
        title: str,
        event_type: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        group_name: Optional[str] = None,
        faculty: Optional[str] = None,
        course: Optional[int] = None,
        location: Optional[str] = None,
        teacher: Optional[str] = None,
        description: Optional[str] = None
    ) -> Schedule:
        """Создание события"""
        event = Schedule(
            title=title,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
            group_name=group_name,
            faculty=faculty,
            course=course,
            location=location,
            teacher=teacher,
            description=description
        )
        self.session.add(event)
        await self.session.flush()
        return event
    
    async def cancel_event(self, event_id: int) -> bool:
        """Отмена события"""
        result = await self.session.execute(
            select(Schedule).where(Schedule.id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if event:
            event.is_cancelled = True
            await self.session.flush()
            return True
        return False
    
    async def reschedule_event(
        self,
        event_id: int,
        new_start_time: datetime,
        new_end_time: Optional[datetime] = None
    ) -> Optional[Schedule]:
        """Перенос события"""
        result = await self.session.execute(
            select(Schedule).where(Schedule.id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if event:
            event.start_time = new_start_time
            if new_end_time:
                event.end_time = new_end_time
            event.is_rescheduled = True
            await self.session.flush()
        
        return event
    
    async def get_changes(
        self,
        group_name: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[Schedule]:
        """Получение изменений в расписании"""
        if since is None:
            since = datetime.utcnow() - timedelta(days=7)
        
        query = (
            select(Schedule)
            .where(
                and_(
                    or_(
                        Schedule.is_cancelled == True,
                        Schedule.is_rescheduled == True
                    ),
                    Schedule.created_at >= since
                )
            )
            .order_by(Schedule.created_at.desc())
        )
        
        if group_name:
            query = query.where(Schedule.group_name == group_name)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    def format_schedule_item(self, item: Schedule) -> str:
        """Форматирование элемента расписания"""
        emoji = self.EVENT_TYPES.get(item.event_type, "📌")
        
        time_str = item.start_time.strftime("%H:%M")
        if item.end_time:
            time_str += f" - {item.end_time.strftime('%H:%M')}"
        
        text = f"{emoji} <b>{time_str}</b> — {item.title}"
        
        if item.location:
            text += f"\n   📍 {item.location}"
        if item.teacher:
            text += f"\n   👨‍🏫 {item.teacher}"
        if item.is_rescheduled:
            text += "\n   ⚠️ <i>Перенесено</i>"
        
        return text
    
    def format_day_schedule(self, items: List[Schedule], date: datetime) -> str:
        """Форматирование расписания на день"""
        date_str = date.strftime("%d.%m.%Y (%A)")
        
        if not items:
            return f"📅 <b>{date_str}</b>\n\n🎉 Занятий нет!"
        
        text = f"📅 <b>{date_str}</b>\n\n"
        text += "\n\n".join(self.format_schedule_item(item) for item in items)
        
        return text

