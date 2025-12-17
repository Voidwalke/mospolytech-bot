"""
Хендлеры FAQ
"""
import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.database import User, async_session
from app.services import FAQService, AnalyticsService
from app.keyboards.faq import FAQKeyboards
from app.keyboards.main import MainKeyboards
from app.keyboards.inline import InlineKeyboards


router = Router(name="faq")


class FAQStates(StatesGroup):
    """Состояния для FAQ"""
    searching = State()


# === Команды и кнопки ===

@router.message(F.text == "❓ FAQ")
@router.message(Command("faq"))
async def show_faq_categories(message: Message, user: User):
    """Показать категории FAQ"""
    async with async_session() as session:
        service = FAQService(session)
        categories = await service.get_all_categories()
        
        # Логируем запрос
        analytics = AnalyticsService(session)
        await analytics.log_request(
            user_id=user.id,
            request_type="faq",
            category="categories"
        )
        await session.commit()
    
    if not categories:
        await message.answer(
            "📚 База FAQ пока пуста.\n"
            "Вы можете задать вопрос оператору через раздел «✉️ Задать вопрос»"
        )
        return
    
    await message.answer(
        "📚 <b>База часто задаваемых вопросов</b>\n\n"
        "Выберите категорию или воспользуйтесь поиском:",
        reply_markup=FAQKeyboards.categories(categories),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "faq_categories")
async def callback_faq_categories(callback: CallbackQuery, user: User):
    """Callback для возврата к категориям"""
    async with async_session() as session:
        service = FAQService(session)
        categories = await service.get_all_categories()
    
    await callback.message.edit_text(
        "📚 <b>База часто задаваемых вопросов</b>\n\n"
        "Выберите категорию или воспользуйтесь поиском:",
        reply_markup=FAQKeyboards.categories(categories),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("faq_cat:"))
async def callback_faq_category(callback: CallbackQuery, user: User):
    """Показать вопросы в категории"""
    category_slug = callback.data.split(":")[1]
    
    async with async_session() as session:
        service = FAQService(session)
        category = await service.get_category_by_slug(category_slug)
        
        if not category:
            await callback.answer("Категория не найдена", show_alert=True)
            return
        
        items = await service.get_items_by_category(category.id)
    
    if not items:
        await callback.message.edit_text(
            f"📁 <b>{category.name}</b>\n\n"
            "В этой категории пока нет вопросов.",
            reply_markup=FAQKeyboards.items([], category_slug),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"📁 <b>{category.name}</b>\n\n"
        f"{category.description or 'Выберите вопрос:'}\n\n"
        f"📋 Вопросов: {len(items)}",
        reply_markup=FAQKeyboards.items(items, category_slug),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("faq_item:"))
async def callback_faq_item(callback: CallbackQuery, user: User):
    """Показать ответ на вопрос"""
    item_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        service = FAQService(session)
        item = await service.get_item_by_id(item_id)
        
        if not item:
            await callback.answer("Вопрос не найден", show_alert=True)
            return
        
        # Увеличиваем счётчик просмотров
        await service.increment_view(item_id)
        
        # Проверяем, в избранном ли
        is_favorite = await service.is_favorite(user.id, item_id)
        
        # Логируем
        analytics = AnalyticsService(session)
        await analytics.log_request(
            user_id=user.id,
            request_type="faq",
            request_text=item.question[:200],
            category=item.category.slug if item.category else None,
            response_type="success"
        )
        await session.commit()
    
    # Формируем ответ
    text = f"❓ <b>{item.question}</b>\n\n"
    text += f"💬 {item.answer}"
    
    # Добавляем кнопки со ссылками, если есть
    url_buttons = InlineKeyboards.url_buttons(item.links)
    
    # Основные действия с учётом избранного
    action_keyboard = FAQKeyboards.item_actions(
        item.id, 
        item.category.slug if item.category else "general",
        is_favorite=is_favorite
    )
    
    # Объединяем клавиатуры
    if url_buttons:
        combined_buttons = url_buttons.inline_keyboard + action_keyboard.inline_keyboard
        from aiogram.types import InlineKeyboardMarkup
        keyboard = InlineKeyboardMarkup(inline_keyboard=combined_buttons)
    else:
        keyboard = action_keyboard
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    await callback.answer()


# === Оценка ответов ===

@router.callback_query(F.data.startswith("faq_rate:"))
async def callback_faq_rate(callback: CallbackQuery, user: User):
    """Оценка полезности ответа"""
    parts = callback.data.split(":")
    item_id = int(parts[1])
    is_helpful = parts[2] == "1"
    
    async with async_session() as session:
        service = FAQService(session)
        await service.rate_item(item_id, is_helpful)
        await session.commit()
    
    if is_helpful:
        await callback.answer("👍 Спасибо за оценку! Рады, что помогли!", show_alert=True)
    else:
        await callback.answer(
            "👎 Жаль, что ответ не помог. Вы можете задать вопрос оператору.",
            show_alert=True
        )


# === Избранное ===

@router.callback_query(F.data.startswith("faq_fav:"))
async def callback_faq_add_favorite(callback: CallbackQuery, user: User):
    """Добавление в избранное"""
    item_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        service = FAQService(session)
        success = await service.add_to_favorites(user.id, item_id)
        await session.commit()
    
    if success:
        await callback.answer("⭐ Добавлено в избранное!", show_alert=True)
    else:
        await callback.answer("Уже в избранном", show_alert=True)


@router.callback_query(F.data.startswith("faq_unfav:"))
async def callback_faq_remove_favorite(callback: CallbackQuery, user: User):
    """Удаление из избранного"""
    item_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        service = FAQService(session)
        await service.remove_from_favorites(user.id, item_id)
        await session.commit()
    
    await callback.answer("☆ Удалено из избранного", show_alert=True)


@router.callback_query(F.data == "faq_favorites")
async def callback_faq_favorites(callback: CallbackQuery, user: User):
    """Показать избранные FAQ"""
    async with async_session() as session:
        service = FAQService(session)
        favorites = await service.get_user_favorites(user.id)
    
    if not favorites:
        await callback.message.edit_text(
            "⭐ <b>Избранное</b>\n\n"
            "У вас пока нет избранных вопросов.\n"
            "Нажмите «☆ В избранное» при просмотре любого ответа.",
            reply_markup=FAQKeyboards.favorites([]),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"⭐ <b>Избранное</b>\n\n"
            f"Сохранённых вопросов: {len(favorites)}",
            reply_markup=FAQKeyboards.favorites(favorites),
            parse_mode="HTML"
        )
    await callback.answer()


# === Поиск ===

@router.callback_query(F.data == "faq_search")
async def callback_faq_search(callback: CallbackQuery, state: FSMContext):
    """Начало поиска по FAQ"""
    await state.set_state(FAQStates.searching)
    
    await callback.message.edit_text(
        "🔍 <b>Поиск по FAQ</b>\n\n"
        "Введите ваш вопрос или ключевые слова.\n"
        "Я найду наиболее подходящие ответы.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(FAQStates.searching)
async def process_faq_search(message: Message, user: User, state: FSMContext):
    """Обработка поискового запроса"""
    query = message.text.strip()
    
    if len(query) < 2:
        await message.answer("Введите более длинный запрос (минимум 2 символа)")
        return
    
    start_time = time.time()
    
    async with async_session() as session:
        service = FAQService(session)
        results = await service.search(query, limit=5)
        
        response_time = int((time.time() - start_time) * 1000)
        
        # Логируем поиск
        analytics = AnalyticsService(session)
        await analytics.log_request(
            user_id=user.id,
            request_type="faq_search",
            request_text=query,
            response_type="found" if results else "not_found",
            response_time_ms=response_time
        )
        await session.commit()
    
    await state.clear()
    
    if not results:
        await message.answer(
            f"🔍 По запросу «{query}» ничего не найдено.\n\n"
            "Попробуйте:\n"
            "• Переформулировать вопрос\n"
            "• Использовать другие ключевые слова\n"
            "• Задать вопрос оператору",
            reply_markup=FAQKeyboards.search_results([]),
            parse_mode="HTML"
        )
        return
    
    text = f"🔍 <b>Результаты поиска по запросу:</b> «{query}»\n\n"
    text += f"Найдено: {len(results)} результат(ов)\n"
    text += "Выберите наиболее подходящий вопрос:"
    
    await message.answer(
        text,
        reply_markup=FAQKeyboards.search_results(results),
        parse_mode="HTML"
    )


# === Автоматический поиск по тексту сообщения ===

def is_not_menu_button(message: Message) -> bool:
    """Фильтр: сообщение НЕ является кнопкой меню"""
    menu_buttons = [
        "❓ FAQ", "📅 Расписание", "📄 Документы", 
        "🎫 Мои обращения", "✉️ Задать вопрос", "👤 Профиль",
        "⚙️ Админ-панель", "◀️ В главное меню", "❌ Отмена",
        "◀️ Назад", "📊 Статистика", "🎫 Тикеты",
        "👥 Пользователи", "📢 Рассылка", "✏️ Редактировать профиль",
        "🔔 Настройки уведомлений", "✅ Отправить", "✏️ Редактировать",
        "1 курс", "2 курс", "3 курс", "4 курс", "5 курс", "6 курс",
        "⏭ Пропустить", "🔗 Ссылки", "ℹ️ Информация",
        "❓ Управление FAQ"  # Кнопка из админки
    ]
    if not message.text:
        return False
    return message.text not in menu_buttons


@router.message(F.text & ~F.text.startswith("/"), is_not_menu_button)
async def auto_search_faq(message: Message, user: User, state: FSMContext):
    """Автоматический поиск по тексту сообщения"""
    
    query = message.text.strip()
    
    if len(query) < 3:
        return  # Слишком короткий запрос
    
    start_time = time.time()
    
    async with async_session() as session:
        service = FAQService(session)
        results = await service.search(query, limit=3, threshold=60)
        
        response_time = int((time.time() - start_time) * 1000)
        
        # Логируем
        analytics = AnalyticsService(session)
        await analytics.log_request(
            user_id=user.id,
            request_type="auto_search",
            request_text=query[:200],
            response_type="found" if results else "not_found",
            response_time_ms=response_time
        )
        await session.commit()
    
    if results:
        # Нашли похожие вопросы
        text = "🤔 <b>Возможно, вы искали:</b>\n\n"
        text += "Я нашёл похожие вопросы в базе FAQ:"
        
        await message.answer(
            text,
            reply_markup=FAQKeyboards.search_results(results),
            parse_mode="HTML"
        )
    else:
        # Ничего не нашли - предлагаем создать тикет
        await message.answer(
            "🤔 Я не нашёл ответа на ваш вопрос в базе FAQ.\n\n"
            "Вы можете:\n"
            "• Попробовать другие ключевые слова\n"
            "• Посмотреть категории FAQ\n"
            "• Задать вопрос оператору",
            reply_markup=FAQKeyboards.search_results([]),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "faq_not_found")
async def callback_faq_not_found(callback: CallbackQuery):
    """Обработка случая, когда ничего не найдено"""
    await callback.answer(
        "Попробуйте задать вопрос оператору",
        show_alert=True
    )

