import os
import base64
import pickle
import datetime
from threading import Thread
from flask import Flask, render_template, session, request, redirect, url_for, jsonify
from pymongo import MongoClient
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from MAILFETCHING import fetch 
from models import primarymodel, secondarymodel
from emails_clean import cleanup_old_emails

load_dotenv()

# -------------------- Flask app --------------------
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")


# -------------------- Mongo --------------------
mongo_uri = os.getenv("mongo_uri")
if not mongo_uri:
    raise RuntimeError("mongo_uri not found in environment")
Client = MongoClient(mongo_uri)
db = Client["Emails"]
tokens_coll = Client['gmail_auth']['tokens']  # stores docs with keys: user_id, email, creds_b64, updated_at

# -------------------- Background processing helpers --------------------
def normalize_classification_output(preds):
    """
    Normalize various outputs from primarymodel.classify_emails to a list of dicts:
    - list[dict]
    - pandas.DataFrame
    - tuple([list[dict]],) accidental
    """
    try:
        import pandas as pd
    except Exception:
        pd = None

    # unwrap accidental single-element tuple
    if isinstance(preds, tuple) and len(preds) == 1:
        preds = preds[0]

    # DataFrame -> list of dicts
    if pd and isinstance(preds, pd.DataFrame):
        if 'prediction' not in preds.columns and 'pred' in preds.columns:
            preds = preds.rename(columns={'pred': 'prediction'})
        return preds.to_dict(orient='records')

    # already list-like
    if isinstance(preds, list):
        normalized = []
        for p in preds:
            if isinstance(p, dict):
                normalized.append(p)
            else:
                normalized.append({'prediction': str(p)})
        return normalized

    # fallback: wrap scalar into prediction
    return [{'prediction': str(preds)}]

def process_emails_for_user(user_doc, verbose=False):
    """
    Fetch and process unread emails for a single user.
    user_doc must contain 'user_id' and 'creds_b64'.
    """
    try:
        user_id = user_doc.get("user_id")
        if not user_id:
            if verbose: print("[WARN] user_doc missing user_id, skipping")
            return

        creds_b64 = user_doc.get("creds_b64")
        if not creds_b64:
            if verbose: print(f"[WARN] user {user_id} missing creds_b64")
            return

        # load credentials
        try:
            creds = pickle.loads(base64.b64decode(creds_b64.encode()))
        except Exception as e:
            print(f"[ERROR] Failed to load creds for {user_id}: {e}")
            return

        # fetch unread emails (fetch.get_unread_emails marks them READ after inserting)
        try:
            inserted = fetch.get_unread_emails(creds, user_id, verbose=verbose)
            if verbose:
                print(f"[INFO] fetch.get_unread_emails inserted {len(inserted)} docs for {user_id}")
        except Exception as e:
            print(f"[ERROR] fetch.get_unread_emails failed for {user_id}: {e}")
            return

        # get newly inserted docs (processed != True)
        col = db[user_id]
        new_docs = list(col.find({"processed": {"$ne": True}}))
        if not new_docs:
            if verbose:
                print(f"[INFO] No new docs to process for user {user_id}")
            return

        # Build dataframe for classifier
        import pandas as pd
        df = pd.DataFrame([{"subject": d.get("subject", ""), "body": d.get("body", ""), "_id": d.get("_id")} for d in new_docs])

        # classify (robust)
        try:
            preds_raw = primarymodel.classify_emails(df)
        except Exception as e:
            print(f"[ERROR] primarymodel.classify_emails raised for {user_id}: {e}")
            preds_raw = []

        preds = normalize_classification_output(preds_raw)
        if verbose:
            print(f"[DEBUG] user={user_id} preds_raw={preds_raw}")
            print(f"[DEBUG] user={user_id} preds_normalized={preds}")

        if len(preds) != len(new_docs):
            print(f"[WARN] Classification length mismatch for user {user_id}: docs={len(new_docs)} preds={len(preds)}")

        # iterate and update DB
        for doc, pred in zip(new_docs, preds):
            try:
                prediction = pred.get("prediction") if isinstance(pred, dict) else str(pred)
            except Exception:
                prediction = str(pred)

            is_spam = (str(prediction).strip().lower() == "spam")
            upd = {"spam": is_spam, "processed": True}

            if not is_spam:
                # attempt event extraction
                try:
                    event = secondarymodel.extract_event(doc.get("body", ""))
                except Exception as e:
                    print(f"[ERROR] extract_event failed for {user_id} doc {doc.get('_id')}: {e}")
                    event = None

                if event:
                    try:
                        cal_link = secondarymodel.cache_and_add_event(user_id, doc['_id'], creds, event)
                        upd["event"] = event
                        upd["cal_link"] = cal_link
                        if verbose: print(f"[INFO] Added event for {user_id} doc {doc.get('_id')}")
                    except Exception as e:
                        print(f"[ERROR] Failed to add event for {user_id} doc {doc.get('_id')}: {e}")
                        # fallback: add summary instead
                        try:
                            upd["summary"] = secondarymodel.summarize_email(doc.get("body", ""))
                        except Exception as e2:
                            print(f"[ERROR] Summarize fallback failed for {user_id} doc {doc.get('_id')}: {e2}")
                            upd["summary"] = "(summary failed)"
                else:
                    # not an event -> summarize
                    try:
                        upd["summary"] = secondarymodel.summarize_email(doc.get("body", ""))
                        if verbose: print(f"[INFO] Summarized email for {user_id} doc {doc.get('_id')}")
                    except Exception as e:
                        print(f"[ERROR] Summarization failed for {user_id} doc {doc.get('_id')}: {e}")
                        upd["summary"] = "(summary failed)"

            # write update
            try:
                col.update_one({"_id": doc["_id"]}, {"$set": upd})
            except Exception as e:
                print(f"[ERROR] Failed to update doc {doc.get('_id')} for {user_id}: {e}")

    except Exception as e:
        print(f"[ERROR] process_emails_for_user: {e}")

def process_emails_background(verbose=False):
    """
    Iterate over tokens collection and process each user.
    """
    if verbose:
        print("[INFO] Running background email processing...")
    try:
        cursor = tokens_coll.find({}, {"user_id": 1, "creds_b64": 1})
        for user_doc in cursor:
            if not user_doc.get("user_id") or not user_doc.get("creds_b64"):
                continue
            process_emails_for_user(user_doc, verbose=verbose)
    except Exception as e:
        print(f"[ERROR] process_emails_background: {e}")
    if verbose:
        print("[INFO] Background processing complete.")

# -------------------- Scheduler --------------------
scheduler = BackgroundScheduler()
scheduler.add_job(func=cleanup_old_emails, trigger="interval", hours=1)
# run background processing every 2 minutes
scheduler.add_job(func=lambda: process_emails_background(verbose=False), trigger="interval", minutes=2)

# don't start scheduler here — we will start it in __main__ to avoid duplicate schedulers in reloader

# -------------------- Routes --------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/continuewithgoogle")
def continue_with_google():
    auth_url = fetch.authenticate_user()
    if not auth_url:
        return redirect("/")
    return redirect(auth_url)

@app.route("/oauth2callback")
def oauthcallback():
    code = request.args.get("code")
    if not code:
        return redirect("/")

    user_id, creds = fetch.exchange_code_for_user(code)
    if not user_id or not creds:
        print("[ERROR] Failed to exchange code for user.")
        return redirect("/")

    # Save session
    session['user_id'] = user_id
    session['creds_b64'] = base64.b64encode(pickle.dumps(creds)).decode()

    # Persist token to DB (fetch.exchange_code_for_user already calls save_token_to_db)
    try:
        # save_token_to_db is idempotent
        fetch.save_token_to_db(getattr(creds, "token_response", {}).get("email", None) or user_id, user_id, creds)
    except Exception as e:
        print(f"[WARN] save_token_to_db failed: {e}")

    # Immediate fetch so user sees emails right away
    try:
        fetch.fetch.get_unread_emails(creds, user_id, limit=10, verbose=True)
    except Exception as e:
        print(f"[WARN] Immediate fetch failed: {e}")

    print(f"[INFO] Login successful: user_id={user_id}")
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return redirect("/")

    user_id = session['user_id']
    page = int(request.args.get("page", 1))
    page_size = 10
    skip = (page - 1) * page_size

    emails_cursor = db[user_id].find().skip(skip).limit(page_size)
    emails = list(emails_cursor)

    all_emails, event_emails, summary_emails = [], [], []

    for e in emails:
        subject = e.get("subject", "(No subject)")
        body = e.get("body", "(No body)")

        all_emails.append({
            "subject": subject,
            "body": body,
            "spam": e.get("spam", False)
        })

        if "event" in e:
            event = e["event"]
            event_emails.append({
                "subject": subject,
                "title": event.get("title", ""),
                "date": event.get("date", ""),
                "start_time": event.get("start_time", ""),
                "end_time": event.get("end_time", ""),
                "location": event.get("location", ""),
                "description": event.get("description", ""),
                "cal_link": e.get("cal_link")
            })

        if "summary" in e:
            summary_emails.append({
                "subject": subject,
                "summary": e["summary"]
            })

    next_page = page + 1 if db[user_id].count_documents({}) > skip + page_size else None

    return render_template(
        "dashboard.html",
        all_emails=all_emails,
        event_emails=event_emails,
        summary_emails=summary_emails,
        next_page=next_page,
        current_page=page,
        last_synced=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    )

@app.route("/manual-process")
def manual_process():
    """Trigger background processing on demand — returns counts for debug."""
    try:
        process_emails_background(verbose=True)
        return jsonify({"status": "ok", "message": "Triggered processing (see server logs)."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/session-debug")
def session_debug():
    return jsonify(dict(session))
@app.route("/fetch-more-emails")
def fetch_more_emails():
    if 'user_id' not in session or 'creds_b64' not in session:
        return jsonify({"status": "error", "message": "Not logged in"}), 403

    user_id = session['user_id']
    creds = pickle.loads(base64.b64decode(session['creds_b64'].encode()))
    page_token = request.args.get("page_token")

    result = fetch.get_unread_emails(creds, user_id, limit=10, page_token=page_token, verbose=False)
    inserted = result.get("inserted", [])
    next_page_token = result.get("next_page_token")

    return jsonify({
        "status": "ok",
        "emails": inserted,
        "next_page_token": next_page_token
    })

@app.route("/privacy-policy")
def pp():
    return render_template("privacy.html")
# -------------------- Entrypoint --------------------
if __name__ == "__main__":
  
    try:
        scheduler.start()
    except Exception as e:
        print(f"[WARN] scheduler already running or failed to start: {e}")
    bg_thread = Thread(target=lambda: process_emails_background(verbose=True), daemon=True)
    bg_thread.start()
    app.run(debug=True, use_reloader=False)
