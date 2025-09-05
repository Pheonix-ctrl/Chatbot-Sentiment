"""
Session-based memory management for chat conversations
Stores conversation history per session ID
"""

import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Simple in-memory storage for conversation history per session
    In production, this could be replaced with Redis or database storage
    """
    
    def __init__(self, max_messages_per_session: int = 20):
        self.sessions: Dict[str, List[Dict[str, Any]]] = {}
        self.session_timestamps: Dict[str, datetime] = {}
        self.max_messages = max_messages_per_session
        
    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        """
        Add a message to the session history
        
        Args:
            session_id: Unique session identifier
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional metadata (SQL query, results, etc.)
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = []
            
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.sessions[session_id].append(message)
        self.session_timestamps[session_id] = datetime.now()
        
        # Trim to max messages to prevent memory bloat
        if len(self.sessions[session_id]) > self.max_messages:
            # Keep the most recent messages
            self.sessions[session_id] = self.sessions[session_id][-self.max_messages:]
            
        logger.info(f"Added {role} message to session {session_id[:8]}...")
        
    def get_conversation_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get conversation history for a session
        
        Args:
            session_id: Session identifier
            limit: Optional limit on number of messages to return
            
        Returns:
            List of messages in OpenAI format [{"role": "user", "content": "..."}, ...]
        """
        if session_id not in self.sessions:
            return []
            
        messages = self.sessions[session_id]
        
        if limit:
            messages = messages[-limit:]
            
        # Convert to OpenAI format (remove our metadata)
        openai_messages = []
        for msg in messages:
            openai_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
            
        logger.info(f"Retrieved {len(openai_messages)} messages for session {session_id[:8]}...")
        return openai_messages
        
    def get_last_sql_query(self, session_id: str) -> Optional[str]:
        """
        Get the last SQL query executed in this session
        Useful for follow-up questions that reference previous results
        """
        if session_id not in self.sessions:
            return None
            
        # Look through recent messages for SQL metadata
        for message in reversed(self.sessions[session_id]):
            if message.get("metadata", {}).get("sql_query"):
                return message["metadata"]["sql_query"]
                
        return None
        
    def get_last_sql_results(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get the last SQL results from this session
        Useful for follow-up formatting questions
        """
        if session_id not in self.sessions:
            return None
            
        # Look through recent messages for SQL results
        for message in reversed(self.sessions[session_id]):
            if message.get("metadata", {}).get("sql_results"):
                return message["metadata"]["sql_results"]
                
        return None
        
    def cleanup_old_sessions(self, hours: int = 24):
        """
        Remove sessions older than specified hours to prevent memory bloat
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        sessions_to_remove = []
        
        for session_id, timestamp in self.session_timestamps.items():
            if timestamp < cutoff:
                sessions_to_remove.append(session_id)
                
        for session_id in sessions_to_remove:
            del self.sessions[session_id]
            del self.session_timestamps[session_id]
            logger.info(f"Cleaned up old session {session_id[:8]}...")
            
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """
        Get information about a session
        """
        if session_id not in self.sessions:
            return {"exists": False}
            
        return {
            "exists": True,
            "message_count": len(self.sessions[session_id]),
            "last_activity": self.session_timestamps[session_id].isoformat(),
            "has_sql_history": any(
                msg.get("metadata", {}).get("sql_query") 
                for msg in self.sessions[session_id]
            )
        }
        
    def clear_session(self, session_id: str):
        """Clear all history for a specific session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        logger.info(f"Cleared session {session_id[:8]}...")


# Global memory manager instance
memory_manager = MemoryManager()


# Convenience functions for easy use
def add_user_message(session_id: str, content: str):
    """Add a user message to session history"""
    memory_manager.add_message(session_id, "user", content)


def add_assistant_message(session_id: str, content: str, sql_query: str = None, sql_results: List[Dict] = None):
    """Add an assistant message with optional SQL metadata"""
    metadata = {}
    if sql_query:
        metadata["sql_query"] = sql_query
    if sql_results:
        metadata["sql_results"] = sql_results
        
    memory_manager.add_message(session_id, "assistant", content, metadata)


def get_conversation_history(session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent conversation history for OpenAI context"""
    return memory_manager.get_conversation_history(session_id, limit)


def get_last_sql_context(session_id: str) -> Dict[str, Any]:
    """Get the last SQL query and results for context"""
    return {
        "last_query": memory_manager.get_last_sql_query(session_id),
        "last_results": memory_manager.get_last_sql_results(session_id)
    }


def clear_session(session_id: str):
    """Clear session memory completely"""
    memory_manager.clear_session(session_id)


def get_session_info(session_id: str) -> Dict[str, Any]:
    """Get session information"""
    return memory_manager.get_session_info(session_id)