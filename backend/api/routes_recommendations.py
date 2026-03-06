"""
routes_recommendations.py — Agentic personalized recommendations endpoint.

POST /api/recommendations/fetch
  Body: { session_id, user_id?, profession_skill?, intent?, skill_rating?, state? }

Returns relevant jobs, schemes, and/or training centers based on the
user's profile using agentic orchestration with Strands + Bedrock.

The orchestrator uses Claude on Bedrock (via Strands) to intelligently 
decide which agents to invoke as tools based on the user's profile and intent.

Usage:
- Send user_id to fetch full profile from DynamoDB (recommended)
- Optionally override intent in request to control which agent is called
- Or send individual fields (profession_skill, intent, skill_rating) for backward compatibility
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import asyncio

from agents.strands_orchestrator import orchestrate_recommendations
from services.dynamodb_service import get_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class RecommendationRequest(BaseModel):
    session_id: str
    user_id: Optional[str] = None           # DynamoDB user ID (when provided, fetches profile)
    intent: Optional[str] = None            # Intent override (job/upskill/loan)
    
    # Fallback fields (used when user_id is not provided)
    profession_skill: Optional[str] = None
    skill_rating: Optional[int] = None
    state: Optional[str] = None
    location: Optional[str] = None          # Alias for state


class RecommendationResponse(BaseModel):
    jobs: list = []
    schemes: list = []
    training_centers: list = []
    message: str = ""


@router.post("/fetch", response_model=RecommendationResponse)
async def get_recommendations(req: RecommendationRequest):
    """
    Fetch personalized recommendations using direct orchestration.
    
    Flow:
    1. Get user profile from DynamoDB (if user_id provided)
    2. Build user profile JSON with skill, intent, rating, state
    3. Call direct orchestrator (queries PostgreSQL directly)
    4. Return formatted response
    """
    logger.info(f"Recommendation request: session_id={req.session_id}, user_id={req.user_id}")
    
    # Step 1: Get user profile - either from DynamoDB or from request params
    user_profile = {}
    
    if req.user_id:
        # Path A: Fetch from DynamoDB
        logger.info(f"Fetching profile from DynamoDB for user_id={req.user_id}")
        try:
            user_data = get_user(req.user_id)
            if not user_data or "profile_assessment" not in user_data:
                logger.warning(f"User profile not found in DynamoDB: {req.user_id}")
                raise HTTPException(status_code=404, detail="User profile not found in DynamoDB")
            
            profile_assessment = user_data["profile_assessment"]
            
            # Required fields
            if "profession_skill" not in profile_assessment:
                raise HTTPException(status_code=400, detail="profession_skill missing in profile")
            
            user_profile["profession_skill"] = profile_assessment["profession_skill"]
            
            # Intent: Use request override if provided, otherwise use profile intent
            if req.intent:
                user_profile["intent"] = req.intent.strip().lower()
                logger.info(f"Using intent override from request: {user_profile['intent']}")
            elif "intent" in profile_assessment:
                user_profile["intent"] = profile_assessment["intent"]
            else:
                raise HTTPException(status_code=400, detail="intent missing in profile and not provided in request")
            
            user_profile["skill_rating"] = int(profile_assessment.get("theory_score", 3))
            
            # Set location (both state and preferred_location for compatibility)
            location = profile_assessment.get("preferred_location", "All India")
            user_profile["state"] = location
            user_profile["preferred_location"] = location
            if profile_assessment.get("salary_expectation"):
               try:
                   user_profile["salary_expectation"] = int(profile_assessment["salary_expectation"])
                   logger.info(f"Parsed salary_expectation: {user_profile['salary_expectation']}")
               except (ValueError, TypeError) as e:
                   logger.warning(f"Failed to parse salary_expectation: {e}")
            # Additional context fields
            if profile_assessment.get("gender"):
                user_profile["gender"] = profile_assessment["gender"]
            if profile_assessment.get("has_training") is not None:
                user_profile["has_training"] = profile_assessment["has_training"]
            if profile_assessment.get("work_type"):
                user_profile["work_type"] = profile_assessment["work_type"]
            if profile_assessment.get("years_experience"):
                user_profile["years_experience"] = int(profile_assessment["years_experience"])
            
            logger.info(f"Profile loaded: skill={user_profile['profession_skill']}, intent={user_profile['intent']}")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching user from DynamoDB: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to fetch user profile: {str(e)}")
    
    else:
        # Path B: Use request parameters (backward compatibility with frontend)
        logger.info("Using request parameters (no user_id provided)")
        if not req.profession_skill or not req.intent:
            raise HTTPException(status_code=400, detail="Either user_id or (profession_skill + intent) required")
        
        user_profile["profession_skill"] = req.profession_skill.strip()
        user_profile["intent"] = req.intent.strip().lower()
        user_profile["skill_rating"] = req.skill_rating or 3
        user_profile["state"] = req.state or req.location or "All India"
    
    # Step 2: Call direct orchestrator
    logger.info("Calling orchestrator")
    loop = asyncio.get_event_loop()
    try:
        results = await loop.run_in_executor(
            None, 
            orchestrate_recommendations, 
            user_profile
        )
        logger.info("Orchestrator completed successfully")
    except Exception as e:
        logger.error(f"Orchestration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Orchestration failed: {str(e)}")
    
    # Step 3: Extract results and format response
    jobs_data = results.get("jobs", [])
    schemes_data = results.get("schemes", [])
    centers_data = results.get("training_centers", [])
    summary = results.get("summary", "")
    
    # Build fallback message if orchestrator didn't provide one
    if not summary:
        parts = []
        if jobs_data:      parts.append(f"{len(jobs_data)} job openings")
        if schemes_data:   parts.append(f"{len(schemes_data)} government schemes")
        if centers_data:   parts.append(f"{len(centers_data)} training centres")
        summary = (
            "Here are your personalized recommendations: " + ", ".join(parts) + "."
            if parts else
            "No results found right now — please try again shortly."
        )
    
    return RecommendationResponse(
        jobs=jobs_data,
        schemes=schemes_data,
        training_centers=centers_data,
        message=summary,
    )
