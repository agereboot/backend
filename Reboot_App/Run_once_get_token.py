"""
run_once_get_token.py
─────────────────────
Run this ONCE locally to generate token.json for Google Calendar OAuth2.

Steps:
1. Download your OAuth2 credentials from Google Cloud Console
   (APIs & Services → Credentials → OAuth 2.0 Client IDs → Download JSON)
2. Save it as oauth_credentials.json in this same folder
3. Run:  python run_once_get_token.py
4. A browser window opens → sign in with your Gmail → Allow access
5. token.json is created → copy it to your Django project root
6. Add to your .env:
       GOOGLE_TOKEN_FILE=token.json
       GOOGLE_CREDENTIALS_FILE=oauth_credentials.json

You only need to run this once. The token auto-refreshes afterwards.
"""

import os

CREDENTIALS_FILE = "oauth_credentials.json"
TOKEN_FILE       = "token.json"
SCOPES           = ["https://www.googleapis.com/auth/calendar"]

if not os.path.exists(CREDENTIALS_FILE):
    print(f"ERROR: {CREDENTIALS_FILE} not found.")
    print("Download it from: Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client IDs → Download JSON")
    exit(1)

from google_auth_oauthlib.flow import InstalledAppFlow

print("Opening browser for Google sign-in...")
flow  = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
creds = flow.run_local_server(port=0)

with open(TOKEN_FILE, "w") as f:
    f.write(creds.to_json())

print(f"\n✅ token.json created successfully!")
print(f"   Copy token.json to your Django project root.")
print(f"   Add to .env:  GOOGLE_TOKEN_FILE=token.json")