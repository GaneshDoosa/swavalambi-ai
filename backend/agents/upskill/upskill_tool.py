"""
upskill_tool.py — Upskill/training search tool definition
"""
from typing import Dict, List
import os
from dotenv import load_dotenv

load_dotenv()

def search_upskill_tool(skill: str, skill_level: int, state: str, query_embedding: List[float] = None) -> List[Dict]:
    """
    Search for training courses based on user's skill and location.
    
    Args:
        skill: User's skill or profession
        skill_level: Skill proficiency level from 1-5
        state: User's state in India
        query_embedding: Pre-generated embedding vector (optional, for performance)
    
    Returns:
        List of relevant training courses ranked by match score
    """
    from agents.agent_factory import get_upskill_agent
    
    # Use singleton agent instance
    agent = get_upskill_agent()
    
    user_profile = {
        "skill": skill,
        "skill_level": skill_level,
        "state": state
    }
    
    return agent.search_courses(user_profile, limit=5, query_embedding=query_embedding)

UPSKILL_TOOL_DEFINITION = {
    "name": "search_upskill",
    "description": "Search for training courses based on user's skill and location. Returns relevant courses ranked by match score.",
    "input_schema": {
        "type": "object",
        "properties": {
            "skill": {
                "type": "string",
                "description": "User's skill or profession"
            },
            "skill_level": {
                "type": "integer",
                "description": "Skill proficiency level from 1-5"
            },
            "state": {
                "type": "string",
                "description": "User's state in India"
            }
        },
        "required": ["skill", "skill_level", "state"]
    }
}
