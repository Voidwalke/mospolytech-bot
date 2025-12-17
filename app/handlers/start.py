"""
Хендлеры старта и базовых команд
"""
import random
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.database import User, async_session
from app.services import UserService
from app.keyboards.main import MainKeyboards
from app.keyboards.faq import FAQKeyboards


router = Router(name="start")


class OnboardingStates(StatesGroup):
    """Состояния онбординга"""
    asking_faculty = State()
    asking_course = State()
    asking_group = State()


# Подсказки для показа после онбординга
WELCOME_TIPS = [
    "💡 Проверяйте расписание каждый вечер — оно может измениться!",
    "💡 За отличную учёбу можно получить ПГАС — до 15 000 ₽/мес!",
    "💡 Справку об обучении можно заказать онлайн через личный кабинет",
    "💡 Подпишитесь на группу факультета в ВК — там публикуют важные объявления",
]


FACULTIES = [
    ("🔧 Машиностроение", "machinery"),
    ("🚗 Транспорт", "transport"),
    ("💻 Информационные технологии", "it"),
    ("📊 Экономика и управление", "economics"),
    ("🎨 Полиграфический институт", "polygraphy"),
    ("🏙️ Урбанистика", "urban"),
    ("⚗️ Химическая технология", "chemistry"),
    ("📐 Другой", "other"),
]


@router.message(CommandStart())
async def cmd_start(message: Message, user: User, state: FSMContext):
    """Команда /start"""
    await state.clear()
    
    # Проверяем, новый ли пользователь (не прошёл онбординг)
    if not user.is_onboarded:
        await start_onboarding(message, user, state)
        return
    
    # Обычное приветствие для существующих пользователей
    tip = random.choice(WELCOME_TIPS)
    
    welcome_text = f"""
🎓 <b>Привет, {user.display_name}!</b>

Рад тебя видеть снова! 👋

{tip}

Выбери раздел в меню или просто напиши свой вопрос 👇
"""
    
    await message.answer(
        welcome_text,
        reply_markup=MainKeyboards.main_menu(user.role),
        parse_mode="HTML"
    )


async def start_onboarding(message: Message, user: User, state: FSMContext):
    """Начало онбординга для нового пользователя"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    welcome_text = f"""
🎓 <b>Добро пожаловать в бот МосПолитеха!</b>

Привет, {user.display_name}! 👋

Я — твой помощник по всем вопросам университета:
• 📅 Расписание и экзамены
• 💰 Стипендии и выплаты
• 📝 Документы и справки
• 🎫 Обращения в деканат

Давай настроим бот под тебя — это займёт 30 секунд!
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Начать настройку", callback_data="onboard_start")],
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="onboard_skip")],
    ])
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "onboard_start")
async def onboard_start(callback: CallbackQuery, state: FSMContext):
    """Начало онбординга"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    # Создаём клавиатуру с факультетами
    buttons = []
    for name, slug in FACULTIES:
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"onboard_fac:{slug}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        "🏛️ <b>Шаг 1/3: Факультет</b>\n\n"
        "На каком факультете ты учишься?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(OnboardingStates.asking_faculty)
    await callback.answer()


@router.callback_query(F.data.startswith("onboard_fac:"), OnboardingStates.asking_faculty)
async def onboard_faculty(callback: CallbackQuery, state: FSMContext):
    """Выбор факультета"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    faculty_slug = callback.data.split(":")[1]
    faculty_name = next((name for name, slug in FACULTIES if slug == faculty_slug), "Другой")
    
    await state.update_data(faculty=faculty_name.replace("🔧 ", "").replace("🚗 ", "").replace("💻 ", "").replace("📊 ", "").replace("🎨 ", "").replace("🏙️ ", "").replace("⚗️ ", "").replace("📐 ", ""))
    
    # Клавиатура с курсами
    buttons = [
        [
            InlineKeyboardButton(text="1️⃣", callback_data="onboard_course:1"),
            InlineKeyboardButton(text="2️⃣", callback_data="onboard_course:2"),
            InlineKeyboardButton(text="3️⃣", callback_data="onboard_course:3"),
        ],
        [
            InlineKeyboardButton(text="4️⃣", callback_data="onboard_course:4"),
            InlineKeyboardButton(text="5️⃣", callback_data="onboard_course:5"),
            InlineKeyboardButton(text="6️⃣", callback_data="onboard_course:6"),
        ],
        [InlineKeyboardButton(text="🎓 Магистратура", callback_data="onboard_course:m")],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        "📚 <b>Шаг 2/3: Курс</b>\n\n"
        "На каком курсе ты учишься?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(OnboardingStates.asking_course)
    await callback.answer()


@router.callback_query(F.data.startswith("onboard_course:"), OnboardingStates.asking_course)
async def onboard_course(callback: CallbackQuery, state: FSMContext):
    """Выбор курса"""
    course = callback.data.split(":")[1]
    
    if course == "m":
        await state.update_data(course=None, is_master=True)
    else:
        await state.update_data(course=int(course), is_master=False)
    
    await callback.message.edit_text(
        "👥 <b>Шаг 3/3: Группа</b>\n\n"
        "Введи номер своей группы\n"
        "<i>Например: 201-361 или ИБ20-01</i>\n\n"
        "Или нажми «Пропустить», если не хочешь указывать",
        parse_mode="HTML"
    )
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="onboard_skip_group")]
    ])
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    
    await state.set_state(OnboardingStates.asking_group)
    await callback.answer()


@router.message(OnboardingStates.asking_group)
async def onboard_group_input(message: Message, user: User, state: FSMContext):
    """Ввод группы"""
    import re
    
    group = message.text.strip().upper()
    
    # Простая валидация
    if len(group) < 3 or len(group) > 20:
        await message.answer(
            "⚠️ Неверный формат группы.\n"
            "Попробуй ещё раз или нажми «Пропустить»"
        )
        return
    
    await state.update_data(group_name=group)
    await finish_onboarding(message, user, state)


@router.callback_query(F.data == "onboard_skip_group")
async def onboard_skip_group(callback: CallbackQuery, user: User, state: FSMContext):
    """Пропуск ввода группы"""
    await finish_onboarding(callback.message, user, state, is_callback=True)
    await callback.answer()


@router.callback_query(F.data == "onboard_skip")
async def onboard_skip(callback: CallbackQuery, user: User, state: FSMContext):
    """Полный пропуск онбординга"""
    # Отмечаем как прошедшего онбординг
    async with async_session() as session:
        service = UserService(session)
        await service.complete_onboarding(user.id)
        await session.commit()
    
    await state.clear()
    
    await callback.message.edit_text(
        "👌 Хорошо! Ты всегда можешь настроить профиль позже в разделе «👤 Профиль»"
    )
    
    await callback.message.answer(
        "🎓 <b>Готово!</b>\n\n"
        "Выбери раздел в меню или просто напиши свой вопрос 👇",
        reply_markup=MainKeyboards.main_menu(user.role),
        parse_mode="HTML"
    )
    await callback.answer()


async def finish_onboarding(message: Message, user: User, state: FSMContext, is_callback: bool = False):
    """Завершение онбординга"""
    data = await state.get_data()
    
    # Сохраняем данные
    async with async_session() as session:
        service = UserService(session)
        
        update_data = {"is_onboarded": True}
        
        if data.get("faculty"):
            update_data["faculty"] = data["faculty"]
        if data.get("course"):
            update_data["course"] = data["course"]
        if data.get("group_name"):
            update_data["group_name"] = data["group_name"]
        
        await service.update_profile(user.id, **update_data)
        await session.commit()
    
    await state.clear()
    
    # Формируем сообщение
    tip = random.choice(WELCOME_TIPS)
    
    complete_text = f"""
🎉 <b>Отлично, настройка завершена!</b>

{tip}

<b>Что дальше?</b>
• ❓ FAQ — найди ответ на свой вопрос
• 📅 Расписание — смотри своё расписание
• 🔗 Ссылки — полезные сервисы университета

Выбери раздел в меню или просто напиши вопрос 👇
"""
    
    if is_callback:
        await message.edit_text("✅ Группа сохранена!")
    
    await message.answer(
        complete_text,
        reply_markup=MainKeyboards.main_menu(user.role),
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: Message, user: User):
    """Команда /help"""
    help_text = """
📚 <b>Справка по боту</b>

<b>Основные команды:</b>
/start - Перезапуск бота
/help - Справка
/faq - База вопросов и ответов
/tickets - Мои обращения
/profile - Мой профиль
/schedule - Расписание
/documents - Документы и шаблоны

<b>Как задать вопрос:</b>
1. Напиши вопрос текстом - я поищу ответ в базе
2. Выбери раздел "❓ FAQ" для просмотра категорий
3. Нажми "✉️ Задать вопрос" для обращения в деканат

<b>Полезные ссылки:</b>
🔗 <a href="https://mospolytech.ru">Сайт МосПолитех</a>
🔗 <a href="https://e.mospolytech.ru">Личный кабинет</a>
🔗 <a href="https://rasp.dmami.ru">Расписание</a>

По вопросам работы бота: @mospolytech_support
"""
    
    await message.answer(help_text, parse_mode="HTML", disable_web_page_preview=True)


@router.message(F.text == "◀️ В главное меню")
@router.message(Command("menu"))
async def cmd_menu(message: Message, user: User, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await message.answer(
        "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
        reply_markup=MainKeyboards.main_menu(user.role),
        parse_mode="HTML"
    )


@router.message(F.text == "❌ Отмена")
async def cancel_action(message: Message, user: User, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await message.answer(
        "❌ Действие отменено",
        reply_markup=MainKeyboards.main_menu(user.role)
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, user: User, state: FSMContext):
    """Команда отмены"""
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer("Нечего отменять 🤷‍♂️")
        return
    
    await state.clear()
    await message.answer(
        "❌ Действие отменено",
        reply_markup=MainKeyboards.main_menu(user.role)
    )


@router.message(Command("id"))
async def cmd_id(message: Message, user: User):
    """Показать ID пользователя"""
    await message.answer(
        f"🆔 <b>Ваши данные:</b>\n\n"
        f"Telegram ID: <code>{user.telegram_id}</code>\n"
        f"ID в системе: <code>{user.id}</code>\n"
        f"Роль: {user.role.value}",
        parse_mode="HTML"
    )

