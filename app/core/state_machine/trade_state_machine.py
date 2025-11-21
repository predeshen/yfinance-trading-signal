"""Trade state machine implementation"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.db.models.trade import Trade, TradeState
from app.db.queries import update_trade_state, update_trade_sl_tp
from app.core.strategy.strategy_protocol import TradeUpdateAction

logger = logging.getLogger(__name__)


class TradeStateMachine:
    """
    Manages trade state transitions.
    
    State transition rules:
    - Open -> ClosedByTp: when price hits TP
    - Open -> ClosedBySl: when price hits SL
    - Open -> ClosedManual: when early close recommended
    - Open -> Expired: when trade expires (optional)
    
    Important: Once closed, no further TP notifications even if price hits old TP
    """
    
    def __init__(self, db: Session):
        """
        Initialize state machine.
        
        Args:
            db: Database session
        """
        self.db = db
        # Track which trades have been closed to prevent duplicate TP notifications
        self._closed_trades = set()
    
    async def check_and_update_trade(
        self,
        trade: Trade,
        current_price: float,
        candle_high: float,
        candle_low: float
    ) -> Optional[TradeUpdateAction]:
        """
        Check if trade should be updated based on current price.
        
        Args:
            trade: Trade to check
            current_price: Current price
            candle_high: Candle high
            candle_low: Candle low
        
        Returns:
            TradeUpdateAction if state change needed, None otherwise
        """
        # Skip if trade is already closed
        if trade.state != TradeState.OPEN:
            # Mark as closed to prevent TP notifications
            self._closed_trades.add(trade.id)
            return None
        
        # Check for SL hit
        if trade.direction == "buy":
            if candle_low <= trade.stop_loss:
                logger.info(f"Trade {trade.id}: SL hit at {trade.stop_loss}")
                return TradeUpdateAction(
                    action_type="close_by_sl",
                    new_state="ClosedBySl",
                    close_price=trade.stop_loss,
                    close_reason="Stop loss hit"
                )
        else:  # sell
            if candle_high >= trade.stop_loss:
                logger.info(f"Trade {trade.id}: SL hit at {trade.stop_loss}")
                return TradeUpdateAction(
                    action_type="close_by_sl",
                    new_state="ClosedBySl",
                    close_price=trade.stop_loss,
                    close_reason="Stop loss hit"
                )
        
        # Check for TP hit (only if trade is still open)
        if trade.direction == "buy":
            if candle_high >= trade.take_profit:
                logger.info(f"Trade {trade.id}: TP hit at {trade.take_profit}")
                return TradeUpdateAction(
                    action_type="close_by_tp",
                    new_state="ClosedByTp",
                    close_price=trade.take_profit,
                    close_reason="Take profit hit"
                )
        else:  # sell
            if candle_low <= trade.take_profit:
                logger.info(f"Trade {trade.id}: TP hit at {trade.take_profit}")
                return TradeUpdateAction(
                    action_type="close_by_tp",
                    new_state="ClosedByTp",
                    close_price=trade.take_profit,
                    close_reason="Take profit hit"
                )
        
        return None
    
    async def apply_action(
        self,
        trade_id: int,
        action: TradeUpdateAction
    ) -> Trade:
        """
        Apply the action to the trade in database.
        
        Args:
            trade_id: Trade ID
            action: Action to apply
        
        Returns:
            Updated trade
        """
        if action.action_type in ["close_by_tp", "close_by_sl", "close_manual"]:
            # Close the trade
            new_state_enum = TradeState[action.new_state.upper().replace("CLOSED", "CLOSED_")]
            
            updated_trade = update_trade_state(
                db=self.db,
                trade_id=trade_id,
                new_state=new_state_enum,
                close_time_utc=datetime.utcnow(),
                close_price=action.close_price,
                close_reason=action.close_reason
            )
            
            # Mark as closed
            self._closed_trades.add(trade_id)
            
            logger.info(
                f"Trade {trade_id} closed: {action.new_state}, "
                f"price={action.close_price}, reason={action.close_reason}"
            )
            
            return updated_trade
        
        elif action.action_type == "update_sl_tp":
            # Update SL/TP
            updated_trade = update_trade_sl_tp(
                db=self.db,
                trade_id=trade_id,
                new_sl=action.new_sl,
                new_tp=action.new_tp
            )
            
            logger.info(
                f"Trade {trade_id} updated: SL={action.new_sl}, TP={action.new_tp}"
            )
            
            return updated_trade
        
        else:
            raise ValueError(f"Unknown action type: {action.action_type}")
    
    def is_trade_closed(self, trade_id: int) -> bool:
        """
        Check if trade is closed.
        
        Args:
            trade_id: Trade ID
        
        Returns:
            True if trade is closed, False otherwise
        """
        return trade_id in self._closed_trades
    
    def should_send_tp_notification(self, trade_id: int, new_state: str) -> bool:
        """
        Determine if TP notification should be sent.
        
        Important rule: Only send TP notification when transitioning from
        Open to ClosedByTp. If trade was closed early (ClosedManual) and
        price later hits old TP, do NOT send notification.
        
        Args:
            trade_id: Trade ID
            new_state: New state
        
        Returns:
            True if TP notification should be sent, False otherwise
        """
        # Only send if:
        # 1. New state is ClosedByTp
        # 2. Trade was not previously closed
        if new_state == "ClosedByTp" and trade_id not in self._closed_trades:
            return True
        
        return False
