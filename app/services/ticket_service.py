"""
Сервис для работы с тикетами (обращениями)
"""
import random
import string
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import Ticket, TicketStatus, TicketMessage, User, UserRole


class TicketService:
    """Сервис для работы с тикетами"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _generate_ticket_number(self) -> str:
        """Генерация номера тикета"""
        prefix = datetime.now().strftime("%Y%m")
        suffix = ''.join(random.choices(string.digits, k=4))
        return f"T{prefix}-{suffix}"
    
    async def create_ticket(
        self,
        user_id: int,
        subject: str,
        description: str,
        category: Optional[str] = None,
        priority: int = 1,
        is_anonymous: bool = False
    ) -> Ticket:
        """Создание нового тикета"""
        ticket = Ticket(
            ticket_number=self._generate_ticket_number(),
            user_id=user_id,
            subject=subject,
            description=description,
            category=category,
            priority=priority,
            is_anonymous=is_anonymous,
            status=TicketStatus.OPEN
        )
        self.session.add(ticket)
        await self.session.flush()
        
        # Добавляем первое сообщение
        message = TicketMessage(
            ticket_id=ticket.id,
            user_id=user_id,
            message=description,
            is_from_staff=False
        )
        self.session.add(message)
        await self.session.flush()
        
        return ticket
    
    async def get_ticket_by_id(self, ticket_id: int) -> Optional[Ticket]:
        """Получение тикета по ID"""
        result = await self.session.execute(
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .options(
                selectinload(Ticket.user),
                selectinload(Ticket.assigned_to),
                selectinload(Ticket.messages).selectinload(TicketMessage.user)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_ticket_by_number(self, ticket_number: str) -> Optional[Ticket]:
        """Получение тикета по номеру"""
        result = await self.session.execute(
            select(Ticket)
            .where(Ticket.ticket_number == ticket_number)
            .options(
                selectinload(Ticket.user),
                selectinload(Ticket.assigned_to),
                selectinload(Ticket.messages).selectinload(TicketMessage.user)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_user_tickets(
        self, 
        user_id: int, 
        status: Optional[TicketStatus] = None,
        limit: int = 20
    ) -> List[Ticket]:
        """Получение тикетов пользователя"""
        query = (
            select(Ticket)
            .where(Ticket.user_id == user_id)
            .order_by(Ticket.created_at.desc())
            .limit(limit)
            .options(selectinload(Ticket.assigned_to))
        )
        
        if status:
            query = query.where(Ticket.status == status)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_open_tickets(
        self,
        assigned_to_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Ticket]:
        """Получение открытых тикетов (для модераторов)"""
        query = (
            select(Ticket)
            .where(
                Ticket.status.in_([
                    TicketStatus.OPEN,
                    TicketStatus.IN_PROGRESS,
                    TicketStatus.WAITING
                ])
            )
            .order_by(Ticket.priority.desc(), Ticket.created_at.asc())
            .limit(limit)
            .options(
                selectinload(Ticket.user),
                selectinload(Ticket.assigned_to)
            )
        )
        
        if assigned_to_id:
            query = query.where(
                or_(
                    Ticket.assigned_to_id == assigned_to_id,
                    Ticket.assigned_to_id == None
                )
            )
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def update_status(
        self, 
        ticket_id: int, 
        new_status: TicketStatus,
        user_id: int,
        comment: Optional[str] = None
    ) -> Optional[Ticket]:
        """Обновление статуса тикета"""
        result = await self.session.execute(
            select(Ticket).where(Ticket.id == ticket_id)
        )
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            return None
        
        old_status = ticket.status
        ticket.status = new_status
        
        if new_status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
            ticket.resolved_at = datetime.utcnow()
        
        # Добавляем системное сообщение
        status_msg = f"Статус изменён: {old_status.value} → {new_status.value}"
        if comment:
            status_msg += f"\n\nКомментарий: {comment}"
        
        message = TicketMessage(
            ticket_id=ticket.id,
            user_id=user_id,
            message=status_msg,
            is_from_staff=True,
            is_internal=False
        )
        self.session.add(message)
        await self.session.flush()
        
        return ticket
    
    async def assign_ticket(
        self, 
        ticket_id: int, 
        assigned_to_id: int
    ) -> Optional[Ticket]:
        """Назначение тикета модератору"""
        result = await self.session.execute(
            select(Ticket).where(Ticket.id == ticket_id)
        )
        ticket = result.scalar_one_or_none()
        
        if ticket:
            ticket.assigned_to_id = assigned_to_id
            if ticket.status == TicketStatus.OPEN:
                ticket.status = TicketStatus.IN_PROGRESS
            await self.session.flush()
        
        return ticket
    
    async def add_message(
        self,
        ticket_id: int,
        user_id: int,
        message: str,
        is_from_staff: bool = False,
        is_internal: bool = False
    ) -> TicketMessage:
        """Добавление сообщения в тикет"""
        # Обновляем статус тикета
        result = await self.session.execute(
            select(Ticket).where(Ticket.id == ticket_id)
        )
        ticket = result.scalar_one_or_none()
        
        if ticket:
            if is_from_staff:
                if ticket.status == TicketStatus.OPEN:
                    ticket.status = TicketStatus.IN_PROGRESS
            else:
                if ticket.status == TicketStatus.WAITING:
                    ticket.status = TicketStatus.IN_PROGRESS
        
        msg = TicketMessage(
            ticket_id=ticket_id,
            user_id=user_id,
            message=message,
            is_from_staff=is_from_staff,
            is_internal=is_internal
        )
        self.session.add(msg)
        await self.session.flush()
        
        return msg
    
    async def get_messages(
        self, 
        ticket_id: int,
        include_internal: bool = False
    ) -> List[TicketMessage]:
        """Получение сообщений тикета"""
        query = (
            select(TicketMessage)
            .where(TicketMessage.ticket_id == ticket_id)
            .order_by(TicketMessage.created_at.asc())
            .options(selectinload(TicketMessage.user))
        )
        
        if not include_internal:
            query = query.where(TicketMessage.is_internal == False)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    # === Статистика ===
    
    async def get_stats(self) -> dict:
        """Получение статистики тикетов"""
        # Общее количество
        total = await self.session.execute(
            select(func.count(Ticket.id))
        )
        
        # По статусам
        stats_by_status = {}
        for status in TicketStatus:
            count = await self.session.execute(
                select(func.count(Ticket.id))
                .where(Ticket.status == status)
            )
            stats_by_status[status.value] = count.scalar() or 0
        
        # Среднее время ответа (для закрытых)
        avg_resolution_time = await self.session.execute(
            select(
                func.avg(
                    func.julianday(Ticket.resolved_at) - 
                    func.julianday(Ticket.created_at)
                )
            )
            .where(Ticket.resolved_at != None)
        )
        
        return {
            "total": total.scalar() or 0,
            "by_status": stats_by_status,
            "avg_resolution_days": round(avg_resolution_time.scalar() or 0, 2)
        }
    
    async def get_unassigned_count(self) -> int:
        """Количество неназначенных тикетов"""
        result = await self.session.execute(
            select(func.count(Ticket.id))
            .where(
                and_(
                    Ticket.assigned_to_id == None,
                    Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
                )
            )
        )
        return result.scalar() or 0

