"""
Клавиатуры админ-панели
"""
from typing import List

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)

from app.database import User, Ticket


class AdminKeyboards:
    """Клавиатуры админ-панели"""
    
    @staticmethod
    def main_menu() -> ReplyKeyboardMarkup:
        """Главное меню админки"""
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="📊 Статистика"),
                    KeyboardButton(text="🎫 Тикеты")
                ],
                [
                    KeyboardButton(text="❓ Управление FAQ"),
                    KeyboardButton(text="📄 Документы")
                ],
                [
                    KeyboardButton(text="👥 Пользователи"),
                    KeyboardButton(text="📢 Рассылка")
                ],
                [KeyboardButton(text="◀️ В главное меню")]
            ],
            resize_keyboard=True
        )
    
    @staticmethod
    def stats_menu() -> InlineKeyboardMarkup:
        """Меню статистики"""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📈 За сегодня",
                        callback_data="stats:today"
                    ),
                    InlineKeyboardButton(
                        text="📊 За неделю",
                        callback_data="stats:week"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📉 За месяц",
                        callback_data="stats:month"
                    ),
                    InlineKeyboardButton(
                        text="📋 За всё время",
                        callback_data="stats:all"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📥 Выгрузить Excel",
                        callback_data="stats:export"
                    )
                ]
            ]
        )
    
    @staticmethod
    def faq_management() -> InlineKeyboardMarkup:
        """Управление FAQ"""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📁 Категории",
                        callback_data="admin_faq:categories"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="➕ Добавить категорию",
                        callback_data="admin_faq:add_category"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="➕ Добавить вопрос",
                        callback_data="admin_faq:add_item"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📊 Статистика FAQ",
                        callback_data="admin_faq:stats"
                    )
                ]
            ]
        )
    
    @staticmethod
    def faq_categories_edit(categories: List) -> InlineKeyboardMarkup:
        """Редактирование категорий FAQ"""
        buttons = []
        
        for cat in categories:
            buttons.append([
                InlineKeyboardButton(
                    text=f"{'✅' if cat.is_active else '❌'} {cat.name}",
                    callback_data=f"admin_faq_cat:{cat.id}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="admin_faq:main"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def faq_category_actions(category_id: int) -> InlineKeyboardMarkup:
        """Действия с категорией FAQ"""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📝 Редактировать",
                        callback_data=f"admin_faq_cat_edit:{category_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 Вопросы категории",
                        callback_data=f"admin_faq_cat_items:{category_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Вкл/Выкл",
                        callback_data=f"admin_faq_cat_toggle:{category_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🗑 Удалить",
                        callback_data=f"admin_faq_cat_delete:{category_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="◀️ Назад",
                        callback_data="admin_faq:categories"
                    )
                ]
            ]
        )
    
    @staticmethod
    def tickets_management(unassigned_count: int = 0) -> InlineKeyboardMarkup:
        """Управление тикетами"""
        unassigned_text = f"🆕 Новые ({unassigned_count})" if unassigned_count else "🆕 Новые"
        
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=unassigned_text,
                        callback_data="admin_tickets:unassigned"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 В работе",
                        callback_data="admin_tickets:in_progress"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✅ Решённые",
                        callback_data="admin_tickets:resolved"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📊 Статистика",
                        callback_data="admin_tickets:stats"
                    )
                ]
            ]
        )
    
    @staticmethod
    def admin_ticket_list(tickets: List[Ticket]) -> InlineKeyboardMarkup:
        """Список тикетов для админа"""
        buttons = []
        
        priority_icons = {1: "🟢", 2: "🟡", 3: "🔴"}
        
        for ticket in tickets[:15]:
            icon = priority_icons.get(ticket.priority, "⚪")
            assigned = "👤" if ticket.assigned_to_id else "❗"
            text = f"{icon}{assigned} {ticket.ticket_number}"
            buttons.append([
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"admin_ticket:{ticket.id}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="admin_tickets:main"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def users_management() -> InlineKeyboardMarkup:
        """Управление пользователями"""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔍 Поиск пользователя",
                        callback_data="admin_users:search"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="👑 Администраторы",
                        callback_data="admin_users:admins"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="👨‍💼 Модераторы",
                        callback_data="admin_users:moderators"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📊 Статистика",
                        callback_data="admin_users:stats"
                    )
                ]
            ]
        )
    
    @staticmethod
    def user_actions(user_id: int, current_role: str) -> InlineKeyboardMarkup:
        """Действия с пользователем"""
        buttons = [
            [
                InlineKeyboardButton(
                    text="📋 История обращений",
                    callback_data=f"admin_user_tickets:{user_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Активность",
                    callback_data=f"admin_user_activity:{user_id}"
                )
            ]
        ]
        
        # Изменение роли
        role_buttons = []
        if current_role != "admin":
            role_buttons.append(
                InlineKeyboardButton(
                    text="👑 Сделать админом",
                    callback_data=f"admin_user_role:{user_id}:admin"
                )
            )
        if current_role != "moderator":
            role_buttons.append(
                InlineKeyboardButton(
                    text="👨‍💼 Сделать модератором",
                    callback_data=f"admin_user_role:{user_id}:moderator"
                )
            )
        if current_role not in ["student", "anonymous"]:
            role_buttons.append(
                InlineKeyboardButton(
                    text="👤 Сделать студентом",
                    callback_data=f"admin_user_role:{user_id}:student"
                )
            )
        
        if role_buttons:
            buttons.append(role_buttons)
        
        buttons.append([
            InlineKeyboardButton(
                text="🚫 Заблокировать",
                callback_data=f"admin_user_ban:{user_id}"
            )
        ])
        
        buttons.append([
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="admin_users:main"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def broadcast_targets() -> InlineKeyboardMarkup:
        """Цели рассылки"""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👥 Все пользователи",
                        callback_data="broadcast:all"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🎓 Студенты",
                        callback_data="broadcast:students"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="👨‍🏫 Преподаватели",
                        callback_data="broadcast:teachers"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📚 Конкретный курс",
                        callback_data="broadcast:course"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="👥 Конкретная группа",
                        callback_data="broadcast:group"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Отмена",
                        callback_data="broadcast:cancel"
                    )
                ]
            ]
        )
    
    @staticmethod
    def confirm_broadcast(target: str, count: int) -> InlineKeyboardMarkup:
        """Подтверждение рассылки"""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"✅ Отправить ({count} чел.)",
                        callback_data=f"broadcast_confirm:{target}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Отмена",
                        callback_data="broadcast:cancel"
                    )
                ]
            ]
        )

