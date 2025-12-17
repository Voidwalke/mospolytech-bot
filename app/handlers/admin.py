"""
Хендлеры админ-панели
"""
from datetime import datetime, timedelta
from io import BytesIO

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.database import User, UserRole, TicketStatus, async_session
from app.services import (
    FAQService, TicketService, UserService, 
    AnalyticsService, NotificationService, DocumentService
)
from app.keyboards.admin import AdminKeyboards
from app.keyboards.main import MainKeyboards
from app.middlewares.auth import role_required


router = Router(name="admin")


class AdminStates(StatesGroup):
    """Состояния админ-панели"""
    # FAQ
    adding_category_name = State()
    adding_category_slug = State()
    adding_category_icon = State()
    adding_item_question = State()
    adding_item_answer = State()
    adding_item_keywords = State()
    selecting_item_category = State()
    
    # Пользователи
    searching_user = State()
    
    # Рассылка
    broadcast_text = State()
    broadcast_confirm = State()
    
    # Документы
    adding_document_name = State()
    adding_document_category = State()
    adding_document_file = State()
    
    # Тикеты
    ticket_reply = State()


# === Проверка доступа ===

def admin_filter(user: User) -> bool:
    """Фильтр для админов и модераторов (доступ к админ-панели)"""
    return user.role in [UserRole.ADMIN, UserRole.MODERATOR]


def admin_only_filter(user: User) -> bool:
    """Фильтр ТОЛЬКО для админов (опасные операции)"""
    return user.role == UserRole.ADMIN


# === Главное меню админки ===

@router.message(F.text == "⚙️ Админ-панель")
@router.message(Command("admin"))
async def admin_panel(message: Message, user: User):
    """Админ-панель"""
    if not admin_filter(user):
        await message.answer("⛔ У вас нет доступа к админ-панели")
        return
    
    async with async_session() as session:
        ticket_service = TicketService(session)
        analytics_service = AnalyticsService(session)
        
        unassigned = await ticket_service.get_unassigned_count()
        dashboard = await analytics_service.get_dashboard_summary()
    
    text = "⚙️ <b>Админ-панель</b>\n\n"
    text += f"📊 <b>Сводка за сегодня:</b>\n"
    text += f"├ Запросов: {dashboard['requests_today']}"
    
    if dashboard['requests_change_percent'] != 0:
        change = dashboard['requests_change_percent']
        emoji = "📈" if change > 0 else "📉"
        text += f" ({emoji} {change:+.1f}%)\n"
    else:
        text += "\n"
    
    text += f"├ Активных за неделю: {dashboard['active_users_week']}\n"
    text += f"└ Новых за неделю: {dashboard['new_users_week']}\n\n"
    
    if unassigned > 0:
        text += f"⚠️ <b>Новых обращений: {unassigned}</b>"
    
    await message.answer(
        text,
        reply_markup=AdminKeyboards.main_menu(),
        parse_mode="HTML"
    )


# === Статистика ===

@router.message(F.text == "📊 Статистика")
@router.message(Command("stats"))
async def show_stats_menu(message: Message, user: User):
    """Меню статистики"""
    if not admin_filter(user):
        return
    
    await message.answer(
        "📊 <b>Статистика</b>\n\n"
        "Выберите период:",
        reply_markup=AdminKeyboards.stats_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("stats:"))
async def callback_stats(callback: CallbackQuery, user: User, bot: Bot):
    """Показ статистики"""
    if not admin_filter(user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    period = callback.data.split(":")[1]
    
    if period == "export":
        # Экспорт в Excel
        await callback.answer("Генерируем отчёт...")
        
        async with async_session() as session:
            analytics = AnalyticsService(session)
            excel_data = await analytics.export_stats_excel(days=30)
        
        file = BufferedInputFile(
            excel_data,
            filename=f"stats_{datetime.now().strftime('%Y%m%d')}.xlsx"
        )
        
        await bot.send_document(
            chat_id=callback.message.chat.id,
            document=file,
            caption="📊 Статистика за последние 30 дней"
        )
        return
    
    # Определяем период
    days_map = {
        "today": 1,
        "week": 7,
        "month": 30,
        "all": 365
    }
    days = days_map.get(period, 7)
    
    async with async_session() as session:
        analytics = AnalyticsService(session)
        user_service = UserService(session)
        ticket_service = TicketService(session)
        faq_service = FAQService(session)
        
        stats = await analytics.get_requests_stats(days)
        user_stats = await user_service.get_stats()
        ticket_stats = await ticket_service.get_stats()
        faq_stats = await faq_service.get_stats()
    
    period_names = {
        "today": "сегодня",
        "week": "неделю",
        "month": "месяц",
        "all": "всё время"
    }
    
    text = f"📊 <b>Статистика за {period_names[period]}</b>\n\n"
    
    text += "<b>📨 Запросы:</b>\n"
    text += f"├ Всего: {stats['total']}\n"
    text += f"├ Время ответа: {stats['avg_response_ms']:.0f} мс\n"
    
    if stats['by_type']:
        text += "└ По типам:\n"
        for t, count in list(stats['by_type'].items())[:5]:
            text += f"   • {t}: {count}\n"
    
    text += f"\n<b>👥 Пользователи:</b>\n"
    text += f"├ Всего: {user_stats['total']}\n"
    text += f"├ Активных: {user_stats['active']}\n"
    text += f"├ Новых сегодня: {user_stats['new_today']}\n"
    text += f"└ Верифицированных: {user_stats['verified']}\n"
    
    text += f"\n<b>🎫 Тикеты:</b>\n"
    text += f"├ Всего: {ticket_stats['total']}\n"
    text += f"├ Открытых: {ticket_stats['by_status'].get('open', 0)}\n"
    text += f"├ В работе: {ticket_stats['by_status'].get('in_progress', 0)}\n"
    text += f"└ Ср. время решения: {ticket_stats['avg_resolution_days']:.1f} дн.\n"
    
    text += f"\n<b>❓ FAQ:</b>\n"
    text += f"├ Категорий: {faq_stats['categories_count']}\n"
    text += f"├ Вопросов: {faq_stats['items_count']}\n"
    text += f"├ Просмотров: {faq_stats['total_views']}\n"
    text += f"└ Полезных: {faq_stats['helpful_count']} / {faq_stats['not_helpful_count']} неполезных"
    
    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.stats_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


# === Управление тикетами ===

@router.message(F.text == "🎫 Тикеты")
async def admin_tickets(message: Message, user: User):
    """Управление тикетами"""
    if not admin_filter(user):
        return
    
    async with async_session() as session:
        service = TicketService(session)
        unassigned = await service.get_unassigned_count()
    
    await message.answer(
        "🎫 <b>Управление обращениями</b>\n\n"
        f"Новых: {unassigned}",
        reply_markup=AdminKeyboards.tickets_management(unassigned),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_tickets:main")
async def callback_admin_tickets_main(callback: CallbackQuery, user: User):
    """Возврат в меню тикетов"""
    if not admin_filter(user):
        return
    
    async with async_session() as session:
        service = TicketService(session)
        unassigned = await service.get_unassigned_count()
    
    await callback.message.edit_text(
        "🎫 <b>Управление обращениями</b>",
        reply_markup=AdminKeyboards.tickets_management(unassigned),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_tickets:"))
async def callback_admin_tickets_filter(callback: CallbackQuery, user: User):
    """Фильтр тикетов"""
    if not admin_filter(user):
        return
    
    filter_type = callback.data.split(":")[1]
    
    async with async_session() as session:
        service = TicketService(session)
        
        if filter_type == "unassigned":
            tickets = await service.get_open_tickets()
            tickets = [t for t in tickets if t.assigned_to_id is None]
            title = "🆕 Новые (неназначенные)"
        elif filter_type == "in_progress":
            from sqlalchemy import select
            from app.database import Ticket
            result = await session.execute(
                select(Ticket)
                .where(Ticket.status == TicketStatus.IN_PROGRESS)
                .order_by(Ticket.updated_at.desc())
                .limit(20)
            )
            tickets = result.scalars().all()
            title = "🔄 В работе"
        elif filter_type == "resolved":
            from sqlalchemy import select
            from app.database import Ticket
            result = await session.execute(
                select(Ticket)
                .where(Ticket.status == TicketStatus.RESOLVED)
                .order_by(Ticket.resolved_at.desc())
                .limit(20)
            )
            tickets = result.scalars().all()
            title = "✅ Решённые"
        elif filter_type == "stats":
            stats = await service.get_stats()
            text = "📊 <b>Статистика тикетов</b>\n\n"
            text += f"Всего: {stats['total']}\n\n"
            text += "По статусам:\n"
            for status, count in stats['by_status'].items():
                text += f"• {status}: {count}\n"
            text += f"\nСреднее время решения: {stats['avg_resolution_days']:.1f} дн."
            
            await callback.message.edit_text(
                text,
                reply_markup=AdminKeyboards.tickets_management(0),
                parse_mode="HTML"
            )
            await callback.answer()
            return
        else:
            await callback.answer("Неизвестный фильтр", show_alert=True)
            return
    
    if not tickets:
        await callback.answer("Нет тикетов", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"🎫 <b>{title}</b>\n\nВыберите обращение:",
        reply_markup=AdminKeyboards.admin_ticket_list(tickets),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_ticket:"))
async def callback_admin_view_ticket(callback: CallbackQuery, user: User):
    """Просмотр тикета админом"""
    if not admin_filter(user):
        return
    
    ticket_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        service = TicketService(session)
        ticket = await service.get_ticket_by_id(ticket_id)
        
        if not ticket:
            await callback.answer("Тикет не найден", show_alert=True)
            return
        
        messages = await service.get_messages(ticket_id, include_internal=True)
    
    status_names = {
        TicketStatus.OPEN: "🆕 Открыт",
        TicketStatus.IN_PROGRESS: "🔄 В работе",
        TicketStatus.WAITING: "⏳ Ожидает ответа",
        TicketStatus.RESOLVED: "✅ Решён",
        TicketStatus.CLOSED: "🔒 Закрыт"
    }
    
    text = f"🎫 <b>{ticket.ticket_number}</b>\n\n"
    text += f"📌 <b>Тема:</b> {ticket.subject}\n"
    text += f"📊 <b>Статус:</b> {status_names.get(ticket.status)}\n"
    text += f"⚡ <b>Приоритет:</b> {'🔴' if ticket.priority == 3 else '🟡' if ticket.priority == 2 else '🟢'}\n"
    
    if not ticket.is_anonymous and ticket.user:
        text += f"👤 <b>От:</b> {ticket.user.display_name}\n"
        if ticket.user.group_name:
            text += f"   Группа: {ticket.user.group_name}\n"
    else:
        text += f"👤 <b>От:</b> Анонимно\n"
    
    if ticket.assigned_to:
        text += f"👨‍💼 <b>Исполнитель:</b> {ticket.assigned_to.display_name}\n"
    else:
        text += f"👨‍💼 <b>Исполнитель:</b> ❗ Не назначен\n"
    
    text += f"\n📄 <b>Описание:</b>\n{ticket.description[:500]}\n"
    
    if messages:
        text += f"\n{'─' * 20}\n<b>Последние сообщения:</b>\n\n"
        for msg in messages[-3:]:
            sender = ticket.user.display_name if not msg.is_from_staff else "👨‍💼 Поддержка"
            if msg.is_internal:
                sender += " (внутр.)"
            text += f"<b>{sender}</b>:\n{msg.message[:200]}\n\n"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Ответить",
                    callback_data=f"admin_ticket_reply:{ticket_id}"
                ),
                InlineKeyboardButton(
                    text="📝 Статус",
                    callback_data=f"admin_ticket_status:{ticket_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Взять на себя" if not ticket.assigned_to_id else "🔄 Переназначить",
                    callback_data=f"admin_ticket_assign:{ticket_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data="admin_tickets:main"
                )
            ]
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_ticket_reply:"))
async def callback_admin_ticket_reply(callback: CallbackQuery, user: User, state: FSMContext):
    """Ответ на тикет"""
    if not admin_filter(user):
        return
    
    ticket_id = int(callback.data.split(":")[1])
    await state.update_data(admin_reply_ticket_id=ticket_id)
    await state.set_state(AdminStates.ticket_reply)
    
    await callback.message.edit_text(
        "💬 <b>Ответ на обращение</b>\n\n"
        "Введите текст ответа:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.ticket_reply)
async def process_admin_ticket_reply(message: Message, user: User, state: FSMContext, bot: Bot):
    """Обработка ответа на тикет"""
    data = await state.get_data()
    ticket_id = data.get("admin_reply_ticket_id")
    
    if not ticket_id:
        await state.clear()
        return
    
    reply_text = message.text.strip()
    
    async with async_session() as session:
        ticket_service = TicketService(session)
        notification_service = NotificationService(session, bot)
        
        # Добавляем сообщение
        await ticket_service.add_message(
            ticket_id=ticket_id,
            user_id=user.id,
            message=reply_text,
            is_from_staff=True
        )
        
        # Получаем тикет для уведомления
        ticket = await ticket_service.get_ticket_by_id(ticket_id)
        
        if ticket and ticket.user:
            # Уведомляем пользователя
            await notification_service.notify_ticket_response(
                ticket.user.telegram_id,
                ticket.ticket_number,
                reply_text
            )
        
        await session.commit()
    
    await state.clear()
    
    await message.answer(
        "✅ Ответ отправлен!",
        reply_markup=AdminKeyboards.main_menu()
    )


@router.callback_query(F.data.startswith("admin_ticket_status:"))
async def callback_admin_ticket_status(callback: CallbackQuery, user: User):
    """Изменение статуса тикета"""
    if not admin_filter(user):
        return
    
    ticket_id = int(callback.data.split(":")[1])
    
    from app.keyboards.tickets import TicketKeyboards
    
    await callback.message.edit_text(
        "📝 <b>Изменение статуса</b>\n\nВыберите новый статус:",
        reply_markup=TicketKeyboards.status_change(ticket_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ticket_set_status:"))
async def callback_set_ticket_status(callback: CallbackQuery, user: User):
    """Установка нового статуса тикета"""
    if not admin_filter(user):
        return
    
    parts = callback.data.split(":")
    ticket_id = int(parts[1])
    new_status = TicketStatus(parts[2])
    
    async with async_session() as session:
        service = TicketService(session)
        await service.update_status(ticket_id, new_status, user.id)
        await session.commit()
    
    await callback.answer(f"Статус изменён на: {new_status.value}", show_alert=True)


@router.callback_query(F.data.startswith("admin_ticket_assign:"))
async def callback_admin_ticket_assign(callback: CallbackQuery, user: User):
    """Назначение тикета на себя"""
    if not admin_filter(user):
        return
    
    ticket_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        service = TicketService(session)
        await service.assign_ticket(ticket_id, user.id)
        await session.commit()
    
    await callback.answer("✅ Тикет назначен на вас", show_alert=True)


# === Управление FAQ ===

@router.message(F.text == "❓ Управление FAQ")
async def admin_faq_menu(message: Message, user: User):
    """Меню управления FAQ"""
    if not admin_filter(user):
        return
    
    await message.answer(
        "❓ <b>Управление FAQ</b>\n\n"
        "Выберите действие:",
        reply_markup=AdminKeyboards.faq_management(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_faq:main")
async def callback_admin_faq_main(callback: CallbackQuery, user: User):
    """Возврат в меню FAQ"""
    if not admin_filter(user):
        return
    
    await callback.message.edit_text(
        "❓ <b>Управление FAQ</b>\n\nВыберите действие:",
        reply_markup=AdminKeyboards.faq_management(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_faq:categories")
async def callback_admin_faq_categories(callback: CallbackQuery, user: User):
    """Список категорий FAQ"""
    if not admin_filter(user):
        return
    
    async with async_session() as session:
        service = FAQService(session)
        categories = await service.get_all_categories(active_only=False)
    
    await callback.message.edit_text(
        "📁 <b>Категории FAQ</b>\n\n"
        "Выберите категорию для редактирования:",
        reply_markup=AdminKeyboards.faq_categories_edit(categories),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_faq:add_category")
async def callback_add_faq_category(callback: CallbackQuery, user: User, state: FSMContext):
    """Добавление категории FAQ"""
    if not admin_filter(user):
        return
    
    await state.set_state(AdminStates.adding_category_name)
    
    await callback.message.edit_text(
        "➕ <b>Добавление категории</b>\n\n"
        "Введите название категории:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.adding_category_name)
async def process_category_name(message: Message, state: FSMContext):
    """Обработка названия категории"""
    name = message.text.strip()
    
    if len(name) < 2:
        await message.answer("Название слишком короткое")
        return
    
    await state.update_data(category_name=name)
    await state.set_state(AdminStates.adding_category_slug)
    
    # Генерируем slug из названия
    import re
    slug = re.sub(r'[^a-zA-Z0-9а-яА-Я]', '_', name.lower())
    slug = re.sub(r'_+', '_', slug).strip('_')
    
    # Транслитерация
    translit = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e',
        'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k',
        'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
        'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts',
        'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '',
        'э': 'e', 'ю': 'yu', 'я': 'ya'
    }
    slug = ''.join(translit.get(c, c) for c in slug)
    
    await message.answer(
        f"Введите slug (идентификатор) для категории.\n"
        f"Предложенный: <code>{slug}</code>\n\n"
        f"Или введите свой:",
        parse_mode="HTML"
    )


@router.message(AdminStates.adding_category_slug)
async def process_category_slug(message: Message, state: FSMContext):
    """Обработка slug категории"""
    import re
    slug = re.sub(r'[^a-zA-Z0-9_]', '', message.text.strip().lower())
    
    if len(slug) < 2:
        await message.answer("Slug слишком короткий")
        return
    
    await state.update_data(category_slug=slug)
    await state.set_state(AdminStates.adding_category_icon)
    
    await message.answer(
        "Введите иконку (emoji) для категории.\n"
        "Например: 📚, 💰, 📅\n\n"
        "Или отправьте 'skip' чтобы пропустить:"
    )


@router.message(AdminStates.adding_category_icon)
async def process_category_icon(message: Message, user: User, state: FSMContext):
    """Обработка иконки категории"""
    icon = message.text.strip() if message.text.lower() != 'skip' else None
    
    data = await state.get_data()
    
    async with async_session() as session:
        service = FAQService(session)
        category = await service.create_category(
            name=data['category_name'],
            slug=data['category_slug'],
            icon=icon
        )
        await session.commit()
    
    await state.clear()
    
    await message.answer(
        f"✅ Категория «{data['category_name']}» создана!",
        reply_markup=AdminKeyboards.main_menu()
    )


@router.callback_query(F.data == "admin_faq:add_item")
async def callback_add_faq_item(callback: CallbackQuery, user: User, state: FSMContext):
    """Добавление вопроса в FAQ"""
    if not admin_filter(user):
        return
    
    async with async_session() as session:
        service = FAQService(session)
        categories = await service.get_all_categories()
    
    if not categories:
        await callback.answer("Сначала создайте категорию", show_alert=True)
        return
    
    await state.set_state(AdminStates.selecting_item_category)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = []
    for cat in categories:
        buttons.append([
            InlineKeyboardButton(
                text=f"{cat.icon or '📁'} {cat.name}",
                callback_data=f"faq_add_to_cat:{cat.id}"
            )
        ])
    
    await callback.message.edit_text(
        "➕ <b>Добавление вопроса</b>\n\n"
        "Выберите категорию:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("faq_add_to_cat:"), AdminStates.selecting_item_category)
async def select_item_category(callback: CallbackQuery, state: FSMContext):
    """Выбор категории для вопроса"""
    category_id = int(callback.data.split(":")[1])
    await state.update_data(item_category_id=category_id)
    await state.set_state(AdminStates.adding_item_question)
    
    await callback.message.edit_text(
        "❓ <b>Введите вопрос:</b>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.adding_item_question)
async def process_item_question(message: Message, state: FSMContext):
    """Обработка вопроса"""
    question = message.text.strip()
    
    if len(question) < 5:
        await message.answer("Вопрос слишком короткий")
        return
    
    await state.update_data(item_question=question)
    await state.set_state(AdminStates.adding_item_answer)
    
    await message.answer(
        "💬 <b>Введите ответ:</b>\n\n"
        "Можно использовать HTML-разметку:\n"
        "<code>&lt;b&gt;жирный&lt;/b&gt;</code>, <code>&lt;i&gt;курсив&lt;/i&gt;</code>",
        parse_mode="HTML"
    )


@router.message(AdminStates.adding_item_answer)
async def process_item_answer(message: Message, state: FSMContext):
    """Обработка ответа"""
    answer = message.text.strip()
    
    if len(answer) < 10:
        await message.answer("Ответ слишком короткий")
        return
    
    await state.update_data(item_answer=answer)
    await state.set_state(AdminStates.adding_item_keywords)
    
    await message.answer(
        "🔑 <b>Введите ключевые слова</b> (через запятую)\n\n"
        "Они помогут найти этот вопрос при поиске.\n"
        "Отправьте 'skip' чтобы пропустить."
    )


@router.message(AdminStates.adding_item_keywords)
async def process_item_keywords(message: Message, user: User, state: FSMContext):
    """Обработка ключевых слов"""
    keywords = message.text.strip() if message.text.lower() != 'skip' else None
    
    data = await state.get_data()
    
    async with async_session() as session:
        service = FAQService(session)
        item = await service.create_item(
            category_id=data['item_category_id'],
            question=data['item_question'],
            answer=data['item_answer'],
            keywords=keywords
        )
        await session.commit()
    
    await state.clear()
    
    await message.answer(
        f"✅ Вопрос добавлен в FAQ!\n\n"
        f"ID: {item.id}",
        reply_markup=AdminKeyboards.main_menu()
    )


@router.callback_query(F.data == "admin_faq:stats")
async def callback_admin_faq_stats(callback: CallbackQuery, user: User):
    """Статистика FAQ"""
    if not admin_filter(user):
        return
    
    async with async_session() as session:
        service = FAQService(session)
        stats = await service.get_stats()
        popular = await service.get_popular_items(limit=5)
    
    text = "📊 <b>Статистика FAQ</b>\n\n"
    text += f"📁 Категорий: {stats['categories_count']}\n"
    text += f"❓ Вопросов: {stats['items_count']}\n"
    text += f"👁 Просмотров: {stats['total_views']}\n"
    text += f"👍 Полезных: {stats['helpful_count']}\n"
    text += f"👎 Неполезных: {stats['not_helpful_count']}\n\n"
    
    if popular:
        text += "<b>🔥 Популярные вопросы:</b>\n"
        for i, item in enumerate(popular, 1):
            text += f"{i}. {item.question[:40]}... ({item.views_count} просм.)\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.faq_management(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_faq_cat:"))
async def callback_admin_faq_cat_view(callback: CallbackQuery, user: User):
    """Просмотр категории FAQ"""
    if not admin_filter(user):
        return
    
    cat_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        service = FAQService(session)
        category = await service.get_category_by_id(cat_id)
    
    if not category:
        await callback.answer("Категория не найдена", show_alert=True)
        return
    
    text = f"📁 <b>{category.name}</b>\n\n"
    text += f"🔑 Slug: {category.slug}\n"
    text += f"{'✅ Активна' if category.is_active else '❌ Неактивна'}\n"
    if category.description:
        text += f"📝 {category.description}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.faq_category_actions(cat_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_faq_cat_items:"))
async def callback_admin_faq_cat_items(callback: CallbackQuery, user: User):
    """Вопросы категории"""
    if not admin_filter(user):
        return
    
    cat_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        service = FAQService(session)
        category = await service.get_category_by_id(cat_id)
        items = await service.get_items_by_category(cat_id)
    
    if not category:
        await callback.answer("Категория не найдена", show_alert=True)
        return
    
    text = f"📁 <b>{category.name}</b> — вопросы:\n\n"
    
    if items:
        for i, item in enumerate(items[:15], 1):
            text += f"{i}. {item.question[:50]}...\n"
    else:
        text += "В категории пока нет вопросов."
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_faq_cat:{cat_id}")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_faq_cat_toggle:"))
async def callback_admin_faq_cat_toggle(callback: CallbackQuery, user: User):
    """Вкл/выкл категорию"""
    if not admin_filter(user):
        return
    
    cat_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        service = FAQService(session)
        category = await service.get_category_by_id(cat_id)
        
        if not category:
            await callback.answer("Категория не найдена", show_alert=True)
            return
        
        await service.toggle_category(cat_id, not category.is_active)
        await session.commit()
    
    status = "включена" if not category.is_active else "отключена"
    await callback.answer(f"Категория {status}", show_alert=True)
    
    # Обновляем список
    async with async_session() as session:
        service = FAQService(session)
        categories = await service.get_all_categories(active_only=False)
    
    await callback.message.edit_text(
        "📁 <b>Категории FAQ</b>\n\nВыберите категорию:",
        reply_markup=AdminKeyboards.faq_categories_edit(categories),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_faq_cat_delete:"))
async def callback_admin_faq_cat_delete(callback: CallbackQuery, user: User):
    """Удаление категории (только для админов)"""
    if not admin_only_filter(user):
        await callback.answer("⛔ Только администратор может удалять категории", show_alert=True)
        return
    
    cat_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        service = FAQService(session)
        await service.delete_category(cat_id)
        await session.commit()
    
    await callback.answer("🗑 Категория удалена", show_alert=True)
    
    # Обновляем список
    async with async_session() as session:
        service = FAQService(session)
        categories = await service.get_all_categories(active_only=False)
    
    await callback.message.edit_text(
        "📁 <b>Категории FAQ</b>\n\nВыберите категорию:",
        reply_markup=AdminKeyboards.faq_categories_edit(categories),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_faq_cat_edit:"))
async def callback_admin_faq_cat_edit(callback: CallbackQuery, user: User):
    """Редактирование категории (placeholder)"""
    if not admin_filter(user):
        return
    
    await callback.answer("Редактирование через бота пока недоступно. Используйте БД.", show_alert=True)


# === Управление пользователями ===

@router.message(F.text == "👥 Пользователи")
async def admin_users_menu(message: Message, user: User):
    """Меню управления пользователями"""
    if not admin_filter(user):
        return
    
    await message.answer(
        "👥 <b>Управление пользователями</b>\n\n"
        "Выберите действие:",
        reply_markup=AdminKeyboards.users_management(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_users:main")
async def callback_admin_users_main(callback: CallbackQuery, user: User):
    """Возврат в меню пользователей"""
    if not admin_filter(user):
        return
    
    await callback.message.edit_text(
        "👥 <b>Управление пользователями</b>",
        reply_markup=AdminKeyboards.users_management(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_users:search")
async def callback_admin_search_user(callback: CallbackQuery, user: User, state: FSMContext):
    """Поиск пользователя"""
    if not admin_filter(user):
        return
    
    await state.set_state(AdminStates.searching_user)
    
    await callback.message.edit_text(
        "🔍 <b>Поиск пользователя</b>\n\n"
        "Введите имя, username, группу или ID:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.searching_user)
async def process_user_search(message: Message, user: User, state: FSMContext):
    """Обработка поиска пользователя"""
    query = message.text.strip()
    
    async with async_session() as session:
        service = UserService(session)
        users = await service.search_users(query)
    
    await state.clear()
    
    if not users:
        await message.answer(
            f"По запросу «{query}» ничего не найдено",
            reply_markup=AdminKeyboards.main_menu()
        )
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = []
    for u in users[:10]:
        role_emoji = {"admin": "👑", "moderator": "👨‍💼", "teacher": "👨‍🏫", "student": "🎓"}.get(u.role.value, "👤")
        text = f"{role_emoji} {u.display_name}"
        if u.group_name:
            text += f" ({u.group_name})"
        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"admin_user_view:{u.id}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users:main")
    ])
    
    await message.answer(
        f"🔍 <b>Результаты поиска:</b> «{query}»\n\n"
        f"Найдено: {len(users)}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_user_view:"))
async def callback_admin_view_user(callback: CallbackQuery, user: User):
    """Просмотр пользователя"""
    if not admin_filter(user):
        return
    
    target_user_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        service = UserService(session)
        target_user = await service.get_by_id(target_user_id)
        
        if not target_user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
    
    role_names = {
        "student": "🎓 Студент",
        "teacher": "👨‍🏫 Преподаватель",
        "moderator": "👨‍💼 Модератор",
        "admin": "👑 Администратор"
    }
    
    text = f"👤 <b>Пользователь #{target_user.id}</b>\n\n"
    text += f"<b>Telegram:</b>\n"
    text += f"├ ID: <code>{target_user.telegram_id}</code>\n"
    text += f"├ Username: @{target_user.username or '—'}\n"
    text += f"└ Имя: {target_user.first_name or '—'} {target_user.last_name or ''}\n\n"
    
    text += f"<b>Профиль:</b>\n"
    text += f"├ ФИО: {target_user.full_name or '—'}\n"
    text += f"├ Группа: {target_user.group_name or '—'}\n"
    text += f"├ Курс: {target_user.course or '—'}\n"
    text += f"└ Роль: {role_names.get(target_user.role.value, target_user.role.value)}\n\n"
    
    text += f"<b>Статус:</b>\n"
    text += f"├ Активен: {'✅' if target_user.is_active else '❌'}\n"
    text += f"├ Верифицирован: {'✅' if target_user.is_verified else '❌'}\n"
    text += f"└ Уведомления: {'🔔' if target_user.notifications_enabled else '🔕'}\n\n"
    
    text += f"📅 Регистрация: {target_user.created_at.strftime('%d.%m.%Y %H:%M')}"
    
    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.user_actions(target_user.id, target_user.role.value),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_user_role:"))
async def callback_change_user_role(callback: CallbackQuery, user: User):
    """Изменение роли пользователя"""
    if user.role != UserRole.ADMIN:
        await callback.answer("Только администратор может менять роли", show_alert=True)
        return
    
    parts = callback.data.split(":")
    target_user_id = int(parts[1])
    new_role = UserRole(parts[2])
    
    async with async_session() as session:
        service = UserService(session)
        await service.set_role(target_user_id, new_role)
        await session.commit()
    
    await callback.answer(f"✅ Роль изменена на {new_role.value}", show_alert=True)


@router.callback_query(F.data.startswith("admin_user_ban:"))
async def callback_ban_user(callback: CallbackQuery, user: User):
    """Блокировка пользователя (только для админов)"""
    if not admin_only_filter(user):
        await callback.answer("⛔ Только администратор может блокировать", show_alert=True)
        return
    
    target_user_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        service = UserService(session)
        await service.deactivate_user(target_user_id)
        await session.commit()
    
    await callback.answer("🚫 Пользователь заблокирован", show_alert=True)


@router.callback_query(F.data == "admin_users:stats")
async def callback_admin_users_stats(callback: CallbackQuery, user: User):
    """Статистика пользователей"""
    if not admin_filter(user):
        return
    
    async with async_session() as session:
        service = UserService(session)
        stats = await service.get_stats()
    
    text = "📊 <b>Статистика пользователей</b>\n\n"
    text += f"👥 Всего: {stats['total']}\n"
    text += f"✅ Активных: {stats['active']}\n"
    text += f"🆕 Новых сегодня: {stats['new_today']}\n"
    text += f"✔️ Верифицированных: {stats['verified']}\n\n"
    
    text += "<b>По ролям:</b>\n"
    for role, count in stats['by_role'].items():
        text += f"• {role}: {count}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.users_management(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_users:admins")
async def callback_admin_users_admins(callback: CallbackQuery, user: User):
    """Список администраторов"""
    if not admin_filter(user):
        return
    
    async with async_session() as session:
        service = UserService(session)
        admins = await service.get_users_by_role(UserRole.ADMIN)
    
    text = "👑 <b>Администраторы</b>\n\n"
    
    if admins:
        for i, admin in enumerate(admins, 1):
            text += f"{i}. {admin.display_name}"
            if admin.username:
                text += f" (@{admin.username})"
            text += "\n"
    else:
        text += "Администраторов нет"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users:main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_users:moderators")
async def callback_admin_users_moderators(callback: CallbackQuery, user: User):
    """Список модераторов"""
    if not admin_filter(user):
        return
    
    async with async_session() as session:
        service = UserService(session)
        moderators = await service.get_users_by_role(UserRole.MODERATOR)
    
    text = "👨‍💼 <b>Модераторы</b>\n\n"
    
    if moderators:
        for i, mod in enumerate(moderators, 1):
            text += f"{i}. {mod.display_name}"
            if mod.username:
                text += f" (@{mod.username})"
            text += "\n"
    else:
        text += "Модераторов нет"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users:main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_user_tickets:"))
async def callback_admin_user_tickets(callback: CallbackQuery, user: User):
    """История обращений пользователя"""
    if not admin_filter(user):
        return
    
    target_user_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        ticket_service = TicketService(session)
        tickets = await ticket_service.get_user_tickets(target_user_id, limit=10)
    
    text = "📋 <b>История обращений</b>\n\n"
    
    if tickets:
        for ticket in tickets:
            status_icons = {"open": "🆕", "in_progress": "🔄", "resolved": "✅", "closed": "🔒"}
            icon = status_icons.get(ticket.status.value, "📋")
            text += f"{icon} {ticket.ticket_number}: {ticket.subject[:30]}...\n"
    else:
        text += "Обращений нет"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_user_view:{target_user_id}")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_user_activity:"))
async def callback_admin_user_activity(callback: CallbackQuery, user: User):
    """Активность пользователя"""
    if not admin_filter(user):
        return
    
    target_user_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        analytics_service = AnalyticsService(session)
        activity = await analytics_service.get_user_activity(target_user_id, limit=10)
    
    text = "📊 <b>Последняя активность</b>\n\n"
    
    if activity:
        for log in activity:
            text += f"• {log.request_type}: {log.request_text[:30] if log.request_text else 'N/A'}...\n"
            text += f"  📅 {log.created_at.strftime('%d.%m %H:%M')}\n"
    else:
        text += "Активности нет"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_user_view:{target_user_id}")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# === Рассылка ===

@router.message(F.text == "📢 Рассылка")
@router.message(Command("broadcast"))
async def admin_broadcast_menu(message: Message, user: User):
    """Меню рассылки"""
    if user.role != UserRole.ADMIN:
        await message.answer("⛔ Только администратор может делать рассылки")
        return
    
    await message.answer(
        "📢 <b>Рассылка</b>\n\n"
        "Выберите аудиторию:",
        reply_markup=AdminKeyboards.broadcast_targets(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("broadcast:"))
async def callback_broadcast_target(callback: CallbackQuery, user: User, state: FSMContext):
    """Выбор целевой аудитории"""
    if user.role != UserRole.ADMIN:
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    target = callback.data.split(":")[1]
    
    if target == "cancel":
        await state.clear()
        await callback.message.edit_text("❌ Рассылка отменена")
        await callback.answer()
        return
    
    await state.update_data(broadcast_target=target)
    await state.set_state(AdminStates.broadcast_text)
    
    target_names = {
        "all": "всем пользователям",
        "students": "студентам",
        "teachers": "преподавателям"
    }
    
    await callback.message.edit_text(
        f"📢 <b>Рассылка: {target_names.get(target, target)}</b>\n\n"
        "Введите текст сообщения.\n"
        "Можно использовать HTML-разметку.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.broadcast_text)
async def process_broadcast_text(message: Message, user: User, state: FSMContext):
    """Обработка текста рассылки"""
    text = message.text.strip()
    
    if len(text) < 5:
        await message.answer("Сообщение слишком короткое")
        return
    
    data = await state.get_data()
    target = data.get("broadcast_target")
    
    # Подсчитываем получателей
    async with async_session() as session:
        service = UserService(session)
        
        if target == "all":
            users = await service.get_users_with_notifications()
        elif target == "students":
            users = await service.get_users_with_notifications(role=UserRole.STUDENT)
        elif target == "teachers":
            users = await service.get_users_with_notifications(role=UserRole.TEACHER)
        else:
            users = []
    
    count = len(users)
    
    await state.update_data(broadcast_text=text, broadcast_count=count)
    await state.set_state(AdminStates.broadcast_confirm)
    
    await message.answer(
        f"📢 <b>Подтверждение рассылки</b>\n\n"
        f"<b>Аудитория:</b> {target}\n"
        f"<b>Получателей:</b> {count}\n\n"
        f"<b>Текст:</b>\n{text[:500]}{'...' if len(text) > 500 else ''}\n\n"
        f"Отправить?",
        reply_markup=AdminKeyboards.confirm_broadcast(target, count),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("broadcast_confirm:"))
async def callback_broadcast_confirm(callback: CallbackQuery, user: User, state: FSMContext, bot: Bot):
    """Подтверждение и отправка рассылки"""
    if user.role != UserRole.ADMIN:
        return
    
    data = await state.get_data()
    text = data.get("broadcast_text")
    target = data.get("broadcast_target")
    
    await state.clear()
    await callback.message.edit_text("📤 Отправка...")
    await callback.answer()
    
    # Получаем пользователей
    async with async_session() as session:
        service = UserService(session)
        notification_service = NotificationService(session, bot)
        
        if target == "all":
            users = await service.get_users_with_notifications()
        elif target == "students":
            users = await service.get_users_with_notifications(role=UserRole.STUDENT)
        elif target == "teachers":
            users = await service.get_users_with_notifications(role=UserRole.TEACHER)
        else:
            users = []
        
        sent = 0
        failed = 0
        
        for u in users:
            try:
                await bot.send_message(
                    chat_id=u.telegram_id,
                    text=f"📢 <b>Объявление</b>\n\n{text}",
                    parse_mode="HTML"
                )
                sent += 1
            except Exception:
                failed += 1
            
            # Небольшая задержка чтобы не превысить лимиты
            import asyncio
            await asyncio.sleep(0.05)
    
    await callback.message.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}",
        parse_mode="HTML"
    )


# === Документы ===

@router.message(F.text == "📄 Документы")
async def admin_documents_menu(message: Message, user: User):
    """Меню управления документами (для админа)"""
    # Эта команда перехватывается раньше, если пользователь не админ
    if not admin_filter(user):
        return
    
    async with async_session() as session:
        service = DocumentService(session)
        stats = await service.get_stats()
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Список документов",
                    callback_data="admin_docs:list"
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ Добавить документ",
                    callback_data="admin_docs:add"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="admin_docs:stats"
                )
            ]
        ]
    )
    
    await message.answer(
        f"📄 <b>Управление документами</b>\n\n"
        f"📋 Всего: {stats['total']}\n"
        f"📥 Скачиваний: {stats['total_downloads']}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_docs:list")
async def callback_admin_docs_list(callback: CallbackQuery, user: User):
    """Список документов"""
    if not admin_filter(user):
        return
    
    async with async_session() as session:
        service = DocumentService(session)
        documents = await service.get_all_documents()
    
    if not documents:
        await callback.answer("Документов пока нет", show_alert=True)
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = []
    for doc in documents[:20]:  # Ограничиваем 20
        icon = {"pdf": "📕", "docx": "📘", "xlsx": "📗"}.get(doc.file_type or "", "📄")
        text = f"{icon} {doc.name[:35]}..."
        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"admin_doc_edit:{doc.id}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_docs:main")
    ])
    
    await callback.message.edit_text(
        f"📋 <b>Список документов</b>\n\n"
        f"Всего: {len(documents)}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_docs:main")
async def callback_admin_docs_main(callback: CallbackQuery, user: User):
    """Возврат в меню документов"""
    if not admin_filter(user):
        return
    
    async with async_session() as session:
        service = DocumentService(session)
        stats = await service.get_stats()
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Список документов", callback_data="admin_docs:list")],
            [InlineKeyboardButton(text="➕ Добавить документ", callback_data="admin_docs:add")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_docs:stats")]
        ]
    )
    
    await callback.message.edit_text(
        f"📄 <b>Управление документами</b>\n\n"
        f"📋 Всего: {stats['total']}\n"
        f"📥 Скачиваний: {stats['total_downloads']}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_docs:add")
async def callback_admin_docs_add(callback: CallbackQuery, user: User, state: FSMContext):
    """Добавление документа"""
    if not admin_filter(user):
        return
    
    await state.set_state(AdminStates.adding_document_name)
    
    await callback.message.edit_text(
        "➕ <b>Добавление документа</b>\n\n"
        "Введите название документа:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.adding_document_name)
async def process_document_name(message: Message, state: FSMContext):
    """Обработка названия документа"""
    name = message.text.strip()
    
    if len(name) < 3:
        await message.answer("Название слишком короткое. Минимум 3 символа.")
        return
    
    await state.update_data(doc_name=name)
    await state.set_state(AdminStates.adding_document_category)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    # Категории документов
    categories = [
        ("📝 Заявления", "applications"),
        ("📋 Справки", "certificates"),
        ("🏢 Практика", "practice"),
        ("🎓 ВКР", "vkr"),
        ("📄 Общие", "general"),
    ]
    
    buttons = []
    for cat_name, cat_slug in categories:
        buttons.append([
            InlineKeyboardButton(text=cat_name, callback_data=f"doc_cat_select:{cat_slug}")
        ])
    
    await message.answer(
        "📁 <b>Выберите категорию:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("doc_cat_select:"), AdminStates.adding_document_category)
async def process_document_category(callback: CallbackQuery, state: FSMContext):
    """Выбор категории документа"""
    category = callback.data.split(":")[1]
    await state.update_data(doc_category=category)
    await state.set_state(AdminStates.adding_document_file)
    
    await callback.message.edit_text(
        "📎 <b>Отправьте ссылку на документ</b>\n\n"
        "Например: https://mospolytech.ru/docs/example.pdf\n\n"
        "Или отправьте 'skip' чтобы добавить без ссылки",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.adding_document_file)
async def process_document_file(message: Message, user: User, state: FSMContext):
    """Обработка файла/ссылки документа"""
    data = await state.get_data()
    
    file_url = None
    file_type = None
    
    if message.text.lower() != 'skip':
        file_url = message.text.strip()
        # Определяем тип файла из URL
        if '.' in file_url:
            file_type = file_url.split('.')[-1].lower()[:10]
    
    # Сохраняем документ
    async with async_session() as session:
        service = DocumentService(session)
        doc = await service.create_document(
            name=data['doc_name'],
            category=data['doc_category'],
            file_url=file_url,
            file_type=file_type
        )
        await session.commit()
    
    await state.clear()
    
    await message.answer(
        f"✅ Документ «{data['doc_name']}» добавлен!\n"
        f"ID: {doc.id}",
        reply_markup=AdminKeyboards.main_menu()
    )


@router.callback_query(F.data == "admin_docs:stats")
async def callback_admin_docs_stats(callback: CallbackQuery, user: User):
    """Статистика документов"""
    if not admin_filter(user):
        return
    
    async with async_session() as session:
        service = DocumentService(session)
        stats = await service.get_stats()
        popular = await service.get_popular_documents(limit=5)
    
    text = "📊 <b>Статистика документов</b>\n\n"
    text += f"📋 Всего документов: {stats['total']}\n"
    text += f"📥 Всего скачиваний: {stats['total_downloads']}\n\n"
    
    if popular:
        text += "<b>🔥 Популярные документы:</b>\n"
        for i, doc in enumerate(popular, 1):
            text += f"{i}. {doc.name[:35]}... ({doc.downloads_count} скач.)\n"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_docs:main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_doc_edit:"))
async def callback_admin_doc_edit(callback: CallbackQuery, user: User):
    """Редактирование документа"""
    if not admin_filter(user):
        return
    
    doc_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        service = DocumentService(session)
        doc = await service.get_document_by_id(doc_id)
    
    if not doc:
        await callback.answer("Документ не найден", show_alert=True)
        return
    
    text = f"📄 <b>{doc.name}</b>\n\n"
    text += f"📁 Категория: {doc.category}\n"
    text += f"📎 Тип: {doc.file_type or 'не указан'}\n"
    text += f"🔗 URL: {doc.file_url or 'нет'}\n"
    text += f"📥 Скачиваний: {doc.downloads_count}\n"
    text += f"📅 Создан: {doc.created_at.strftime('%d.%m.%Y')}"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin_doc_delete:{doc_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_docs:list")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_doc_delete:"))
async def callback_admin_doc_delete(callback: CallbackQuery, user: User):
    """Удаление документа (только для админов)"""
    if not admin_only_filter(user):
        await callback.answer("⛔ Только администратор может удалять документы", show_alert=True)
        return
    
    doc_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        service = DocumentService(session)
        await service.delete_document(doc_id)
        await session.commit()
    
    await callback.answer("🗑 Документ удалён", show_alert=True)
    
    # Возвращаемся к списку
    async with async_session() as session:
        service = DocumentService(session)
        stats = await service.get_stats()
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список документов", callback_data="admin_docs:list")],
        [InlineKeyboardButton(text="➕ Добавить документ", callback_data="admin_docs:add")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_docs:stats")]
    ])
    
    await callback.message.edit_text(
        f"📄 <b>Управление документами</b>\n\n"
        f"📋 Всего: {stats['total']}\n"
        f"📥 Скачиваний: {stats['total_downloads']}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# === Возврат в главное меню ===

@router.message(F.text == "◀️ В главное меню")
async def back_to_main_menu(message: Message, user: User, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await message.answer(
        "🏠 <b>Главное меню</b>",
        reply_markup=MainKeyboards.main_menu(user.role),
        parse_mode="HTML"
    )

