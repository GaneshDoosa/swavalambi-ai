"""
agent_sessions.py — Shared agent session storage for chat and voice routes
"""

# Shared in-memory dictionary to hold Agent instances mapped by session_id
# This ensures voice and text chat use the same agent instance
_agent_sessions = {}


def get_agent_session(session_id: str):
    """Get agent session by session_id"""
    return _agent_sessions.get(session_id)


def set_agent_session(session_id: str, agent):
    """Set agent session for session_id"""
    _agent_sessions[session_id] = agent


def has_agent_session(session_id: str) -> bool:
    """Check if agent session exists"""
    return session_id in _agent_sessions
