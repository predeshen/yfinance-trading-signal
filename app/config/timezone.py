"""
Timezone utilities for converting timestamps to Africa/Johannesburg (CAT).
"""
from datetime import datetime
from zoneinfo import ZoneInfo


class TimezoneConverter:
    """Handles timezone conversions for the application"""
    
    def __init__(self, timezone: str = "Africa/Johannesburg"):
        """
        Initialize timezone converter.
        
        Args:
            timezone: IANA timezone name (default: Africa/Johannesburg)
        """
        self.timezone = timezone
        self.tz = ZoneInfo(timezone)
    
    def utc_to_local(self, utc_dt: datetime) -> datetime:
        """
        Convert UTC datetime to local timezone.
        
        Args:
            utc_dt: UTC datetime (naive or aware)
        
        Returns:
            Datetime in local timezone
        """
        if utc_dt.tzinfo is None:
            # Assume naive datetime is UTC
            utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))
        
        return utc_dt.astimezone(self.tz)
    
    def format_local(self, utc_dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
        """
        Format UTC datetime as local timezone string.
        
        Args:
            utc_dt: UTC datetime
            fmt: strftime format string
        
        Returns:
            Formatted datetime string in local timezone
        """
        local_dt = self.utc_to_local(utc_dt)
        return local_dt.strftime(fmt)
    
    def now_local(self) -> datetime:
        """Get current time in local timezone"""
        return datetime.now(self.tz)
    
    def now_utc(self) -> datetime:
        """Get current time in UTC"""
        return datetime.now(ZoneInfo("UTC"))


# Global timezone converter instance
_tz_converter: TimezoneConverter | None = None


def get_timezone_converter(timezone: str = "Africa/Johannesburg") -> TimezoneConverter:
    """Get or create global timezone converter instance"""
    global _tz_converter
    if _tz_converter is None:
        _tz_converter = TimezoneConverter(timezone)
    return _tz_converter
