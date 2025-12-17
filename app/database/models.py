"""
Модели базы данных
"""
import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class UserRole(enum.Enum):
    """Роли пользователей"""
    STUDENT = "student"           # Студент
    TEACHER = "teacher"           # Преподаватель
    MODERATOR = "moderator"       # Модератор (деканат)
    ADMIN = "admin"               # Администратор
    ANONYMOUS = "anonymous"       # Анонимный пользователь


class TicketStatus(enum.Enum):
    """Статусы тикетов"""
    OPEN = "open"                 # Открыт
    IN_PROGRESS = "in_progress"   # В работе
    WAITING = "waiting"           # Ожидает ответа
    RESOLVED = "resolved"         # Решён
    CLOSED = "closed"             # Закрыт


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Дополнительные данные
    full_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # ФИО полное
    course: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)          # Курс
    group_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)   # Группа
    student_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)   # Номер студ. билета
    faculty: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)     # Факультет
    
    # Роль и статус
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), 
        default=UserRole.STUDENT,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Настройки
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="ru", nullable=False)
    
    # Онбординг
    is_onboarded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tips_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    last_activity: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Отношения
    tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket", 
        back_populates="user",
        foreign_keys="Ticket.user_id"
    )
    logs: Mapped[List["RequestLog"]] = relationship("RequestLog", back_populates="user")
    feedbacks: Mapped[List["Feedback"]] = relationship("Feedback", back_populates="user")
    
    __table_args__ = (
        Index("ix_users_role", "role"),
        Index("ix_users_group", "group_name"),
    )
    
    def __repr__(self):
        return f"<User {self.telegram_id} ({self.role.value})>"
    
    @property
    def display_name(self) -> str:
        """Отображаемое имя пользователя"""
        if self.full_name:
            return self.full_name
        if self.first_name:
            name = self.first_name
            if self.last_name:
                name += f" {self.last_name}"
            return name
        if self.username:
            return f"@{self.username}"
        return f"User {self.telegram_id}"


class FAQCategory(Base):
    """Категория FAQ"""
    __tablename__ = "faq_categories"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Emoji или иконка
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Отношения
    items: Mapped[List["FAQItem"]] = relationship("FAQItem", back_populates="category")
    
    def __repr__(self):
        return f"<FAQCategory {self.slug}>"


class FAQItem(Base):
    """Вопрос-ответ FAQ"""
    __tablename__ = "faq_items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("faq_categories.id", ondelete="CASCADE"),
        nullable=False
    )
    
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Ключевые слова через запятую
    
    # Ссылки и кнопки (JSON-like текст)
    links: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: [{"text": "...", "url": "..."}]
    
    # Статистика
    views_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    helpful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    not_helpful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Отношения
    category: Mapped["FAQCategory"] = relationship("FAQCategory", back_populates="items")
    
    __table_args__ = (
        Index("ix_faq_items_category", "category_id"),
        Index("ix_faq_items_keywords", "keywords"),
    )
    
    def __repr__(self):
        return f"<FAQItem {self.id}: {self.question[:50]}...>"


class Ticket(Base):
    """Тикет (обращение)"""
    __tablename__ = "tickets"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    
    user_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    assigned_to_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus), 
        default=TicketStatus.OPEN,
        nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1-низкий, 2-средний, 3-высокий
    
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Отношения
    user: Mapped["User"] = relationship(
        "User", 
        back_populates="tickets",
        foreign_keys=[user_id]
    )
    assigned_to: Mapped[Optional["User"]] = relationship(
        "User", 
        foreign_keys=[assigned_to_id]
    )
    messages: Mapped[List["TicketMessage"]] = relationship("TicketMessage", back_populates="ticket")
    
    __table_args__ = (
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_user", "user_id"),
        Index("ix_tickets_assigned", "assigned_to_id"),
    )
    
    def __repr__(self):
        return f"<Ticket {self.ticket_number}: {self.status.value}>"


class TicketMessage(Base):
    """Сообщение в тикете"""
    __tablename__ = "ticket_messages"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_from_staff: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Внутренняя заметка
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    
    # Отношения
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="messages")
    user: Mapped["User"] = relationship("User")
    
    def __repr__(self):
        return f"<TicketMessage {self.id} for Ticket {self.ticket_id}>"


class Document(Base):
    """Документ/шаблон"""
    __tablename__ = "documents"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Файл
    file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Telegram file_id
    file_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # Внешняя ссылка
    file_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # pdf, docx, etc.
    
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    downloads_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    __table_args__ = (
        Index("ix_documents_category", "category"),
    )
    
    def __repr__(self):
        return f"<Document {self.id}: {self.name}>"


class Schedule(Base):
    """Расписание / События"""
    __tablename__ = "schedules"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # lesson, exam, event, holiday
    
    group_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    faculty: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    course: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    teacher: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_rescheduled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    
    __table_args__ = (
        Index("ix_schedules_group", "group_name"),
        Index("ix_schedules_date", "start_time"),
    )
    
    def __repr__(self):
        return f"<Schedule {self.id}: {self.title}>"


class RequestLog(Base):
    """Лог обращений"""
    __tablename__ = "request_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)  # faq, ticket, document, schedule
    request_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Результат
    response_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # success, not_found, error
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    # Отношения
    user: Mapped[Optional["User"]] = relationship("User", back_populates="logs")
    
    __table_args__ = (
        Index("ix_request_logs_type", "request_type"),
        Index("ix_request_logs_category", "category"),
    )
    
    def __repr__(self):
        return f"<RequestLog {self.id}: {self.request_type}>"


class Feedback(Base):
    """Обратная связь"""
    __tablename__ = "feedbacks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    feedback_type: Mapped[str] = mapped_column(String(50), nullable=False)  # faq_rating, suggestion, complaint
    
    # Для оценки FAQ
    faq_item_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    
    # Текст
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    
    # Отношения
    user: Mapped[Optional["User"]] = relationship("User", back_populates="feedbacks")
    
    def __repr__(self):
        return f"<Feedback {self.id}: {self.feedback_type}>"


class Notification(Base):
    """Уведомление"""
    __tablename__ = "notifications"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Таргетинг
    target_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Для конкретной роли
    target_group: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Для группы
    target_course: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Для курса
    target_faculty: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Для факультета
    
    # Статус
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    
    def __repr__(self):
        return f"<Notification {self.id}: {self.title}>"


class UserFavorite(Base):
    """Избранные FAQ пользователя"""
    __tablename__ = "user_favorites"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    faq_item_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("faq_items.id", ondelete="CASCADE"),
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    
    __table_args__ = (
        Index("ix_user_favorites_user", "user_id"),
        Index("ix_user_favorites_unique", "user_id", "faq_item_id", unique=True),
    )
    
    def __repr__(self):
        return f"<UserFavorite user={self.user_id} faq={self.faq_item_id}>"


class BroadcastTemplate(Base):
    """Шаблон рассылки"""
    __tablename__ = "broadcast_templates"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Категория шаблона
    category: Mapped[str] = mapped_column(String(100), default="general", nullable=False)
    
    # Использование
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    def __repr__(self):
        return f"<BroadcastTemplate {self.id}: {self.name}>"

