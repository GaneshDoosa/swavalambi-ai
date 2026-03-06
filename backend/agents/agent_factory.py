"""
agent_factory.py — Singleton factory for agent instances
"""

import os
from typing import Optional
from agents.jobs.jobs_agent import JobsAgent
from agents.scheme.scheme_agent import SchemeAgent
from agents.upskill.upskill_agent import UpskillAgent
from common.providers.provider_factory import get_embedding_provider
from common.stores.vector_stores import PostgresPgVectorStore

# Global singleton instances
_jobs_agent_instance: Optional[JobsAgent] = None
_scheme_agent_instance: Optional[SchemeAgent] = None
_upskill_agent_instance: Optional[UpskillAgent] = None
_vector_store_instance: Optional[PostgresPgVectorStore] = None


def get_vector_store() -> PostgresPgVectorStore:
    """
    Get or create the singleton vector store instance.
    
    This ensures only one PostgreSQL connection pool exists across the application.
    """
    global _vector_store_instance
    
    if _vector_store_instance is None:
        _vector_store_instance = PostgresPgVectorStore(
            connection_string=os.getenv("POSTGRES_CONNECTION_STRING")
        )
    
    return _vector_store_instance


def get_jobs_agent() -> JobsAgent:
    """Get or create the singleton jobs agent instance."""
    global _jobs_agent_instance
    
    if _jobs_agent_instance is None:
        _jobs_agent_instance = JobsAgent(
            embedding_provider=get_embedding_provider(),
            vector_store=get_vector_store(),
            index_name="jobs"
        )
    
    return _jobs_agent_instance


def get_scheme_agent() -> SchemeAgent:
    """Get or create the singleton scheme agent instance."""
    global _scheme_agent_instance
    
    if _scheme_agent_instance is None:
        _scheme_agent_instance = SchemeAgent(
            embedding_provider=get_embedding_provider(),
            vector_store=get_vector_store(),
            index_name="schemes"
        )
    
    return _scheme_agent_instance


def get_upskill_agent() -> UpskillAgent:
    """Get or create the singleton upskill agent instance."""
    global _upskill_agent_instance
    
    if _upskill_agent_instance is None:
        _upskill_agent_instance = UpskillAgent(
            embedding_provider=get_embedding_provider(),
            vector_store=get_vector_store(),
            index_name="upskill"
        )
    
    return _upskill_agent_instance


def reset_agents():
    """Reset all singleton instances (useful for testing)"""
    global _jobs_agent_instance, _scheme_agent_instance, _upskill_agent_instance, _vector_store_instance
    _jobs_agent_instance = None
    _scheme_agent_instance = None
    _upskill_agent_instance = None
    _vector_store_instance = None
