"""
Database models for the vectorrag application.
"""
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class DbChatSession(Base):
    """Database model for chat sessions"""
    __tablename__ = "chat_sessions"
    
    session_id = Column(String, primary_key=True)
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    meta_data = Column(JSON)
    
    # Relationship to messages
    messages = relationship("DbChatMessage", back_populates="session", cascade="all, delete-orphan")


class DbChatMessage(Base):
    """Database model for chat messages"""
    __tablename__ = "chat_messages"
    
    message_id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("chat_sessions.session_id"))
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    meta_data = Column(JSON)
    
    # Relationship to session
    session = relationship("DbChatSession", back_populates="messages")
