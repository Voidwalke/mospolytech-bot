"""
Валидаторы данных
"""
import re
from typing import Optional, Tuple


class Validators:
    """Класс с методами валидации"""
    
    @staticmethod
    def validate_full_name(name: str) -> Tuple[bool, Optional[str]]:
        """
        Валидация ФИО
        Returns: (is_valid, error_message)
        """
        name = name.strip()
        
        if len(name) < 5:
            return False, "ФИО слишком короткое (минимум 5 символов)"
        
        if len(name) > 200:
            return False, "ФИО слишком длинное (максимум 200 символов)"
        
        # Проверяем, что содержит только допустимые символы
        if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s\-\.]+$', name):
            return False, "ФИО должно содержать только буквы, пробелы и дефисы"
        
        # Проверяем, что есть минимум 2 слова (имя и фамилия)
        words = name.split()
        if len(words) < 2:
            return False, "Введите как минимум имя и фамилию"
        
        return True, None
    
    @staticmethod
    def validate_group(group: str) -> Tuple[bool, Optional[str]]:
        """
        Валидация номера группы
        Форматы: 201-361, 191-721, ИБ20-01
        """
        group = group.strip().upper()
        
        # Формат xxx-xxx (например 201-361)
        if re.match(r'^\d{3}-\d{3}$', group):
            return True, None
        
        # Формат АА00-00 или АААА00-000 (например ИБ20-01)
        if re.match(r'^[А-ЯA-Z]{2,5}\d{2}-\d{2,3}$', group):
            return True, None
        
        return False, "Неверный формат группы. Примеры: 201-361, ИБ20-01"
    
    @staticmethod
    def validate_course(course: int) -> Tuple[bool, Optional[str]]:
        """Валидация курса"""
        if course < 1 or course > 6:
            return False, "Курс должен быть от 1 до 6"
        return True, None
    
    @staticmethod
    def validate_student_id(student_id: str) -> Tuple[bool, Optional[str]]:
        """Валидация номера студенческого билета"""
        student_id = student_id.strip()
        
        if len(student_id) < 4:
            return False, "Номер студенческого слишком короткий"
        
        if len(student_id) > 20:
            return False, "Номер студенческого слишком длинный"
        
        # Должен содержать хотя бы цифры
        if not re.search(r'\d', student_id):
            return False, "Номер студенческого должен содержать цифры"
        
        return True, None
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        """Валидация email"""
        email = email.strip().lower()
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "Неверный формат email"
        
        return True, None
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, Optional[str]]:
        """Валидация телефона"""
        # Убираем все нецифровые символы
        digits = re.sub(r'\D', '', phone)
        
        if len(digits) < 10:
            return False, "Номер телефона слишком короткий"
        
        if len(digits) > 12:
            return False, "Номер телефона слишком длинный"
        
        return True, None
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """Очистка текста от потенциально опасных HTML тегов"""
        # Разрешённые теги для Telegram
        allowed_tags = ['b', 'i', 'u', 's', 'code', 'pre', 'a']
        
        # Удаляем все теги кроме разрешённых
        # Упрощённая версия - для продакшена лучше использовать библиотеку
        import html
        text = html.escape(text)
        
        return text
    
    @staticmethod
    def validate_ticket_subject(subject: str) -> Tuple[bool, Optional[str]]:
        """Валидация темы тикета"""
        subject = subject.strip()
        
        if len(subject) < 5:
            return False, "Тема слишком короткая (минимум 5 символов)"
        
        if len(subject) > 200:
            return False, "Тема слишком длинная (максимум 200 символов)"
        
        return True, None
    
    @staticmethod
    def validate_ticket_description(description: str) -> Tuple[bool, Optional[str]]:
        """Валидация описания тикета"""
        description = description.strip()
        
        if len(description) < 10:
            return False, "Описание слишком короткое (минимум 10 символов)"
        
        if len(description) > 5000:
            return False, "Описание слишком длинное (максимум 5000 символов)"
        
        return True, None

