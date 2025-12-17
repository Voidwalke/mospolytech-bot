"""
Хендлеры обратной связи
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.database import User, Feedback, async_session
from app.keyboards.inline import InlineKeyboards
from app.keyboards.main import MainKeyboards


router = Router(name="feedback")


class FeedbackStates(StatesGroup):
    """Состояния обратной связи"""
    entering_feedback = State()
    entering_suggestion = State()


@router.message(Command("feedback"))
async def cmd_feedback(message: Message, user: User):
    """Команда обратной связи"""
    await message.answer(
        "💬 <b>Обратная связь</b>\n\n"
        "Мы ценим ваше мнение! Выберите, что хотите сделать:",
        reply_markup=InlineKeyboards.feedback_rating(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("rate:"))
async def callback_rate(callback: CallbackQuery, user: User, state: FSMContext):
    """Обработка оценки"""
    action = callback.data.split(":")[1]
    
    if action == "feedback":
        await state.set_state(FeedbackStates.entering_feedback)
        await callback.message.edit_text(
            "💬 <b>Оставьте ваш отзыв</b>\n\n"
            "Напишите, что вам понравилось или не понравилось в работе бота:",
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Это оценка от 1 до 5
    rating = int(action)
    
    async with async_session() as session:
        feedback = Feedback(
            user_id=user.id,
            feedback_type="bot_rating",
            rating=rating
        )
        session.add(feedback)
        await session.commit()
    
    stars = "⭐" * rating
    
    if rating >= 4:
        response = f"Спасибо за оценку {stars}! Мы рады, что вам нравится!"
    elif rating >= 2:
        response = f"Спасибо за оценку {stars}. Мы постараемся стать лучше!"
    else:
        response = f"Спасибо за честную оценку {stars}. Расскажите, что мы можем улучшить?"
        await state.set_state(FeedbackStates.entering_feedback)
    
    await callback.answer(response, show_alert=True)
    
    if rating < 2:
        await callback.message.edit_text(
            "💬 <b>Расскажите подробнее</b>\n\n"
            "Что мы можем улучшить?",
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"✅ <b>Спасибо за вашу оценку!</b>\n\n"
            f"Ваша оценка: {stars}\n\n"
            "Если у вас есть предложения по улучшению, используйте /suggestion",
            parse_mode="HTML"
        )


@router.message(FeedbackStates.entering_feedback)
async def process_feedback(message: Message, user: User, state: FSMContext):
    """Обработка текста отзыва"""
    feedback_text = message.text.strip()
    
    if len(feedback_text) < 5:
        await message.answer("Отзыв слишком короткий. Напишите подробнее.")
        return
    
    async with async_session() as session:
        feedback = Feedback(
            user_id=user.id,
            feedback_type="feedback",
            message=feedback_text
        )
        session.add(feedback)
        await session.commit()
    
    await state.clear()
    
    await message.answer(
        "✅ <b>Спасибо за ваш отзыв!</b>\n\n"
        "Мы обязательно его изучим и постараемся стать лучше.",
        reply_markup=MainKeyboards.main_menu(user.role),
        parse_mode="HTML"
    )


@router.message(Command("suggestion"))
async def cmd_suggestion(message: Message, state: FSMContext):
    """Команда предложения"""
    await state.set_state(FeedbackStates.entering_suggestion)
    
    await message.answer(
        "💡 <b>Предложение по улучшению</b>\n\n"
        "Опишите вашу идею или предложение:\n\n"
        "<i>Мы читаем все предложения и стараемся реализовать лучшие идеи!</i>",
        reply_markup=MainKeyboards.cancel(),
        parse_mode="HTML"
    )


@router.message(FeedbackStates.entering_suggestion)
async def process_suggestion(message: Message, user: User, state: FSMContext):
    """Обработка предложения"""
    suggestion_text = message.text.strip()
    
    if len(suggestion_text) < 10:
        await message.answer("Опишите вашу идею подробнее (минимум 10 символов)")
        return
    
    async with async_session() as session:
        feedback = Feedback(
            user_id=user.id,
            feedback_type="suggestion",
            message=suggestion_text
        )
        session.add(feedback)
        await session.commit()
    
    await state.clear()
    
    await message.answer(
        "✅ <b>Спасибо за предложение!</b>\n\n"
        "Ваша идея сохранена. Если она будет реализована, "
        "мы обязательно вас уведомим!",
        reply_markup=MainKeyboards.main_menu(user.role),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "close")
async def callback_close(callback: CallbackQuery):
    """Закрытие сообщения"""
    await callback.message.delete()
    await callback.answer()

