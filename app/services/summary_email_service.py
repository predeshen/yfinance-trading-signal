"""Summary email service"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.notifications.email_service import EmailNotificationService
from app.db.models.signal import Signal
from app.db.models.trade import Trade, TradeState
from app.db.models.error_log import ErrorLog

logger = logging.getLogger(__name__)


class SummaryEmailService:
    """Periodic email summary service"""
    
    def __init__(
        self,
        db: Session,
        email_service: EmailNotificationService
    ):
        """
        Initialize summary email service.
        
        Args:
            db: Database session
            email_service: Email notification service
        """
        self.db = db
        self.email_service = email_service
        self.last_summary_time = datetime.utcnow()
    
    async def send_summary(self) -> None:
        """Compile and send email summary"""
        logger.info("Compiling email summary...")
        
        try:
            period_end = datetime.utcnow()
            period_start = self.last_summary_time
            
            # Query signals
            signals = self.db.query(Signal).filter(
                Signal.time_generated_utc >= period_start,
                Signal.time_generated_utc <= period_end
            ).all()
            
            # Query trades opened
            trades_opened = self.db.query(Trade).filter(
                Trade.open_time_utc >= period_start,
                Trade.open_time_utc <= period_end
            ).all()
            
            # Query trades closed
            trades_closed = self.db.query(Trade).filter(
                Trade.close_time_utc >= period_start,
                Trade.close_time_utc <= period_end,
                Trade.state != TradeState.OPEN
            ).all()
            
            # Query errors
            errors = self.db.query(ErrorLog).filter(
                ErrorLog.timestamp_utc >= period_start,
                ErrorLog.timestamp_utc <= period_end
            ).all()
            
            # Format data for email
            signals_data = [
                {
                    'symbol': s.symbol_alias,
                    'direction': s.direction,
                    'entry': s.entry_price_at_signal,
                    'sl': s.initial_sl,
                    'tp': s.initial_tp,
                    'rr': s.estimated_rr or 0
                }
                for s in signals
            ]
            
            trades_closed_data = [
                {
                    'symbol': t.symbol_alias,
                    'direction': t.direction,
                    'result': 'TP' if t.state == TradeState.CLOSED_BY_TP else 'SL',
                    'r_multiple': 0  # Simplified
                }
                for t in trades_closed
            ]
            
            errors_data = [
                {
                    'component': e.component,
                    'message': e.message
                }
                for e in errors
            ]
            
            # Send email
            await self.email_service.send_summary_email(
                period_start=period_start,
                period_end=period_end,
                signals=signals_data,
                trades_opened=[],
                trades_closed=trades_closed_data,
                updates=[],
                errors=errors_data
            )
            
            # Update last summary time
            self.last_summary_time = period_end
            
            logger.info("Email summary sent successfully")
        
        except Exception as e:
            logger.error(f"Error sending email summary: {e}", exc_info=True)
