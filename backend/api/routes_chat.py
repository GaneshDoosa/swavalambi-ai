from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from schemas.models import ChatRequest, ChatResponse, LanguageUpdateRequest
from agents.profiling_agent import ProfilingAgent
from services.dynamodb_service import update_chat_history
from common.agent_sessions import get_agent_session, set_agent_session, has_agent_session
from common.text_utils import strip_profile_markers as _strip_profile_markers
from common.chat_persistence import save_agent_history
import asyncio
import warnings
import logging
import sys
import os
import json

# Suppress Pydantic serialization warnings for Strands message objects
# These warnings occur because Strands uses complex internal message structures
# but we're already converting everything to simple types (str, bool, int)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic.main")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("[%(levelname)s] routes_chat: %(message)s"))
    logger.addHandler(_handler)
logger.propagate = False

router = APIRouter()




@router.post("/chat-profile", response_model=ChatResponse, summary="AI Gateway chat using Strands")
async def chat_profile(request: ChatRequest):
    """
    Pass the user message to the ProfilingAgent to extract intent and theory score.
    Uses Strands framework underneath to maintain memory context based on session_id.
    """
    # Retrieve or create agent session
    is_new_session = not has_agent_session(request.session_id)
    
    if is_new_session:
        # Get user's preferred language and check if photo is uploaded
        preferred_language = "en-IN"  # default
        has_uploaded_photo = False
        if request.user_id:
            try:
                from services.dynamodb_service import get_user
                user_data = get_user(request.user_id)
                if user_data:
                    if "preferred_language" in user_data:
                        preferred_language = user_data["preferred_language"]
                    
                    # Check if photo is already uploaded
                    profile_assessment = user_data.get("profile_assessment", {})
                    if profile_assessment.get("work_sample_score") is not None:
                        has_uploaded_photo = True
            except Exception as e:
                logger.warning("Failed to get user data: %s", e)
        
        set_agent_session(request.session_id, ProfilingAgent(
            session_id=request.session_id,
            user_name=request.user_name or "",
            preferred_language=preferred_language,
            has_uploaded_photo=has_uploaded_photo
        ))
        
        # If user_id is provided, try to restore previous chat history
        chat_restored = False
        if request.user_id:
            try:
                from services.dynamodb_service import get_user
                user = get_user(request.user_id)
                if user and "chat_history" in user and user["chat_history"]:
                    # Restore the agent's memory with previous messages
                    chat_history = user["chat_history"]
                    # Convert to Strands message format
                    restored_messages = []
                    for msg in chat_history:
                        # Skip messages with empty content
                        if msg.get("content") and msg["content"].strip():
                            # Strip any PROFILE_DATA markers from old contaminated records
                            clean_content = _strip_profile_markers(msg["content"])
                            if clean_content:
                                restored_messages.append({
                                    "role": msg["role"],
                                    "content": [{"text": clean_content}]
                                })
                    # Set the agent's messages
                    get_agent_session(request.session_id).agent.messages = restored_messages
                    logger.info("Restored %d messages from DynamoDB for user %s", len(restored_messages), request.user_id)
                    chat_restored = True
            except Exception as e:
                logger.warning("Failed to restore chat history: %s", e)
        
        # If this is a new session and no chat was restored, initialize with greeting
        # Generate greeting based on user's preferred language
        if not chat_restored and request.user_id:
            try:
                from services.dynamodb_service import get_user
                user_data = get_user(request.user_id)
                preferred_language = user_data.get("preferred_language", "hi-IN") if user_data else "hi-IN"
                user_name = request.user_name or ""
                
                # Multilingual greetings
                greetings = {
                    "hi-IN": {
                        "with_name": f"नमस्ते, {user_name}! 😊 मैं आपका स्वावलंबी सहायक हूं। आइए आपकी प्रोफाइल बनाएं। आप किस तरह का काम करते हैं? (जैसे, **दर्जी**, **बढ़ई**, **प्लंबर**, **वेल्डर**, **ब्यूटीशियन**)",
                        "without_name": "नमस्ते! मैं आपका स्वावलंबी सहायक हूं। आइए आपकी प्रोफाइल बनाएं। बताइए, आप किस तरह का काम करते हैं? (जैसे, **दर्जी**, **बढ़ई**, **प्लंबर**, **वेल्डर**, **ब्यूटीशियन**)"
                    },
                    "te-IN": {
                        "with_name": f"నమస్తే, {user_name}! 😊 నేను మీ స్వావలంబి సహాయకుడిని. మీ ప్రొఫైల్ రూపొందించుకుందాం. మీరు ఏ రకమైన పని చేస్తారు? (ఉదా., **టైలర్**, **కార్పెంటర్**, **ప్లంబర్**, **వెల్డర్**, **బ్యూటీషియన్**)",
                        "without_name": "నమస్తే! నేను మీ స్వావలంబి సహాయకుడిని. మీ ప్రొఫైల్ రూపొందించుకుందాం. చెప్పండి, మీరు ఏ రకమైన పని చేస్తారు? (ఉదా., **టైలర్**, **కార్పెంటర్**, **ప్లంబర్**, **వెల్డర్**, **బ్యూటీషియన్**)"
                    },
                    "ta-IN": {
                        "with_name": f"வணக்கம், {user_name}! 😊 நான் உங்கள் ஸ்வாவலம்பி உதவியாளர். உங்கள் சுயவிவரத்தை உருவாக்குவோம். நீங்கள் என்ன வேலை செய்கிறீர்கள்? (எ.கா., **தையல்காரர்**, **தச்சர்**, **பிளம்பர்**, **வெல்டர்**, **அழகுக் கலைஞர்**)",
                        "without_name": "வணக்கம்! நான் உங்கள் ஸ்வாவலம்பி உதவியாளர். உங்கள் சுயவிவரத்தை உருவாக்குவோம். சொல்லுங்கள், நீங்கள் என்ன வேலை செய்கிறீர்கள்? (எ.கா., **தையல்காரர்**, **தச்சர்**, **பிளம்பர்**, **வெல்டர்**, **அழகுக் கலைஞர்**)"
                    },
                    "mr-IN": {
                        "with_name": f"नमस्कार, {user_name}! 😊 मी तुमचा स्वावलंबी सहाय्यक आहे. चला तुमचे प्रोफाइल तयार करूया. तुम्ही कोणत्या प्रकारचे काम करता? (उदा., **शिंपी**, **सुतार**, **प्लंबर**, **वेल्डर**, **ब्युटिशियन**)",
                        "without_name": "नमस्कार! मी तुमचा स्वावलंबी सहाय्यक आहे. चला तुमचे प्रोफाइल तयार करूया. सांगा, तुम्ही कोणत्या प्रकारचे काम करता? (उदा., **शिंपी**, **सुतार**, **प्लंबर**, **वेल्डर**, **ब्युटिशियन**)"
                    },
                    "kn-IN": {
                        "with_name": f"ನಮಸ್ಕಾರ, {user_name}! 😊 ನಾನು ನಿಮ್ಮ ಸ್ವಾವಲಂಬಿ ಸಹಾಯಕ. ನಿಮ್ಮ ಪ್ರೊಫೈಲ್ ರಚಿಸೋಣ. ನೀವು ಯಾವ ರೀತಿಯ ಕೆಲಸ ಮಾಡುತ್ತೀರಿ? (ಉದಾ., **ಟೈಲರ್**, **ಬಡಗಿ**, **ಪ್ಲಂಬರ್**, **ವೆಲ್ಡರ್**, **ಬ್ಯೂಟಿಶಿಯನ್**)",
                        "without_name": "ನಮಸ್ಕಾರ! ನಾನು ನಿಮ್ಮ ಸ್ವಾವಲಂಬಿ ಸಹಾಯಕ. ನಿಮ್ಮ ಪ್ರೊಫೈಲ್ ರಚಿಸೋಣ. ಹೇಳಿ, ನೀವು ಯಾವ ರೀತಿಯ ಕೆಲಸ ಮಾಡುತ್ತೀರಿ? (ಉದಾ., **ಟೈಲರ್**, **ಬಡಗಿ**, **ಪ್ಲಂಬರ್**, **ವೆಲ್ಡರ್**, **ಬ್ಯೂಟಿಶಿಯನ್**)"
                    },
                    "bn-IN": {
                        "with_name": f"নমস্কার, {user_name}! 😊 আমি আপনার স্বাবলম্বী সহায়ক। আসুন আপনার প্রোফাইল তৈরি করি। আপনি কী ধরনের কাজ করেন? (যেমন, **দর্জি**, **ছুতোর**, **প্লাম্বার**, **ওয়েল্ডার**, **বিউটিশিয়ান**)",
                        "without_name": "নমস্কার! আমি আপনার স্বাবলম্বী সহায়ক। আসুন আপনার প্রোফাইল তৈরি করি। বলুন, আপনি কী ধরনের কাজ করেন? (যেমন, **দর্জি**, **ছুতোর**, **প্লাম্বার**, **ওয়েল্ডার**, **বিউটিশিয়ান**)"
                    },
                    "gu-IN": {
                        "with_name": f"નમસ્તે, {user_name}! 😊 હું તમારો સ્વાવલંબી સહાયક છું. ચાલો તમારી પ્રોફાઇલ બનાવીએ. તમે કેવા પ્રકારનું કામ કરો છો? (દા.ત., **દરજી**, **સુથાર**, **પ્લમ્બર**, **વેલ્ડર**, **બ્યુટિશિયન**)",
                        "without_name": "નમસ્તે! હું તમારો સ્વાવલંબી સહાયક છું. ચાલો તમારી પ્રોફાઇલ બનાવીએ. કહો, તમે કેવા પ્રકારનું કામ કરો છો? (દા.ત., **દરજી**, **સુથાર**, **પ્લમ્બર**, **વેલ્ડર**, **બ્યુટિશિયન**)"
                    },
                    "ml-IN": {
                        "with_name": f"നമസ്കാരം, {user_name}! 😊 ഞാൻ നിങ്ങളുടെ സ്വാവലംബി സഹായകനാണ്. നിങ്ങളുടെ പ്രൊഫൈൽ സൃഷ്ടിക്കാം. നിങ്ങൾ ഏത് തരത്തിലുള്ള ജോലി ചെയ്യുന്നു? (ഉദാ., **ടെയിലർ**, **ആശാരി**, **പ്ലംബർ**, **വെൽഡർ**, **ബ്യൂട്ടീഷ്യൻ**)",
                        "without_name": "നമസ്കാരം! ഞാൻ നിങ്ങളുടെ സ്വാവലംബി സഹായകനാണ്. നിങ്ങളുടെ പ്രൊഫൈൽ സൃഷ്ടിക്കാം. പറയൂ, നിങ്ങൾ ഏത് തരത്തിലുള്ള ജോലി ചെയ്യുന്നു? (ഉദാ., **ടെയിലർ**, **ആശാരി**, **പ്ലംബർ**, **വെൽഡർ**, **ബ്യൂട്ടീഷ്യൻ**)"
                    },
                    "pa-IN": {
                        "with_name": f"ਸਤ ਸ੍ਰੀ ਅਕਾਲ, {user_name}! 😊 ਮੈਂ ਤੁਹਾਡਾ ਸਵਾਵਲੰਬੀ ਸਹਾਇਕ ਹਾਂ। ਆਓ ਤੁਹਾਡੀ ਪ੍ਰੋਫਾਈਲ ਬਣਾਈਏ। ਤੁਸੀਂ ਕਿਸ ਤਰ੍ਹਾਂ ਦਾ ਕੰਮ ਕਰਦੇ ਹੋ? (ਜਿਵੇਂ, **ਦਰਜ਼ੀ**, **ਤਰਖਾਣ**, **ਪਲੰਬਰ**, **ਵੈਲਡਰ**, **ਬਿਊਟੀਸ਼ੀਅਨ**)",
                        "without_name": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਮੈਂ ਤੁਹਾਡਾ ਸਵਾਵਲੰਬੀ ਸਹਾਇਕ ਹਾਂ। ਆਓ ਤੁਹਾਡੀ ਪ੍ਰੋਫਾਈਲ ਬਣਾਈਏ। ਦੱਸੋ, ਤੁਸੀਂ ਕਿਸ ਤਰ੍ਹਾਂ ਦਾ ਕੰਮ ਕਰਦੇ ਹੋ? (ਜਿਵੇਂ, **ਦਰਜ਼ੀ**, **ਤਰਖਾਣ**, **ਪਲੰਬਰ**, **ਵੈਲਡਰ**, **ਬਿਊਟੀਸ਼ੀਅਨ**)"
                    },
                    "en-IN": {
                        "with_name": f"Namaste, {user_name}! 😊 I'm your Swavalambi Assistant. Let's build your profile. What kind of work do you do? (e.g., **Tailor**, **Carpenter**, **Plumber**, **Welder**, **Beautician**)",
                        "without_name": "Namaste! I am your Swavalambi assistant. Let's build your profile. Tell me, what kind of work do you do? (e.g., **Tailor**, **Carpenter**, **Plumber**, **Welder**, **Beautician**)"
                    }
                }
                
                # Get greeting in user's language
                lang_greetings = greetings.get(preferred_language, greetings["en-IN"])
                
                # Check if user_name is valid (not empty, not a phone number)
                if user_name and not user_name.isdigit() and len(user_name.strip()) > 1 and not user_name.startswith('+'):
                    greeting = lang_greetings["with_name"]
                else:
                    greeting = lang_greetings["without_name"]
                
                # Initialize chat history with greeting
                initial_chat = [{"role": "assistant", "content": greeting}]
                update_chat_history(request.user_id, initial_chat)
                logger.info("Initialized chat history with %s greeting for user %s", preferred_language, request.user_id)
                
                # CRITICAL: Also seed the greeting into agent.messages so it is
                # included in every subsequent DynamoDB save (not just the first one)
                get_agent_session(request.session_id).agent.messages = [
                    {"role": "assistant", "content": [{"text": greeting}]}
                ]
                logger.info("Seeded greeting into agent.messages to prevent overwrite")
            except Exception as e:
                logger.warning("Failed to initialize chat history: %s", e)
        
    agent = get_agent_session(request.session_id)
    
    # Sync language if it changed mid-session
    if request.language and hasattr(agent, "preferred_language") and agent.preferred_language != request.language:
        logger.info("Language mismatch detected in session %s. Updating from %s to %s", 
                    request.session_id, agent.preferred_language, request.language)
        agent.update_language(request.language)
    
    try:
        # Get response from the Strands LLM — run blocking sync call in thread pool
        # to prevent freezing the event loop (which blocks all other requests)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: agent.run(request.message))
        
        # Save chat history to DynamoDB if user_id is provided
        if request.user_id:
            try:
                logger.debug("Attempting to save chat history for user %s", request.user_id)
                # Strands Agent stores conversation history in agent.messages
                if hasattr(agent.agent, "messages") and agent.agent.messages:
                    raw_messages = agent.agent.messages
                    logger.debug("Found %d raw messages in agent.messages", len(raw_messages))
                save_agent_history(agent, request.user_id)
            except Exception as e:
                logger.warning("Failed to persist chat history to DynamoDB: %s", e)
        
        # Save profile assessment data if complete
        if request.user_id and result.get("profile_data"):
            try:
                logger.info("Profile data detected, saving to DynamoDB...")
                logger.info("Profile data content: %s", result['profile_data'])
                from services.dynamodb_service import save_profile_assessment
                save_profile_assessment(request.user_id, result["profile_data"])
                logger.info("Successfully saved profile assessment for user %s", request.user_id)
            except Exception as e:
                logger.error("Failed to save profile assessment: %s", e)
                import traceback
                traceback.print_exc()
        else:
            if request.user_id:
                logger.debug("No profile_data in result for user %s. Result keys: %s", request.user_id, list(result.keys()))
                
        # Return response - ensure all values are JSON-serializable
        # Create a clean response object with explicit type conversion
        return ChatResponse(
            response=str(result.get("response", "")),
            is_ready_for_photo=bool(result.get("is_ready_for_photo", False)),
            is_complete=bool(result.get("is_complete", False)),
            intent_extracted=str(result["intent_extracted"]) if result.get("intent_extracted") else None,
            profession_skill_extracted=str(result["profession_skill_extracted"]) if result.get("profession_skill_extracted") else None,
            theory_score_extracted=int(result["theory_score_extracted"]) if result.get("theory_score_extracted") is not None else None,
            gender_extracted=str(result["gender_extracted"]) if result.get("gender_extracted") else None,
            location_extracted=str(result["location_extracted"]) if result.get("location_extracted") else None,
        )
    except Exception as e:
        logger.error("Agent error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to communicate with AI Gateway.")


@router.put("/chat-profile/language", summary="Update language for an active agent session")
async def update_agent_language(request: LanguageUpdateRequest):
    """
    Update the language of an existing ProfilingAgent session.
    Allows mid-session language changes to be reflected in the AI's response.
    """
    agent = get_agent_session(request.session_id)
    if not agent:
        logger.info("No active agent session found for %s to update language", request.session_id)
        return {"updated": False, "message": "No active session"}
    
    try:
        agent.update_language(request.language)
        logger.info("Updated language to %s for session %s", request.language, request.session_id)
        return {"updated": True}
    except Exception as e:
        logger.error("Failed to update agent language: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat-profile-stream", summary="Streaming AI chat using Server-Sent Events")
async def chat_profile_stream(request: ChatRequest):
    """
    Streaming version of chat-profile endpoint.
    Returns Server-Sent Events (SSE) stream of LLM response chunks.
    
    Enable/disable with ENABLE_STREAMING environment variable.
    """
    # Check if streaming is enabled
    enable_streaming = os.getenv("ENABLE_STREAMING", "false").lower() == "true"
    
    if not enable_streaming:
        # Fallback to non-streaming endpoint
        return await chat_profile(request)
    
    # Retrieve or create agent session (same as non-streaming)
    is_new_session = not has_agent_session(request.session_id)
    
    if is_new_session:
        # Get user's preferred language and check if photo is uploaded
        preferred_language = "en-IN"
        has_uploaded_photo = False
        if request.user_id:
            try:
                from services.dynamodb_service import get_user
                user_data = get_user(request.user_id)
                if user_data:
                    if "preferred_language" in user_data:
                        preferred_language = user_data["preferred_language"]
                    
                    # Check if photo is already uploaded
                    profile_assessment = user_data.get("profile_assessment", {})
                    if profile_assessment.get("work_sample_score") is not None:
                        has_uploaded_photo = True
            except Exception as e:
                logger.warning("Failed to get user data: %s", e)
        
        set_agent_session(request.session_id, ProfilingAgent(
            session_id=request.session_id,
            user_name=request.user_name or "",
            preferred_language=preferred_language,
            has_uploaded_photo=has_uploaded_photo
        ))
        
        # Restore chat history if available
        chat_restored = False
        if request.user_id:
            try:
                from services.dynamodb_service import get_user
                user = get_user(request.user_id)
                if user and "chat_history" in user and user["chat_history"]:
                    chat_history = user["chat_history"]
                    restored_messages = []
                    for msg in chat_history:
                        # Skip messages with empty content
                        if msg.get("content") and msg["content"].strip():
                            # Strip any PROFILE_DATA markers from old contaminated records
                            clean_content = _strip_profile_markers(msg["content"])
                            if clean_content:
                                restored_messages.append({
                                    "role": msg["role"],
                                    "content": [{"text": clean_content}]
                                })
                    get_agent_session(request.session_id).agent.messages = restored_messages
                    logger.info("Restored %d messages for streaming session", len(restored_messages))
                    chat_restored = True
            except Exception as e:
                logger.warning("Failed to restore chat history: %s", e)
        
        # Initialize greeting if needed (same as non-streaming)
        if not chat_restored and request.user_id:
            try:
                from services.dynamodb_service import get_user, update_chat_history
                user_data = get_user(request.user_id)
                preferred_language = user_data.get("preferred_language", "hi-IN") if user_data else "hi-IN"
                user_name = request.user_name or ""
                
                # Multilingual greetings (same as non-streaming)
                greetings = {
                    "hi-IN": {
                        "with_name": f"नमस्ते, {user_name}! 😊 मैं आपका स्वावलंबी सहायक हूं। आइए आपकी प्रोफाइल बनाएं। आप किस तरह का काम करते हैं? (जैसे, **दर्जी**, **बढ़ई**, **प्लंबर**, **वेल्डर**, **ब्यूटीशियन**)",
                        "without_name": "नमस्ते! मैं आपका स्वावलंबी सहायक हूं। आइए आपकी प्रोफाइल बनाएं। बताइए, आप किस तरह का काम करते हैं? (जैसे, **दर्जी**, **बढ़ई**, **प्लंबर**, **वेल्डर**, **ब्यूटीशियन**)"
                    },
                    "te-IN": {
                        "with_name": f"నమస్తే, {user_name}! 😊 నేను మీ స్వావలంబి సహాయకుడిని. మీ ప్రొఫైల్ రూపొందించుకుందాం. మీరు ఏ రకమైన పని చేస్తారు? (ఉదా., **టైలర్**, **కార్పెంటర్**, **ప్లంబర్**, **వెల్డర్**, **బ్యూటీషియన్**)",
                        "without_name": "నమస్తే! నేను మీ స్వావలంబి సహాయకుడిని. మీ ప్రొఫైల్ రూపొందించుకుందాం. చెప్పండి, మీరు ఏ రకమైన పని చేస్తారు? (ఉదా., **టైలర్**, **కార్పెంటర్**, **ప్లంబర్**, **వెల్డర్**, **బ్యూటీషియన్**)"
                    },
                    # Add other languages as needed...
                    "en-IN": {
                        "with_name": f"Namaste, {user_name}! 😊 I'm your Swavalambi Assistant. Let's build your profile. What kind of work do you do? (e.g., **Tailor**, **Carpenter**, **Plumber**, **Welder**, **Beautician**)",
                        "without_name": "Namaste! I am your Swavalambi assistant. Let's build your profile. Tell me, what kind of work do you do? (e.g., **Tailor**, **Carpenter**, **Plumber**, **Welder**, **Beautician**)"
                    }
                }
                
                lang_greetings = greetings.get(preferred_language, greetings["en-IN"])
                if user_name and not user_name.isdigit() and len(user_name.strip()) > 1 and not user_name.startswith('+'):
                    greeting = lang_greetings["with_name"]
                else:
                    greeting = lang_greetings["without_name"]
                
                initial_chat = [{"role": "assistant", "content": greeting}]
                update_chat_history(request.user_id, initial_chat)
                logger.info("Initialized streaming chat with %s greeting", preferred_language)
                
                # CRITICAL: Seed greeting into agent.messages to prevent overwrite on first save
                get_agent_session(request.session_id).agent.messages = [
                    {"role": "assistant", "content": [{"text": greeting}]}
                ]
                logger.info("Seeded greeting into streaming agent.messages")
            except Exception as e:
                logger.warning("Failed to initialize greeting: %s", e)
    
    agent = get_agent_session(request.session_id)
    
    # Sync language if it changed mid-session
    if request.language and hasattr(agent, "preferred_language") and agent.preferred_language != request.language:
        logger.info("Language mismatch detected in streaming session %s. Updating from %s to %s", 
                    request.session_id, agent.preferred_language, request.language)
        agent.update_language(request.language)
    
    # Generator function for SSE streaming
    async def generate_stream():
        try:
            full_response = ""
            
            # Stream chunks from agent
            async for chunk in agent.run_stream(request.message):
                full_response += chunk
                
                # Send chunk as SSE
                yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
            
            # Process complete response for metadata
            # CRITICAL: Use last_full_response which contains the unfiltered response with markers
            actual_full_response = getattr(agent, 'last_full_response', full_response)
            result = agent._process_response(actual_full_response)
            
            # Check final output against the strict backend flag
            if getattr(agent, "has_uploaded_photo", False):
                result["is_ready_for_photo"] = False
            
            print(f"Final is_ready_for_photo: {result.get('is_ready_for_photo', False)}")
            
            # Save chat history
            if request.user_id:
                try:
                    save_agent_history(agent, request.user_id)
                except Exception as e:
                    logger.warning("Failed to save chat history: %s", e)
            # Save profile assessment if complete
            if request.user_id and result.get("profile_data"):
                try:
                    from services.dynamodb_service import save_profile_assessment
                    save_profile_assessment(request.user_id, result["profile_data"])
                    logger.info("Saved profile assessment for user %s", request.user_id)
                except Exception as e:
                    logger.error("Failed to save profile assessment: %s", e)
            
            # Send final metadata
            final_data = {
                "chunk": "",
                "done": True,
                "is_ready_for_photo": result.get("is_ready_for_photo", False),
                "is_complete": result.get("is_complete", False),
                "intent_extracted": result.get("intent_extracted"),
                "profession_skill_extracted": result.get("profession_skill_extracted"),
                "theory_score_extracted": result.get("theory_score_extracted"),
                "gender_extracted": result.get("gender_extracted"),
                "location_extracted": result.get("location_extracted"),
            }
            yield f"data: {json.dumps(final_data)}\n\n"
            
        except Exception as e:
            logger.error("Streaming error: %s", e)
            error_data = {"error": str(e), "done": True}
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
