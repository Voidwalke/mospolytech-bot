"""
Хендлеры профиля пользователя
"""
import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.database import User, async_session
from app.services import UserService
from app.keyboards.main import MainKeyboards


router = Router(name="profile")


class ProfileStates(StatesGroup):
    """Состояния редактирования профиля"""
    editing_name = State()
    editing_group = State()
    editing_course = State()
    editing_student_id = State()


# === Просмотр профиля ===

@router.message(F.text == "👤 Профиль")
@router.message(Command("profile"))
async def show_profile(message: Message, user: User):
    """Показать профиль пользователя"""
    role_names = {
        "student": "🎓 Студент",
        "teacher": "👨‍🏫 Преподаватель",
        "moderator": "👨‍💼 Модератор",
        "admin": "👑 Администратор",
        "anonymous": "🎭 Анонимный"
    }
    
    text = "👤 <b>Ваш профиль</b>\n\n"
    
    text += f"<b>Telegram:</b>\n"
    text += f"├ ID: <code>{user.telegram_id}</code>\n"
    if user.username:
        text += f"├ Username: @{user.username}\n"
    text += f"└ Имя: {user.first_name or '—'}"
    if user.last_name:
        text += f" {user.last_name}"
    text += "\n\n"
    
    text += f"<b>Данные в системе:</b>\n"
    text += f"├ ФИО: {user.full_name or '📝 Не указано'}\n"
    text += f"├ Группа: {user.group_name or '📝 Не указана'}\n"
    text += f"├ Курс: {user.course or '📝 Не указан'}\n"
    text += f"├ № студ. билета: {user.student_id or '📝 Не указан'}\n"
    text += f"└ Факультет: {user.faculty or '📝 Не указан'}\n\n"
    
    text += f"<b>Статус:</b>\n"
    text += f"├ Роль: {role_names.get(user.role.value, user.role.value)}\n"
    text += f"├ Верификация: {'✅ Подтверждён' if user.is_verified else '❌ Не подтверждён'}\n"
    text += f"└ Уведомления: {'🔔 Включены' if user.notifications_enabled else '🔕 Выключены'}\n\n"
    
    text += f"📅 <b>Регистрация:</b> {user.created_at.strftime('%d.%m.%Y')}"
    
    await message.answer(
        text,
        reply_markup=MainKeyboards.profile_menu(),
        parse_mode="HTML"
    )


# === Редактирование профиля ===

@router.message(F.text == "✏️ Редактировать профиль")
async def edit_profile_menu(message: Message):
    """Меню редактирования профиля"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 ФИО", callback_data="edit_profile:name")],
            [InlineKeyboardButton(text="👥 Группа", callback_data="edit_profile:group")],
            [InlineKeyboardButton(text="📚 Курс", callback_data="edit_profile:course")],
            [InlineKeyboardButton(text="🎫 № студ. билета", callback_data="edit_profile:student_id")],
        ]
    )
    
    await message.answer(
        "✏️ <b>Редактирование профиля</b>\n\n"
        "Выберите, что хотите изменить:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("edit_profile:"))
async def start_edit_field(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования поля"""
    field = callback.data.split(":")[1]
    
    prompts = {
        "name": ("📝 Введите ваше полное ФИО:", ProfileStates.editing_name),
        "group": ("👥 Введите номер вашей группы\n(например: 201-361):", ProfileStates.editing_group),
        "course": ("📚 Выберите ваш курс:", ProfileStates.editing_course),
        "student_id": ("🎫 Введите номер студенческого билета:", ProfileStates.editing_student_id)
    }
    
    prompt, state_to_set = prompts.get(field, (None, None))
    
    if not prompt:
        await callback.answer("Неизвестное поле", show_alert=True)
        return
    
    await state.set_state(state_to_set)
    
    if field == "course":
        await callback.message.edit_text(prompt, parse_mode="HTML")
        await callback.message.answer(
            "Выберите курс:",
            reply_markup=MainKeyboards.courses()
        )
    else:
        await callback.message.edit_text(prompt, parse_mode="HTML")
        await callback.message.answer(
            "Введите данные или нажмите Отмена:",
            reply_markup=MainKeyboards.cancel()
        )
    
    await callback.answer()


@router.message(ProfileStates.editing_name)
async def process_edit_name(message: Message, user: User, state: FSMContext):
    """Обработка изменения ФИО"""
    name = message.text.strip()
    
    # Валидация ФИО
    if len(name) < 5:
        await message.answer("⚠️ ФИО слишком короткое. Введите полное ФИО.")
        return
    
    if len(name) > 200:
        await message.answer("⚠️ ФИО слишком длинное.")
        return
    
    # Проверяем, что это похоже на ФИО (только буквы, пробелы, дефисы)
    if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s\-\.]+$', name):
        await message.answer("⚠️ ФИО должно содержать только буквы, пробелы и дефисы.")
        return
    
    async with async_session() as session:
        service = UserService(session)
        await service.update_profile(user.id, full_name=name)
        await session.commit()
    
    await state.clear()
    await message.answer(
        f"✅ ФИО обновлено: <b>{name}</b>",
        reply_markup=MainKeyboards.profile_menu(),
        parse_mode="HTML"
    )


@router.message(ProfileStates.editing_group)
async def process_edit_group(message: Message, user: User, state: FSMContext):
    """Обработка изменения группы"""
    group = message.text.strip().upper()
    
    # Валидация формата группы (например: 201-361, 191-721)
    if not re.match(r'^\d{3}-\d{3}$', group) and not re.match(r'^[А-Яа-я]{2,5}\d{2}-\d{2,3}$', group):
        await message.answer(
            "⚠️ Неверный формат группы.\n"
            "Примеры: 201-361, 191-721, ИБ20-01"
        )
        return
    
    async with async_session() as session:
        service = UserService(session)
        await service.update_profile(user.id, group_name=group)
        await session.commit()
    
    await state.clear()
    await message.answer(
        f"✅ Группа обновлена: <b>{group}</b>",
        reply_markup=MainKeyboards.profile_menu(),
        parse_mode="HTML"
    )


@router.message(ProfileStates.editing_course)
async def process_edit_course(message: Message, user: User, state: FSMContext):
    """Обработка изменения курса"""
    text = message.text.strip()
    
    # Извлекаем номер курса
    match = re.search(r'(\d)', text)
    if not match:
        await message.answer("⚠️ Выберите курс из предложенных кнопок или введите число от 1 до 6")
        return
    
    course = int(match.group(1))
    
    if course < 1 or course > 6:
        await message.answer("⚠️ Курс должен быть от 1 до 6")
        return
    
    async with async_session() as session:
        service = UserService(session)
        await service.update_profile(user.id, course=course)
        await session.commit()
    
    await state.clear()
    await message.answer(
        f"✅ Курс обновлён: <b>{course}</b>",
        reply_markup=MainKeyboards.profile_menu(),
        parse_mode="HTML"
    )


@router.message(ProfileStates.editing_student_id)
async def process_edit_student_id(message: Message, user: User, state: FSMContext):
    """Обработка изменения номера студенческого"""
    student_id = message.text.strip()
    
    # Базовая валидация
    if len(student_id) < 4 or len(student_id) > 20:
        await message.answer("⚠️ Неверный формат номера студенческого билета")
        return
    
    async with async_session() as session:
        service = UserService(session)
        await service.update_profile(user.id, student_id=student_id)
        await session.commit()
    
    await state.clear()
    await message.answer(
        f"✅ Номер студенческого обновлён: <b>{student_id}</b>",
        reply_markup=MainKeyboards.profile_menu(),
        parse_mode="HTML"
    )


# === Настройки уведомлений ===

@router.message(F.text == "🔔 Настройки уведомлений")
async def notifications_settings(message: Message, user: User):
    """Настройки уведомлений"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    status = "🔔 Включены" if user.notifications_enabled else "🔕 Выключены"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{'🔕 Выключить' if user.notifications_enabled else '🔔 Включить'}",
                    callback_data="toggle_notifications"
                )
            ]
        ]
    )
    
    await message.answer(
        f"🔔 <b>Настройки уведомлений</b>\n\n"
        f"Текущий статус: {status}\n\n"
        f"Уведомления включают:\n"
        f"• Ответы на ваши обращения\n"
        f"• Изменения в расписании\n"
        f"• Важные объявления",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications(callback: CallbackQuery, user: User):
    """Переключение уведомлений"""
    async with async_session() as session:
        service = UserService(session)
        new_state = await service.toggle_notifications(user.id)
        await session.commit()
    
    status = "🔔 включены" if new_state else "🔕 выключены"
    await callback.answer(f"Уведомления {status}", show_alert=True)
    
    # Обновляем сообщение
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{'🔕 Выключить' if new_state else '🔔 Включить'}",
                    callback_data="toggle_notifications"
                )
            ]
        ]
    )
    
    await callback.message.edit_reply_markup(reply_markup=keyboard)

