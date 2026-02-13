"""
Chat functionality for managing chat sessions and messages.
"""
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from backend.shared.constants import CHAT_HISTORY_DB_PATH_STR, DATABASE_DIR
from backend.shared.logger import get_logger
from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
logger = get_logger("CHAT_MANAGER")


class DbChatSession(Base):
    """Database model for chat sessions"""

    __tablename__ = "chat_sessions"

    session_id = Column(String, primary_key=True)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    meta_data = Column(JSON, nullable=True)

    messages = relationship(
        "DbChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


class DbChatMessage(Base):
    """Database model for chat messages"""

    __tablename__ = "chat_messages"

    message_id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("chat_sessions.session_id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    meta_data = Column(JSON, nullable=True)

    session = relationship("DbChatSession", back_populates="messages")


class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ChatMessage:
    """Represents a single chat message"""

    role: MessageRole
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    message_id: Optional[str] = None

    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
        if isinstance(self.role, str):
            self.role = MessageRole(self.role)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["role"] = self.role.value
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        return cls(**data)


@dataclass
class ChatSession:
    """Represents a complete chat session"""

    session_id: str
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)

    def add_message(self, message: ChatMessage):
        """Add a message to the session"""
        self.messages.append(message)
        self.updated_at = datetime.now()
        # Update title if it's the first user message
        if not self.title and message.role == MessageRole.USER:
            self.title = (
                message.content[:50] + "..."
                if len(message.content) > 50
                else message.content
            )

    def get_context_for_llm(self, max_messages: int = 20) -> List[Dict[str, str]]:
        """Get formatted messages for LLM context"""
        # Get recent messages, prioritizing the most recent ones
        recent_messages = (
            self.messages[-max_messages:]
            if len(self.messages) > max_messages
            else self.messages
        )
        return [
            {"role": msg.role.value, "content": msg.content} for msg in recent_messages
        ]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        data["messages"] = [msg.to_dict() for msg in self.messages]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatSession":
        # Make a copy to avoid modifying the original data
        data_copy = data.copy()
        messages_data = data_copy.pop("messages", [])

        # Create session with empty messages list first
        data_copy["messages"] = []
        session = cls(**data_copy)

        # Then populate the messages
        session.messages = [
            ChatMessage.from_dict(msg_data) for msg_data in messages_data
        ]
        return session


class ChatHistoryManager:
    """Manages chat sessions and history"""

    def __init__(self):
        # Ensure database directory exists
        DATABASE_DIR.mkdir(parents=True, exist_ok=True)

        # Initialize database connection
        self.engine = create_engine(
            f"sqlite:///{CHAT_HISTORY_DB_PATH_STR}",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)

        # Create session factory
        self.Session = sessionmaker(bind=self.engine)

        self.active_sessions: Dict[str, ChatSession] = {}
        self.max_context_messages = 20
        self.max_tokens_per_message = 1000  # Approximate token limit per message

    def save_session_to_db(self, session: ChatSession):
        """Save a ChatSession object to the database"""
        with self.Session() as db_session:
            # Check if session already exists
            db_chat_session = (
                db_session.query(DbChatSession)
                .filter_by(session_id=session.session_id)
                .first()
            )

            if not db_chat_session:
                # Create new session
                db_chat_session = DbChatSession(
                    session_id=session.session_id,
                    title=session.title,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    meta_data=session.metadata,
                )
                db_session.add(db_chat_session)
            else:
                # Update existing session
                db_chat_session.title = session.title
                db_chat_session.updated_at = session.updated_at
                db_chat_session.meta_data = session.metadata

                # Delete existing messages to avoid duplicates
                db_session.query(DbChatMessage).filter_by(
                    session_id=session.session_id
                ).delete()

            # Add messages
            for message in session.messages:
                db_message = DbChatMessage(
                    message_id=message.message_id,
                    session_id=session.session_id,
                    role=message.role.value,
                    content=message.content,
                    timestamp=message.timestamp,
                    meta_data=message.metadata,
                )
                db_session.add(db_message)

            # Commit changes
            db_session.commit()

    def load_session_from_db(self, session_id: str) -> Optional[ChatSession]:
        """Load a ChatSession object from the database"""
        with self.Session() as db_session:
            # Query session
            db_chat_session = (
                db_session.query(DbChatSession).filter_by(session_id=session_id).first()
            )

            if not db_chat_session:
                return None

            # Query messages
            db_messages = (
                db_session.query(DbChatMessage).filter_by(session_id=session_id).all()
            )

            # Create ChatMessage objects
            messages = [
                ChatMessage(
                    role=MessageRole(msg.role),
                    content=msg.content,
                    timestamp=msg.timestamp,
                    metadata=msg.meta_data,
                    message_id=msg.message_id,
                )
                for msg in db_messages
            ]

            # Create ChatSession object
            return ChatSession(
                session_id=db_chat_session.session_id,
                title=db_chat_session.title,
                created_at=db_chat_session.created_at,
                updated_at=db_chat_session.updated_at,
                metadata=db_chat_session.meta_data,
                messages=messages,
            )

    def create_session(self, session_id: Optional[str] = None) -> ChatSession:
        """Create a new chat session"""
        if session_id is None:
            session_id = str(uuid.uuid4())

        session = ChatSession(
            session_id=session_id,
            messages=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self.active_sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a chat session by ID"""
        # Check active sessions first
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]

        # Try to load from database
        session = self.load_session_from_db(session_id)
        if session:
            self.active_sessions[session_id] = session

        return session

    def add_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """Add a message to a session"""
        session = self.get_session(session_id) or self.create_session(session_id)

        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {},
        )

        session.add_message(message)
        self.save_session_to_db(session)
        return message

    def get_conversation_context(
        self, session_id: str, max_messages: int = None
    ) -> List[Dict[str, str]]:
        """Get formatted conversation context for LLM"""
        session = self.get_session(session_id)
        if not session:
            return []
        return session.get_context_for_llm(max_messages or self.max_context_messages)

    def reduce_history(
        self, session: ChatSession, target_messages: int = 10
    ) -> ChatSession:
        """Reduce chat history to manage token limits"""
        if len(session.messages) <= target_messages:
            return session

        # Extract system messages and recent messages
        system_messages = [
            msg for msg in session.messages if msg.role == MessageRole.SYSTEM
        ]
        recent_messages = session.messages[-target_messages:]

        # Combine and deduplicate messages
        seen_ids = set()
        final_messages = []

        for msg in system_messages + recent_messages:
            if msg.message_id not in seen_ids:
                final_messages.append(msg)
                seen_ids.add(msg.message_id)

        session.messages = final_messages
        return session

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all available chat sessions"""
        sessions = []

        # Get sessions from database
        with self.Session() as db_session:
            db_chat_sessions = db_session.query(DbChatSession).all()

            for db_chat_session in db_chat_sessions:
                # Count messages for this session
                message_count = (
                    db_session.query(DbChatMessage)
                    .filter_by(session_id=db_chat_session.session_id)
                    .count()
                )

                sessions.append(
                    {
                        "session_id": db_chat_session.session_id,
                        "title": db_chat_session.title or "Untitled Chat",
                        "created_at": db_chat_session.created_at.isoformat(),
                        "updated_at": db_chat_session.updated_at.isoformat(),
                        "message_count": message_count,
                    }
                )

        # Sort by updated_at (most recent first)
        sessions.sort(key=lambda x: x["updated_at"], reverse=True)
        return sessions[:limit]

    def delete_session(self, session_id: str) -> bool:
        """Delete a chat session"""
        try:
            # Remove from active sessions if exists
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]

            # Delete from database
            with self.Session() as db_session:
                # Delete session (cascade will delete messages)
                db_chat_session = (
                    db_session.query(DbChatSession)
                    .filter_by(session_id=session_id)
                    .first()
                )
                if db_chat_session:
                    db_session.delete(db_chat_session)
                    db_session.commit()

            return True
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False

    def update_session(self, session_id: str, title: str = None) -> Optional[ChatSession]:
        """Update a chat session's metadata (e.g. title)"""
        # Get existing session
        session = self.get_session(session_id)
        if not session:
            return None

        # Update fields
        if title is not None:
            session.title = title
            
        # Update timestamp
        session.updated_at = datetime.now()

        # Save to database
        self.save_session_to_db(session)
        
        return session

    def clear_old_sessions(self, days_old: int = 30):
        """Clear sessions older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        deleted_count = 0

        # Delete old sessions from database only
        try:
            with self.Session() as db_session:
                # Find old sessions
                old_sessions = (
                    db_session.query(DbChatSession)
                    .filter(DbChatSession.updated_at < cutoff_date)
                    .all()
                )

                # Get session IDs for active session cleanup
                old_session_ids = [session.session_id for session in old_sessions]

                # Delete sessions from database
                for session in old_sessions:
                    db_session.delete(session)
                    deleted_count += 1

                db_session.commit()

                # Remove from active sessions
                for session_id in old_session_ids:
                    if session_id in self.active_sessions:
                        del self.active_sessions[session_id]

        except Exception as e:
            logger.error(f"Error clearing old sessions from database: {e}")

        logger.info(f"Cleared {deleted_count} old chat sessions")
        return deleted_count


# Global chat history manager instance
chat_history_manager = ChatHistoryManager()
