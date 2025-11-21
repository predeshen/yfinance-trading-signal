"""
Configuration management using Pydantic settings.
Loads configuration from environment variables.
"""
from typing import Dict
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramConfig(BaseSettings):
    """Telegram bot configuration"""
    bot_token: str = Field(..., alias="TELEGRAM__BOT_TOKEN")
    chat_id: str = Field(..., alias="TELEGRAM__CHAT_ID")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class SmtpConfig(BaseSettings):
    """SMTP email configuration"""
    server: str = Field(..., alias="SMTP__SERVER")
    port: int = Field(..., alias="SMTP__PORT")
    user: str = Field(..., alias="SMTP__USER")
    password: str = Field(..., alias="SMTP__PASSWORD")
    from_email: str = Field(..., alias="SMTP__FROM_EMAIL")
    to_email: str = Field(..., alias="SMTP__TO_EMAIL")
    use_ssl: bool = Field(..., alias="SMTP__USE_SSL")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class ScannerConfig(BaseSettings):
    """Scanner service configuration"""
    symbols: Dict[str, str] = Field(default_factory=dict)
    scan_interval_seconds: int = Field(60, alias="SCANNER__SCAN_INTERVAL_SECONDS")
    heartbeat_interval_minutes: int = Field(15, alias="SCANNER__HEARTBEAT_INTERVAL_MINUTES")
    email_summary_interval_hours: int = Field(2, alias="SCANNER__EMAIL_SUMMARY_INTERVAL_HOURS")
    risk_percentage: float = Field(0.01, alias="SCANNER__RISK_PERCENTAGE")
    default_equity: float = Field(10000, alias="SCANNER__DEFAULT_EQUITY")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    @classmethod
    def load_symbols_from_env(cls) -> Dict[str, str]:
        """Parse symbol mappings from environment variables"""
        import os
        symbols = {}
        prefix = "SCANNER__SYMBOLS__"
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                alias = key[len(prefix):]
                symbols[alias] = value
        
        return symbols


class DatabaseConfig(BaseSettings):
    """Database configuration"""
    user: str = Field(..., alias="POSTGRES_USER")
    password: str = Field(..., alias="POSTGRES_PASSWORD")
    db: str = Field(..., alias="POSTGRES_DB")
    host: str = Field(..., alias="POSTGRES_HOST")
    port: int = Field(..., alias="POSTGRES_PORT")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    @property
    def url(self) -> str:
        """Get database connection URL"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class AppConfig(BaseSettings):
    """Main application configuration"""
    timezone: str = Field("Africa/Johannesburg", alias="APP_TIMEZONE")
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    smtp: SmtpConfig = Field(default_factory=SmtpConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    scanner: ScannerConfig = Field(default_factory=ScannerConfig)
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Load scanner config with symbols
        symbols = ScannerConfig.load_symbols_from_env()
        if symbols:
            # Get current scanner config values, excluding symbols to avoid duplicate
            scanner_data = self.scanner.model_dump(exclude={'symbols'})
            self.scanner = ScannerConfig(symbols=symbols, **scanner_data)
    
    def validate_all(self) -> None:
        """Validate all configuration sections"""
        errors = []
        
        # Validate Telegram config
        if not self.telegram.bot_token:
            errors.append("TELEGRAM__BOT_TOKEN is required")
        if not self.telegram.chat_id:
            errors.append("TELEGRAM__CHAT_ID is required")
        
        # Validate SMTP config
        if not self.smtp.server:
            errors.append("SMTP__SERVER is required")
        if not self.smtp.user:
            errors.append("SMTP__USER is required")
        if not self.smtp.password:
            errors.append("SMTP__PASSWORD is required")
        
        # Validate Database config
        if not self.database.user:
            errors.append("POSTGRES_USER is required")
        if not self.database.password:
            errors.append("POSTGRES_PASSWORD is required")
        if not self.database.db:
            errors.append("POSTGRES_DB is required")
        
        # Validate Scanner config
        if not self.scanner.symbols:
            errors.append("No symbol mappings found. Set SCANNER__SYMBOLS__* environment variables")
        
        if errors:
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))


# Global config instance
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Get or create global configuration instance"""
    global _config
    if _config is None:
        _config = AppConfig()
        _config.validate_all()
    return _config
