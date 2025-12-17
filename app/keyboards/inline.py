"""
Общие inline клавиатуры
"""
import json
from typing import List, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.database import Document


class InlineKeyboards:
    """Общие inline клавиатуры"""
    
    @staticmethod
    def pagination(
        current_page: int,
        total_pages: int,
        callback_prefix: str
    ) -> InlineKeyboardMarkup:
        """Пагинация"""
        buttons = []
        
        nav_row = []
        if current_page > 1:
            nav_row.append(
                InlineKeyboardButton(
                    text="◀️",
                    callback_data=f"{callback_prefix}:{current_page - 1}"
                )
            )
        
        nav_row.append(
            InlineKeyboardButton(
                text=f"{current_page}/{total_pages}",
                callback_data="noop"
            )
        )
        
        if current_page < total_pages:
            nav_row.append(
                InlineKeyboardButton(
                    text="▶️",
                    callback_data=f"{callback_prefix}:{current_page + 1}"
                )
            )
        
        if nav_row:
            buttons.append(nav_row)
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def feedback_rating() -> InlineKeyboardMarkup:
        """Оценка качества"""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="⭐", callback_data="rate:1"),
                    InlineKeyboardButton(text="⭐⭐", callback_data="rate:2"),
                    InlineKeyboardButton(text="⭐⭐⭐", callback_data="rate:3"),
                    InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data="rate:4"),
                    InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data="rate:5")
                ],
                [
                    InlineKeyboardButton(
                        text="💬 Оставить отзыв",
                        callback_data="rate:feedback"
                    )
                ]
            ]
        )
    
    @staticmethod
    def confirm_action(
        confirm_callback: str,
        cancel_callback: str,
        confirm_text: str = "✅ Да",
        cancel_text: str = "❌ Нет"
    ) -> InlineKeyboardMarkup:
        """Подтверждение действия"""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=confirm_text,
                        callback_data=confirm_callback
                    ),
                    InlineKeyboardButton(
                        text=cancel_text,
                        callback_data=cancel_callback
                    )
                ]
            ]
        )
    
    @staticmethod
    def documents_categories(categories: dict) -> InlineKeyboardMarkup:
        """Категории документов"""
        buttons = []
        
        for slug, data in categories.items():
            if data["count"] > 0:
                buttons.append([
                    InlineKeyboardButton(
                        text=f"{data['name']} ({data['count']})",
                        callback_data=f"docs_cat:{slug}"
                    )
                ])
        
        buttons.append([
            InlineKeyboardButton(
                text="🔍 Поиск документа",
                callback_data="docs_search"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def documents_list(documents: List[Document]) -> InlineKeyboardMarkup:
        """Список документов"""
        buttons = []
        
        for doc in documents:
            icon = "📄"
            if doc.file_type:
                icons = {"pdf": "📕", "docx": "📘", "xlsx": "📗", "doc": "📘"}
                icon = icons.get(doc.file_type.lower(), "📄")
            
            text = f"{icon} {doc.name[:40]}"
            buttons.append([
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"doc_view:{doc.id}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(
                text="◀️ К категориям",
                callback_data="docs_categories"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def document_actions(doc_id: int, has_file: bool = True) -> InlineKeyboardMarkup:
        """Действия с документом"""
        buttons = []
        
        if has_file:
            buttons.append([
                InlineKeyboardButton(
                    text="📥 Скачать",
                    callback_data=f"doc_download:{doc_id}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="docs_categories"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def schedule_navigation(
        group: str,
        current_date: str
    ) -> InlineKeyboardMarkup:
        """Навигация по расписанию"""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="◀️ Пред. день",
                        callback_data=f"schedule_prev:{group}:{current_date}"
                    ),
                    InlineKeyboardButton(
                        text="След. день ▶️",
                        callback_data=f"schedule_next:{group}:{current_date}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📅 Сегодня",
                        callback_data=f"schedule_today:{group}"
                    ),
                    InlineKeyboardButton(
                        text="📆 Неделя",
                        callback_data=f"schedule_week:{group}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📝 Экзамены",
                        callback_data=f"schedule_exams:{group}"
                    )
                ]
            ]
        )
    
    @staticmethod
    def url_buttons(links_json: Optional[str]) -> Optional[InlineKeyboardMarkup]:
        """Кнопки со ссылками из JSON"""
        if not links_json:
            return None
        
        try:
            links = json.loads(links_json)
            if not links:
                return None
            
            buttons = []
            for link in links:
                if "text" in link and "url" in link:
                    buttons.append([
                        InlineKeyboardButton(
                            text=link["text"],
                            url=link["url"]
                        )
                    ])
            
            return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
        except (json.JSONDecodeError, TypeError):
            return None
    
    @staticmethod
    def close() -> InlineKeyboardMarkup:
        """Кнопка закрытия"""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="❌ Закрыть",
                        callback_data="close"
                    )
                ]
            ]
        )

