"""
Форматтеры для вывода данных
"""
from datetime import datetime, timedelta
from typing import Optional


class Formatters:
    """Класс с методами форматирования"""
    
    @staticmethod
    def format_datetime(dt: datetime, include_time: bool = True) -> str:
        """Форматирование даты и времени"""
        if include_time:
            return dt.strftime("%d.%m.%Y %H:%M")
        return dt.strftime("%d.%m.%Y")
    
    @staticmethod
    def format_date_relative(dt: datetime) -> str:
        """Относительное форматирование даты"""
        now = datetime.utcnow()
        diff = now - dt
        
        if diff.days == 0:
            if diff.seconds < 60:
                return "только что"
            elif diff.seconds < 3600:
                minutes = diff.seconds // 60
                return f"{minutes} мин. назад"
            else:
                hours = diff.seconds // 3600
                return f"{hours} ч. назад"
        elif diff.days == 1:
            return "вчера"
        elif diff.days < 7:
            return f"{diff.days} дн. назад"
        else:
            return dt.strftime("%d.%m.%Y")
    
    @staticmethod
    def format_number(num: int) -> str:
        """Форматирование больших чисел"""
        if num >= 1000000:
            return f"{num / 1000000:.1f}M"
        elif num >= 1000:
            return f"{num / 1000:.1f}K"
        return str(num)
    
    @staticmethod
    def format_duration(seconds: int) -> str:
        """Форматирование длительности"""
        if seconds < 60:
            return f"{seconds} сек."
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} мин."
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} ч."
        else:
            days = seconds // 86400
            return f"{days} дн."
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Форматирование размера файла"""
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} ТБ"
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """Обрезка текста с добавлением многоточия"""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def format_phone(phone: str) -> str:
        """Форматирование телефона"""
        import re
        digits = re.sub(r'\D', '', phone)
        
        if len(digits) == 11 and digits.startswith('7'):
            return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
        elif len(digits) == 10:
            return f"+7 ({digits[0:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
        
        return phone
    
    @staticmethod
    def format_weekday(dt: datetime, short: bool = False) -> str:
        """Форматирование дня недели"""
        days_full = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        days_short = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        
        if short:
            return days_short[dt.weekday()]
        return days_full[dt.weekday()]
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """Экранирование специальных символов Markdown"""
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
    @staticmethod
    def format_list(items: list, bullet: str = "•") -> str:
        """Форматирование списка"""
        return "\n".join(f"{bullet} {item}" for item in items)
    
    @staticmethod
    def format_progress_bar(current: int, total: int, length: int = 10) -> str:
        """Форматирование прогресс-бара"""
        if total == 0:
            return "░" * length
        
        filled = int(length * current / total)
        empty = length - filled
        
        return "█" * filled + "░" * empty

