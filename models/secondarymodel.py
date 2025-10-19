import google.generativeai as genai
import json, re, datetime
from pymongo import MongoClient
from calender import add_events_to_calendar
import os
from dotenv import load_dotenv

# Load env
load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# MongoDB setup
db_client = MongoClient(os.getenv("mongo_uri"))
db = db_client['Emails']

# Create model instance ONCE
model = genai.GenerativeModel("models/gemini-2.0-flash-001")


def extract_event(email_body):
    if isinstance(email_body, tuple):
        email_body = email_body[0]

    prompt = f"""
Extract an EVENT from this email if any exists.
Return JSON with fields: "title", "date", "start_time", "end_time", "location", "description".
If no event → return {{}}
Email:
\"\"\"{email_body}\"\"\""""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        match = re.search(r'({.*})', text, re.DOTALL)
        if not match:
            return None

        event = json.loads(match.group(1))

        if not event.get("title") or not event.get("date"):
            return None

        event.setdefault("start_time", "00:00")
        event.setdefault("end_time", "01:00")
        event.setdefault("location", "N/A")
        event.setdefault("description", "")

        return event

    except Exception as e:
        print(f"[ERROR extract_event]: {e}")
        return None


def summarize_email(email_body):
    if isinstance(email_body, tuple):
        email_body = email_body[0]

    prompt = f"Summarize the following email in 2-3 concise sentences:\n\"\"\"{email_body}\"\"\""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[ERROR summarize_email]: {e}")
        return None


def cache_and_add_event(user_id, email_id, creds, event_details):
    events_collection = db[f"{user_id}_events"]

    existing = events_collection.find_one({"email_id": email_id})
    if not existing:
        events_collection.insert_one({
            "email_id": email_id,
            **event_details,
            "added_at": datetime.datetime.utcnow()
        })

    try:
        cal_link = add_events_to_calendar(creds, event_details)
        return cal_link
    except Exception as e:
        print(f"[ERROR adding to calendar]: {e}")
        return None
