"""
Хендлеры документов
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.database import User, async_session
from app.services import DocumentService, AnalyticsService
from app.keyboards.inline import InlineKeyboards
from app.keyboards.main import MainKeyboards


router = Router(name="documents")


class DocumentStates(StatesGroup):
    """Состояния для документов"""
    searching = State()


@router.message(F.text == "📄 Документы")
@router.message(Command("documents"))
async def show_documents(message: Message, user: User):
    """Показать категории документов"""
    async with async_session() as session:
        service = DocumentService(session)
        categories = await service.get_categories_with_counts()
        
        # Логируем
        analytics = AnalyticsService(session)
        await analytics.log_request(
            user_id=user.id,
            request_type="documents",
            category="categories"
        )
        await session.commit()
    
    await message.answer(
        "📄 <b>Документы и шаблоны</b>\n\n"
        "Здесь вы найдёте:\n"
        "• Бланки заявлений\n"
        "• Инструкции и памятки\n"
        "• Шаблоны документов\n"
        "• Положения и приказы\n\n"
        "Выберите категорию:",
        reply_markup=InlineKeyboards.documents_categories(categories),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "docs_categories")
async def callback_docs_categories(callback: CallbackQuery, user: User):
    """Возврат к категориям документов"""
    async with async_session() as session:
        service = DocumentService(session)
        categories = await service.get_categories_with_counts()
    
    await callback.message.edit_text(
        "📄 <b>Документы и шаблоны</b>\n\n"
        "Выберите категорию:",
        reply_markup=InlineKeyboards.documents_categories(categories),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("docs_cat:"))
async def callback_docs_category(callback: CallbackQuery, user: User):
    """Показать документы в категории"""
    category_slug = callback.data.split(":")[1]
    
    async with async_session() as session:
        service = DocumentService(session)
        documents = await service.get_all_documents(category=category_slug)
    
    if not documents:
        await callback.answer("В этой категории пока нет документов", show_alert=True)
        return
    
    cat_name = DocumentService.CATEGORIES.get(category_slug, "Документы")
    
    await callback.message.edit_text(
        f"📁 <b>{cat_name}</b>\n\n"
        f"Документов: {len(documents)}\n\n"
        f"Выберите документ:",
        reply_markup=InlineKeyboards.documents_list(documents),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("doc_view:"))
async def callback_view_document(callback: CallbackQuery, user: User):
    """Просмотр информации о документе"""
    doc_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        service = DocumentService(session)
        doc = await service.get_document_by_id(doc_id)
        
        if not doc:
            await callback.answer("Документ не найден", show_alert=True)
            return
    
    text = f"📄 <b>{doc.name}</b>\n\n"
    
    if doc.description:
        text += f"{doc.description}\n\n"
    
    if doc.file_type:
        text += f"📁 Формат: {doc.file_type.upper()}\n"
    
    text += f"📥 Скачиваний: {doc.downloads_count}\n"
    text += f"📅 Обновлён: {doc.updated_at.strftime('%d.%m.%Y')}"
    
    has_file = bool(doc.file_id or doc.file_url)
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboards.document_actions(doc.id, has_file),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("doc_download:"))
async def callback_download_document(callback: CallbackQuery, user: User, bot: Bot):
    """Скачивание документа"""
    doc_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        service = DocumentService(session)
        doc = await service.get_document_by_id(doc_id)
        
        if not doc:
            await callback.answer("Документ не найден", show_alert=True)
            return
        
        # Увеличиваем счётчик скачиваний
        await service.increment_downloads(doc_id)
        
        # Логируем
        analytics = AnalyticsService(session)
        await analytics.log_request(
            user_id=user.id,
            request_type="document_download",
            request_text=doc.name,
            category=doc.category,
            response_type="success"
        )
        await session.commit()
    
    try:
        if doc.file_id:
            # Файл уже загружен в Telegram
            await bot.send_document(
                chat_id=callback.message.chat.id,
                document=doc.file_id,
                caption=f"📄 {doc.name}"
            )
        elif doc.file_url:
            # Внешняя ссылка
            await callback.message.answer(
                f"📄 <b>{doc.name}</b>\n\n"
                f"🔗 <a href=\"{doc.file_url}\">Скачать документ</a>",
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        else:
            await callback.answer("Файл временно недоступен", show_alert=True)
            return
        
        await callback.answer("📥 Документ отправлен")
        
    except Exception as e:
        await callback.answer(f"Ошибка при отправке: {str(e)}", show_alert=True)


# === Поиск документов ===

@router.callback_query(F.data == "docs_search")
async def start_document_search(callback: CallbackQuery, state: FSMContext):
    """Начало поиска документа"""
    await state.set_state(DocumentStates.searching)
    
    await callback.message.edit_text(
        "🔍 <b>Поиск документа</b>\n\n"
        "Введите название или ключевые слова:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(DocumentStates.searching)
async def process_document_search(message: Message, user: User, state: FSMContext):
    """Обработка поиска документа"""
    query = message.text.strip()
    
    if len(query) < 2:
        await message.answer("Введите минимум 2 символа")
        return
    
    await state.clear()
    
    async with async_session() as session:
        service = DocumentService(session)
        results = await service.search(query, limit=10)
        
        # Логируем
        analytics = AnalyticsService(session)
        await analytics.log_request(
            user_id=user.id,
            request_type="document_search",
            request_text=query,
            response_type="found" if results else "not_found"
        )
        await session.commit()
    
    if not results:
        await message.answer(
            f"🔍 По запросу «{query}» ничего не найдено.\n\n"
            "Попробуйте другие ключевые слова или посмотрите категории.",
            reply_markup=InlineKeyboards.documents_categories(
                await get_categories_with_counts()
            ),
            parse_mode="HTML"
        )
        return
    
    # Формируем список найденных документов
    documents = [doc for doc, score in results]
    
    await message.answer(
        f"🔍 <b>Результаты поиска:</b> «{query}»\n\n"
        f"Найдено: {len(documents)} документ(ов)",
        reply_markup=InlineKeyboards.documents_list(documents),
        parse_mode="HTML"
    )


async def get_categories_with_counts():
    """Вспомогательная функция для получения категорий"""
    async with async_session() as session:
        service = DocumentService(session)
        return await service.get_categories_with_counts()

