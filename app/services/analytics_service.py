"""
Сервис аналитики и логирования
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import io

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import RequestLog, User, Feedback


class AnalyticsService:
    """Сервис для аналитики и отчётов"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def log_request(
        self,
        user_id: Optional[int],
        request_type: str,
        request_text: Optional[str] = None,
        category: Optional[str] = None,
        response_type: Optional[str] = None,
        response_time_ms: Optional[int] = None
    ) -> RequestLog:
        """Логирование запроса"""
        log = RequestLog(
            user_id=user_id,
            request_type=request_type,
            request_text=request_text,
            category=category,
            response_type=response_type,
            response_time_ms=response_time_ms
        )
        self.session.add(log)
        await self.session.flush()
        return log
    
    async def get_requests_stats(
        self,
        days: int = 30
    ) -> Dict:
        """Статистика запросов за период"""
        since = datetime.utcnow() - timedelta(days=days)
        
        # Общее количество
        total = await self.session.execute(
            select(func.count(RequestLog.id))
            .where(RequestLog.created_at >= since)
        )
        
        # По типам
        by_type = await self.session.execute(
            select(RequestLog.request_type, func.count(RequestLog.id))
            .where(RequestLog.created_at >= since)
            .group_by(RequestLog.request_type)
        )
        
        # По категориям
        by_category = await self.session.execute(
            select(RequestLog.category, func.count(RequestLog.id))
            .where(
                and_(
                    RequestLog.created_at >= since,
                    RequestLog.category != None
                )
            )
            .group_by(RequestLog.category)
            .order_by(func.count(RequestLog.id).desc())
            .limit(10)
        )
        
        # Среднее время ответа
        avg_response = await self.session.execute(
            select(func.avg(RequestLog.response_time_ms))
            .where(
                and_(
                    RequestLog.created_at >= since,
                    RequestLog.response_time_ms != None
                )
            )
        )
        
        # По дням
        daily_stats = await self.session.execute(
            select(
                func.date(RequestLog.created_at).label("date"),
                func.count(RequestLog.id).label("count")
            )
            .where(RequestLog.created_at >= since)
            .group_by(func.date(RequestLog.created_at))
            .order_by(func.date(RequestLog.created_at))
        )
        
        return {
            "total": total.scalar() or 0,
            "by_type": dict(by_type.all()),
            "by_category": dict(by_category.all()),
            "avg_response_ms": round(avg_response.scalar() or 0, 2),
            "daily": [{"date": str(row.date), "count": row.count} for row in daily_stats.all()]
        }
    
    async def get_popular_queries(self, limit: int = 20) -> List[tuple]:
        """Популярные запросы"""
        result = await self.session.execute(
            select(RequestLog.request_text, func.count(RequestLog.id).label("count"))
            .where(RequestLog.request_text != None)
            .group_by(RequestLog.request_text)
            .order_by(func.count(RequestLog.id).desc())
            .limit(limit)
        )
        return result.all()
    
    async def get_user_activity(
        self,
        user_id: int,
        days: int = 30
    ) -> Dict:
        """Активность конкретного пользователя"""
        since = datetime.utcnow() - timedelta(days=days)
        
        # Количество запросов
        total = await self.session.execute(
            select(func.count(RequestLog.id))
            .where(
                and_(
                    RequestLog.user_id == user_id,
                    RequestLog.created_at >= since
                )
            )
        )
        
        # По типам
        by_type = await self.session.execute(
            select(RequestLog.request_type, func.count(RequestLog.id))
            .where(
                and_(
                    RequestLog.user_id == user_id,
                    RequestLog.created_at >= since
                )
            )
            .group_by(RequestLog.request_type)
        )
        
        return {
            "total_requests": total.scalar() or 0,
            "by_type": dict(by_type.all())
        }
    
    async def get_feedback_stats(self, days: int = 30) -> Dict:
        """Статистика обратной связи"""
        since = datetime.utcnow() - timedelta(days=days)
        
        # Средняя оценка
        avg_rating = await self.session.execute(
            select(func.avg(Feedback.rating))
            .where(
                and_(
                    Feedback.created_at >= since,
                    Feedback.rating != None
                )
            )
        )
        
        # Распределение оценок
        rating_dist = await self.session.execute(
            select(Feedback.rating, func.count(Feedback.id))
            .where(
                and_(
                    Feedback.created_at >= since,
                    Feedback.rating != None
                )
            )
            .group_by(Feedback.rating)
        )
        
        # Количество предложений
        suggestions = await self.session.execute(
            select(func.count(Feedback.id))
            .where(
                and_(
                    Feedback.created_at >= since,
                    Feedback.feedback_type == "suggestion"
                )
            )
        )
        
        return {
            "avg_rating": round(avg_rating.scalar() or 0, 2),
            "rating_distribution": dict(rating_dist.all()),
            "suggestions_count": suggestions.scalar() or 0
        }
    
    async def export_stats_excel(self, days: int = 30) -> bytes:
        """Экспорт статистики в Excel"""
        try:
            import pandas as pd
            from openpyxl import Workbook
        except ImportError:
            raise ImportError("pandas и openpyxl необходимы для экспорта")
        
        stats = await self.get_requests_stats(days)
        feedback = await self.get_feedback_stats(days)
        
        # Создаём Excel файл
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Общая статистика
            general_df = pd.DataFrame([{
                "Всего запросов": stats["total"],
                "Среднее время ответа (мс)": stats["avg_response_ms"],
                "Средняя оценка": feedback["avg_rating"],
                "Предложений": feedback["suggestions_count"]
            }])
            general_df.to_excel(writer, sheet_name="Общая", index=False)
            
            # По типам
            if stats["by_type"]:
                types_df = pd.DataFrame(
                    list(stats["by_type"].items()),
                    columns=["Тип", "Количество"]
                )
                types_df.to_excel(writer, sheet_name="По типам", index=False)
            
            # По категориям
            if stats["by_category"]:
                cat_df = pd.DataFrame(
                    list(stats["by_category"].items()),
                    columns=["Категория", "Количество"]
                )
                cat_df.to_excel(writer, sheet_name="По категориям", index=False)
            
            # По дням
            if stats["daily"]:
                daily_df = pd.DataFrame(stats["daily"])
                daily_df.to_excel(writer, sheet_name="По дням", index=False)
        
        output.seek(0)
        return output.read()
    
    async def get_dashboard_summary(self) -> Dict:
        """Сводка для дашборда администратора"""
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        
        # Запросы сегодня
        today_requests = await self.session.execute(
            select(func.count(RequestLog.id))
            .where(func.date(RequestLog.created_at) == today)
        )
        
        # Запросы вчера
        yesterday_requests = await self.session.execute(
            select(func.count(RequestLog.id))
            .where(func.date(RequestLog.created_at) == yesterday)
        )
        
        # Новые пользователи за неделю
        new_users = await self.session.execute(
            select(func.count(User.id))
            .where(func.date(User.created_at) >= week_ago)
        )
        
        # Активные пользователи за неделю
        active_users = await self.session.execute(
            select(func.count(User.id))
            .where(User.last_activity >= datetime.utcnow() - timedelta(days=7))
        )
        
        today_count = today_requests.scalar() or 0
        yesterday_count = yesterday_requests.scalar() or 0
        
        # Процент изменения
        if yesterday_count > 0:
            change_percent = round(((today_count - yesterday_count) / yesterday_count) * 100, 1)
        else:
            change_percent = 100 if today_count > 0 else 0
        
        return {
            "requests_today": today_count,
            "requests_yesterday": yesterday_count,
            "requests_change_percent": change_percent,
            "new_users_week": new_users.scalar() or 0,
            "active_users_week": active_users.scalar() or 0
        }

