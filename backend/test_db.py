import boto3
import os
from dotenv import load_dotenv

load_dotenv()
session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
)
dynamodb = session.resource("dynamodb")
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE", "swavalambi_users"))

def check_history():
    # Use scan to just get the first user to see
    response = table.scan()
    for item in response.get("Item", response.get("Items", [])):
        print(f"User: {item.get('user_id')}")
        history = item.get("chat_history", [])
        for msg in history[-3:]:
            print(msg)
        print("---")

check_history()
