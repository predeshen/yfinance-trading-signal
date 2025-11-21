"""Error log database model"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.db.database import Base


class ErrorLog(Base):
    """
    Error log model for tracking system errors.
    """
    __tablename__ = "error_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp_utc = Column(DateTime, nullable=False, index=True)
    component = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    message = Column(String, nullable=False)
    exception_type = Column(String, nullable=True)
    symbol_alias = Column(String, nullable=True, index=True)
    stack_trace = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<ErrorLog(id={self.id}, component={self.component}, severity={self.severity})>"
