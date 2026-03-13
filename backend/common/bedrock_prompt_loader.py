"""
bedrock_prompt_loader.py

Utility for fetching prompt text from AWS Bedrock Prompt Management.
Uses the `bedrock-agent` boto3 client (NOT bedrock-runtime).

Usage:
    from common.bedrock_prompt_loader import get_prompt_text

    text = get_prompt_text(
        prompt_id="arn:aws:bedrock:us-east-1:123456789012:prompt/abc123",
        version="DRAFT",                   # "DRAFT" or "1", "2", etc.
        variables={"user_language": "Hindi", "known_user_context": ""},
        boto_session=self.boto3_session,
    )

Variable substitution:
    Bedrock prompts can contain {{variable_name}} placeholders.
    Pass a `variables` dict and they will be substituted before returning.

Caching:
    Prompts are cached in memory (per process) keyed by (prompt_id, version).
    This avoids redundant API calls across multiple agent instantiations.

IAM requirement:
    The IAM role/user must have `bedrock:GetPrompt` permission on the prompt ARN.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# In-process cache: (prompt_id, version) -> raw prompt text
_prompt_cache: dict[tuple[str, str], str] = {}


def get_prompt_text(
    prompt_id: str,
    version: str = "DRAFT",
    variables: Optional[dict] = None,
    boto_session=None,
) -> str:
    """
    Fetches a prompt from AWS Bedrock Prompt Management and returns its text
    with any `{{variable}}` placeholders substituted from `variables`.

    Args:
        prompt_id:     Prompt ID or full ARN from Bedrock Prompt Management.
        version:       Prompt version — "DRAFT" or a numeric string like "1".
        variables:     Dict of variable names → values to substitute in the prompt.
        boto_session:  An existing boto3.Session to reuse credentials/region.
                       If None, boto3 uses the default credential chain.

    Returns:
        The resolved prompt text string.

    Raises:
        ValueError:   If no prompt text could be extracted from the response.
        Exception:    Propagates any boto3/API errors.
    """
    import boto3

    cache_key = (prompt_id, version)
    if cache_key in _prompt_cache:
        raw_text = _prompt_cache[cache_key]
        logger.info(
            f"[BedrockPromptLoader] Cache hit for prompt '{prompt_id}' v{version}"
        )
    else:
        # Use the provided session or fall back to default boto3 session
        if boto_session is not None:
            client = boto_session.client("bedrock-agent")
        else:
            client = boto3.client("bedrock-agent")

        logger.info(
            f"[BedrockPromptLoader] Fetching prompt '{prompt_id}' v{version} from Bedrock..."
        )

        response = client.get_prompt(
            promptIdentifier=prompt_id,
            promptVersion=version,
        )

        # The API response contains a list of variant objects.
        # Each variant has a `templateConfiguration` with a `text` entry.
        raw_text = _extract_text_from_response(response, prompt_id)
        _prompt_cache[cache_key] = raw_text

        prompt_name = response.get("name", prompt_id)
        logger.info(
            f"[BedrockPromptLoader] Loaded prompt '{prompt_name}' "
            f"({len(raw_text)} chars) from Bedrock Prompt Management."
        )

    # Substitute {{variable}} placeholders
    if variables:
        for key, value in variables.items():
            raw_text = raw_text.replace("{{" + key + "}}", str(value) if value is not None else "")

    return raw_text


def _extract_text_from_response(response: dict, prompt_id: str) -> str:
    """
    Extracts the raw prompt text from a `get_prompt` API response.

    AWS stores prompts under response['variants'][0]['templateConfiguration']['text']['text']
    We try the first TEXT variant we find.
    """
    variants = response.get("variants", [])
    if not variants:
        raise ValueError(
            f"Bedrock Prompt Management returned no variants for prompt '{prompt_id}'. "
            f"Make sure the prompt exists and has at least one variant."
        )

    for variant in variants:
        template_config = variant.get("templateConfiguration", {})

        # TEXT template type
        text_config = template_config.get("text", {})
        if text_config and "text" in text_config:
            return text_config["text"]

        # CHAT template type — concatenate system + user messages
        chat_config = template_config.get("chat", {})
        if chat_config:
            parts = []
            system_messages = chat_config.get("system", [])
            for msg in system_messages:
                if "text" in msg:
                    parts.append(msg["text"])
            messages = chat_config.get("messages", [])
            for msg in messages:
                role = msg.get("role", "").upper()
                for block in msg.get("content", []):
                    if "text" in block:
                        parts.append(f"[{role}]\n{block['text']}")
            if parts:
                return "\n\n".join(parts)

    raise ValueError(
        f"Could not extract text from any variant of prompt '{prompt_id}'. "
        f"Response variants: {variants}"
    )


def clear_cache() -> None:
    """Clears the in-memory prompt cache. Useful in tests or when you want to force a refresh."""
    _prompt_cache.clear()
    logger.info("[BedrockPromptLoader] Prompt cache cleared.")


def get_prompt_parts(
    prompt_id: str,
    version: str = "DRAFT",
    variables: Optional[dict] = None,
    boto_session=None,
) -> dict:
    """
    Fetches a Chat-template prompt from Bedrock Prompt Management and returns
    a dict with 'system' and 'user' keys — extracted from System instructions
    and the first User message respectively.

    Useful when you have one combined Bedrock prompt (e.g. swavalambi-vision-agent)
    that stores both the system prompt and user prompt in a single Chat template.

    Falls back gracefully:
    - If the prompt is a TEXT template (not Chat), returns the full text as 'system' and '' as 'user'.
    - Substitutes {{variable}} placeholders in both parts.

    Returns:
        {"system": "...", "user": "..."}
    """
    import boto3

    cache_key = (prompt_id, version)
    if cache_key in _prompt_cache:
        raw_response = _prompt_cache[cache_key]
        logger.info(f"[BedrockPromptLoader] Cache hit (parts) for '{prompt_id}' v{version}")
    else:
        if boto_session is not None:
            client = boto_session.client("bedrock-agent")
        else:
            client = boto3.client("bedrock-agent")

        logger.info(f"[BedrockPromptLoader] Fetching prompt parts '{prompt_id}' v{version}...")
        raw_response = client.get_prompt(promptIdentifier=prompt_id, promptVersion=version)
        _prompt_cache[cache_key] = raw_response
        logger.info(f"[BedrockPromptLoader] Loaded prompt '{raw_response.get('name', prompt_id)}' from Bedrock.")

    variants = raw_response.get("variants", [])
    if not variants:
        raise ValueError(f"No variants found for prompt '{prompt_id}'.")

    variant = variants[0]
    template_config = variant.get("templateConfiguration", {})

    system_text = ""
    user_text = ""

    chat_config = template_config.get("chat", {})
    if chat_config:
        # Extract system instructions
        for msg in chat_config.get("system", []):
            if "text" in msg:
                system_text += msg["text"]
        # Extract first user message
        for msg in chat_config.get("messages", []):
            if msg.get("role") == "user":
                for block in msg.get("content", []):
                    if "text" in block:
                        user_text += block["text"]
                break
    else:
        # TEXT template — treat whole thing as system prompt
        text_config = template_config.get("text", {})
        system_text = text_config.get("text", "")

    # Substitute {{variable}} placeholders in both parts
    if variables:
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            replacement = str(value) if value is not None else ""
            system_text = system_text.replace(placeholder, replacement)
            user_text = user_text.replace(placeholder, replacement)

    return {"system": system_text, "user": user_text}

