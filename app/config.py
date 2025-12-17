"""
Конфигурация приложения
"""
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Telegram
    BOT_TOKEN: str
    ADMIN_IDS_STR: str = Field(default="", alias="ADMIN_IDS")
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./bot.db"
    
    # Redis
    REDIS_URL: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "change-me-in-production"
    
    # Webhook
    WEBHOOK_URL: Optional[str] = None
    WEBHOOK_PATH: str = "/webhook"
    WEBAPP_HOST: str = "0.0.0.0"
    WEBAPP_PORT: int = 8080
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # External APIs
    MOSPOLYTECH_API_URL: str = "https://e.mospolytech.ru/"
    
    @property
    def ADMIN_IDS(self) -> List[int]:
        """Парсинг списка ID администраторов"""
        if not self.ADMIN_IDS_STR or not self.ADMIN_IDS_STR.strip():
            return []
        try:
            return [int(x.strip()) for x in self.ADMIN_IDS_STR.split(",") if x.strip().isdigit()]
        except (ValueError, AttributeError):
            return []
    
    @property
    def is_webhook(self) -> bool:
        """Проверка использования webhook"""
        return bool(self.WEBHOOK_URL)


@lru_cache
def get_settings() -> Settings:
    """Получение настроек (с кэшированием)"""
    return Settings()


settings = get_settings()
