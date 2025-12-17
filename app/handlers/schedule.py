"""
Хендлеры расписания
"""
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.database import User, async_session
from app.services import ScheduleService, AnalyticsService
from app.keyboards.inline import InlineKeyboards
from app.keyboards.main import MainKeyboards


router = Router(name="schedule")


class ScheduleStates(StatesGroup):
    """Состояния для расписания"""
    entering_group = State()


@router.message(F.text == "📅 Расписание")
@router.message(Command("schedule"))
async def show_schedule_menu(message: Message, user: User, state: FSMContext):
    """Показать меню расписания"""
    # Проверяем, есть ли группа у пользователя
    if not user.group_name:
        await state.set_state(ScheduleStates.entering_group)
        await message.answer(
            "📅 <b>Расписание</b>\n\n"
            "Для просмотра расписания укажите вашу группу.\n"
            "Например: <code>201-361</code> или <code>191-721</code>",
            reply_markup=MainKeyboards.cancel(),
            parse_mode="HTML"
        )
        return
    
    # Показываем расписание на сегодня
    await show_today_schedule(message, user)


async def show_today_schedule(message: Message, user: User):
    """Показать расписание на сегодня"""
    today = datetime.utcnow()
    
    async with async_session() as session:
        service = ScheduleService(session)
        items = await service.get_today_schedule(user.group_name)
        
        # Логируем
        analytics = AnalyticsService(session)
        await analytics.log_request(
            user_id=user.id,
            request_type="schedule",
            category="today"
        )
        await session.commit()
    
    # Форматируем расписание
    text = service.format_day_schedule(items, today)
    text += f"\n\n👥 Группа: {user.group_name}"
    
    await message.answer(
        text,
        reply_markup=InlineKeyboards.schedule_navigation(
            user.group_name,
            today.strftime("%Y-%m-%d")
        ),
        parse_mode="HTML"
    )


@router.message(ScheduleStates.entering_group)
async def process_group_input(message: Message, user: User, state: FSMContext):
    """Обработка ввода группы"""
    import re
    
    group = message.text.strip().upper()
    
    # Валидация
    if not re.match(r'^\d{3}-\d{3}$', group) and not re.match(r'^[А-Яа-яA-Za-z]{2,5}\d{2}-\d{2,3}$', group):
        await message.answer(
            "⚠️ Неверный формат группы.\n"
            "Примеры: 201-361, 191-721, ИБ20-01\n\n"
            "Попробуйте ещё раз:"
        )
        return
    
    # Сохраняем группу в профиль
    from app.services import UserService
    async with async_session() as session:
        service = UserService(session)
        await service.update_profile(user.id, group_name=group)
        await session.commit()
    
    # Обновляем user объект
    user.group_name = group
    
    await state.clear()
    await show_today_schedule(message, user)


# === Навигация по расписанию ===

@router.callback_query(F.data.startswith("schedule_today:"))
async def callback_schedule_today(callback: CallbackQuery, user: User):
    """Расписание на сегодня"""
    group = callback.data.split(":")[1]
    today = datetime.utcnow()
    
    async with async_session() as session:
        service = ScheduleService(session)
        items = await service.get_today_schedule(group)
    
    text = service.format_day_schedule(items, today)
    text += f"\n\n👥 Группа: {group}"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboards.schedule_navigation(
            group,
            today.strftime("%Y-%m-%d")
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("schedule_prev:"))
async def callback_schedule_prev(callback: CallbackQuery):
    """Предыдущий день"""
    parts = callback.data.split(":")
    group = parts[1]
    current_date = datetime.strptime(parts[2], "%Y-%m-%d")
    prev_date = current_date - timedelta(days=1)
    
    async with async_session() as session:
        service = ScheduleService(session)
        items = await service.get_schedule_for_date(group, prev_date)
    
    text = service.format_day_schedule(items, prev_date)
    text += f"\n\n👥 Группа: {group}"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboards.schedule_navigation(
            group,
            prev_date.strftime("%Y-%m-%d")
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("schedule_next:"))
async def callback_schedule_next(callback: CallbackQuery):
    """Следующий день"""
    parts = callback.data.split(":")
    group = parts[1]
    current_date = datetime.strptime(parts[2], "%Y-%m-%d")
    next_date = current_date + timedelta(days=1)
    
    async with async_session() as session:
        service = ScheduleService(session)
        items = await service.get_schedule_for_date(group, next_date)
    
    text = service.format_day_schedule(items, next_date)
    text += f"\n\n👥 Группа: {group}"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboards.schedule_navigation(
            group,
            next_date.strftime("%Y-%m-%d")
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("schedule_week:"))
async def callback_schedule_week(callback: CallbackQuery):
    """Расписание на неделю"""
    group = callback.data.split(":")[1]
    today = datetime.utcnow()
    
    async with async_session() as session:
        service = ScheduleService(session)
        items = await service.get_schedule_for_group(
            group,
            start_date=today,
            end_date=today + timedelta(days=7)
        )
    
    if not items:
        text = f"📅 <b>Расписание на неделю</b>\n👥 Группа: {group}\n\n"
        text += "🎉 На этой неделе занятий нет!"
    else:
        text = f"📅 <b>Расписание на неделю</b>\n👥 Группа: {group}\n\n"
        
        # Группируем по дням
        by_day = {}
        for item in items:
            day = item.start_time.date()
            if day not in by_day:
                by_day[day] = []
            by_day[day].append(item)
        
        for day in sorted(by_day.keys()):
            day_items = by_day[day]
            day_name = day.strftime("%d.%m (%A)")
            text += f"\n<b>📆 {day_name}</b>\n"
            for item in day_items:
                text += f"  {service.format_schedule_item(item)}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboards.schedule_navigation(
            group,
            today.strftime("%Y-%m-%d")
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("schedule_exams:"))
async def callback_schedule_exams(callback: CallbackQuery):
    """Расписание экзаменов"""
    group = callback.data.split(":")[1]
    
    async with async_session() as session:
        service = ScheduleService(session)
        exams = await service.get_upcoming_exams(group_name=group)
    
    if not exams:
        text = f"📝 <b>Экзамены</b>\n👥 Группа: {group}\n\n"
        text += "Предстоящих экзаменов не найдено."
    else:
        text = f"📝 <b>Предстоящие экзамены</b>\n👥 Группа: {group}\n\n"
        
        for exam in exams:
            date_str = exam.start_time.strftime("%d.%m.%Y %H:%M")
            text += f"📅 <b>{date_str}</b>\n"
            text += f"   📚 {exam.title}\n"
            if exam.location:
                text += f"   📍 {exam.location}\n"
            if exam.teacher:
                text += f"   👨‍🏫 {exam.teacher}\n"
            text += "\n"
    
    today = datetime.utcnow()
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboards.schedule_navigation(
            group,
            today.strftime("%Y-%m-%d")
        ),
        parse_mode="HTML"
    )
    await callback.answer()


# === Быстрые команды ===

@router.message(Command("today"))
async def cmd_today(message: Message, user: User):
    """Расписание на сегодня"""
    if not user.group_name:
        await message.answer(
            "⚠️ Укажите группу в профиле для просмотра расписания.\n"
            "Используйте /profile"
        )
        return
    
    await show_today_schedule(message, user)


@router.message(Command("tomorrow"))
async def cmd_tomorrow(message: Message, user: User):
    """Расписание на завтра"""
    if not user.group_name:
        await message.answer(
            "⚠️ Укажите группу в профиле для просмотра расписания.\n"
            "Используйте /profile"
        )
        return
    
    tomorrow = datetime.utcnow() + timedelta(days=1)
    
    async with async_session() as session:
        service = ScheduleService(session)
        items = await service.get_schedule_for_date(user.group_name, tomorrow)
    
    text = service.format_day_schedule(items, tomorrow)
    text += f"\n\n👥 Группа: {user.group_name}"
    
    await message.answer(
        text,
        reply_markup=InlineKeyboards.schedule_navigation(
            user.group_name,
            tomorrow.strftime("%Y-%m-%d")
        ),
        parse_mode="HTML"
    )


@router.message(Command("exams"))
async def cmd_exams(message: Message, user: User):
    """Экзамены"""
    if not user.group_name:
        await message.answer(
            "⚠️ Укажите группу в профиле для просмотра экзаменов.\n"
            "Используйте /profile"
        )
        return
    
    async with async_session() as session:
        service = ScheduleService(session)
        exams = await service.get_upcoming_exams(group_name=user.group_name)
    
    if not exams:
        await message.answer(
            f"📝 <b>Экзамены</b>\n👥 Группа: {user.group_name}\n\n"
            "Предстоящих экзаменов не найдено.",
            parse_mode="HTML"
        )
        return
    
    text = f"📝 <b>Предстоящие экзамены</b>\n👥 Группа: {user.group_name}\n\n"
    
    for exam in exams:
        date_str = exam.start_time.strftime("%d.%m.%Y %H:%M")
        text += f"📅 <b>{date_str}</b>\n"
        text += f"   📚 {exam.title}\n"
        if exam.location:
            text += f"   📍 {exam.location}\n"
        if exam.teacher:
            text += f"   👨‍🏫 {exam.teacher}\n"
        text += "\n"
    
    await message.answer(text, parse_mode="HTML")

