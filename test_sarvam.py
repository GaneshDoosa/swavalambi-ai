import time
import requests
from sarvamai import SarvamAI

API_KEY = "sk_91lkacnl_dvyNQhTyQhtWOU00MCsGcfAm"
TEXT = "नमस्ते, harry! 😊 मैं आपका स्वावलंबी सहायक हूं। आइए आपकी प्रोफाइल बनाएं। आप किस तरह का काम करते हैं? (जैसे, दर्जी, बढ़ई, प्लंबर, वेल्डर, ब्यूटीशियन)"

print("--- Testing Sarvam SDK ---")
client = SarvamAI(api_subscription_key=API_KEY)

start_time = time.time()
client.text_to_speech.convert(
    text=TEXT,
    target_language_code="hi-IN",
)
end_time = time.time()
print(f"Time taken (SDK): {end_time - start_time:.2f} seconds")

print("\n--- Testing Direct Requests (like backend) ---")
start_time = time.time()
url = "https://api.sarvam.ai/text-to-speech"
headers = {
    "api-subscription-key": API_KEY,
    "Content-Type": "application/json"
}
data = {
    "text": TEXT,
    "target_language_code": "hi-IN",
    "model": "bulbul:v3",
    "speaker": "shubh",
    "speech_sample_rate": 8000,
}
response = requests.post(url, headers=headers, json=data)
end_time = time.time()
print(f"Time taken (Requests POST): {end_time - start_time:.2f} seconds, Status code: {response.status_code}")

