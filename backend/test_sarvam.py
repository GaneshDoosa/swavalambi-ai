import requests
import os
from dotenv import load_dotenv
import json

load_dotenv('d:/Projects/AI4Bharath/swavalmbi-ai/backend/.env')
api_key = os.getenv('SARVAM_API_KEY')

url = 'https://api.sarvam.ai/text-to-speech'
headers = {
    'api-subscription-key': api_key,
    'Content-Type': 'application/json'
}

print("Testing Payload 1: 'inputs' array")
data1 = {
    'inputs': ['नमस्कार! मैं बहुत अच्छा हूँ'],
    'target_language_code': 'hi-IN',
    'model': 'bulbul:v3',
    'speaker': 'meera',
    'speech_sample_rate': 24000
}
r1 = requests.post(url, headers=headers, json=data1)
print(f"Status: {r1.status_code}")
print(f"Response: {r1.text[:200]}")

print("\nTesting Payload 2: 'text' string")
data2 = {
    'text': 'नमस्कार! मैं बहुत अच्छा हूँ',
    'target_language_code': 'hi-IN',
    'model': 'bulbul:v3',
    'speaker': 'meera',
    'speech_sample_rate': 24000
}
r2 = requests.post(url, headers=headers, json=data2)
print(f"Status: {r2.status_code}")
print(f"Response: {r2.text[:200]}")
