import json
import uuid
import os
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional
import asyncio
from dataclasses import dataclass, asdict

from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey, Text, JSON, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session as DbSession
from sqlalchemy.pool import StaticPool

# Define Base class for SQLAlchemy models
Base = declarative_base()

# Database models
class DbChatSession(Base):
    """Database model for chat sessions"""
    __tablename__ = "chat_sessions"
    
    session_id = Column(String, primary_key=True)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    meta_data = Column(JSON, nullable=True)
    
    # Relationship with messages
    messages = relationship("DbChatMessage", back_populates="session", cascade="all, delete-orphan")
    
class DbChatMessage(Base):
    """Database model for chat messages"""
    __tablename__ = "chat_messages"
    
    message_id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("chat_sessions.session_id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    meta_data = Column(JSON, nullable=True)
    
    # Relationship with session
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
            self.title = message.content[:50] + "..." if len(message.content) > 50 else message.content

    def get_context_for_llm(self, max_messages: int = 20) -> List[Dict[str, str]]:
        """Get formatted messages for LLM context"""
        # Get recent messages, prioritizing the most recent ones
        recent_messages = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        return [{"role": msg.role.value, "content": msg.content} for msg in recent_messages]

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
        session.messages = [ChatMessage.from_dict(msg_data) for msg_data in messages_data]
        return session


class ChatHistoryManager:
    """Manages chat sessions and history"""

    def __init__(self, storage_path: str = "backend/chat_sessions"):
        # Create database directory if it doesn't exist
        db_dir = Path("backend/database")
        db_dir.mkdir(exist_ok=True)
        
        # Initialize database connection
        db_path = os.path.join(db_dir, "chat_history.db")
        self.engine = create_engine(f"sqlite:///{db_path}", 
                                   connect_args={"check_same_thread": False},
                                   poolclass=StaticPool)
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        
        # Create session factory
        self.Session = sessionmaker(bind=self.engine)
        
        # Keep legacy storage path for migration purposes
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        self.active_sessions: Dict[str, ChatSession] = {}
        self.max_context_messages = 20
        self.max_tokens_per_message = 1000  # Approximate token limit per message
        self._pending_saves: List[asyncio.Task] = []
        
        # Migrate existing JSON data to database if needed
        self._migrate_json_to_db()
        
    def _migrate_json_to_db(self):
        """Migrate existing JSON files to the database"""
        try:
            # Check if migration has already been done
            with self.Session() as db_session:
                # If there are already sessions in the database, skip migration
                if db_session.query(DbChatSession).first():
                    return
                    
            # Get all JSON files in the storage path
            json_files = list(self.storage_path.glob("*.json"))
            if not json_files:
                return
                
            print(f"Migrating {len(json_files)} chat sessions from JSON to database...")
            
            # Process each JSON file
            for session_file in json_files:
                try:
                    with open(session_file, "r", encoding="utf-8") as f:
                        session_data = json.load(f)
                    
                    # Create ChatSession object
                    session = ChatSession.from_dict(session_data)
                    
                    # Save to database
                    self._save_session_to_db(session)
                    
                except Exception as e:
                    print(f"Error migrating session {session_file}: {e}")
            
            print("Migration completed successfully.")
        except Exception as e:
            print(f"Error during migration: {e}")
            
    def _save_session_to_db(self, session: ChatSession):
        """Save a ChatSession object to the database"""
        with self.Session() as db_session:
            # Check if session already exists
            db_chat_session = db_session.query(DbChatSession).filter_by(session_id=session.session_id).first()
            
            if not db_chat_session:
                # Create new session
                db_chat_session = DbChatSession(
                    session_id=session.session_id,
                    title=session.title,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    meta_data=session.metadata
                )
                db_session.add(db_chat_session)
            else:
                # Update existing session
                db_chat_session.title = session.title
                db_chat_session.updated_at = session.updated_at
                db_chat_session.meta_data = session.metadata
                
                # Delete existing messages to avoid duplicates
                db_session.query(DbChatMessage).filter_by(session_id=session.session_id).delete()
            
            # Add messages
            for message in session.messages:
                db_message = DbChatMessage(
                    message_id=message.message_id,
                    session_id=session.session_id,
                    role=message.role.value,
                    content=message.content,
                    timestamp=message.timestamp,
                    meta_data=message.metadata
                )
                db_session.add(db_message)
                
            # Commit changes
            db_session.commit()
            
    def _load_session_from_db(self, session_id: str) -> Optional[ChatSession]:
        """Load a ChatSession object from the database"""
        with self.Session() as db_session:
            # Query session
            db_chat_session = db_session.query(DbChatSession).filter_by(session_id=session_id).first()
            
            if not db_chat_session:
                return None
                
            # Query messages
            db_messages = db_session.query(DbChatMessage).filter_by(session_id=session_id).all()
            
            # Create ChatMessage objects
            messages = [
                ChatMessage(
                    role=MessageRole(msg.role),
                    content=msg.content,
                    timestamp=msg.timestamp,
                    metadata=msg.meta_data,
                    message_id=msg.message_id
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
                messages=messages
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

        # Try to load from storage
        session = self.load_session(session_id)
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
        self._save_session(session)
        return message
        
    def _save_session(self, session: ChatSession):
        """Save session with appropriate method (async or sync)"""
        try:
            loop = asyncio.get_running_loop()
            task = asyncio.create_task(self.save_session_async(session))
            self._pending_saves.append(task)
            # Clean up completed tasks
            self._pending_saves = [t for t in self._pending_saves if not t.done()]
        except RuntimeError:
            # No event loop, save synchronously
            self.save_session(session)

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
        system_messages = [msg for msg in session.messages if msg.role == MessageRole.SYSTEM]
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

    def save_session(self, session: ChatSession):
        """Save session to storage (synchronous)"""
        try:
            # Save to database
            self._save_session_to_db(session)
            
            # Also save to JSON for backward compatibility
            session_file = self.storage_path / f"{session.session_id}.json"
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving session {session.session_id}: {e}")

    async def save_session_async(self, session: ChatSession):
        """Save session to storage (asynchronous)"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.save_session, session)

    async def wait_for_pending_saves(self):
        """Wait for all pending async save operations to complete"""
        if self._pending_saves:
            await asyncio.gather(*self._pending_saves, return_exceptions=True)
            self._pending_saves.clear()

    def load_session(self, session_id: str) -> Optional[ChatSession]:
        """Load session from storage"""
        # Try to load from database first
        session = self._load_session_from_db(session_id)
        if session:
            return session
            
        # Fall back to JSON file for backward compatibility
        session_file = self.storage_path / f"{session_id}.json"
        if not session_file.exists():
            return None

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                session = ChatSession.from_dict(json.load(f))
                # Save to database for future use
                self._save_session_to_db(session)
                return session
        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
            return None

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all available chat sessions"""
        sessions = []
        
        # Get sessions from database
        with self.Session() as db_session:
            db_chat_sessions = db_session.query(DbChatSession).all()
            
            for db_chat_session in db_chat_sessions:
                # Count messages for this session
                message_count = db_session.query(DbChatMessage).filter_by(session_id=db_chat_session.session_id).count()
                
                sessions.append({
                    "session_id": db_chat_session.session_id,
                    "title": db_chat_session.title or "Untitled Chat",
                    "created_at": db_chat_session.created_at.isoformat(),
                    "updated_at": db_chat_session.updated_at.isoformat(),
                    "message_count": message_count,
                })
        
        # Check for any JSON files not in the database (for backward compatibility)
        db_session_ids = {session["session_id"] for session in sessions}
        for session_file in self.storage_path.glob("*.json"):
            try:
                session_id = session_file.stem
                if session_id not in db_session_ids:
                    with open(session_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    sessions.append({
                        "session_id": data["session_id"],
                        "title": data.get("title", "Untitled Chat"),
                        "created_at": data["created_at"],
                        "updated_at": data["updated_at"],
                        "message_count": len(data.get("messages", [])),
                    })
                    # Load and save to database for future use
                    session = self.load_session(session_id)
                    if session:
                        self._save_session_to_db(session)
            except Exception as e:
                print(f"Error reading session file {session_file}: {e}")
                
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
                db_chat_session = db_session.query(DbChatSession).filter_by(session_id=session_id).first()
                if db_chat_session:
                    db_session.delete(db_chat_session)
                    db_session.commit()
                
            # Remove JSON file if exists (for backward compatibility)
            session_file = self.storage_path / f"{session_id}.json"
            if session_file.exists():
                session_file.unlink()
                
            return True
        except Exception as e:
            print(f"Error deleting session {session_id}: {e}")
            return False

    def clear_old_sessions(self, days_old: int = 30):
        """Clear sessions older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        deleted_count = 0

        # Delete old sessions from database
        try:
            with self.Session() as db_session:
                # Find old sessions
                old_sessions = db_session.query(DbChatSession).filter(
                    DbChatSession.updated_at < cutoff_date
                ).all()
                
                # Get session IDs for JSON file deletion
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
                
                # Delete corresponding JSON files
                for session_id in old_session_ids:
                    session_file = self.storage_path / f"{session_id}.json"
                    if session_file.exists():
                        session_file.unlink()
        except Exception as e:
            print(f"Error clearing old sessions from database: {e}")
            
        # Also check JSON files for any that might not be in the database
        for session_file in self.storage_path.glob("*.json"):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                updated_at = datetime.fromisoformat(data["updated_at"])
                if updated_at < cutoff_date:
                    session_file.unlink()
                    deleted_count += 1
            except Exception as e:
                print(f"Error processing session file {session_file}: {e}")

        print(f"Cleared {deleted_count} old chat sessions")
        return deleted_count

# Global chat history manager instance
chat_history_manager = ChatHistoryManager()
