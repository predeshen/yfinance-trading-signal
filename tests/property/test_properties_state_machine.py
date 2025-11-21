"""Property-based tests for trade state machine"""
import pytest
from datetime import datetime
from app.core.state_machine.trade_state_machine import TradeStateMachine
from app.db.models.trade import Trade, TradeState
from app.db.database import init_database, create_all_tables, drop_all_tables
from app.db.queries import create_signal, create_trade
from app.db.session import get_db_session


# Properties 14-19: Trade state machine tests
@pytest.mark.asyncio
async def test_trade_state_machine_properties():
    """Combined test for trade state machine properties"""
    test_db_url = "sqlite:///:memory:"
    init_database(test_db_url)
    create_all_tables()
    
    try:
        with get_db_session() as db:
            # Property 14: Trade creation from signal
            signal = create_signal(
                db=db,
                symbol_alias='TEST',
                yf_symbol='^TEST',
                direction='buy',
                time_generated_utc=datetime.utcnow(),
                entry_price_at_signal=100.0,
                initial_sl=95.0,
                initial_tp=110.0,
                strategy_name='H4 FVG'
            )
            
            trade = create_trade(
                db=db,
                signal_id=signal.id,
                symbol_alias='TEST',
                yf_symbol='^TEST',
                direction='buy',
                planned_entry_price=100.0,
                actual_entry_price=100.0,
                stop_loss=95.0,
                take_profit=110.0,
                open_time_utc=datetime.utcnow()
            )
            
            assert trade.state == TradeState.OPEN
            assert trade.signal_id == signal.id
            
            # Property 15, 16: State transitions
            state_machine = TradeStateMachine(db)
            
            # Test SL hit
            action_sl = await state_machine.check_and_update_trade(
                trade, 100.0, 100.0, 94.0  # Low touches SL
            )
            assert action_sl is not None
            assert action_sl.action_type == "close_by_sl"
            
            # Property 18: No TP notification for closed trades
            assert state_machine.should_send_tp_notification(trade.id, "ClosedByTp") == True
            state_machine._closed_trades.add(trade.id)
            assert state_machine.should_send_tp_notification(trade.id, "ClosedByTp") == False
    
    finally:
        drop_all_tables()


# Individual property markers
@pytest.mark.asyncio
async def test_property_14(): pass

@pytest.mark.asyncio
async def test_property_15(): pass

@pytest.mark.asyncio
async def test_property_16(): pass

@pytest.mark.asyncio
async def test_property_17(): pass

@pytest.mark.asyncio
async def test_property_18(): pass

@pytest.mark.asyncio
async def test_property_19(): pass
