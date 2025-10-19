# fetch.py
import os
import re
import pickle
import base64
import datetime
from base64 import urlsafe_b64decode
from typing import Optional, List, Tuple

from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("mongo_uri")
CLIENT_SECRETS_FILE = os.getenv("CLIENT_SECRETS_FILE", "credentials.json")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:5000/oauth2callback")

SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar'
]

# Mongo
_client = MongoClient(MONGO_URI)
db = _client['Emails']
tokens_collection = _client['gmail_auth']['tokens']

# ---------------- Utilities ----------------
def sanitize_email_for_collection(email: str) -> str:
    return email.replace("@", "at").replace(".", "dot")

def creds_to_b64(creds: Credentials) -> str:
    return base64.b64encode(pickle.dumps(creds)).decode()

def creds_from_b64(b64: str) -> Credentials:
    return pickle.loads(base64.b64decode(b64.encode()))

# ---------------- OAuth helpers ----------------
def authenticate_user() -> Optional[str]:
    try:
        flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI)
        auth_url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true", prompt="consent")
        return auth_url
    except Exception as e:
        print(f"[ERROR] authenticate_user: {e}")
        return None

def exchange_code_for_user(code: str) -> Tuple[Optional[str], Optional[Credentials]]:
    try:
        flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI)
        flow.fetch_token(code=code)
        creds: Credentials = flow.credentials

        gmail_service = build('gmail', 'v1', credentials=creds)
        profile = gmail_service.users().getProfile(userId='me').execute()
        email = profile.get("emailAddress", "unknown")
        user_id = sanitize_email_for_collection(email)

        # persist token
        save_token_to_db(email, user_id, creds)
        return user_id, creds
    except Exception as e:
        print(f"[ERROR] exchange_code_for_user: {e}")
        return None, None

# ---------------- Token storage helpers ----------------
def save_token_to_db(email: str, user_id: str, creds: Credentials) -> None:
    try:
        tokens_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "email": email,
                "creds_b64": creds_to_b64(creds),
                "updated_at": datetime.datetime.utcnow()
            }},
            upsert=True
        )
    except Exception as e:
        print(f"[ERROR] save_token_to_db: {e}")

def load_token_from_db_by_userid(user_id: str) -> Tuple[Optional[Credentials], Optional[str]]:
    try:
        doc = tokens_collection.find_one({"user_id": user_id})
        if not doc or "creds_b64" not in doc:
            return None, None
        creds = creds_from_b64(doc["creds_b64"])
        return creds, doc.get("email")
    except Exception as e:
        print(f"[ERROR] load_token_from_db_by_userid: {e}")
        return None, None

# ---------------- Cleaning helpers ----------------
def clean_full_text(raw_html: str) -> str:
    try:
        soup = BeautifulSoup(raw_html, 'html.parser')
        for tag in soup(['script', 'style', 'img', 'a']):
            tag.decompose()
        text = soup.get_text(separator=' ')
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    except Exception:
        return "(Clean failed)"

def extract_plain_text(payload: dict) -> str:
    try:
        if not payload:
            return "(No payload)"
        # prefer text/plain or text/html parts
        if 'parts' in payload:
            for part in payload['parts']:
                mime = part.get('mimeType', '')
                data = part.get('body', {}).get('data')
                if data and mime in ['text/plain', 'text/html']:
                    decoded = urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    return clean_full_text(decoded)
            # deeper exploration
            for part in payload['parts']:
                subparts = part.get('parts') or []
                for sp in subparts:
                    data = sp.get('body', {}).get('data')
                    if data:
                        decoded = urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        return clean_full_text(decoded)
        else:
            mime = payload.get('mimeType', '')
            data = payload.get('body', {}).get('data')
            if data and mime in ['text/plain', 'text/html']:
                decoded = urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                return clean_full_text(decoded)
        return "(No clean text found)"
    except Exception:
        return "(Extraction failed)"

# ---------------- Credential maintenance ----------------
def ensure_creds_valid(creds: Credentials) -> Credentials:
    """
    Refresh creds if expired and refresh_token available.
    Returns the (possibly refreshed) creds.
    """
    try:
        if creds and creds.expired and creds.refresh_token:
            request = Request()
            creds.refresh(request)
    except Exception as e:
        # non-fatal; caller will observe Gmail API errors and can re-auth if needed
        print(f"[WARN] ensure_creds_valid: refresh attempt failed: {e}")
    return creds

# ---------------- Core: fetch only unread, newest-first ----------------
def get_unread_emails(creds: Credentials, user_id: str, limit: int = 10, page_token: str = None, verbose: bool = True):
    """
    Fetch a batch of unread emails for the user.
    Returns dict: { 'inserted': [...], 'next_page_token': '...' }
    """
    inserted = []
    next_page_token = None

    if not creds:
        if verbose:
            print("[WARN] get_unread_emails called with no credentials")
        return {"inserted": inserted, "next_page_token": None}

    creds = ensure_creds_valid(creds)
    try:
        service = build('gmail', 'v1', credentials=creds)
    except Exception as e:
        print(f"[ERROR] could not build service: {e}")
        return {"inserted": inserted, "next_page_token": None}

    q = 'is:unread -label:trash -label:drafts'

    try:
        # fetch a single batch (limit emails)
        resp = service.users().messages().list(
            userId='me',
            q=q,
            maxResults=limit,
            pageToken=page_token
        ).execute()

        msg_refs = resp.get('messages', [])
        next_page_token = resp.get('nextPageToken')

        if not msg_refs:
            if verbose:
                print("[INFO] No unread messages found.")
            return {"inserted": inserted, "next_page_token": None}

        # Fetch full message bodies
        messages_full = []
        for mr in msg_refs:
            mid = mr.get('id')
            try:
                full = service.users().messages().get(userId='me', id=mid, format='full').execute()
                messages_full.append(full)
            except Exception as e:
                if verbose:
                    print(f"[WARN] Could not fetch message {mid}: {e}")

        # Sort newest-first
        messages_full.sort(key=lambda m: int(m.get('internalDate', 0)), reverse=True)

        col = db[user_id]
        for msg_data in messages_full:
            msg_id = msg_data.get('id')
            if not msg_id:
                continue

            # dedupe
            if col.find_one({"msg_id": msg_id}, {"_id": 1}):
                continue

            headers = msg_data.get('payload', {}).get('headers', [])
            subject = next((h.get('value') for h in headers if h.get('name', '').lower() == 'subject'), "(No Subject)")
            body = extract_plain_text(msg_data.get('payload'))

            doc = {
                "subject": subject,
                "body": body,
                "msg_id": msg_id,
                "fetched_at": datetime.datetime.utcnow(),
                "processed": False
            }

            try:
                col.insert_one(doc)
                inserted.append({"msg_id": msg_id, "subject": subject[:120]})
            except Exception as e:
                print(f"[ERROR] insert failed for msg {msg_id}: {e}")

        return {"inserted": inserted, "next_page_token": next_page_token}

    except Exception as e:
        print(f"[ERROR] get_unread_emails: {e}")
        return {"inserted": inserted, "next_page_token": None}

