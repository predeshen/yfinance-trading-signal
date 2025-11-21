"""
Property-based tests for configuration management.
"""
import os
import pytest
from hypothesis import given, settings, strategies as st
from app.config.settings import (
    TelegramConfig,
    SmtpConfig,
    ScannerConfig,
    DatabaseConfig,
    AppConfig,
)


# Feature: trading-scanner-python, Property 34: Configuration validation
@given(
    telegram_token=st.one_of(st.none(), st.text(min_size=1)),
    chat_id=st.one_of(st.none(), st.text(min_size=1)),
    smtp_server=st.one_of(st.none(), st.text(min_size=1)),
    smtp_user=st.one_of(st.none(), st.text(min_size=1)),
    smtp_password=st.one_of(st.none(), st.text(min_size=1)),
    db_user=st.one_of(st.none(), st.text(min_size=1)),
    db_password=st.one_of(st.none(), st.text(min_size=1)),
    db_name=st.one_of(st.none(), st.text(min_size=1)),
)
@settings(max_examples=100)
def test_configuration_validation_rejects_invalid_configs(
    telegram_token, chat_id, smtp_server, smtp_user, smtp_password,
    db_user, db_password, db_name
):
    """
    Feature: trading-scanner-python, Property 34: Configuration validation
    
    For any configuration loaded from environment variables, the system should
    validate all required fields and fail with clear errors if validation fails.
    
    Validates: Requirements 9.2, 9.3
    """
    # Set up environment with potentially invalid values
    env_backup = {}
    env_vars = {
        "TELEGRAM__BOT_TOKEN": telegram_token or "",
        "TELEGRAM__CHAT_ID": chat_id or "",
        "SMTP__SERVER": smtp_server or "",
        "SMTP__PORT": "465",
        "SMTP__USER": smtp_user or "",
        "SMTP__PASSWORD": smtp_password or "",
        "SMTP__FROM_EMAIL": "test@test.com",
        "SMTP__TO_EMAIL": "test@test.com",
        "SMTP__USE_SSL": "true",
        "POSTGRES_USER": db_user or "",
        "POSTGRES_PASSWORD": db_password or "",
        "POSTGRES_DB": db_name or "",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "APP_TIMEZONE": "Africa/Johannesburg",
        "SCANNER__SCAN_INTERVAL_SECONDS": "60",
        "SCANNER__SYMBOLS__TEST": "^TEST",
    }
    
    # Backup and set environment
    for key, value in env_vars.items():
        env_backup[key] = os.environ.get(key)
        os.environ[key] = value
    
    try:
        # Check if all required fields are present
        all_required_present = all([
            telegram_token,
            chat_id,
            smtp_server,
            smtp_user,
            smtp_password,
            db_user,
            db_password,
            db_name,
        ])
        
        if all_required_present:
            # Should succeed
            config = AppConfig()
            config.validate_all()
            assert config.telegram.bot_token == telegram_token
            assert config.smtp.server == smtp_server
            assert config.database.user == db_user
        else:
            # Should fail validation
            with pytest.raises(ValueError) as exc_info:
                config = AppConfig()
                config.validate_all()
            
            # Error message should be clear
            assert "Configuration validation failed" in str(exc_info.value)
    
    finally:
        # Restore environment
        for key, value in env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_configuration_validation_with_valid_config():
    """Test that valid configuration passes validation"""
    env_backup = {}
    env_vars = {
        "TELEGRAM__BOT_TOKEN": "valid_token",
        "TELEGRAM__CHAT_ID": "123456",
        "SMTP__SERVER": "smtp.test.com",
        "SMTP__PORT": "465",
        "SMTP__USER": "user@test.com",
        "SMTP__PASSWORD": "password",
        "SMTP__FROM_EMAIL": "from@test.com",
        "SMTP__TO_EMAIL": "to@test.com",
        "SMTP__USE_SSL": "true",
        "POSTGRES_USER": "testuser",
        "POSTGRES_PASSWORD": "testpass",
        "POSTGRES_DB": "testdb",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "APP_TIMEZONE": "Africa/Johannesburg",
        "SCANNER__SYMBOLS__TEST": "^TEST",
    }
    
    for key, value in env_vars.items():
        env_backup[key] = os.environ.get(key)
        os.environ[key] = value
    
    try:
        config = AppConfig()
        config.validate_all()  # Should not raise
        
        assert config.telegram.bot_token == "valid_token"
        assert config.smtp.server == "smtp.test.com"
        assert config.database.user == "testuser"
    
    finally:
        for key, value in env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value



# Feature: trading-scanner-python, Property 35: Symbol mapping parsing
@given(
    alias=st.text(
        min_size=1,
        max_size=20,
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122)
    ).filter(lambda x: x.isalnum()),
    yf_symbol=st.text(min_size=1, max_size=20).filter(lambda x: len(x.strip()) > 0)
)
@settings(max_examples=100)
def test_symbol_mapping_parsing(alias, yf_symbol):
    """
    Feature: trading-scanner-python, Property 35: Symbol mapping parsing
    
    For any symbol mapping in environment variables following the format
    "SCANNER__SYMBOLS__ALIAS=yfinance_symbol", the system should correctly
    parse the alias and yfinance symbol.
    
    Validates: Requirements 9.4
    """
    env_backup = {}
    env_key = f"SCANNER__SYMBOLS__{alias}"
    
    # Backup and set environment
    env_backup[env_key] = os.environ.get(env_key)
    os.environ[env_key] = yf_symbol
    
    try:
        # Parse symbols from environment
        symbols = ScannerConfig.load_symbols_from_env()
        
        # Should contain our mapping
        assert alias in symbols
        assert symbols[alias] == yf_symbol
    
    finally:
        # Restore environment
        if env_backup[env_key] is None:
            os.environ.pop(env_key, None)
        else:
            os.environ[env_key] = env_backup[env_key]


def test_symbol_mapping_parsing_multiple_symbols():
    """Test parsing multiple symbol mappings"""
    env_backup = {}
    test_symbols = {
        "US30": "^DJI",
        "XAUUSD": "XAUUSD=X",
        "DAX": "^GDAXI",
    }
    
    for alias, yf_symbol in test_symbols.items():
        env_key = f"SCANNER__SYMBOLS__{alias}"
        env_backup[env_key] = os.environ.get(env_key)
        os.environ[env_key] = yf_symbol
    
    try:
        symbols = ScannerConfig.load_symbols_from_env()
        
        for alias, yf_symbol in test_symbols.items():
            assert alias in symbols
            assert symbols[alias] == yf_symbol
    
    finally:
        for env_key, value in env_backup.items():
            if value is None:
                os.environ.pop(env_key, None)
            else:
                os.environ[env_key] = value



# Feature: trading-scanner-python, Property 36: Timezone configuration usage
@given(
    utc_timestamp=st.datetimes(
        min_value=pytest.importorskip("datetime").datetime(2020, 1, 1),
        max_value=pytest.importorskip("datetime").datetime(2030, 12, 31)
    )
)
@settings(max_examples=100)
def test_timezone_configuration_usage(utc_timestamp):
    """
    Feature: trading-scanner-python, Property 36: Timezone configuration usage
    
    For any timestamp conversion operation, the system should use the timezone
    configured in APP_TIMEZONE environment variable.
    
    Validates: Requirements 9.5
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from app.config.timezone import TimezoneConverter
    
    # Test with configured timezone
    configured_tz = "Africa/Johannesburg"
    converter = TimezoneConverter(configured_tz)
    
    # Convert UTC to local
    local_dt = converter.utc_to_local(utc_timestamp)
    
    # Should be in the configured timezone
    assert local_dt.tzinfo == ZoneInfo(configured_tz)
    
    # Format should include timezone info
    formatted = converter.format_local(utc_timestamp)
    assert "CAT" in formatted or "SAST" in formatted  # South Africa time zones


def test_timezone_converter_with_different_timezones():
    """Test timezone converter with various timezones"""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from app.config.timezone import TimezoneConverter
    
    utc_dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
    
    # Test Africa/Johannesburg
    converter_cat = TimezoneConverter("Africa/Johannesburg")
    local_cat = converter_cat.utc_to_local(utc_dt)
    assert local_cat.hour == 14  # UTC+2
    
    # Test with different timezone
    converter_utc = TimezoneConverter("UTC")
    local_utc = converter_utc.utc_to_local(utc_dt)
    assert local_utc.hour == 12  # No change
