"""Centralized error handling"""
import logging
import traceback
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Centralized error handling for the application.
    
    Handles different types of errors:
    - Startup errors (fatal)
    - Runtime errors (non-fatal)
    - Data errors (non-fatal)
    """
    
    def __init__(self, db: Session, notification_service=None):
        """
        Initialize error handler.
        
        Args:
            db: Database session
            notification_service: Notification service for alerts
        """
        self.db = db
        self.notification_service = notification_service
    
    async def handle_startup_error(
        self,
        component: str,
        error: Exception
    ) -> None:
        """
        Handle fatal startup errors.
        
        Actions:
        1. Log error with full stack trace
        2. Send Telegram error alert
        3. Send email error alert
        4. Raise exception to abort startup
        
        Args:
            component: Component where error occurred
            error: The exception
        """
        error_msg = f"FATAL STARTUP ERROR in {component}: {str(error)}"
        stack_trace = traceback.format_exc()
        
        # Log error
        logger.critical(
            error_msg,
            extra={'component': component},
            exc_info=True
        )
        
        # Send notifications
        if self.notification_service:
            try:
                await self.notification_service.send_error_alert(
                    component=component,
                    severity="CRITICAL",
                    message=str(error),
                    exception_type=type(error).__name__,
                    symbol=None
                )
            except Exception as e:
                logger.error(f"Failed to send error notification: {e}")
        
        # Log to database
        try:
            from app.db.queries import create_error_log
            create_error_log(
                db=self.db,
                timestamp_utc=datetime.utcnow(),
                component=component,
                severity="CRITICAL",
                message=str(error),
                exception_type=type(error).__name__,
                symbol_alias=None,
                stack_trace=stack_trace
            )
        except Exception as e:
            logger.error(f"Failed to log error to database: {e}")
        
        # Re-raise to abort startup
        raise
    
    async def handle_runtime_error(
        self,
        component: str,
        error: Exception,
        symbol: Optional[str] = None
    ) -> None:
        """
        Handle non-fatal runtime errors.
        
        Actions:
        1. Log error with context
        2. Write to error_logs table
        3. Send Telegram error alert
        4. Continue execution
        
        Args:
            component: Component where error occurred
            error: The exception
            symbol: Symbol being processed (if applicable)
        """
        error_msg = f"RUNTIME ERROR in {component}: {str(error)}"
        if symbol:
            error_msg += f" (symbol: {symbol})"
        
        stack_trace = traceback.format_exc()
        
        # Log error
        logger.error(
            error_msg,
            extra={'component': component, 'symbol': symbol},
            exc_info=True
        )
        
        # Send notification
        if self.notification_service:
            try:
                await self.notification_service.send_error_alert(
                    component=component,
                    severity="ERROR",
                    message=str(error),
                    exception_type=type(error).__name__,
                    symbol=symbol
                )
            except Exception as e:
                logger.error(f"Failed to send error notification: {e}")
        
        # Log to database
        try:
            from app.db.queries import create_error_log
            create_error_log(
                db=self.db,
                timestamp_utc=datetime.utcnow(),
                component=component,
                severity="ERROR",
                message=str(error),
                exception_type=type(error).__name__,
                symbol_alias=symbol,
                stack_trace=stack_trace
            )
        except Exception as e:
            logger.error(f"Failed to log error to database: {e}")
    
    async def handle_data_error(
        self,
        symbol: str,
        error: Exception
    ) -> None:
        """
        Handle data-related errors.
        
        Actions:
        1. Log warning
        2. Skip current operation
        3. Continue with next symbol
        
        Args:
            symbol: Symbol being processed
            error: The exception
        """
        error_msg = f"DATA ERROR for {symbol}: {str(error)}"
        
        # Log warning
        logger.warning(
            error_msg,
            extra={'component': 'DataProvider', 'symbol': symbol}
        )
        
        # Log to database (lower severity)
        try:
            from app.db.queries import create_error_log
            create_error_log(
                db=self.db,
                timestamp_utc=datetime.utcnow(),
                component="DataProvider",
                severity="WARNING",
                message=str(error),
                exception_type=type(error).__name__,
                symbol_alias=symbol,
                stack_trace=None
            )
        except Exception as e:
            logger.error(f"Failed to log error to database: {e}")
