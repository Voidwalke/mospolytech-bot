"""
Клавиатуры тикетов
"""
from typing import List

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)

from app.database import Ticket, TicketStatus


class TicketKeyboards:
    """Клавиатуры для работы с тикетами"""
    
    # Категории обращений
    CATEGORIES = [
        ("schedule", "📅 Расписание"),
        ("scholarship", "💰 Стипендии"),
        ("enrollment", "📝 Зачисление/Отчисление"),
        ("debts", "📚 Задолженности"),
        ("practice", "🏢 Практика"),
        ("documents", "📄 Документы"),
        ("other", "❓ Другое")
    ]
    
    @staticmethod
    def category_select() -> InlineKeyboardMarkup:
        """Выбор категории обращения"""
        buttons = []
        
        for slug, name in TicketKeyboards.CATEGORIES:
            buttons.append([
                InlineKeyboardButton(
                    text=name,
                    callback_data=f"ticket_cat:{slug}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="ticket_cancel"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def priority_select() -> InlineKeyboardMarkup:
        """Выбор приоритета"""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🟢 Низкий",
                        callback_data="ticket_priority:1"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🟡 Средний",
                        callback_data="ticket_priority:2"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔴 Высокий",
                        callback_data="ticket_priority:3"
                    )
                ]
            ]
        )
    
    @staticmethod
    def anonymous_option() -> InlineKeyboardMarkup:
        """Опция анонимного обращения"""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👤 Обычное обращение",
                        callback_data="ticket_anon:0"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🎭 Анонимное обращение",
                        callback_data="ticket_anon:1"
                    )
                ]
            ]
        )
    
    @staticmethod
    def user_tickets(tickets: List[Ticket]) -> InlineKeyboardMarkup:
        """Список тикетов пользователя"""
        buttons = []
        
        status_icons = {
            TicketStatus.OPEN: "🆕",
            TicketStatus.IN_PROGRESS: "🔄",
            TicketStatus.WAITING: "⏳",
            TicketStatus.RESOLVED: "✅",
            TicketStatus.CLOSED: "🔒"
        }
        
        for ticket in tickets[:10]:  # Максимум 10
            icon = status_icons.get(ticket.status, "📋")
            text = f"{icon} {ticket.ticket_number}: {ticket.subject[:30]}"
            buttons.append([
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"ticket_view:{ticket.id}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(
                text="➕ Новое обращение",
                callback_data="create_ticket"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def ticket_actions(ticket: Ticket, is_staff: bool = False) -> InlineKeyboardMarkup:
        """Действия с тикетом"""
        buttons = []
        
        # Для пользователя
        if ticket.status not in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
            buttons.append([
                InlineKeyboardButton(
                    text="💬 Добавить сообщение",
                    callback_data=f"ticket_reply:{ticket.id}"
                )
            ])
        
        if ticket.status == TicketStatus.RESOLVED:
            buttons.append([
                InlineKeyboardButton(
                    text="✅ Закрыть обращение",
                    callback_data=f"ticket_close:{ticket.id}"
                ),
                InlineKeyboardButton(
                    text="🔄 Переоткрыть",
                    callback_data=f"ticket_reopen:{ticket.id}"
                )
            ])
        
        # Для модератора
        if is_staff:
            buttons.append([
                InlineKeyboardButton(
                    text="📝 Изменить статус",
                    callback_data=f"admin_ticket_status:{ticket.id}"
                )
            ])
            buttons.append([
                InlineKeyboardButton(
                    text="👤 Назначить",
                    callback_data=f"admin_ticket_assign:{ticket.id}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(
                text="◀️ К списку",
                callback_data="tickets_list"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def status_change(ticket_id: int) -> InlineKeyboardMarkup:
        """Изменение статуса тикета"""
        buttons = []
        
        statuses = [
            (TicketStatus.IN_PROGRESS, "🔄 В работе"),
            (TicketStatus.WAITING, "⏳ Ожидает ответа"),
            (TicketStatus.RESOLVED, "✅ Решён"),
            (TicketStatus.CLOSED, "🔒 Закрыт")
        ]
        
        for status, name in statuses:
            buttons.append([
                InlineKeyboardButton(
                    text=name,
                    callback_data=f"ticket_set_status:{ticket_id}:{status.value}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=f"ticket_view:{ticket_id}"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def confirm_send() -> ReplyKeyboardMarkup:
        """Подтверждение отправки"""
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="✅ Отправить"),
                    KeyboardButton(text="✏️ Редактировать")
                ],
                [KeyboardButton(text="❌ Отмена")]
            ],
            resize_keyboard=True
        )

