"""
text_utils.py — Shared text processing utilities
"""


def strip_profile_markers(text: str) -> str:
    """
    Remove PROFILE_DATA_START...PROFILE_DATA_END blocks (and the JSON inside)
    from a message string. Returns the cleaned text.

    This prevents internal profile JSON from leaking into the chat UI or
    being stored in DynamoDB when the LLM embeds the block in its response.
    Uses a loop to handle multiple occurrences in one string.
    """
    start_marker = "PROFILE_DATA_START"
    end_marker = "PROFILE_DATA_END"
    while start_marker in text and end_marker in text:
        s = text.find(start_marker)
        e = text.find(end_marker) + len(end_marker)
        text = (text[:s].strip() + "\n\n" + text[e:].strip()).strip()
    return text
