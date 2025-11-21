"""Trade database model"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.db.database import Base


class TradeState(str, Enum):
    """Trade state enumeration"""
    OPEN = "Open"
    CLOSED_BY_TP = "ClosedByTp"
    CLOSED_BY_SL = "ClosedBySl"
    CLOSED_MANUAL = "ClosedManual"
    EXPIRED = "Expired"


class Trade(Base):
    """
    Trade model representing an active or closed trade.
    """
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False)
    symbol_alias = Column(String, nullable=False, index=True)
    yf_symbol = Column(String, nullable=False)
    direction = Column(String, nullable=False)  # "buy" or "sell"
    planned_entry_price = Column(Float, nullable=False)
    actual_entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    state = Column(SQLEnum(TradeState), nullable=False, default=TradeState.OPEN, index=True)
    open_time_utc = Column(DateTime, nullable=False, index=True)
    close_time_utc = Column(DateTime, nullable=True)
    close_price = Column(Float, nullable=True)
    close_reason = Column(String, nullable=True)
    
    # Relationship
    signal = relationship("Signal", back_populates="trade")
    
    def __repr__(self):
        return f"<Trade(id={self.id}, symbol={self.symbol_alias}, state={self.state})>"
