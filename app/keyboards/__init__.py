"""
Клавиатуры
"""
from app.keyboards.main import MainKeyboards
from app.keyboards.faq import FAQKeyboards
from app.keyboards.tickets import TicketKeyboards
from app.keyboards.admin import AdminKeyboards
from app.keyboards.inline import InlineKeyboards

__all__ = [
    "MainKeyboards",
    "FAQKeyboards", 
    "TicketKeyboards",
    "AdminKeyboards",
    "InlineKeyboards"
]

