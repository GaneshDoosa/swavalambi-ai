"""
chat_persistence.py — Shared helpers for saving ProfilingAgent history to DynamoDB.

Both routes_chat.py and routes_voice.py use the ProfilingAgent and need to
serialize its in-memory messages and persist them to DynamoDB after every turn.
Centralizing this logic here ensures that fixes (e.g. stripping profile markers,
preserving image metadata) apply consistently across all entry points.
"""
import logging
from common.text_utils import strip_profile_markers
from services.dynamodb_service import update_chat_history

logger = logging.getLogger(__name__)


def save_agent_history(agent, user_id: str) -> int:
    """
    Serialize the ProfilingAgent's in-memory messages, strip any internal
    PROFILE_DATA markers, and save the cleaned history to DynamoDB.

    Image metadata preservation:
    The agent only carries plain text. When a work sample is uploaded,
    routes_vision.py caches the full image message (with s3Key, s3Bucket,
    imagePreviewUrl) in agent.image_messages keyed by the text content.
    Here we restore those rich records so they are never lost on save.
    No extra DB read is needed — the cache lives in agent memory.

    Returns the number of messages saved (0 if nothing was saved).
    """
    if not user_id:
        return 0

    try:
        inner = getattr(agent, "agent", None)
        if not inner or not getattr(inner, "messages", None):
            logger.debug("save_agent_history: no messages to save for user %s", user_id)
            return 0

        # In-memory image metadata cache set by routes_vision.py at upload time
        image_cache = getattr(agent, "image_messages", {})

        # ── Serialize agent messages ─────────────────────────────────────
        serialized = []
        for msg in inner.messages:
            role = None
            content_str = ""

            if isinstance(msg, dict):
                role = msg.get("role")
                content = msg.get("content")
            elif hasattr(msg, "role"):
                role = msg.role
                content = getattr(msg, "content", None)
            else:
                continue

            if not role:
                continue

            if content is None:
                content_str = ""
            elif isinstance(content, str):
                content_str = content
            elif isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, str):
                        parts.append(block)
                    elif isinstance(block, dict) and "text" in block:
                        parts.append(str(block["text"]))
                    elif hasattr(block, "text"):
                        parts.append(str(block.text))
                    elif hasattr(block, "__dict__") and "text" in block.__dict__:
                        parts.append(str(block.__dict__["text"]))
                content_str = " ".join(parts).strip()
            else:
                content_str = str(content)

            content_str = strip_profile_markers(content_str)

            if not content_str:
                continue

            # If this message matches a cached image upload, use the full rich record
            if role == "user" and content_str in image_cache:
                serialized.append(image_cache[content_str])
                logger.debug("save_agent_history: restored image metadata for: %s", content_str[:60])
            else:
                serialized.append({"role": role, "content": content_str})

        if not serialized:
            logger.warning("save_agent_history: serialized 0 messages for user %s", user_id)
            return 0

        update_chat_history(user_id, serialized)
        logger.info("save_agent_history: saved %d messages for user %s", len(serialized), user_id)
        return len(serialized)

    except Exception as e:
        logger.warning("save_agent_history: failed for user %s: %s", user_id, e)
        return 0
