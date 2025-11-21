"""Signal database model"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from app.db.database import Base


class Signal(Base):
    """
    Signal model representing a generated trading signal.
    """
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol_alias = Column(String, nullable=False, index=True)
    yf_symbol = Column(String, nullable=False)
    direction = Column(String, nullable=False)  # "buy" or "sell"
    time_generated_utc = Column(DateTime, nullable=False, index=True)
    entry_price_at_signal = Column(Float, nullable=False)
    initial_sl = Column(Float, nullable=False)
    initial_tp = Column(Float, nullable=False)
    strategy_name = Column(String, nullable=False)
    notes = Column(String, nullable=True)
    estimated_rr = Column(Float, nullable=True)
    
    # Relationship
    trade = relationship("Trade", back_populates="signal", uselist=False)
    
    def __repr__(self):
        return f"<Signal(id={self.id}, symbol={self.symbol_alias}, direction={self.direction})>"
