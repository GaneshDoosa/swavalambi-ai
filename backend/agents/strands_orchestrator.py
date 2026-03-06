"""
strands_orchestrator.py — Intent-based orchestrator
Calls only the relevant tool based on user intent
"""
import os
import logging
from typing import Dict, List, Any
from dotenv import load_dotenv

from agents.scheme.scheme_tool import search_schemes_tool
from agents.jobs.jobs_tool import search_jobs_tool
from agents.upskill.upskill_tool import search_upskill_tool
from common.providers.provider_factory import get_embedding_provider

load_dotenv()

logger = logging.getLogger(__name__)

# Get singleton embedding provider instance
_embedding_provider = get_embedding_provider()


def orchestrate(user_profile: Dict[str, Any] = None, task: str = None, context: Dict[str, Any] = None, max_iterations: int = 10) -> Dict[str, Any]:
    """
    Intent-based orchestration - calls only the relevant tool based on user intent.
    
    Supported intents:
    - 'job' -> search_jobs_tool
    - 'upskill' -> search_upskill_tool
    - 'loan' -> search_schemes_tool
    
    Args:
        user_profile: User profile dict (for recommendations)
        task: High-level task description (for complex workflows)
        context: Additional context
        max_iterations: Maximum agentic loop iterations (unused in direct mode)
    
    Returns:
        Dictionary with results from the invoked agent
    """
    import time
    start_time = time.time()
    
    print(f"\n{'='*60}")
    print("INTENT-BASED ORCHESTRATION STARTED")
    print(f"{'='*60}")
    
    if not user_profile:
        raise ValueError("Must provide user_profile")
    
    # Extract profile fields
    skill = user_profile.get('profession_skill', user_profile.get('skill', ''))
    intent = user_profile.get('intent', 'job').lower()
    skill_level = user_profile.get('skill_rating', user_profile.get('skill_level', 3))
    state = user_profile.get('preferred_location', user_profile.get('state', 'All India'))
    
    print(f"\n📋 User Profile:")
    print(f"  Skill: {skill}")
    print(f"  Intent: {intent}")
    print(f"  Level: {skill_level}/5")
    print(f"  Location: {state}")
    
    # Generate embedding once (optimization)
    print(f"\n🔄 Generating embedding...")
    embed_start = time.time()
    query_text = f"{skill} {intent} {state}"
    query_embedding = _embedding_provider.generate_embedding(query_text)
    embed_time = time.time() - embed_start
    print(f"✅ Embedding generated (1024 dimensions) in {embed_time:.3f}s")
    
    # Initialize empty results
    jobs = []
    schemes = []
    training_centers = []
    
    # Call only the relevant tool based on intent
    print(f"\n🔍 Calling tool based on intent: '{intent}'")
    tool_start = time.time()
    
    if intent == 'job':
        print(f"  → Searching jobs...")
        tool_call_start = time.time()
        salary_expectation = user_profile.get('salary_expectation')
        print(f"  💰 Salary from profile: {salary_expectation}")
        jobs = search_jobs_tool(skill, skill_level, state, query_embedding=query_embedding, salary_expectation=salary_expectation)[:5]
        tool_call_time = time.time() - tool_call_start
        print(f"  → Tool call completed in {tool_call_time:.3f}s")
        print(f"  ✅ Found {len(jobs)} jobs")
        message = f"Found {len(jobs)} job opportunities for {skill} professionals in {state}."
        
    elif intent == 'upskill':
        print(f"  → Searching training centers...")
        tool_call_start = time.time()
        training_centers = search_upskill_tool(skill, skill_level, state, query_embedding=query_embedding)[:5]
        tool_call_time = time.time() - tool_call_start
        print(f"  → Tool call completed in {tool_call_time:.3f}s")
        print(f"  ✅ Found {len(training_centers)} training centers")
        message = f"Found {len(training_centers)} training programs for {skill} in {state}."
        
    elif intent == 'loan':
        print(f"  → Searching schemes...")
        tool_call_start = time.time()
        schemes = search_schemes_tool(skill, intent, skill_level, state, query_embedding=query_embedding)[:5]
        tool_call_time = time.time() - tool_call_start
        print(f"  → Tool call completed in {tool_call_time:.3f}s")
        print(f"  ✅ Found {len(schemes)} schemes")
        message = f"Found {len(schemes)} government schemes for {skill} professionals in {state}."
        
    else:
        # Default to job search if intent is not recognized
        print(f"  ⚠️  Unknown intent '{intent}', defaulting to job search...")
        tool_call_start = time.time()
        jobs = search_jobs_tool(skill, skill_level, state, query_embedding=query_embedding)[:5]
        tool_call_time = time.time() - tool_call_start
    tool_time = time.time() - tool_start
    
    total_time = time.time() - start_time
    print(f"\n⏱️  Performance:")
    print(f"  Embedding: {embed_time:.3f}s")
    print(f"  Tool execution: {tool_time:.3f}s")
    print(f"  Total: {total_time:.3f}s")
    
    total_time = time.time() - start_time
    print(f"\n⏱️  Performance:")
    print(f"  Embedding: {embed_time:.3f}s")
    print(f"  Tool execution: {tool_time:.3f}s")
    print(f"  Total: {total_time:.3f}s")
    
   
    all_results = {
        "profile": None,
        "vision_analysis": None,
        "jobs": jobs,
        "schemes": schemes,
        "training_centers": training_centers,
        "conversation": [],
        "summary": message
    }
     
    return all_results


# Convenience function for recommendations (backward compatibility)
def orchestrate_recommendations(user_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience wrapper for recommendation use case"""
    return orchestrate(user_profile=user_profile, max_iterations=5)


def _deduplicate_by_id(items: List[Dict]) -> List[Dict]:
    """Remove duplicate items based on id field"""
    seen = set()
    unique = []
    for item in items:
        item_id = item.get('id') or item.get('scheme_id') or item.get('job_id')
        if item_id and item_id not in seen:
            seen.add(item_id)
            unique.append(item)
        elif not item_id:
            unique.append(item)
    return unique
