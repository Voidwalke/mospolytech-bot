"""
Хендлеры тикетов (обращений)
"""
from typing import Union

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.database import User, TicketStatus, async_session
from app.services import TicketService, NotificationService
from app.keyboards.tickets import TicketKeyboards
from app.keyboards.main import MainKeyboards


router = Router(name="tickets")


class TicketStates(StatesGroup):
    """Состояния создания тикета"""
    selecting_category = State()
    selecting_anonymous = State()
    entering_subject = State()
    entering_description = State()
    confirming = State()
    replying = State()


# === Список тикетов ===

@router.message(F.text == "🎫 Мои обращения")
@router.message(Command("tickets"))
async def show_user_tickets(message: Message, user: User):
    """Показать тикеты пользователя"""
    async with async_session() as session:
        service = TicketService(session)
        tickets = await service.get_user_tickets(user.id, limit=15)
    
    if not tickets:
        await message.answer(
            "📋 <b>Ваши обращения</b>\n\n"
            "У вас пока нет обращений.\n"
            "Нажмите кнопку ниже, чтобы создать новое.",
            reply_markup=TicketKeyboards.user_tickets([]),
            parse_mode="HTML"
        )
        return
    
    # Статистика
    open_count = sum(1 for t in tickets if t.status in [TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
    resolved_count = sum(1 for t in tickets if t.status == TicketStatus.RESOLVED)
    
    await message.answer(
        f"📋 <b>Ваши обращения</b>\n\n"
        f"🔓 Открытых: {open_count}\n"
        f"✅ Решённых: {resolved_count}\n"
        f"📊 Всего: {len(tickets)}\n\n"
        f"Выберите обращение для просмотра:",
        reply_markup=TicketKeyboards.user_tickets(tickets),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "tickets_list")
async def callback_tickets_list(callback: CallbackQuery, user: User):
    """Callback для списка тикетов"""
    async with async_session() as session:
        service = TicketService(session)
        tickets = await service.get_user_tickets(user.id, limit=15)
    
    await callback.message.edit_text(
        "📋 <b>Ваши обращения</b>\n\n"
        "Выберите обращение для просмотра:",
        reply_markup=TicketKeyboards.user_tickets(tickets),
        parse_mode="HTML"
    )
    await callback.answer()


# === Просмотр тикета ===

@router.callback_query(F.data.startswith("ticket_view:"))
async def callback_view_ticket(callback: CallbackQuery, user: User):
    """Просмотр тикета"""
    ticket_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        service = TicketService(session)
        ticket = await service.get_ticket_by_id(ticket_id)
        
        if not ticket:
            await callback.answer("Обращение не найдено", show_alert=True)
            return
        
        # Проверяем доступ
        if ticket.user_id != user.id and user.role.value not in ["admin", "moderator"]:
            await callback.answer("Нет доступа к этому обращению", show_alert=True)
            return
        
        messages = await service.get_messages(ticket_id)
    
    # Статусы
    status_names = {
        TicketStatus.OPEN: "🆕 Открыт",
        TicketStatus.IN_PROGRESS: "🔄 В работе",
        TicketStatus.WAITING: "⏳ Ожидает ответа",
        TicketStatus.RESOLVED: "✅ Решён",
        TicketStatus.CLOSED: "🔒 Закрыт"
    }
    
    priority_names = {1: "🟢 Низкий", 2: "🟡 Средний", 3: "🔴 Высокий"}
    
    text = f"🎫 <b>Обращение {ticket.ticket_number}</b>\n\n"
    text += f"📌 <b>Тема:</b> {ticket.subject}\n"
    text += f"📊 <b>Статус:</b> {status_names.get(ticket.status, ticket.status.value)}\n"
    text += f"⚡ <b>Приоритет:</b> {priority_names.get(ticket.priority, 'Обычный')}\n"
    
    if ticket.assigned_to:
        text += f"👤 <b>Исполнитель:</b> {ticket.assigned_to.display_name}\n"
    
    text += f"📅 <b>Создан:</b> {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    
    if ticket.resolved_at:
        text += f"✅ <b>Решён:</b> {ticket.resolved_at.strftime('%d.%m.%Y %H:%M')}\n"
    
    text += f"\n{'─' * 20}\n\n"
    
    # Сообщения
    for msg in messages[-5:]:  # Последние 5 сообщений
        sender = "👤 Вы" if msg.user_id == user.id else "👨‍💼 Поддержка"
        if msg.is_from_staff:
            sender = "👨‍💼 Поддержка"
        text += f"<b>{sender}</b> ({msg.created_at.strftime('%d.%m %H:%M')}):\n"
        text += f"{msg.message[:300]}{'...' if len(msg.message) > 300 else ''}\n\n"
    
    is_staff = user.role.value in ["admin", "moderator"]
    
    await callback.message.edit_text(
        text,
        reply_markup=TicketKeyboards.ticket_actions(ticket, is_staff),
        parse_mode="HTML"
    )
    await callback.answer()


# === Создание тикета ===

@router.message(F.text == "✉️ Задать вопрос")
@router.callback_query(F.data == "create_ticket")
async def start_create_ticket(event: Union[Message, CallbackQuery], user: User, state: FSMContext):
    """Начало создания тикета"""
    await state.set_state(TicketStates.selecting_category)
    
    text = (
        "📝 <b>Новое обращение</b>\n\n"
        "Выберите категорию вашего вопроса:"
    )
    
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(
            text,
            reply_markup=TicketKeyboards.category_select(),
            parse_mode="HTML"
        )
        await event.answer()
    else:
        await event.answer(
            text,
            reply_markup=TicketKeyboards.category_select(),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("ticket_cat:"), TicketStates.selecting_category)
async def select_ticket_category(callback: CallbackQuery, state: FSMContext):
    """Выбор категории тикета"""
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
    await state.set_state(TicketStates.selecting_anonymous)
    
    # Находим название категории
    cat_names = dict(TicketKeyboards.CATEGORIES)
    cat_name = cat_names.get(category, category)
    
    await callback.message.edit_text(
        f"📁 Категория: {cat_name}\n\n"
        "Выберите тип обращения:",
        reply_markup=TicketKeyboards.anonymous_option(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ticket_anon:"), TicketStates.selecting_anonymous)
async def select_anonymous(callback: CallbackQuery, state: FSMContext):
    """Выбор анонимного режима"""
    is_anonymous = callback.data.split(":")[1] == "1"
    await state.update_data(is_anonymous=is_anonymous)
    await state.set_state(TicketStates.entering_subject)
    
    await callback.message.edit_text(
        "📝 <b>Тема обращения</b>\n\n"
        "Кратко опишите суть вопроса (до 100 символов):\n\n"
        "<i>Например: Не могу получить справку об обучении</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(TicketStates.entering_subject)
async def enter_subject(message: Message, state: FSMContext):
    """Ввод темы тикета"""
    subject = message.text.strip()
    
    if len(subject) < 5:
        await message.answer("⚠️ Тема слишком короткая. Введите минимум 5 символов.")
        return
    
    if len(subject) > 200:
        await message.answer("⚠️ Тема слишком длинная. Максимум 200 символов.")
        return
    
    await state.update_data(subject=subject)
    await state.set_state(TicketStates.entering_description)
    
    await message.answer(
        "📄 <b>Описание проблемы</b>\n\n"
        "Подробно опишите вашу ситуацию.\n"
        "Укажите все важные детали: ФИО, группу, номер заявки и т.д.\n\n"
        "<i>Чем подробнее вы опишете проблему, тем быстрее мы сможем помочь.</i>",
        reply_markup=MainKeyboards.cancel(),
        parse_mode="HTML"
    )


@router.message(TicketStates.entering_description)
async def enter_description(message: Message, user: User, state: FSMContext):
    """Ввод описания тикета"""
    description = message.text.strip()
    
    if len(description) < 10:
        await message.answer("⚠️ Описание слишком короткое. Введите минимум 10 символов.")
        return
    
    await state.update_data(description=description)
    
    # Получаем все данные
    data = await state.get_data()
    
    # Показываем превью
    cat_names = dict(TicketKeyboards.CATEGORIES)
    
    text = "📋 <b>Проверьте ваше обращение:</b>\n\n"
    text += f"📁 <b>Категория:</b> {cat_names.get(data['category'], data['category'])}\n"
    text += f"{'🎭' if data['is_anonymous'] else '👤'} <b>Тип:</b> {'Анонимное' if data['is_anonymous'] else 'Обычное'}\n"
    text += f"📌 <b>Тема:</b> {data['subject']}\n\n"
    text += f"📄 <b>Описание:</b>\n{description[:500]}{'...' if len(description) > 500 else ''}\n\n"
    text += "Всё верно?"
    
    await state.set_state(TicketStates.confirming)
    
    await message.answer(
        text,
        reply_markup=TicketKeyboards.confirm_send(),
        parse_mode="HTML"
    )


@router.message(F.text == "✅ Отправить", TicketStates.confirming)
async def confirm_ticket(message: Message, user: User, state: FSMContext, bot: Bot):
    """Подтверждение и создание тикета"""
    data = await state.get_data()
    
    async with async_session() as session:
        service = TicketService(session)
        
        ticket = await service.create_ticket(
            user_id=user.id,
            subject=data['subject'],
            description=data['description'],
            category=data['category'],
            is_anonymous=data['is_anonymous']
        )
        
        await session.commit()
        
        # Уведомляем модераторов
        notification_service = NotificationService(session, bot)
        await notification_service.notify_new_ticket(ticket.ticket_number, ticket.subject)
        await session.commit()
    
    await state.clear()
    
    await message.answer(
        f"✅ <b>Обращение создано!</b>\n\n"
        f"📋 Номер: <code>{ticket.ticket_number}</code>\n\n"
        f"Мы постараемся ответить как можно скорее.\n"
        f"Вы получите уведомление, когда появится ответ.\n\n"
        f"Отслеживать статус: /tickets",
        reply_markup=MainKeyboards.main_menu(user.role),
        parse_mode="HTML"
    )


@router.message(F.text == "✏️ Редактировать", TicketStates.confirming)
async def edit_ticket(message: Message, state: FSMContext):
    """Редактирование тикета"""
    await state.set_state(TicketStates.entering_description)
    await message.answer(
        "📄 Введите новое описание:",
        reply_markup=MainKeyboards.cancel()
    )


@router.callback_query(F.data == "ticket_cancel")
async def cancel_ticket_creation(callback: CallbackQuery, user: User, state: FSMContext):
    """Отмена создания тикета"""
    await state.clear()
    await callback.message.edit_text("❌ Создание обращения отменено")
    await callback.answer()


# === Ответ на тикет ===

@router.callback_query(F.data.startswith("ticket_reply:"))
async def start_ticket_reply(callback: CallbackQuery, state: FSMContext):
    """Начало ответа на тикет"""
    ticket_id = int(callback.data.split(":")[1])
    await state.update_data(reply_ticket_id=ticket_id)
    await state.set_state(TicketStates.replying)
    
    await callback.message.edit_text(
        "💬 <b>Добавить сообщение</b>\n\n"
        "Введите ваше сообщение:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(TicketStates.replying)
async def process_ticket_reply(message: Message, user: User, state: FSMContext):
    """Обработка ответа на тикет"""
    data = await state.get_data()
    ticket_id = data.get("reply_ticket_id")
    
    if not ticket_id:
        await state.clear()
        return
    
    reply_text = message.text.strip()
    
    if len(reply_text) < 2:
        await message.answer("⚠️ Сообщение слишком короткое")
        return
    
    async with async_session() as session:
        service = TicketService(session)
        
        ticket = await service.get_ticket_by_id(ticket_id)
        if not ticket:
            await message.answer("❌ Обращение не найдено")
            await state.clear()
            return
        
        await service.add_message(
            ticket_id=ticket_id,
            user_id=user.id,
            message=reply_text,
            is_from_staff=user.role.value in ["admin", "moderator"]
        )
        await session.commit()
    
    await state.clear()
    
    await message.answer(
        "✅ Сообщение добавлено!\n\n"
        "Используйте /tickets для просмотра обращений.",
        reply_markup=MainKeyboards.main_menu(user.role)
    )


# === Закрытие/переоткрытие тикета ===

@router.callback_query(F.data.startswith("ticket_close:"))
async def close_ticket(callback: CallbackQuery, user: User):
    """Закрытие тикета"""
    ticket_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        service = TicketService(session)
        await service.update_status(ticket_id, TicketStatus.CLOSED, user.id)
        await session.commit()
    
    await callback.answer("✅ Обращение закрыто", show_alert=True)
    await callback.message.edit_text(
        "🔒 <b>Обращение закрыто</b>\n\n"
        "Спасибо за использование нашего сервиса!\n"
        "Если у вас возникнут новые вопросы, создайте новое обращение.",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("ticket_reopen:"))
async def reopen_ticket(callback: CallbackQuery, user: User):
    """Переоткрытие тикета"""
    ticket_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        service = TicketService(session)
        await service.update_status(ticket_id, TicketStatus.OPEN, user.id, "Переоткрыто пользователем")
        await session.commit()
    
    await callback.answer("🔓 Обращение переоткрыто", show_alert=True)


# === Эскалация из FAQ ===

@router.callback_query(F.data.startswith("escalate:"))
async def escalate_from_faq(callback: CallbackQuery, state: FSMContext):
    """Эскалация вопроса из FAQ"""
    faq_item_id = callback.data.split(":")[1]
    await state.update_data(escalated_from_faq=faq_item_id)
    await state.set_state(TicketStates.selecting_category)
    
    await callback.message.edit_text(
        "📝 <b>Создание обращения</b>\n\n"
        "Ответ в FAQ не помог? Давайте создадим обращение в деканат.\n\n"
        "Выберите категорию:",
        reply_markup=TicketKeyboards.category_select(),
        parse_mode="HTML"
    )
    await callback.answer()

