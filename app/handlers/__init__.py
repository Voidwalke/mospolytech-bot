"""
Обработчики событий
"""
from aiogram import Router

from app.handlers.start import router as start_router
from app.handlers.faq import router as faq_router
from app.handlers.tickets import router as tickets_router
from app.handlers.profile import router as profile_router
from app.handlers.documents import router as documents_router
from app.handlers.schedule import router as schedule_router
from app.handlers.admin import router as admin_router
from app.handlers.feedback import router as feedback_router
from app.handlers.info import router as info_router


def setup_routers() -> Router:
    """Настройка всех роутеров"""
    main_router = Router()
    
    # Регистрируем роутеры в порядке приоритета
    # ВАЖНО: FAQ должен быть последним, т.к. имеет catch-all хендлер для поиска
    main_router.include_router(admin_router)     # Админка первая
    main_router.include_router(start_router)     # Старт и базовые команды
    main_router.include_router(tickets_router)   # Тикеты
    main_router.include_router(profile_router)   # Профиль
    main_router.include_router(documents_router) # Документы
    main_router.include_router(schedule_router)  # Расписание
    main_router.include_router(info_router)      # Информация, ссылки, факты
    main_router.include_router(feedback_router)  # Обратная связь
    main_router.include_router(faq_router)       # FAQ (последний - имеет catch-all)
    
    return main_router

