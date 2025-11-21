"""Notification service protocol"""
from typing import Protocol, Optional
from datetime import datetime


class NotificationService(Protocol):
    """Protocol for notification services"""
    
    async def send_signal_alert(
        self,
        signal_id: int,
        symbol_alias: str,
        yf_symbol: str,
        direction: str,
        entry_price: float,
        sl: float,
        tp: float,
        estimated_rr: float,
        strategy_name: str,
        notes: str,
        lot_size: float,
        risk_percentage: float
    ) -> None:
        """Send signal alert"""
        ...
    
    async def send_update_alert(
        self,
        trade_id: int,
        symbol_alias: str,
        yf_symbol: str,
        direction: str,
        old_sl: float,
        new_sl: float,
        old_tp: float,
        new_tp: float,
        current_price: float,
        reason: str
    ) -> None:
        """Send update alert"""
        ...
    
    async def send_close_alert(
        self,
        trade_id: int,
        symbol_alias: str,
        yf_symbol: str,
        direction: str,
        entry_price: float,
        exit_price: float,
        sl: float,
        tp: float,
        r_multiple: float,
        holding_time: str,
        close_type: str  # "tp" or "sl"
    ) -> None:
        """Send close alert"""
        ...
    
    async def send_heartbeat(
        self,
        symbol_alias: str,
        last_scan: datetime,
        open_trade_count: int,
        last_error: Optional[str]
    ) -> None:
        """Send heartbeat"""
        ...
    
    async def send_error_alert(
        self,
        component: str,
        severity: str,
        message: str,
        exception_type: str,
        symbol: Optional[str]
    ) -> None:
        """Send error alert"""
        ...
