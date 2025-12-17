"""
Главные клавиатуры
"""
from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton,
    ReplyKeyboardRemove
)

from app.database import UserRole


class MainKeyboards:
    """Главные клавиатуры бота"""
    
    @staticmethod
    def main_menu(role: UserRole = UserRole.STUDENT) -> ReplyKeyboardMarkup:
        """Главное меню"""
        buttons = [
            [
                KeyboardButton(text="❓ FAQ"),
                KeyboardButton(text="📅 Расписание")
            ],
            [
                KeyboardButton(text="📄 Документы"),
                KeyboardButton(text="🎫 Мои обращения")
            ],
            [
                KeyboardButton(text="✉️ Задать вопрос"),
                KeyboardButton(text="👤 Профиль")
            ],
            [
                KeyboardButton(text="🔗 Ссылки"),
                KeyboardButton(text="ℹ️ Информация")
            ]
        ]
        
        # Добавляем кнопку админа для модераторов и админов
        if role in [UserRole.ADMIN, UserRole.MODERATOR]:
            buttons.append([KeyboardButton(text="⚙️ Админ-панель")])
        
        return ReplyKeyboardMarkup(
            keyboard=buttons,
            resize_keyboard=True,
            input_field_placeholder="Выберите действие или напишите вопрос"
        )
    
    @staticmethod
    def cancel() -> ReplyKeyboardMarkup:
        """Клавиатура отмены"""
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True
        )
    
    @staticmethod
    def confirm_cancel() -> ReplyKeyboardMarkup:
        """Клавиатура подтверждения/отмены"""
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="✅ Подтвердить"),
                    KeyboardButton(text="❌ Отмена")
                ]
            ],
            resize_keyboard=True
        )
    
    @staticmethod
    def yes_no() -> ReplyKeyboardMarkup:
        """Клавиатура Да/Нет"""
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="✅ Да"),
                    KeyboardButton(text="❌ Нет")
                ]
            ],
            resize_keyboard=True
        )
    
    @staticmethod
    def back() -> ReplyKeyboardMarkup:
        """Клавиатура возврата"""
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True
        )
    
    @staticmethod
    def skip_back() -> ReplyKeyboardMarkup:
        """Клавиатура пропуска/возврата"""
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="⏭ Пропустить"),
                    KeyboardButton(text="◀️ Назад")
                ]
            ],
            resize_keyboard=True
        )
    
    @staticmethod
    def remove() -> ReplyKeyboardRemove:
        """Удаление клавиатуры"""
        return ReplyKeyboardRemove()
    
    @staticmethod
    def profile_menu() -> ReplyKeyboardMarkup:
        """Меню профиля"""
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✏️ Редактировать профиль")],
                [KeyboardButton(text="🔔 Настройки уведомлений")],
                [KeyboardButton(text="◀️ В главное меню")]
            ],
            resize_keyboard=True
        )
    
    @staticmethod
    def courses() -> ReplyKeyboardMarkup:
        """Выбор курса"""
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="1 курс"),
                    KeyboardButton(text="2 курс"),
                    KeyboardButton(text="3 курс")
                ],
                [
                    KeyboardButton(text="4 курс"),
                    KeyboardButton(text="5 курс"),
                    KeyboardButton(text="6 курс")
                ],
                [KeyboardButton(text="❌ Отмена")]
            ],
            resize_keyboard=True
        )

