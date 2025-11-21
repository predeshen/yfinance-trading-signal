"""Database query utilities"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.db.models.signal import Signal
from app.db.models.trade import Trade, TradeState
from app.db.models.heartbeat import Heartbeat
from app.db.models.error_log import ErrorLog


def create_signal(
    db: Session,
    symbol_alias: str,
    yf_symbol: str,
    direction: str,
    time_generated_utc: datetime,
    entry_price_at_signal: float,
    initial_sl: float,
    initial_tp: float,
    strategy_name: str,
    notes: Optional[str] = None,
    estimated_rr: Optional[float] = None,
) -> Signal:
    """Create a new signal"""
    signal = Signal(
        symbol_alias=symbol_alias,
        yf_symbol=yf_symbol,
        direction=direction,
        time_generated_utc=time_generated_utc,
        entry_price_at_signal=entry_price_at_signal,
        initial_sl=initial_sl,
        initial_tp=initial_tp,
        strategy_name=strategy_name,
        notes=notes,
        estimated_rr=estimated_rr,
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


def create_trade(
    db: Session,
    signal_id: int,
    symbol_alias: str,
    yf_symbol: str,
    direction: str,
    planned_entry_price: float,
    actual_entry_price: float,
    stop_loss: float,
    take_profit: float,
    open_time_utc: datetime,
) -> Trade:
    """Create a new trade"""
    trade = Trade(
        signal_id=signal_id,
        symbol_alias=symbol_alias,
        yf_symbol=yf_symbol,
        direction=direction,
        planned_entry_price=planned_entry_price,
        actual_entry_price=actual_entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        state=TradeState.OPEN,
        open_time_utc=open_time_utc,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


def get_open_trades(db: Session, symbol_alias: Optional[str] = None) -> List[Trade]:
    """Get all open trades, optionally filtered by symbol"""
    query = db.query(Trade).filter(Trade.state == TradeState.OPEN)
    if symbol_alias:
        query = query.filter(Trade.symbol_alias == symbol_alias)
    return query.all()


def get_closed_trades(
    db: Session,
    symbol_alias: Optional[str] = None,
    direction: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Trade]:
    """Get closed trades, optionally filtered by symbol and direction"""
    query = db.query(Trade).filter(Trade.state != TradeState.OPEN)
    
    if symbol_alias:
        query = query.filter(Trade.symbol_alias == symbol_alias)
    if direction:
        query = query.filter(Trade.direction == direction)
    
    query = query.order_by(Trade.close_time_utc.desc())
    
    if limit:
        query = query.limit(limit)
    
    return query.all()


def update_trade_state(
    db: Session,
    trade_id: int,
    new_state: TradeState,
    close_time_utc: Optional[datetime] = None,
    close_price: Optional[float] = None,
    close_reason: Optional[str] = None,
) -> Trade:
    """Update trade state"""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise ValueError(f"Trade {trade_id} not found")
    
    trade.state = new_state
    if close_time_utc:
        trade.close_time_utc = close_time_utc
    if close_price is not None:
        trade.close_price = close_price
    if close_reason:
        trade.close_reason = close_reason
    
    db.commit()
    db.refresh(trade)
    return trade


def update_trade_sl_tp(
    db: Session,
    trade_id: int,
    new_sl: Optional[float] = None,
    new_tp: Optional[float] = None,
) -> Trade:
    """Update trade SL/TP"""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise ValueError(f"Trade {trade_id} not found")
    
    if new_sl is not None:
        trade.stop_loss = new_sl
    if new_tp is not None:
        trade.take_profit = new_tp
    
    db.commit()
    db.refresh(trade)
    return trade


def create_heartbeat(
    db: Session,
    symbol_alias: str,
    timestamp_utc: datetime,
    open_trade_count: int,
    last_error: Optional[str] = None,
) -> Heartbeat:
    """Create a heartbeat record"""
    heartbeat = Heartbeat(
        symbol_alias=symbol_alias,
        timestamp_utc=timestamp_utc,
        open_trade_count=open_trade_count,
        last_error=last_error,
    )
    db.add(heartbeat)
    db.commit()
    db.refresh(heartbeat)
    return heartbeat


def create_error_log(
    db: Session,
    timestamp_utc: datetime,
    component: str,
    severity: str,
    message: str,
    exception_type: Optional[str] = None,
    symbol_alias: Optional[str] = None,
    stack_trace: Optional[str] = None,
) -> ErrorLog:
    """Create an error log record"""
    error_log = ErrorLog(
        timestamp_utc=timestamp_utc,
        component=component,
        severity=severity,
        message=message,
        exception_type=exception_type,
        symbol_alias=symbol_alias,
        stack_trace=stack_trace,
    )
    db.add(error_log)
    db.commit()
    db.refresh(error_log)
    return error_log


def get_recent_errors(
    db: Session,
    hours: int = 24,
    symbol_alias: Optional[str] = None,
) -> List[ErrorLog]:
    """Get recent error logs"""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(ErrorLog).filter(ErrorLog.timestamp_utc >= cutoff)
    if symbol_alias:
        query = query.filter(ErrorLog.symbol_alias == symbol_alias)
    
    return query.order_by(ErrorLog.timestamp_utc.desc()).all()


def get_mae_mfe_stats(
    db: Session,
    symbol_alias: str,
    direction: str,
    limit: int = 100,
) -> dict:
    """
    Calculate MAE/MFE statistics from historical closed trades.
    
    Returns:
        Dictionary with median_mae, median_mfe, avg_mae, avg_mfe
    """
    closed_trades = get_closed_trades(
        db,
        symbol_alias=symbol_alias,
        direction=direction,
        limit=limit
    )
    
    if not closed_trades:
        return {
            "median_mae": None,
            "median_mfe": None,
            "avg_mae": None,
            "avg_mfe": None,
            "count": 0,
        }
    
    # Calculate MAE/MFE for each trade
    # Note: This is a simplified version. In production, you'd store
    # actual MAE/MFE values during trade monitoring
    maes = []
    mfes = []
    
    for trade in closed_trades:
        if trade.close_price and trade.actual_entry_price:
            if direction == "buy":
                # For buy: MAE is lowest point, MFE is highest point
                # Simplified: use close price as proxy
                pnl = trade.close_price - trade.actual_entry_price
                if pnl < 0:
                    maes.append(abs(pnl))
                else:
                    mfes.append(pnl)
            else:
                # For sell: opposite
                pnl = trade.actual_entry_price - trade.close_price
                if pnl < 0:
                    maes.append(abs(pnl))
                else:
                    mfes.append(pnl)
    
    import statistics
    
    return {
        "median_mae": statistics.median(maes) if maes else None,
        "median_mfe": statistics.median(mfes) if mfes else None,
        "avg_mae": statistics.mean(maes) if maes else None,
        "avg_mfe": statistics.mean(mfes) if mfes else None,
        "count": len(closed_trades),
    }
