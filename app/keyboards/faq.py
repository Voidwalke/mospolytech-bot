"""
Клавиатуры FAQ
"""
from typing import List

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)

from app.database import FAQCategory, FAQItem


class FAQKeyboards:
    """Клавиатуры для FAQ"""
    
    @staticmethod
    def categories(categories: List[FAQCategory]) -> InlineKeyboardMarkup:
        """Клавиатура категорий FAQ"""
        buttons = []
        
        for cat in categories:
            icon = cat.icon or "📁"
            buttons.append([
                InlineKeyboardButton(
                    text=f"{icon} {cat.name}",
                    callback_data=f"faq_cat:{cat.slug}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(
                text="🔍 Поиск по FAQ",
                callback_data="faq_search"
            )
        ])
        
        buttons.append([
            InlineKeyboardButton(
                text="⭐ Избранное",
                callback_data="faq_favorites"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def items(items: List[FAQItem], category_slug: str) -> InlineKeyboardMarkup:
        """Клавиатура вопросов в категории"""
        buttons = []
        
        for item in items:
            # Обрезаем длинные вопросы
            text = item.question[:50] + "..." if len(item.question) > 50 else item.question
            if item.is_pinned:
                text = "📌 " + text
            
            buttons.append([
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"faq_item:{item.id}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(
                text="◀️ К категориям",
                callback_data="faq_categories"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def item_actions(item_id: int, category_slug: str, is_favorite: bool = False) -> InlineKeyboardMarkup:
        """Действия для конкретного ответа FAQ"""
        fav_text = "⭐ В избранном" if is_favorite else "☆ В избранное"
        fav_action = "unfav" if is_favorite else "fav"
        
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👍 Полезно",
                        callback_data=f"faq_rate:{item_id}:1"
                    ),
                    InlineKeyboardButton(
                        text="👎 Не помогло",
                        callback_data=f"faq_rate:{item_id}:0"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=fav_text,
                        callback_data=f"faq_{fav_action}:{item_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✉️ Задать вопрос оператору",
                        callback_data=f"escalate:{item_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"◀️ Назад к списку",
                        callback_data=f"faq_cat:{category_slug}"
                    )
                ]
            ]
        )
    
    @staticmethod
    def favorites(items: list) -> InlineKeyboardMarkup:
        """Клавиатура избранных FAQ"""
        buttons = []
        
        for item in items:
            text = "⭐ " + (item.question[:45] + "..." if len(item.question) > 45 else item.question)
            buttons.append([
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"faq_item:{item.id}"
                )
            ])
        
        if not items:
            buttons.append([
                InlineKeyboardButton(
                    text="📭 Избранное пусто",
                    callback_data="faq_categories"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(
                text="◀️ К категориям",
                callback_data="faq_categories"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def search_results(items: List[tuple]) -> InlineKeyboardMarkup:
        """Результаты поиска"""
        buttons = []
        
        for item, score in items:
            text = item.question[:45] + "..." if len(item.question) > 45 else item.question
            # Добавляем индикатор релевантности
            if score >= 80:
                text = "🎯 " + text
            elif score >= 60:
                text = "✓ " + text
            
            buttons.append([
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"faq_item:{item.id}"
                )
            ])
        
        if not items:
            buttons.append([
                InlineKeyboardButton(
                    text="❌ Ничего не найдено",
                    callback_data="faq_not_found"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(
                text="✉️ Задать вопрос оператору",
                callback_data="create_ticket"
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text="◀️ К категориям",
                callback_data="faq_categories"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def popular() -> ReplyKeyboardMarkup:
        """Популярные вопросы (reply keyboard)"""
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📅 Где посмотреть расписание?")],
                [KeyboardButton(text="💰 Как получить стипендию?")],
                [KeyboardButton(text="📝 Как написать заявление?")],
                [KeyboardButton(text="◀️ В главное меню")]
            ],
            resize_keyboard=True
        )

