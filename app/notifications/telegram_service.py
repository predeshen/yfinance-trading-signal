"""Telegram notification service"""
import logging
from datetime import datetime
from typing import Optional
import aiohttp
from app.config.timezone import TimezoneConverter

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    """
    Telegram notification service using Bot API.
    
    Sends formatted messages to configured Telegram chat.
    """
    
    def __init__(self, bot_token: str, chat_id: str, timezone: str = "Africa/Johannesburg"):
        """
        Initialize Telegram service.
        
        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID
            timezone: Timezone for timestamp conversion
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.tz_converter = TimezoneConverter(timezone)
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    async def _send_message(self, text: str) -> None:
        """
        Send message to Telegram.
        
        Args:
            text: Message text
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    'chat_id': self.chat_id,
                    'text': text,
                    'parse_mode': 'HTML'
                }
                
                async with session.post(self.api_url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Telegram API error: {error_text}")
                    else:
                        logger.info("Telegram message sent successfully")
        
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
    
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
        """Send [SIGNAL] alert"""
        timestamp_cat = self.tz_converter.format_local(datetime.utcnow())
        
        message = f"""<b>[SIGNAL] {symbol_alias} ({yf_symbol}) {direction.upper()}</b>

• Time: {timestamp_cat}
• Mode: Pure signal (assumed entry at current price)
• Entry price (signal): {entry_price:.2f}
• Stop Loss: {sl:.2f}
• Take Profit: {tp:.2f}
• Estimated RR (data-based): {estimated_rr:.2f}
• Suggested lot size: {lot_size:.2f} lots (risking {risk_percentage*100:.1f}% of equity)
• TFs: H4 bias, H1/M15 structure, M5/M1 confirmation
• Strategy: {strategy_name}
• Notes: {notes}

ID: {signal_id}"""
        
        await self._send_message(message)
    
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
        """Send [UPDATE] alert"""
        timestamp_cat = self.tz_converter.format_local(datetime.utcnow())
        
        action = "MOVE SL" if new_sl != old_sl else "EXTEND TP"
        
        message = f"""<b>[UPDATE] {symbol_alias} ({yf_symbol}) {direction.upper()}</b>

• Time: {timestamp_cat}
• Trade ID: {trade_id}
• Action: {action}
• Old SL: {old_sl:.2f} → New SL: {new_sl:.2f}
• Old TP: {old_tp:.2f} → New TP: {new_tp:.2f}
• Current price: {current_price:.2f}
• Reason: {reason}"""
        
        await self._send_message(message)
    
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
        close_type: str
    ) -> None:
        """Send [CLOSE] alert"""
        timestamp_cat = self.tz_converter.format_local(datetime.utcnow())
        
        if close_type == "tp":
            title = f"<b>[CLOSE] {symbol_alias} ({yf_symbol}) {direction.upper()} – TP HIT 🎯</b>"
        else:
            title = f"<b>[CLOSE] {symbol_alias} ({yf_symbol}) {direction.upper()} – SL HIT ❌</b>"
        
        message = f"""{title}

• Time: {timestamp_cat}
• Trade ID: {trade_id}
• Entry: {entry_price:.2f}
• Exit: {exit_price:.2f}
• SL: {sl:.2f}
• TP: {tp:.2f}
• Result: {r_multiple:.2f}R
• Holding time: {holding_time}"""
        
        await self._send_message(message)
    
    async def send_heartbeat(
        self,
        symbol_alias: str,
        last_scan: datetime,
        open_trade_count: int,
        last_error: Optional[str]
    ) -> None:
        """Send [HEARTBEAT] alert"""
        timestamp_cat = self.tz_converter.format_local(datetime.utcnow())
        last_scan_cat = self.tz_converter.format_local(last_scan)
        
        error_text = last_error if last_error else "None"
        
        message = f"""<b>[HEARTBEAT] {symbol_alias} Scanner</b>

• Time: {timestamp_cat}
• Last scan: {last_scan_cat}
• Open trades: {open_trade_count}
• Last error: {error_text}"""
        
        await self._send_message(message)
    
    async def send_error_alert(
        self,
        component: str,
        severity: str,
        message: str,
        exception_type: str,
        symbol: Optional[str]
    ) -> None:
        """Send [ERROR] alert"""
        timestamp_cat = self.tz_converter.format_local(datetime.utcnow())
        
        symbol_text = symbol if symbol else "-"
        
        error_message = f"""<b>[ERROR] {component}</b>

• Time: {timestamp_cat}
• Severity: {severity}
• Message: {message}
• Exception: {exception_type}
• Symbol: {symbol_text}"""
        
        await self._send_message(error_message)
