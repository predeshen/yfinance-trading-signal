"""Symbol scanner service"""
import logging
from datetime import datetime, timedelta
from typing import Dict
from sqlalchemy.orm import Session

from app.data.yfinance_provider import YFinanceMarketDataProvider
from app.core.domain.multi_timeframe_context import MultiTimeframeContext
from app.core.strategy.h4_fvg_strategy import H4FvgStrategy
from app.core.strategy.strategy_protocol import TradeContext
from app.core.state_machine.trade_state_machine import TradeStateMachine
from app.notifications.telegram_service import TelegramNotificationService
from app.db.queries import create_signal, create_trade, get_open_trades
from app.utils.error_handler import ErrorHandler

logger = logging.getLogger(__name__)


class SymbolScannerService:
    """
    Main scanning service that runs periodically.
    
    Responsibilities:
    - Fetch/update market data for all symbols
    - Evaluate for new signals
    - Check open trades for SL/TP hits
    - Apply SL/TP adjustments
    - Send notifications
    """
    
    def __init__(
        self,
        db: Session,
        config,
        data_provider: YFinanceMarketDataProvider,
        strategy: H4FvgStrategy,
        state_machine: TradeStateMachine,
        notification_service: TelegramNotificationService,
        error_handler: ErrorHandler
    ):
        """
        Initialize scanner service.
        
        Args:
            db: Database session
            config: Application configuration
            data_provider: Market data provider
            strategy: Trading strategy
            state_machine: Trade state machine
            notification_service: Notification service
            error_handler: Error handler
        """
        self.db = db
        self.config = config
        self.data_provider = data_provider
        self.strategy = strategy
        self.state_machine = state_machine
        self.notification_service = notification_service
        self.error_handler = error_handler
        
        # Track last scan time per symbol
        self.last_scan: Dict[str, datetime] = {}
    
    async def scan_symbol(self, alias: str, yf_symbol: str) -> None:
        """
        Scan a single symbol.
        
        Steps:
        1. Fetch/update candles for all timeframes
        2. Build MultiTimeframeContext
        3. Check if H4 candle closed since last scan
        4. If yes: evaluate for new signal
        5. For each open trade on this symbol:
           - Check for SL/TP hit
           - Evaluate for adjustments
        6. Send notifications as needed
        
        Args:
            alias: Symbol alias
            yf_symbol: yfinance symbol
        """
        try:
            logger.info(f"Scanning {alias} ({yf_symbol})...")
            
            # Step 1: Fetch candles for all timeframes
            now_utc = datetime.utcnow()
            
            h4_df = await self.data_provider.get_candles(yf_symbol, "240m", timedelta(days=30))
            h1_df = await self.data_provider.get_candles(yf_symbol, "60m", timedelta(days=14))
            m30_df = await self.data_provider.get_candles(yf_symbol, "30m", timedelta(days=7))
            m15_df = await self.data_provider.get_candles(yf_symbol, "15m", timedelta(days=7))
            m5_df = await self.data_provider.get_candles(yf_symbol, "5m", timedelta(days=3))
            m1_df = await self.data_provider.get_candles(yf_symbol, "1m", timedelta(days=1))
            
            # Get current price
            current_price = h1_df['close'].iloc[-1] if not h1_df.empty else 0
            
            # Step 2: Build context
            ctx = MultiTimeframeContext(
                alias=alias,
                yf_symbol=yf_symbol,
                now_utc=now_utc,
                h4=h4_df,
                h1=h1_df,
                m30=m30_df,
                m15=m15_df,
                m5=m5_df,
                m1=m1_df,
                current_price=current_price
            )
            
            # Step 3 & 4: Evaluate for new signal
            signal = await self.strategy.evaluate_new_signal(ctx)
            
            if signal:
                logger.info(f"New signal generated for {alias}!")
                
                # Save signal to database
                db_signal = create_signal(
                    db=self.db,
                    symbol_alias=signal.symbol_alias,
                    yf_symbol=signal.yf_symbol,
                    direction=signal.direction,
                    time_generated_utc=signal.time_generated_utc,
                    entry_price_at_signal=signal.entry_price_at_signal,
                    initial_sl=signal.initial_sl,
                    initial_tp=signal.initial_tp,
                    strategy_name=signal.strategy_name,
                    notes=signal.notes,
                    estimated_rr=signal.estimated_rr
                )
                
                # Create trade
                trade = create_trade(
                    db=self.db,
                    signal_id=db_signal.id,
                    symbol_alias=signal.symbol_alias,
                    yf_symbol=signal.yf_symbol,
                    direction=signal.direction,
                    planned_entry_price=signal.entry_price_at_signal,
                    actual_entry_price=signal.entry_price_at_signal,
                    stop_loss=signal.initial_sl,
                    take_profit=signal.initial_tp,
                    open_time_utc=signal.time_generated_utc
                )
                
                # Calculate lot size
                risk_amount, lot_size = self.strategy.sl_tp_estimator.calculate_risk_and_lot_size(
                    signal.entry_price_at_signal,
                    signal.initial_sl,
                    signal.direction
                )
                
                # Send notification
                await self.notification_service.send_signal_alert(
                    signal_id=db_signal.id,
                    symbol_alias=signal.symbol_alias,
                    yf_symbol=signal.yf_symbol,
                    direction=signal.direction,
                    entry_price=signal.entry_price_at_signal,
                    sl=signal.initial_sl,
                    tp=signal.initial_tp,
                    estimated_rr=signal.estimated_rr,
                    strategy_name=signal.strategy_name,
                    notes=signal.notes,
                    lot_size=lot_size,
                    risk_percentage=self.config.scanner.risk_percentage
                )
            
            # Step 5: Check open trades
            open_trades = get_open_trades(self.db, symbol_alias=alias)
            
            for trade in open_trades:
                # Build trade context
                trade_ctx = TradeContext(
                    trade_id=trade.id,
                    symbol_alias=trade.symbol_alias,
                    yf_symbol=trade.yf_symbol,
                    direction=trade.direction,
                    entry_price=trade.actual_entry_price,
                    current_price=current_price,
                    current_sl=trade.stop_loss,
                    current_tp=trade.take_profit,
                    candle_high=h1_df['high'].iloc[-1] if not h1_df.empty else current_price,
                    candle_low=h1_df['low'].iloc[-1] if not h1_df.empty else current_price,
                    mtf_context=ctx
                )
                
                # Check for SL/TP hits
                action = await self.state_machine.check_and_update_trade(
                    trade,
                    current_price,
                    trade_ctx.candle_high,
                    trade_ctx.candle_low
                )
                
                if action:
                    # Apply action
                    updated_trade = await self.state_machine.apply_action(trade.id, action)
                    
                    # Send notification
                    if action.action_type == "close_by_tp":
                        # Calculate R multiple
                        sl_distance = abs(trade.actual_entry_price - trade.stop_loss)
                        profit = abs(action.close_price - trade.actual_entry_price)
                        r_multiple = profit / sl_distance if sl_distance > 0 else 0
                        
                        # Calculate holding time
                        holding_time = datetime.utcnow() - trade.open_time_utc
                        holding_str = f"{holding_time.days}d {holding_time.seconds//3600}h"
                        
                        await self.notification_service.send_close_alert(
                            trade_id=trade.id,
                            symbol_alias=trade.symbol_alias,
                            yf_symbol=trade.yf_symbol,
                            direction=trade.direction,
                            entry_price=trade.actual_entry_price,
                            exit_price=action.close_price,
                            sl=trade.stop_loss,
                            tp=trade.take_profit,
                            r_multiple=r_multiple,
                            holding_time=holding_str,
                            close_type="tp"
                        )
                    
                    elif action.action_type == "close_by_sl":
                        sl_distance = abs(trade.actual_entry_price - trade.stop_loss)
                        loss = abs(action.close_price - trade.actual_entry_price)
                        r_multiple = -loss / sl_distance if sl_distance > 0 else 0
                        
                        holding_time = datetime.utcnow() - trade.open_time_utc
                        holding_str = f"{holding_time.days}d {holding_time.seconds//3600}h"
                        
                        await self.notification_service.send_close_alert(
                            trade_id=trade.id,
                            symbol_alias=trade.symbol_alias,
                            yf_symbol=trade.yf_symbol,
                            direction=trade.direction,
                            entry_price=trade.actual_entry_price,
                            exit_price=action.close_price,
                            sl=trade.stop_loss,
                            tp=trade.take_profit,
                            r_multiple=r_multiple,
                            holding_time=holding_str,
                            close_type="sl"
                        )
                    
                    elif action.action_type == "update_sl_tp":
                        await self.notification_service.send_update_alert(
                            trade_id=trade.id,
                            symbol_alias=trade.symbol_alias,
                            yf_symbol=trade.yf_symbol,
                            direction=trade.direction,
                            old_sl=trade.stop_loss,
                            new_sl=action.new_sl or trade.stop_loss,
                            old_tp=trade.take_profit,
                            new_tp=action.new_tp or trade.take_profit,
                            current_price=current_price,
                            reason=action.close_reason or "Adjustment"
                        )
            
            # Update last scan time
            self.last_scan[alias] = now_utc
            
            logger.info(f"Scan complete for {alias}")
        
        except Exception as e:
            logger.error(f"Error scanning {alias}: {e}", exc_info=True)
            await self.error_handler.handle_data_error(alias, e)
    
    async def run_scan_cycle(self) -> None:
        """Run one complete scan cycle for all symbols"""
        logger.info("=" * 60)
        logger.info("Starting scan cycle...")
        logger.info("=" * 60)
        
        for alias, yf_symbol in self.config.scanner.symbols.items():
            try:
                await self.scan_symbol(alias, yf_symbol)
            except Exception as e:
                logger.error(f"Error in scan cycle for {alias}: {e}", exc_info=True)
                await self.error_handler.handle_runtime_error(
                    "SymbolScanner",
                    e,
                    symbol=alias
                )
        
        logger.info("Scan cycle complete")
