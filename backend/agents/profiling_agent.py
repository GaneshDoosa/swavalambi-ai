from strands import Agent
from strands.models import BedrockModel, AnthropicModel
import boto3
import os
import json
import logging

logger = logging.getLogger(__name__)

try:
    from common.bedrock_prompt_loader import get_prompt_text as _get_bedrock_prompt
except ImportError:
    _get_bedrock_prompt = None

# Supported skills - limited to these 5 only
SUPPORTED_SKILLS = {
    "tailor": ["tailor", "tailoring", "sewing", "stitching", "garment"],
    "carpenter": ["carpenter", "carpentry", "wood", "woodwork", "woodworking"],
    "plumber": ["plumber", "plumbing"],
    "welder": ["welder", "welding", "weld"],
    "beautician": ["beautician", "beauty", "makeup", "hair", "salon", "cosmetology"]
}


def normalize_skill(skill_input: str) -> str:
    """
    Normalize user skill input to one of the 5 supported skills.
    Returns the normalized skill or the original input if no match.
    """
    if not skill_input:
        return skill_input
    
    skill_lower = skill_input.lower().strip()
    
    # Check each supported skill and its variations
    for canonical_skill, variations in SUPPORTED_SKILLS.items():
        if skill_lower in variations or any(var in skill_lower for var in variations):
            return canonical_skill
    
    # Return original if no match (agent will handle guiding user)
    return skill_input

class ProfilingAgent:
    def __init__(self, session_id: str, user_name: str = "", preferred_language: str = "en-IN", has_uploaded_photo: bool = False):
        self.session_id = session_id
        self.user_name = user_name
        self.preferred_language = preferred_language
        self.has_uploaded_photo = has_uploaded_photo  # Store so routes can override is_ready_for_photo
        
        # Build a boto3 session for Bedrock models
        self.boto3_session = boto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        )
        
        # Check if we should use the direct Anthropic API or AWS Bedrock
        self.use_anthropic = os.getenv("USE_ANTHROPIC", "false").lower() == "true"
        
        # Initialize primary model (Claude)
        if self.use_anthropic:
            model_id = os.getenv("ANTHROPIC_MODEL_ID", "claude-3-5-sonnet-latest")
            api_key = os.getenv("ANTHROPIC_API_KEY")
            
            self.primary_model = AnthropicModel(
                model_id=model_id,
                max_tokens=1000,
                params={"temperature": 0.7},
                client_args={"api_key": api_key}
            )
        else:
            model_id = os.getenv("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-5-20250929-v1:0")
            
            self.primary_model = BedrockModel(
                model_id=model_id,
                temperature=0.7,
                boto_session=self.boto3_session,
            )
        
        # Initialize fallback model (Amazon Nova)
        fallback_model_id = os.getenv("FALLBACK_MODEL_ID", "us.amazon.nova-lite-v1:0")
        self.fallback_model = BedrockModel(
            model_id=fallback_model_id,
            temperature=0.7,
            boto_session=self.boto3_session,
        )

        # Build user-context preamble if name is known
        if user_name and not user_name.isdigit() and len(user_name.strip()) > 1:
            known_user_context = (
                f"\n\n        IMPORTANT USER CONTEXT: The user's name is already known — it is '{user_name}'. "
                f"You MUST NOT ask for their name again. Address them as '{user_name}' naturally in conversation. "
                f"Skip the name-collection step and go directly to asking about their profession/skill.\n"
            )
        else:
            known_user_context = ""

        # Language mapping for instruction
        language_names: dict[str, str] = {
            "hi-IN": "Hindi (हिंदी)",
            "te-IN": "Telugu (తెలుగు)",
            "ta-IN": "Tamil (தமிழ்)",
            "mr-IN": "Marathi (मराठी)",
            "kn-IN": "Kannada (ಕನ್ನಡ)",
            "bn-IN": "Bengali (বাংলা)",
            "gu-IN": "Gujarati (ગુજરાતી)",
            "ml-IN": "Malayalam (മലയാളം)",
            "pa-IN": "Punjabi (ਪੰਜਾਬੀ)",
            "en-IN": "English"
        }
        user_language = language_names.get(preferred_language, "English")

        # -------------------------------------------------------------------------
        # Load system prompt from Bedrock Prompt Management (with fallback)
        # -------------------------------------------------------------------------
        self.system_prompt = self._load_system_prompt(
            user_language=user_language,
            known_user_context=known_user_context,
            preferred_language=preferred_language,
            has_uploaded_photo=has_uploaded_photo
        )

        # Create the Strands Agent with the system prompt
        self.agent = Agent(
            model=self.primary_model,
            system_prompt=self.system_prompt,
        )

        # Create fallback agent with Nova
        self.fallback_agent = Agent(
            model=self.fallback_model,
            system_prompt=self.system_prompt,
        )

    def update_language(self, new_language_code: str):
        """
        Dynamically update the agent's language and rebuild the system prompt.
        This allows mid-session language changes without losing conversation history.
        """
        self.preferred_language = new_language_code
        
        # Mapping for instruction
        language_names: dict[str, str] = {
            "hi-IN": "Hindi (हिंदी)",
            "te-IN": "Telugu (తెలుగు)",
            "ta-IN": "Tamil (தமிழ்)",
            "mr-IN": "Marathi (मराठी)",
            "kn-IN": "Kannada (ಕನ್ನಡ)",
            "bn-IN": "Bengali (বাংলা)",
            "gu-IN": "Gujarati (ગુજરાતી)",
            "ml-IN": "Malayalam (മലയാളം)",
            "pa-IN": "Punjabi (ਪੰਜਾਬੀ)",
            "en-IN": "English"
        }
        user_language = language_names.get(new_language_code, "English")
        
        # Build user-context preamble (re-using current logic)
        if self.user_name and not self.user_name.isdigit() and len(self.user_name.strip()) > 1:
            known_user_context = (
                f"\n\n        IMPORTANT USER CONTEXT: The user's name is already known — it is '{self.user_name}'. "
                f"You MUST NOT ask for their name again. Address them as '{self.user_name}' naturally in conversation. "
                f"Skip the name-collection step and go directly to asking about their profession/skill.\n"
            )
        else:
            known_user_context = ""
        
        # Re-load system prompt
        self.system_prompt = self._load_system_prompt(
            user_language=user_language,
            known_user_context=known_user_context,
            preferred_language=new_language_code,
            has_uploaded_photo=self.has_uploaded_photo
        )
        
        # Update live agents
        self.agent.system_prompt = self.system_prompt
        self.fallback_agent.system_prompt = self.system_prompt
        
        logger.info(f"[ProfilingAgent] Session {self.session_id} updated language to {new_language_code}")

    def _load_system_prompt(self, user_language: str, known_user_context: str, preferred_language: str, has_uploaded_photo: bool) -> str:
        """
        Attempts to load the system prompt from AWS Bedrock Prompt Management.
        Falls back to the hardcoded inline prompt if:
          - BEDROCK_PROFILING_PROMPT_ID env var is not set, or
          - the bedrock_prompt_loader is not importable, or
          - the API call fails for any reason.
        """
        prompt_id = os.getenv("BEDROCK_PROFILING_PROMPT_ID", "").strip()
        prompt_version = os.getenv("BEDROCK_PROFILING_PROMPT_VERSION") or os.getenv("BEDROCK_PROMPT_VERSION", "DRAFT")

        if prompt_id and _get_bedrock_prompt is not None:
            try:
                text = _get_bedrock_prompt(
                    prompt_id=prompt_id,
                    version=prompt_version,
                    variables={
                        "user_language": user_language,
                        "known_user_context": known_user_context,
                        "preferred_language": preferred_language,
                        "has_uploaded_photo": str(has_uploaded_photo).lower(),
                    },
                    boto_session=self.boto3_session,
                )
                logger.info(
                    "[ProfilingAgent] System prompt loaded from Bedrock Prompt Management "
                    f"(id={prompt_id}, version={prompt_version})"
                )
                return text
            except Exception as exc:
                logger.warning(
                    f"[ProfilingAgent] Failed to load prompt from Bedrock (id={prompt_id}): {exc}. "
                    "Falling back to hardcoded prompt."
                )
        else:
            if not prompt_id:
                logger.info(
                    "[ProfilingAgent] BEDROCK_PROFILING_PROMPT_ID not set — using hardcoded system prompt."
                )

        # ---- Hardcoded fallback prompt (original) --------------------------------
        return self._hardcoded_system_prompt(user_language, known_user_context, preferred_language, has_uploaded_photo)

    def _hardcoded_system_prompt(self, user_language: str, known_user_context: str, preferred_language: str, has_uploaded_photo: bool = False) -> str:
        """Returns the system prompt loaded from the external text file."""
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "profiling_prompt.txt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                template = f.read()
            return template.format(
                user_language=user_language,
                known_user_context=known_user_context,
                preferred_language=preferred_language,
                has_uploaded_photo=has_uploaded_photo
            )
        except Exception as e:
            logger.error(f"Failed to load profiling_prompt.txt: {e}")
            # Fallback tiny prompt just to not crash, though we should fix the file if this happens
            return f"You are a helpful assistant. Error loading prompt: {e}"

        # Initialize the Strands Agent with the primary model (Claude)
        self.agent = Agent(
            system_prompt=self.system_prompt,
            model=self.primary_model,
        )
        
        # Initialize fallback agent with Nova model
        self.fallback_agent = Agent(
            system_prompt=self.system_prompt,
            model=self.fallback_model,
        )

    def _sanitize_messages(self, agent) -> None:
        """
        Remove any empty text content blocks from agent.messages before
        sending to Anthropic. Claude rejects requests where any content
        block has an empty 'text' field.

        This can happen when:
        - Chat history is restored from DynamoDB with near-empty messages
        - Profile data stripping leaves an otherwise-empty assistant message
        - Strands internally inserts placeholder blocks during tool use
        """
        if not hasattr(agent, "messages") or not agent.messages:
            return
        sanitized = []
        for msg in agent.messages:
            if isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, list):
                    clean_blocks = [
                        block for block in content
                        if not (isinstance(block, dict)
                                and block.get("type", "text") == "text"
                                and not block.get("text", "").strip())
                    ]
                    if not clean_blocks:
                        continue  # skip message entirely if all blocks were empty
                    msg = dict(msg)
                    msg["content"] = clean_blocks
                elif isinstance(content, str) and not content.strip():
                    continue  # skip message with empty string content
            sanitized.append(msg)
        agent.messages = sanitized

    def run(self, user_message: str) -> dict:
        """
        Runs the conversational agent with the user's latest message.
        Uses the correct Strands API: agent(prompt) returns a response object.
        Automatically falls back to Amazon Nova if Claude fails.
        """
        response_text = None
        used_fallback = False
        
        # Sanitize before calling — removes empty text blocks Anthropic rejects
        self._sanitize_messages(self.agent)
        try:
            print(f"[INFO] Attempting with primary model (Claude)...")
            response = self.agent(user_message)
            response_text = str(response)
            print(f"[INFO] Primary model succeeded")
        except Exception as e:
            print(f"[WARN] Primary model (Claude) failed: {e}")
            print(f"[INFO] Falling back to Amazon Nova...")
            
            # Fallback to Nova model
            try:
                # Sync conversation history from primary to fallback agent
                if hasattr(self.agent, "messages") and self.agent.messages:
                    self.fallback_agent.messages = self.agent.messages.copy()
                
                response = self.fallback_agent(user_message)
                response_text = str(response)
                used_fallback = True
                print(f"[INFO] Fallback model (Nova) succeeded")
                
                # Sync back to primary agent for next turn
                if hasattr(self.fallback_agent, "messages"):
                    self.agent.messages = self.fallback_agent.messages.copy()
                    
            except Exception as fallback_error:
                print(f"[ERROR] Fallback model (Nova) also failed: {fallback_error}")
                raise Exception(f"Both primary and fallback models failed. Primary: {e}, Fallback: {fallback_error}")
        
        if not response_text:
            raise Exception("No response generated from any model")

        return self._process_response(response_text)
    
    async def run_stream(self, user_message: str):
        """
        Streams the conversational agent response using Strands streaming.
        Yields chunks of text as they arrive from the LLM.
        
        Filters out PROFILE_DATA markers and JSON only when they appear,
        otherwise streams normally for fast UI updates.
        
        Stores the complete unfiltered response in self.last_full_response
        for profile data extraction.
        
        Uses Strands' stream_async() method for async streaming.
        """
        try:
            print(f"[INFO] Starting streaming response with Strands...")
            
            full_response = ""
            markers_detected = False
            buffer = ""  # Buffer to check for "PROFILE" before yielding
            
            # Sanitize before streaming — removes empty text blocks Anthropic rejects
            self._sanitize_messages(self.agent)

            # Use Strands' stream_async() method for async streaming
            async for event in self.agent.stream_async(user_message):
                # Extract text from "data" field in events
                if "data" in event:
                    chunk_text = event["data"]
                    full_response += chunk_text
                    
                    # If markers already detected, just buffer (don't stream)
                    if markers_detected:
                        continue
                    
                    # Add to buffer
                    buffer += chunk_text
                    
                    # Check if buffer contains start of "PROFILE"
                    if "PROFILE" in buffer:
                        markers_detected = True
                        # Remove "PROFILE" and everything after from buffer
                        clean_buffer = buffer[:buffer.find("PROFILE")]
                        if clean_buffer:
                            yield clean_buffer
                        buffer = ""
                        print(f"[INFO] Profile markers detected, stopping stream to UI")
                        continue
                    
                    # If buffer is getting long without "PROFILE", yield it
                    # Keep last 10 chars in buffer to catch "PROFILE" across chunks
                    if len(buffer) > 10:
                        yield_text = buffer[:-10]
                        yield yield_text
                        buffer = buffer[-10:]
                
            # Yield any remaining buffer (if no markers detected)
            if not markers_detected and buffer:
                yield buffer
            
            # Store the complete unfiltered response for profile extraction
            self.last_full_response = full_response
                
            print(f"[INFO] Streaming complete, total length: {len(full_response)}")
            
            # If profile markers were found, yield the clean message after markers
            if markers_detected and "PROFILE_DATA_END" in full_response:
                end_marker = "PROFILE_DATA_END"
                end_idx = full_response.find(end_marker) + len(end_marker)
                text_after = full_response[end_idx:].strip()
                
                # Yield the message after markers (photo request or closing)
                if text_after:
                    print(f"[INFO] Yielding text after markers: {text_after[:100]}")
                    yield "\n\n" + text_after
            
        except Exception as e:
            print(f"[ERROR] Streaming failed: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback to non-streaming
            print("[INFO] Falling back to non-streaming")
            response = self.agent(user_message)
            self.last_full_response = str(response)
            yield str(response)
            yield str(response)
    
    def _process_response(self, response_text: str) -> dict:
        """
        Process the complete response text and extract profile data if present.
        """
        # Check if the LLM outputted the final JSON profile with markers
        if "PROFILE_DATA_START" in response_text and "PROFILE_DATA_END" in response_text:
            try:
                print(f"[INFO] Found profile data markers in response")
                # Extract JSON between markers
                start_marker = "PROFILE_DATA_START"
                end_marker = "PROFILE_DATA_END"
                start_idx = response_text.find(start_marker) + len(start_marker)
                end_idx = response_text.find(end_marker)
                json_str = response_text[start_idx:end_idx].strip()
                
                print(f"[INFO] Extracted JSON string: {json_str}")
                profile = json.loads(json_str)
                print(f"[INFO] Parsed profile data: {profile}")
                
                # Normalize the profession_skill to one of the 5 supported skills
                if "profession_skill" in profile:
                    original_skill = profile["profession_skill"]
                    normalized_skill = normalize_skill(original_skill)
                    profile["profession_skill"] = normalized_skill
                    if original_skill != normalized_skill:
                        print(f"[INFO] Normalized skill from '{original_skill}' to '{normalized_skill}'")
                
                is_ready = profile.get("is_ready_for_photo", False)
                
                # CRITICAL FIX: Remove the profile data markers from the response
                # Extract text before markers (if any)
                text_before_markers = response_text[:response_text.find(start_marker)].strip()
                
                # Extract any message after the JSON markers (photo request or closing)
                message_after_json = response_text[end_idx + len(end_marker):].strip()
                
                # Combine text before and after markers, excluding the markers themselves
                clean_response = (text_before_markers + "\n\n" + message_after_json).strip()
                
                # Use the cleaned message from LLM if present, otherwise use default
                if clean_response:
                    final_response = clean_response
                elif is_ready:
                    # Skill-specific work sample message
                    skill = profile.get("profession_skill", "")
                    work_sample_examples = {
                        "tailor": "clothes you've stitched or tailored",
                        "carpenter": "furniture or woodwork you've made",
                        "plumber": "plumbing installation or repair work you've done",
                        "welder": "welded items, structures, or fabrication work",
                        "beautician": "makeup or hair styling work you've done"
                    }
                    example = work_sample_examples.get(skill, "your work")
                    final_response = f"Great! Now please upload a photo of {example}. This will help us assess your skills and match you with better opportunities. 📸"
                else:
                    final_response = "Thank you! Your profile information has been successfully saved. We look forward to helping you grow!"
                
                print(f"[INFO] Returning profile_data with {len(profile)} fields")
                return {
                    "response": final_response,
                    "is_ready_for_photo": is_ready,
                    "is_complete": not is_ready,
                    "intent_extracted": profile.get("intent"),
                    "profession_skill_extracted": profile.get("profession_skill"),
                    "theory_score_extracted": profile.get("theory_score"),
                    "gender_extracted": profile.get("gender"),
                    "location_extracted": profile.get("preferred_location") or None,
                    "profile_data": profile,  # Pass the complete profile for storage
                }
            except Exception as e:
                print(f"[ERROR] Failed to parse profile JSON: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[DEBUG] No profile markers found in response. Response preview: {response_text[:200]}")

        # Normal conversational turn
        return {
            "response": response_text,
            "is_ready_for_photo": False,
            "is_complete": False,
            "intent_extracted": None,
            "profession_skill_extracted": None,
            "theory_score_extracted": None,
            "gender_extracted": None,
            "location_extracted": None,
            "profile_data": None,
        }
