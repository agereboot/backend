"""
google_meet_service.py  (OAuth2 version — works with regular Gmail)
────────────────────────────────────────────────────────────────────
Creates Google Meet links via Google Calendar API using OAuth2 tokens.

Setup
─────
1. pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
2. Create OAuth2 credentials in Google Cloud Console (Desktop App)
3. Run run_once_get_token.py locally to generate token.json
4. Place token.json in your Django project root (or set GOOGLE_TOKEN_FILE env var)

Environment variables
─────────────────────
GOOGLE_TOKEN_FILE        path to token.json  (default: "token.json")
GOOGLE_CREDENTIALS_FILE  path to oauth_credentials.json (only needed if token expires)
"""

import os
import uuid
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

TOKEN_FILE       = os.environ.get("GOOGLE_TOKEN_FILE",       "token.json")
CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE", "oauth_credentials.json")

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _get_calendar_service():
    if not os.path.exists(TOKEN_FILE):
        logger.warning("token.json not found — Google Meet integration disabled.")
        return None

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())

        if not creds or not creds.valid:
            logger.error("Google OAuth2 credentials invalid. Re-run run_once_get_token.py.")
            return None

        return build("calendar", "v3", credentials=creds, cache_discovery=False)

    except Exception as exc:
        logger.error("Failed to build Google Calendar service: %s", exc)
        return None


def create_google_meet_event(*, title, description, start_datetime, duration_minutes, patient_email, doctor_email):
    service      = _get_calendar_service()
    end_datetime = start_datetime + timedelta(minutes=duration_minutes)

    event_body = {
        "summary":     title,
        "description": description,
        "start": {"dateTime": start_datetime.isoformat(), "timeZone": "Asia/Kolkata"},
        "end":   {"dateTime": end_datetime.isoformat(),   "timeZone": "Asia/Kolkata"},
        "attendees": [{"email": patient_email}, {"email": doctor_email}],
        "conferenceData": {
            "createRequest": {
                "requestId":             uuid.uuid4().hex,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "email", "minutes": 60}, {"method": "popup", "minutes": 15}],
        },
        "guestsCanModifyEvent":  False,
        "guestsCanInviteOthers": False,
    }

    if service is None:
        fake_code = uuid.uuid4().hex[:12]
        return {
            "meet_link":         "https://meet.google.com/kyj-gkgo-emk",
            "calendar_event_id": f"placeholder_event_{fake_code}",
            "html_link":         "",
        }

    try:
        event = (
            service.events()
            .insert(calendarId="primary", body=event_body, conferenceDataVersion=1, sendUpdates="all")
            .execute()
        )
        entry_points = event.get("conferenceData", {}).get("entryPoints", [])
        meet_link = next((ep.get("uri", "") for ep in entry_points if ep.get("entryPointType") == "video"), "")
        return {"meet_link": meet_link, "calendar_event_id": event.get("id", ""), "html_link": event.get("htmlLink", "")}

    except Exception as exc:
        logger.error("Google Calendar event creation failed: %s", exc)
        fake_code = uuid.uuid4().hex[:12]
        return {"meet_link": f"https://meet.google.com/error-{fake_code}", "calendar_event_id": "", "html_link": ""}


def delete_google_meet_event(calendar_event_id: str) -> bool:
    if not calendar_event_id or calendar_event_id.startswith(("placeholder", "error")):
        return True
    service = _get_calendar_service()
    if not service:
        return False
    try:
        service.events().delete(calendarId="primary", eventId=calendar_event_id, sendUpdates="all").execute()
        return True
    except Exception as exc:
        logger.error("Failed to delete event %s: %s", calendar_event_id, exc)
        return False


def update_google_meet_event(*, calendar_event_id, new_start_datetime, duration_minutes):
    if not calendar_event_id or calendar_event_id.startswith(("placeholder", "error")):
        return {"meet_link": "", "calendar_event_id": calendar_event_id, "html_link": ""}
    service = _get_calendar_service()
    if not service:
        return {"meet_link": "", "calendar_event_id": calendar_event_id, "html_link": ""}
    try:
        end_datetime = new_start_datetime + timedelta(minutes=duration_minutes)
        event = service.events().get(calendarId="primary", eventId=calendar_event_id).execute()
        event["start"] = {"dateTime": new_start_datetime.isoformat(), "timeZone": "Asia/Kolkata"}
        event["end"]   = {"dateTime": end_datetime.isoformat(),       "timeZone": "Asia/Kolkata"}
        updated = (
            service.events()
            .update(calendarId="primary", eventId=calendar_event_id, body=event, conferenceDataVersion=1, sendUpdates="all")
            .execute()
        )
        entry_points = updated.get("conferenceData", {}).get("entryPoints", [])
        meet_link = next((ep.get("uri", "") for ep in entry_points if ep.get("entryPointType") == "video"), "")
        return {"meet_link": meet_link, "calendar_event_id": updated.get("id", calendar_event_id), "html_link": updated.get("htmlLink", "")}
    except Exception as exc:
        logger.error("Failed to update event %s: %s", calendar_event_id, exc)
        return {"meet_link": "", "calendar_event_id": calendar_event_id, "html_link": ""}