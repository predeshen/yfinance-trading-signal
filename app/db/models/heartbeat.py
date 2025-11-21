"""Heartbeat database model"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.db.database import Base


class Heartbeat(Base):
    """
    Heartbeat model for tracking system health.
    """
    __tablename__ = "heartbeats"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol_alias = Column(String, nullable=False, index=True)
    timestamp_utc = Column(DateTime, nullable=False, index=True)
    open_trade_count = Column(Integer, nullable=False)
    last_error = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<Heartbeat(id={self.id}, symbol={self.symbol_alias}, timestamp={self.timestamp_utc})>"
