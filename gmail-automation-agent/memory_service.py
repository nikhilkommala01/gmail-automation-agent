import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """A message in a user conversation."""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: str

    def to_dict(self):
        return asdict(self)


@dataclass
class MemoryEntry:
    """A memory entry in long-term storage."""
    key: str
    value: Any
    timestamp: str
    ttl_seconds: Optional[int] = None  # Time-to-live; None means permanent

    def to_dict(self):
        return {
            'key': self.key,
            'value': self.value,
            'timestamp': self.timestamp,
            'ttl_seconds': self.ttl_seconds,
        }


class InMemorySessionService:
    """In-memory session storage for short-term user state."""

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, session_id: str) -> None:
        """Create a new session."""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'created_at': datetime.utcnow().isoformat(),
                'last_activity': datetime.utcnow().isoformat(),
                'conversation': [],
                'metadata': {},
            }
            logger.info(f"Created session {session_id}")

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a session."""
        return self.sessions.get(session_id)

    def update_session(self, session_id: str, data: Dict[str, Any]) -> None:
        """Update session data."""
        if session_id in self.sessions:
            self.sessions[session_id].update(data)
            self.sessions[session_id]['last_activity'] = datetime.utcnow().isoformat()
            logger.info(f"Updated session {session_id}")

    def add_message(self, session_id: str, message: ConversationMessage) -> None:
        """Add a message to session conversation history."""
        if session_id in self.sessions:
            self.sessions[session_id]['conversation'].append(message.to_dict())

    def get_conversation(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a session."""
        session = self.get_session(session_id)
        return session.get('conversation', []) if session else []

    def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session {session_id}")


class MemoryBank:
    """Long-term memory storage for persistent user preferences and facts."""

    def __init__(self):
        self.memory: Dict[str, MemoryEntry] = {}

    def store(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store a memory entry."""
        entry = MemoryEntry(
            key=key,
            value=value,
            timestamp=datetime.utcnow().isoformat(),
            ttl_seconds=ttl_seconds,
        )
        self.memory[key] = entry
        logger.info(f"Stored memory: {key}")

    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve a memory entry."""
        entry = self.memory.get(key)
        if entry:
            # Check TTL
            if entry.ttl_seconds:
                stored_time = datetime.fromisoformat(entry.timestamp)
                elapsed = (datetime.utcnow() - stored_time).total_seconds()
                if elapsed > entry.ttl_seconds:
                    del self.memory[key]
                    logger.info(f"Memory expired: {key}")
                    return None
            return entry.value
        return None

    def list_keys(self) -> List[str]:
        """List all memory keys."""
        return list(self.memory.keys())

    def delete(self, key: str) -> None:
        """Delete a memory entry."""
        if key in self.memory:
            del self.memory[key]
            logger.info(f"Deleted memory: {key}")

    def clear(self) -> None:
        """Clear all memory."""
        self.memory.clear()
        logger.info("Cleared all memory")


class ContextCompactor:
    """Compacts conversation context to reduce token usage."""

    @staticmethod
    def compact_conversation(messages: List[Dict[str, Any]], max_messages: int = 10) -> List[Dict[str, Any]]:
        """Keep only the most recent N messages."""
        if len(messages) <= max_messages:
            return messages
        return messages[-max_messages:]

    @staticmethod
    def summarize_messages(messages: List[Dict[str, Any]]) -> str:
        """Create a brief summary of message history."""
        if not messages:
            return "(no messages)"
        
        summary_lines = []
        for msg in messages[-5:]:  # Last 5 messages
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if len(content) > 100:
                content = content[:100] + '...'
            summary_lines.append(f"{role}: {content}")
        
        return "\n".join(summary_lines)
