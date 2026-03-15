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


def delete_agent_session(session_id: str) -> bool:
    """Remove an agent session by session_id. Returns True if it existed."""
    if session_id in _agent_sessions:
        del _agent_sessions[session_id]
        return True
    return False


def delete_sessions_for_user(user_id: str) -> int:
    """
    Remove ALL agent sessions associated with a given user_id.
    Scans all sessions — needed when we only know the user_id, not the session_id.
    Returns the number of sessions removed.
    """
    # A session_id is typically user_id or user_id + suffix; we match broadly.
    to_delete = [sid for sid, agent in _agent_sessions.items()
                 if getattr(agent, "session_id", "").startswith(user_id)
                 or sid.startswith(user_id)]
    for sid in to_delete:
        del _agent_sessions[sid]
    return len(to_delete)
