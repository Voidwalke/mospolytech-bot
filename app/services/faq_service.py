"""
Сервис для работы с FAQ
"""
import json
from typing import List, Optional, Tuple

from rapidfuzz import fuzz, process
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import FAQCategory, FAQItem, RequestLog, UserFavorite


class FAQService:
    """Сервис для работы с базой FAQ"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # === Категории ===
    
    async def get_all_categories(self, active_only: bool = True) -> List[FAQCategory]:
        """Получение всех категорий"""
        query = select(FAQCategory).order_by(FAQCategory.order, FAQCategory.name)
        
        if active_only:
            query = query.where(FAQCategory.is_active == True)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_category_by_slug(self, slug: str) -> Optional[FAQCategory]:
        """Получение категории по slug"""
        result = await self.session.execute(
            select(FAQCategory)
            .where(FAQCategory.slug == slug)
            .options(selectinload(FAQCategory.items))
        )
        return result.scalar_one_or_none()
    
    async def get_category_by_id(self, category_id: int) -> Optional[FAQCategory]:
        """Получение категории по ID"""
        result = await self.session.execute(
            select(FAQCategory).where(FAQCategory.id == category_id)
        )
        return result.scalar_one_or_none()
    
    async def toggle_category(self, category_id: int, is_active: bool) -> bool:
        """Включение/выключение категории"""
        await self.session.execute(
            update(FAQCategory)
            .where(FAQCategory.id == category_id)
            .values(is_active=is_active)
        )
        return True
    
    async def create_category(
        self,
        name: str,
        slug: str,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        order: int = 0
    ) -> FAQCategory:
        """Создание новой категории"""
        category = FAQCategory(
            name=name,
            slug=slug,
            description=description,
            icon=icon,
            order=order
        )
        self.session.add(category)
        await self.session.flush()
        return category
    
    async def update_category(
        self,
        category_id: int,
        **kwargs
    ) -> Optional[FAQCategory]:
        """Обновление категории"""
        result = await self.session.execute(
            select(FAQCategory).where(FAQCategory.id == category_id)
        )
        category = result.scalar_one_or_none()
        
        if category:
            for key, value in kwargs.items():
                if hasattr(category, key):
                    setattr(category, key, value)
            await self.session.flush()
        
        return category
    
    async def delete_category(self, category_id: int) -> bool:
        """Удаление категории"""
        result = await self.session.execute(
            select(FAQCategory).where(FAQCategory.id == category_id)
        )
        category = result.scalar_one_or_none()
        
        if category:
            await self.session.delete(category)
            return True
        return False
    
    # === FAQ Items ===
    
    async def get_items_by_category(
        self, 
        category_id: int, 
        active_only: bool = True
    ) -> List[FAQItem]:
        """Получение вопросов по категории"""
        query = (
            select(FAQItem)
            .where(FAQItem.category_id == category_id)
            .order_by(FAQItem.is_pinned.desc(), FAQItem.order, FAQItem.id)
        )
        
        if active_only:
            query = query.where(FAQItem.is_active == True)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_item_by_id(self, item_id: int) -> Optional[FAQItem]:
        """Получение вопроса по ID"""
        result = await self.session.execute(
            select(FAQItem)
            .where(FAQItem.id == item_id)
            .options(selectinload(FAQItem.category))
        )
        return result.scalar_one_or_none()
    
    async def create_item(
        self,
        category_id: int,
        question: str,
        answer: str,
        keywords: Optional[str] = None,
        links: Optional[List[dict]] = None,
        order: int = 0
    ) -> FAQItem:
        """Создание нового вопроса"""
        item = FAQItem(
            category_id=category_id,
            question=question,
            answer=answer,
            keywords=keywords,
            links=json.dumps(links) if links else None,
            order=order
        )
        self.session.add(item)
        await self.session.flush()
        return item
    
    async def update_item(self, item_id: int, **kwargs) -> Optional[FAQItem]:
        """Обновление вопроса"""
        result = await self.session.execute(
            select(FAQItem).where(FAQItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if item:
            if 'links' in kwargs and isinstance(kwargs['links'], list):
                kwargs['links'] = json.dumps(kwargs['links'])
            
            for key, value in kwargs.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            await self.session.flush()
        
        return item
    
    async def delete_item(self, item_id: int) -> bool:
        """Удаление вопроса"""
        result = await self.session.execute(
            select(FAQItem).where(FAQItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if item:
            await self.session.delete(item)
            return True
        return False
    
    async def increment_view(self, item_id: int):
        """Увеличение счётчика просмотров"""
        await self.session.execute(
            update(FAQItem)
            .where(FAQItem.id == item_id)
            .values(views_count=FAQItem.views_count + 1)
        )
    
    async def rate_item(self, item_id: int, is_helpful: bool):
        """Оценка полезности ответа"""
        if is_helpful:
            await self.session.execute(
                update(FAQItem)
                .where(FAQItem.id == item_id)
                .values(helpful_count=FAQItem.helpful_count + 1)
            )
        else:
            await self.session.execute(
                update(FAQItem)
                .where(FAQItem.id == item_id)
                .values(not_helpful_count=FAQItem.not_helpful_count + 1)
            )
    
    # === Поиск ===
    
    async def search(
        self, 
        query: str, 
        limit: int = 5,
        threshold: int = 50
    ) -> List[Tuple[FAQItem, int]]:
        """
        Поиск по FAQ с использованием fuzzy matching.
        Возвращает список (item, score) отсортированный по релевантности.
        """
        # Получаем все активные вопросы
        result = await self.session.execute(
            select(FAQItem)
            .where(FAQItem.is_active == True)
            .options(selectinload(FAQItem.category))
        )
        items = result.scalars().all()
        
        if not items:
            return []
        
        # Создаём словарь для поиска
        search_data = {}
        for item in items:
            # Комбинируем вопрос и ключевые слова для поиска
            search_text = item.question
            if item.keywords:
                search_text += " " + item.keywords
            search_data[item.id] = (item, search_text)
        
        # Используем rapidfuzz для поиска
        texts = {item_id: data[1] for item_id, data in search_data.items()}
        
        matches = process.extract(
            query,
            texts,
            scorer=fuzz.token_set_ratio,
            limit=limit * 2  # Берём больше, потом отфильтруем
        )
        
        results = []
        for text, score, item_id in matches:
            if score >= threshold:
                item = search_data[item_id][0]
                results.append((item, score))
        
        # Сортируем по score и берём limit
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    async def get_popular_items(self, limit: int = 10) -> List[FAQItem]:
        """Получение популярных вопросов"""
        result = await self.session.execute(
            select(FAQItem)
            .where(FAQItem.is_active == True)
            .order_by(FAQItem.views_count.desc())
            .limit(limit)
            .options(selectinload(FAQItem.category))
        )
        return result.scalars().all()
    
    async def get_pinned_items(self) -> List[FAQItem]:
        """Получение закреплённых вопросов"""
        result = await self.session.execute(
            select(FAQItem)
            .where(FAQItem.is_active == True, FAQItem.is_pinned == True)
            .order_by(FAQItem.order)
            .options(selectinload(FAQItem.category))
        )
        return result.scalars().all()
    
    # === Статистика ===
    
    async def get_stats(self) -> dict:
        """Получение статистики FAQ"""
        # Количество категорий
        cat_count = await self.session.execute(
            select(func.count(FAQCategory.id))
            .where(FAQCategory.is_active == True)
        )
        
        # Количество вопросов
        item_count = await self.session.execute(
            select(func.count(FAQItem.id))
            .where(FAQItem.is_active == True)
        )
        
        # Общее количество просмотров
        total_views = await self.session.execute(
            select(func.sum(FAQItem.views_count))
        )
        
        # Общее количество оценок
        total_helpful = await self.session.execute(
            select(func.sum(FAQItem.helpful_count))
        )
        total_not_helpful = await self.session.execute(
            select(func.sum(FAQItem.not_helpful_count))
        )
        
        return {
            "categories_count": cat_count.scalar() or 0,
            "items_count": item_count.scalar() or 0,
            "total_views": total_views.scalar() or 0,
            "helpful_count": total_helpful.scalar() or 0,
            "not_helpful_count": total_not_helpful.scalar() or 0
        }
    
    # === Избранное ===
    
    async def add_to_favorites(self, user_id: int, faq_item_id: int) -> bool:
        """Добавление в избранное"""
        # Проверяем, есть ли уже в избранном
        existing = await self.session.execute(
            select(UserFavorite)
            .where(UserFavorite.user_id == user_id, UserFavorite.faq_item_id == faq_item_id)
        )
        if existing.scalar_one_or_none():
            return False  # Уже в избранном
        
        favorite = UserFavorite(user_id=user_id, faq_item_id=faq_item_id)
        self.session.add(favorite)
        await self.session.flush()
        return True
    
    async def remove_from_favorites(self, user_id: int, faq_item_id: int) -> bool:
        """Удаление из избранного"""
        result = await self.session.execute(
            select(UserFavorite)
            .where(UserFavorite.user_id == user_id, UserFavorite.faq_item_id == faq_item_id)
        )
        favorite = result.scalar_one_or_none()
        
        if favorite:
            await self.session.delete(favorite)
            return True
        return False
    
    async def is_favorite(self, user_id: int, faq_item_id: int) -> bool:
        """Проверка, есть ли в избранном"""
        result = await self.session.execute(
            select(UserFavorite)
            .where(UserFavorite.user_id == user_id, UserFavorite.faq_item_id == faq_item_id)
        )
        return result.scalar_one_or_none() is not None
    
    async def get_user_favorites(self, user_id: int) -> List[FAQItem]:
        """Получение избранных FAQ пользователя"""
        result = await self.session.execute(
            select(FAQItem)
            .join(UserFavorite, FAQItem.id == UserFavorite.faq_item_id)
            .where(UserFavorite.user_id == user_id, FAQItem.is_active == True)
            .options(selectinload(FAQItem.category))
            .order_by(UserFavorite.created_at.desc())
        )
        return result.scalars().all()

