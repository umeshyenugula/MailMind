from googleapiclient.discovery import build
from datetime import datetime, timedelta

def add_events_to_calendar(creds, event):
    """
    Adds an event to Google Calendar.
    Returns the event link.
    """
    service = build("calendar", "v3", credentials=creds)

    date_str = event.get("date")
    start_time_str = event.get("start_time", "00:00")
    end_time_str = event.get("end_time", "01:00")

    try:
        start_dt = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M")
    except:
        # fallback to all-day event
        start_dt = datetime.strptime(date_str, "%Y-%m-%d")
        end_dt = start_dt + timedelta(hours=1)

    event_body = {
        "summary": event.get("title", "No Title"),
        "location": event.get("location", ""),
        "description": event.get("description", ""),
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kolkata"},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Kolkata"},
    }

    created_event = service.events().insert(calendarId="primary", body=event_body).execute()
    return created_event.get("htmlLink")
