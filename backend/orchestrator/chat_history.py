import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio
from dataclasses import dataclass, asdict
from enum import Enum


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

        context = []
        for msg in recent_messages:
            context.append({"role": msg.role.value, "content": msg.content})

        return context

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

    def __init__(self, storage_path: str = "backend/chat_sessions"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.active_sessions: Dict[str, ChatSession] = {}
        self.max_context_messages = 20
        self.max_tokens_per_message = 1000  # Approximate token limit per message
        self._pending_saves: List[asyncio.Task] = []

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
        session = self.get_session(session_id)
        if not session:
            session = self.create_session(session_id)

        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {},
        )

        session.add_message(message)

        # Auto-save session (try async first, fallback to sync)
        try:
            # Check if we're in an event loop
            loop = asyncio.get_running_loop()
            task = asyncio.create_task(self.save_session_async(session))
            self._pending_saves.append(task)
            # Clean up completed tasks
            self._pending_saves = [t for t in self._pending_saves if not t.done()]
        except RuntimeError:
            # No event loop, save synchronously
            self.save_session(session)

        return message

    def get_conversation_context(
        self, session_id: str, max_messages: int = None
    ) -> List[Dict[str, str]]:
        """Get conversation context for LLM"""
        session = self.get_session(session_id)
        if not session:
            return []

        max_msgs = max_messages or self.max_context_messages
        return session.get_context_for_llm(max_msgs)

    def reduce_history(
        self, session: ChatSession, target_messages: int = 10
    ) -> ChatSession:
        """Reduce chat history to manage token limits"""
        if len(session.messages) <= target_messages:
            return session

        # Always keep the first system message if it exists
        system_messages = [
            msg for msg in session.messages if msg.role == MessageRole.SYSTEM
        ]

        # Keep the most recent messages
        recent_messages = session.messages[-target_messages:]

        # Combine system messages with recent messages
        reduced_messages = system_messages + recent_messages

        # Remove duplicates while preserving order
        seen_ids = set()
        final_messages = []
        for msg in reduced_messages:
            if msg.message_id not in seen_ids:
                final_messages.append(msg)
                seen_ids.add(msg.message_id)

        session.messages = final_messages
        return session

    def save_session(self, session: ChatSession):
        """Save session to storage (synchronous)"""
        session_file = self.storage_path / f"{session.session_id}.json"

        try:
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
        session_file = self.storage_path / f"{session_id}.json"

        if not session_file.exists():
            return None

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ChatSession.from_dict(data)
        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
            return None

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all available chat sessions"""
        sessions = []

        for session_file in self.storage_path.glob("*.json"):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                sessions.append(
                    {
                        "session_id": data["session_id"],
                        "title": data.get("title", "Untitled Chat"),
                        "created_at": data["created_at"],
                        "updated_at": data["updated_at"],
                        "message_count": len(data.get("messages", [])),
                    }
                )
            except Exception as e:
                print(f"Error reading session file {session_file}: {e}")

        # Sort by updated_at (most recent first)
        sessions.sort(key=lambda x: x["updated_at"], reverse=True)

        return sessions[:limit]

    def delete_session(self, session_id: str) -> bool:
        """Delete a chat session"""
        try:
            # Remove from active sessions
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]

            # Remove file
            session_file = self.storage_path / f"{session_id}.json"
            if session_file.exists():
                session_file.unlink()

            return True
        except Exception as e:
            print(f"Error deleting session {session_id}: {e}")
            return False

    def clear_old_sessions(self, days_old: int = 30):
        """Clear sessions older than specified days"""
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=days_old)
        deleted_count = 0

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
