"""Heartbeat service"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from app.notifications.telegram_service import TelegramNotificationService
from app.db.queries import create_heartbeat, get_open_trades, get_recent_errors

logger = logging.getLogger(__name__)


class HeartbeatService:
    """Periodic heartbeat service"""
    
    def __init__(
        self,
        db: Session,
        config,
        notification_service: TelegramNotificationService
    ):
        """
        Initialize heartbeat service.
        
        Args:
            db: Database session
            config: Application configuration
            notification_service: Notification service
        """
        self.db = db
        self.config = config
        self.notification_service = notification_service
        self.last_scan_times = {}
    
    async def send_heartbeats(self) -> None:
        """Send heartbeat for each symbol"""
        logger.info("Sending heartbeats...")
        
        for alias in self.config.scanner.symbols.keys():
            try:
                # Get open trade count
                open_trades = get_open_trades(self.db, symbol_alias=alias)
                open_count = len(open_trades)
                
                # Get last error
                recent_errors = get_recent_errors(self.db, hours=1, symbol_alias=alias)
                last_error = recent_errors[0].message if recent_errors else None
                
                # Get last scan time
                last_scan = self.last_scan_times.get(alias, datetime.utcnow())
                
                # Create heartbeat record
                create_heartbeat(
                    db=self.db,
                    symbol_alias=alias,
                    timestamp_utc=datetime.utcnow(),
                    open_trade_count=open_count,
                    last_error=last_error
                )
                
                # Send Telegram notification
                await self.notification_service.send_heartbeat(
                    symbol_alias=alias,
                    last_scan=last_scan,
                    open_trade_count=open_count,
                    last_error=last_error
                )
                
                logger.info(f"Heartbeat sent for {alias}")
            
            except Exception as e:
                logger.error(f"Error sending heartbeat for {alias}: {e}")
    
    def update_last_scan(self, alias: str, timestamp: datetime) -> None:
        """Update last scan time for symbol"""
        self.last_scan_times[alias] = timestamp
