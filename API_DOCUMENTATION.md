# Swavalambi API Documentation

## Overview
This document maps all API endpoints invoked from the frontend UI, organized by feature/page.

**Base URL**: Configured via environment variables
- Lambda: `VITE_API_URL_LAMBDA`
- ECS: `VITE_API_URL_ECS`
- API Base: `${API_URL}/api`

---

## 1. Authentication & Registration

### POST `/api/auth/register`
**Used in**: Register page
**Purpose**: Register new user with email and password
**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "name": "User Name"
}
```
**Response**:
```json
{
  "user_id": "uuid",
  "message": "User registered. Please check email for verification code."
}
```

### POST `/api/auth/verify-email`
**Used in**: Register page (after registration)
**Purpose**: Verify email with confirmation code
**Request**: Query params `email` and `code`

### POST `/api/auth/login`
**Used in**: Login page
**Purpose**: Login with email and password
**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```
**Response**:
```json
{
  "access_token": "jwt_token",
  "user_id": "uuid",
  "email": "user@example.com"
}
```

### POST `/api/auth/forgot-password`
**Used in**: Forgot Password page
**Purpose**: Initiate password reset flow
**Request**: Query param `email`

### POST `/api/auth/reset-password`
**Used in**: Forgot Password page
**Purpose**: Reset password with verification code
**Request**: Query params `email`, `code`, `new_password`

---

## 2. Home Page

### GET `/api/users/{user_id}`
**Used in**: Home page (on load)
**Purpose**: Fetch user profile data including name, preferences
**Response**:
```json
{
  "user_id": "uuid",
  "name": "User Name",
  "email": "user@example.com",
  "phone": "+91...",
  "skill": "tailor",
  "intent": "job",
  "skill_rating": 3,
  "preferred_language": "hi-IN",
  "voice_autoplay": true,
  "location": "Mumbai"
}
```

### POST `/api/recommendations/fetch`
**Used in**: Home page (on load)
**Purpose**: Fetch personalized recommendations (jobs, schemes, training centers)
**Request**:
```json
{
  "session_id": "session-uuid",
  "profession_skill": "tailor",
  "intent": "job",
  "skill_rating": 3,
  "location": "Mumbai"
}
```
**Response**:
```json
{
  "jobs": [
    {
      "id": "job-1",
      "title": "Tailor",
      "company": "ABC Garments",
      "location": "Mumbai",
      "salary": "₹15,000-20,000",
      "vacancies": 5,
      "apply_url": "https://ncs.gov.in/...",
      "education": "10th Pass",
      "posted_days_ago": 2
    }
  ],
  "schemes": [
    {
      "id": "scheme-1",
      "name": "PM Vishwakarma Scheme",
      "ministry": "Ministry of MSME",
      "description": "Financial support for artisans",
      "categories": ["Loan", "Training"],
      "tags": ["Collateral-free", "Skill Development"],
      "url": "https://myscheme.gov.in/..."
    }
  ],
  "training_centers": [
    {
      "id": "center-1",
      "name": "Skill India Training Center",
      "address": "Mumbai, Maharashtra",
      "courses": ["Tailoring", "Fashion Design"],
      "center_type": "Government",
      "url": "https://skillindiadigital.gov.in/..."
    }
  ],
  "message": "Found 5 jobs, 3 schemes, 2 training centers"
}
```

---

## 3. Jobs Page

### POST `/api/recommendations/fetch`
**Used in**: Jobs page (on load)
**Purpose**: Fetch job recommendations with intent override
**Request**:
```json
{
  "session_id": "session-uuid",
  "user_id": "uuid",
  "intent": "job"
}
```
**Response**: Same as Home page jobs array

---

## 4. Upskill Page

### POST `/api/recommendations/fetch`
**Used in**: Upskill page (on load)
**Purpose**: Fetch training center recommendations
**Request**:
```json
{
  "session_id": "session-uuid",
  "user_id": "uuid",
  "intent": "upskill"
}
```
**Response**: Same as Home page training_centers array

---

## 5. Schemes Page

### POST `/api/recommendations/fetch`
**Used in**: Schemes page (on load)
**Purpose**: Fetch government scheme recommendations
**Request**:
```json
{
  "session_id": "session-uuid",
  "user_id": "uuid",
  "intent": "loan"
}
```
**Response**: Same as Home page schemes array

---

## 6. Assistant (Chat) Page

### GET `/api/users/{user_id}/chat-history`
**Used in**: Assistant page (on load)
**Purpose**: Load previous chat conversation
**Response**:
```json
{
  "chat_history": [
    {
      "role": "assistant",
      "content": "नमस्ते! मैं आपका स्वावलंबी सहायक हूं..."
    },
    {
      "role": "user",
      "content": "मैं दर्जी हूं"
    }
  ]
}
```

### POST `/api/chat/chat-profile`
**Used in**: Assistant page (text message)
**Purpose**: Send text message to AI assistant for profiling
**Request**:
```json
{
  "session_id": "session-uuid",
  "message": "I am a tailor",
  "user_id": "uuid",
  "user_name": "Ganesh"
}
```
**Response**:
```json
{
  "response": "Great! How many years of experience do you have?",
  "is_ready_for_photo": false,
  "is_complete": false,
  "intent_extracted": "job",
  "profession_skill_extracted": "tailor",
  "theory_score_extracted": null,
  "gender_extracted": null,
  "location_extracted": null
}
```

### POST `/api/chat/chat-profile-stream`
**Used in**: Assistant page (text message with streaming enabled)
**Purpose**: Stream AI responses in real-time using Server-Sent Events
**Request**: Same as `/chat/chat-profile`
**Response**: SSE stream with chunks:
```
data: {"chunk": "Great! "}
data: {"chunk": "How many "}
data: {"chunk": "years of experience..."}
data: {"done": true, "is_complete": false, "intent_extracted": "job"}
```

### POST `/api/users/{user_id}/chat-history`
**Used in**: Assistant page (after each message)
**Purpose**: Save chat history to DynamoDB
**Request**:
```json
{
  "chat_history": [
    {"role": "assistant", "content": "..."},
    {"role": "user", "content": "..."}
  ]
}
```

### DELETE `/api/users/{user_id}/chat-history`
**Used in**: Assistant page (clear chat button)
**Purpose**: Clear all chat history for reassessment

---

## 7. Voice Features (Assistant Page)

### POST `/api/voice/transcribe`
**Used in**: Assistant page (voice input)
**Purpose**: Convert audio to text (STT)
**Request**: FormData with `audio` file and `language`
**Response**:
```json
{
  "transcribed_text": "मैं दर्जी हूं",
  "language": "hi-IN"
}
```

### POST `/api/voice/synthesize`
**Used in**: Assistant page (text-to-speech playback)
**Purpose**: Convert text to speech (TTS)
**Request**:
```json
{
  "text": "नमस्ते! मैं आपका सहायक हूं",
  "language": "hi-IN"
}
```
**Response**:
```json
{
  "audio_base64": "base64_encoded_audio",
  "audio_format": "mp3"
}
```

### POST `/api/voice/chat`
**Used in**: Assistant page (voice message - non-streaming)
**Purpose**: Complete voice interaction (STT + AI + TTS)
**Request**: FormData with `audio`, `session_id`, `language`, `user_id`
**Response**:
```json
{
  "transcribed_text": "मैं दर्जी हूं",
  "response_text": "बहुत अच्छा! आपको कितने साल का अनुभव है?",
  "audio_base64": "base64_encoded_audio",
  "audio_format": "mp3",
  "is_ready_for_photo": false,
  "is_complete": false,
  "intent_extracted": "job"
}
```

### POST `/api/voice/chat-stream`
**Used in**: Assistant page (voice message - streaming)
**Purpose**: Real-time streaming voice chat with chunked responses
**Request**: Same as `/voice/chat`
**Response**: SSE stream with multiple event types:
```
data: {"type": "transcription", "text": "मैं दर्जी हूं"}
data: {"type": "text_chunk", "text": "बहुत "}
data: {"type": "text_chunk", "text": "अच्छा! "}
data: {"type": "audio_complete", "audio_base64": "...", "audio_format": "mp3"}
data: {"type": "complete", "is_complete": false, "intent_extracted": "job"}
```

---

## 8. Vision Assessment (Assistant Page)

### POST `/api/vision/analyze-vision`
**Used in**: Assistant page (photo upload)
**Purpose**: Analyze work sample photo and provide skill rating
**Request**: FormData with:
- `session_id`
- `photo` (image file)
- `user_id`
- `skill` (e.g., "tailor")
- `intent` (e.g., "job")
- `theory_score` (optional)

**Response**:
```json
{
  "feedback": "Your stitching shows good consistency. Pattern alignment is excellent. Overall skill level: Intermediate (Level 3)",
  "skill_rating": 3,
  "detailed_scores": {
    "stitch_consistency": 92,
    "pattern_alignment": 95,
    "seam_finishing": 85
  }
}
```

---

## 9. User Preferences

### PUT `/api/users/{user_id}/preferences`
**Used in**: Assistant page (language/voice settings)
**Purpose**: Update user preferences
**Request**: Query params `language` and/or `voice_autoplay`
**Example**: `/api/users/123/preferences?language=hi-IN&voice_autoplay=true`

---

## 10. Profile Picture

### POST `/api/users/{user_id}/profile-picture`
**Used in**: Profile page
**Purpose**: Upload profile picture
**Request**: FormData with `file`
**Response**:
```json
{
  "profile_picture_url": "https://s3.amazonaws.com/..."
}
```

### DELETE `/api/users/{user_id}/profile-picture`
**Used in**: Profile page
**Purpose**: Delete profile picture

---

## Assessment Flow & Redirects

### After Assessment Completion

When `is_complete: true` is returned from the chat or vision API:

1. **Intent: "job"** → Redirects to `/jobs`
2. **Intent: "upskill"** → Redirects to `/upskill`
3. **Intent: "loan"** → Redirects to `/home`
4. **Default** → Redirects to `/home`

**Redirect Behavior**:
- 10-second delay before showing redirect modal
- 10-second countdown in modal
- User can cancel redirect
- Auto-navigates when countdown reaches 0

### Stored Data After Assessment

The following data is cached in `localStorage`:
- `swavalambi_user_id`
- `swavalambi_session_id` (sessionStorage)
- `swavalambi_name`
- `swavalambi_skill` (e.g., "tailor")
- `swavalambi_intent` ("job", "upskill", "loan")
- `swavalambi_skill_rating` (0-5)
- `swavalambi_theory_score`
- `swavalambi_gender`
- `swavalambi_location`
- `swavalambi_language` (e.g., "hi-IN")
- `swavalambi_voice_autoplay` (true/false)
- `swavalambi_profile_picture` (URL)

---

## Supported Languages

The app supports 10 Indian languages:
- Hindi (hi-IN)
- Telugu (te-IN)
- Tamil (ta-IN)
- Marathi (mr-IN)
- Kannada (kn-IN)
- Bengali (bn-IN)
- Gujarati (gu-IN)
- Malayalam (ml-IN)
- Punjabi (pa-IN)
- English (en-IN)

---

## Error Handling

All API calls include error handling:
- Network errors show user-friendly messages
- Failed API calls display fallback content
- Voice/vision failures prompt retry
- Authentication errors redirect to login

---

## Performance Optimizations

1. **Streaming**: Text and voice responses stream in real-time
2. **Caching**: Profile data cached in localStorage
3. **Lazy Loading**: Chat history loaded on demand
4. **Auto-play**: Voice responses play automatically (configurable)
5. **Session Management**: Persistent sessions across page refreshes
