"""
Сервис для работы с документами
"""
from typing import List, Optional

from rapidfuzz import fuzz, process
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Document


class DocumentService:
    """Сервис для работы с документами"""
    
    # Категории документов
    CATEGORIES = {
        "applications": "📝 Заявления",
        "certificates": "📄 Справки",
        "practice": "🏢 Практика",
        "vkr": "🎓 ВКР",
        "general": "📋 Общие",
        "instructions": "📑 Инструкции",
        "templates": "📋 Шаблоны",
        "regulations": "📖 Положения",
        "orders": "📜 Приказы"
    }
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_all_documents(
        self, 
        category: Optional[str] = None,
        active_only: bool = True
    ) -> List[Document]:
        """Получение всех документов"""
        query = select(Document).order_by(Document.name)
        
        if category:
            query = query.where(Document.category == category)
        
        if active_only:
            query = query.where(Document.is_active == True)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_document_by_id(self, doc_id: int) -> Optional[Document]:
        """Получение документа по ID"""
        result = await self.session.execute(
            select(Document).where(Document.id == doc_id)
        )
        return result.scalar_one_or_none()
    
    async def create_document(
        self,
        name: str,
        category: str,
        description: Optional[str] = None,
        file_id: Optional[str] = None,
        file_url: Optional[str] = None,
        file_type: Optional[str] = None,
        keywords: Optional[str] = None
    ) -> Document:
        """Создание документа"""
        doc = Document(
            name=name,
            category=category,
            description=description,
            file_id=file_id,
            file_url=file_url,
            file_type=file_type,
            keywords=keywords
        )
        self.session.add(doc)
        await self.session.flush()
        return doc
    
    async def update_document(self, doc_id: int, **kwargs) -> Optional[Document]:
        """Обновление документа"""
        result = await self.session.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        
        if doc:
            for key, value in kwargs.items():
                if hasattr(doc, key):
                    setattr(doc, key, value)
            await self.session.flush()
        
        return doc
    
    async def delete_document(self, doc_id: int) -> bool:
        """Удаление документа"""
        result = await self.session.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        
        if doc:
            await self.session.delete(doc)
            return True
        return False
    
    async def increment_downloads(self, doc_id: int):
        """Увеличение счётчика скачиваний"""
        await self.session.execute(
            update(Document)
            .where(Document.id == doc_id)
            .values(downloads_count=Document.downloads_count + 1)
        )
    
    async def search(
        self, 
        query: str, 
        limit: int = 10,
        threshold: int = 50
    ) -> List[tuple]:
        """Поиск документов"""
        result = await self.session.execute(
            select(Document).where(Document.is_active == True)
        )
        documents = result.scalars().all()
        
        if not documents:
            return []
        
        # Создаём словарь для поиска
        search_data = {}
        for doc in documents:
            search_text = doc.name
            if doc.description:
                search_text += " " + doc.description
            if doc.keywords:
                search_text += " " + doc.keywords
            search_data[doc.id] = (doc, search_text)
        
        texts = {doc_id: data[1] for doc_id, data in search_data.items()}
        
        matches = process.extract(
            query,
            texts,
            scorer=fuzz.token_set_ratio,
            limit=limit * 2
        )
        
        results = []
        for text, score, doc_id in matches:
            if score >= threshold:
                doc = search_data[doc_id][0]
                results.append((doc, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    async def get_categories_with_counts(self) -> dict:
        """Получение категорий с количеством документов"""
        result = {}
        
        for slug, name in self.CATEGORIES.items():
            count = await self.session.execute(
                select(func.count(Document.id))
                .where(Document.category == slug, Document.is_active == True)
            )
            result[slug] = {
                "name": name,
                "count": count.scalar() or 0
            }
        
        return result
    
    async def get_popular_documents(self, limit: int = 5) -> List[Document]:
        """Получение популярных документов"""
        result = await self.session.execute(
            select(Document)
            .where(Document.is_active == True)
            .order_by(Document.downloads_count.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_stats(self) -> dict:
        """Статистика документов"""
        total = await self.session.execute(
            select(func.count(Document.id))
            .where(Document.is_active == True)
        )
        
        total_downloads = await self.session.execute(
            select(func.sum(Document.downloads_count))
        )
        
        return {
            "total": total.scalar() or 0,
            "total_downloads": total_downloads.scalar() or 0
        }

