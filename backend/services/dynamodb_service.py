"""
dynamodb_service.py — DynamoDB CRUD helpers for Swavalambi user profiles.

Table: swavalambi_users
PK:   user_id  (phone number, e.g. "+919876543210")
"""

import boto3
import os
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_TABLE_NAME = os.getenv("DYNAMODB_TABLE", "swavalambi_users")


def _get_table():
    session = boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    )
    dynamodb = session.resource("dynamodb")
    return dynamodb.Table(_TABLE_NAME)


def create_or_update_user(user_id: str, name: str) -> dict:
    """
    Upsert a user record. Only sets name + created_at if not already present
    (so re-registration doesn't wipe assessment data).
    """
    table = _get_table()
    now = datetime.now(timezone.utc).isoformat()

    table.update_item(
        Key={"user_id": user_id},
        UpdateExpression=(
            "SET #n = if_not_exists(#n, :name), "
            "created_at = if_not_exists(created_at, :now), "
            "updated_at = :now"
        ),
        ExpressionAttributeNames={"#n": "name"},
        ExpressionAttributeValues={":name": name, ":now": now},
    )
    logger.info(f"Upserted user {user_id}")
    return {"user_id": user_id, "name": name}


def save_assessment(
    user_id: str,
    skill: str,
    intent: str,
    skill_rating: int,
    theory_score: int = 0,
    session_id: Optional[str] = None,
) -> None:
    """
    Persist the result of a skill assessment + profiling conversation.
    Called after vision analysis completes.
    """
    table = _get_table()
    now = datetime.now(timezone.utc).isoformat()

    update_expr = (
        "SET skill = :skill, intent = :intent, "
        "skill_rating = :rating, theory_score = :theory, "
        "updated_at = :now"
    )
    values = {
        ":skill": skill,
        ":intent": intent,
        ":rating": skill_rating,
        ":theory": theory_score,
        ":now": now,
    }
    if session_id:
        update_expr += ", session_id = :sid"
        values[":sid"] = session_id

    table.update_item(
        Key={"user_id": user_id},
        UpdateExpression=update_expr,
        ExpressionAttributeValues=values,
    )
    logger.info(f"Saved assessment for {user_id}: skill={skill}, rating={skill_rating}")


def save_profile_assessment(
    user_id: str,
    profile_data: dict
) -> None:
    """
    Save the complete profile assessment data from the profiling agent.
    Stores the structured assessment in DynamoDB with flexible schema.
    
    Args:
        user_id: User's phone number
        profile_data: Dictionary containing any key-value pairs extracted by the agent
                     (flexible schema to support dynamic questions)
    """
    logger.info(f"[SAVE_PROFILE] Starting save for user {user_id}")
    logger.info(f"[SAVE_PROFILE] Profile data keys: {list(profile_data.keys())}")
    logger.info(f"[SAVE_PROFILE] Profile data: {profile_data}")
    
    table = _get_table()
    now = datetime.now(timezone.utc).isoformat()
    
    # Add metadata to profile data
    profile_data_with_meta = {
        **profile_data,
        "assessment_timestamp": now,
        "assessment_version": "1.0"
    }

    # Update DynamoDB with complete profile data and key fields for quick access
    update_expr_parts = ["profile_assessment = :profile", "updated_at = :now"]
    expr_values = {
        ":profile": profile_data_with_meta,
        ":now": now,
    }
    
    # Dynamically add common fields if present (for backward compatibility and quick queries)
    if "profession_skill" in profile_data:
        update_expr_parts.append("skill = :skill")
        expr_values[":skill"] = profile_data["profession_skill"]
        logger.info(f"[SAVE_PROFILE] Setting skill = {profile_data['profession_skill']}")
    
    if "intent" in profile_data:
        update_expr_parts.append("intent = :intent")
        expr_values[":intent"] = profile_data["intent"]
        logger.info(f"[SAVE_PROFILE] Setting intent = {profile_data['intent']}")
    
    if "theory_score" in profile_data:
        update_expr_parts.append("theory_score = :theory")
        expr_values[":theory"] = profile_data["theory_score"]
        logger.info(f"[SAVE_PROFILE] Setting theory_score = {profile_data['theory_score']}")
    
    if "gender" in profile_data:
        update_expr_parts.append("gender = :gender")
        expr_values[":gender"] = profile_data["gender"]
        logger.info(f"[SAVE_PROFILE] Setting gender = {profile_data['gender']}")
    
    if "preferred_location" in profile_data:
        update_expr_parts.append("preferred_location = :location")
        expr_values[":location"] = profile_data["preferred_location"]
        logger.info(f"[SAVE_PROFILE] Setting preferred_location = {profile_data['preferred_location']}")

    update_expression = "SET " + ", ".join(update_expr_parts)
    logger.info(f"[SAVE_PROFILE] Update expression: {update_expression}")
    logger.info(f"[SAVE_PROFILE] Expression values: {expr_values}")
    
    table.update_item(
        Key={"user_id": user_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expr_values
    )
    logger.info(f"[SAVE_PROFILE] Successfully saved profile assessment for {user_id}: {profile_data.get('profession_skill', 'N/A')}, theory={profile_data.get('theory_score', 'N/A')}")


def get_user(user_id: str) -> Optional[dict]:
    """
    Fetch a user record by user_id (phone number).
    Returns None if the user does not exist.
    """
    table = _get_table()
    resp = table.get_item(Key={"user_id": user_id})
    item = resp.get("Item")
    if not item:
        return None
    # Convert Decimal → int for JSON serialisation
    for key in ("skill_rating", "theory_score"):
        if key in item:
            item[key] = int(item[key])
    return item


def delete_user(user_id: str) -> None:
    """
    Permanently delete a user record from DynamoDB by user_id.
    """
    table = _get_table()
    table.delete_item(Key={"user_id": user_id})
    logger.info(f"Deleted user {user_id}")

def update_chat_history(user_id: str, chat_history: list) -> None:
    """
    Appends or overwrites the chat history for a specific user.
    """
    table = _get_table()
    now = datetime.now(timezone.utc).isoformat()
    
    table.update_item(
        Key={"user_id": user_id},
        UpdateExpression="SET chat_history = :history, updated_at = :now",
        ExpressionAttributeValues={
            ":history": chat_history,
            ":now": now
        }
    )
    logger.info(f"Updated chat history for user {user_id}")


def clear_chat_history(user_id: str) -> None:
    """
    Clears the chat history for a specific user (for reassessment).
    """
    table = _get_table()
    now = datetime.now(timezone.utc).isoformat()
    
    table.update_item(
        Key={"user_id": user_id},
        UpdateExpression="SET chat_history = :empty, updated_at = :now",
        ExpressionAttributeValues={
            ":empty": [],
            ":now": now
        }
    )
    logger.info(f"Cleared chat history for user {user_id}")


def reset_assessment(user_id: str) -> None:
    """
    Completely resets a user's assessment data for retaking the assessment.
    Clears: skill, skill_rating, theory_score, intent, chat_history, session_id, profile_assessment
    Keeps: name, created_at, profile_picture, vision_upload_history
    """
    table = _get_table()
    now = datetime.now(timezone.utc).isoformat()
    
    table.update_item(
        Key={"user_id": user_id},
        UpdateExpression=(
            "SET skill = :empty_str, "
            "skill_rating = :zero, "
            "theory_score = :zero, "
            "intent = :default_intent, "
            "chat_history = :empty_list, "
            "updated_at = :now "
            "REMOVE session_id, profile_assessment, gender, preferred_location"
        ),
        ExpressionAttributeValues={
            ":empty_str": "",
            ":zero": 0,
            ":default_intent": "job",
            ":empty_list": [],
            ":now": now
        }
    )
    logger.info(f"Reset assessment data for user {user_id}")

