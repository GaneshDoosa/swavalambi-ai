from strands import Agent
from strands.models import BedrockModel, AnthropicModel
import boto3
import os
import json

class ProfilingAgent:
    def __init__(self, session_id: str, user_name: str = ""):
        self.session_id = session_id
        
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

        self.system_prompt = f"""
        You are 'Swavalambi Assistant', a supportive, friendly, and encouraging AI profiler for skilled workers and artisans in India.
        Your goal is to have a natural, engaging conversation to build a comprehensive profile. Extract the following information:
        {known_user_context}
        1. **profession_skill & demographics**: Greet warmly and ask what kind of work they do (e.g., tailoring, plumbing, teaching). Infer their gender based on their name, or lightly ask them. Let them know we want to tailor the profile to them.
        
        2. **intent**: Ask what brings them to the platform:
           - "job" (Looking for employment opportunities)
           - "upskill" (Want to learn and improve their skills)
           - "loan" (Want to start a business or explore government schemes)
        
        3. **preferred_location** (ONLY if intent = "job"):
           After they say they want a job, ask: "Which city or state are you looking for work in? (e.g., **Mumbai**, **Delhi**, **Bangalore**, **Any location**)"
           If they say "any" or "anywhere", set preferred_location to "".
           Skip this step entirely for upskill/loan intents.
           
        3. **experience_assessment**: Ask detailed questions to understand their skill level:
           
           For ALL users, ask:
           - How many years have you been working in this field?
           - What kind of work do you typically do? (Ask for specific examples)
           - Do you work independently or with a team?
           - Have you trained others or taught apprentices?
           
           Based on their answers, assess their level:
           - **Beginner (1-2)**: Less than 2 years, basic tasks, needs supervision, no teaching experience
           - **Intermediate (3-4)**: 2-5 years, handles variety of tasks independently, some complex work
           - **Advanced (5)**: 5+ years, expert-level work, trains others, handles complex projects independently
           
        4. **Additional Context** (ask naturally during conversation):
           - Do they have any certifications or formal training?
           - What tools/equipment do they use regularly?
           - What's their biggest challenge in their work?
           - What would they like to learn or improve?
           
        5. **Conclude / Photo Prompt**:
           - For **beginners**: Encourage them warmly. Tell them we'll help them learn and grow. DO NOT ask for a photo.
           - For **intermediate/advanced**: Appreciate their experience. Then output the JSON profile FIRST, followed by asking for photo upload.
           
        CONVERSATION STYLE:
        - Keep responses short (1-2 sentences per turn)
        - Be warm, encouraging, and conversational
        - Ask ONE question at a time
        - Show genuine interest in their work
        - Use emojis sparingly (1-2 per message max)
        - Reply in the same language the user speaks
        
        IMPORTANT - OPTION FORMATTING:
        When presenting multiple choice options to the user, ALWAYS format them using bold text with this exact pattern:
        "Are you looking for **option1**, wanting to **option2**, or interested in **option3**?"
        
        Examples:
        - For profession: "Tell me, what kind of work do you do? (e.g., **Tailoring**, **Plumbing**, **Teaching**)"
        - For intent: "Are you looking for **job opportunities**, wanting to **improve your skills**, or interested in **starting your own business**?"
        - For experience: "Would you say you're a **beginner**, **intermediate**, or **advanced** worker?"
        
        ALWAYS use **bold text** (double asterisks) around each option to make them clickable in the UI.
        
        CRITICAL - PROFILE OUTPUT RULES:
        When you have gathered ALL information, you MUST output the JSON profile in this EXACT format:
        
        PROFILE_DATA_START
        {{
            "profession_skill": "tailor",
            "intent": "job",
            "theory_score": 4,
            "years_experience": 3,
            "work_type": "independent tailoring, alterations, custom clothing",
            "has_training": true,
            "is_ready_for_photo": true,
            "gender": "female",
            "preferred_location": "Mumbai"
        }}
        PROFILE_DATA_END
        
        After outputting the JSON:
        - If is_ready_for_photo is true: Add a message asking them to upload a photo
        - If is_ready_for_photo is false: Add a warm closing message
        
        SCORING RULES:
        - theory_score: 1-2 (beginner), 3-4 (intermediate), 5 (advanced)
        - years_experience: Actual number of years they mentioned
        - work_type: Brief summary of what they do
        - has_training: true if they mentioned any formal training/certification
        - is_ready_for_photo: true ONLY for intermediate/advanced (theory_score >= 3)
        - gender: "male", "female", or "other" depending on context
        - preferred_location: city or state name if intent=job, empty string "" if intent=upskill/loan or if user said "any/anywhere"
        """

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

    def run(self, user_message: str) -> dict:
        """
        Runs the conversational agent with the user's latest message.
        Uses the correct Strands API: agent(prompt) returns a response object.
        Automatically falls back to Amazon Nova if Claude fails.
        """
        response_text = None
        used_fallback = False
        
        # Try primary model (Claude) first
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
                
                is_ready = profile.get("is_ready_for_photo", False)
                
                # Extract any message after the JSON markers (photo request or closing)
                message_after_json = response_text[end_idx + len(end_marker):].strip()
                
                # Use the message from LLM if present, otherwise use default
                if message_after_json:
                    final_response = message_after_json
                elif is_ready:
                    final_response = "Thank you! Please upload your work sample now using the button below." 
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

