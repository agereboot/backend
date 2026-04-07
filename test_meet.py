"""
test_meet.py
────────────
Run with:  python test_meet.py
(No Django needed — runs standalone)
"""

from datetime import datetime, timezone, timedelta
from Google_meet_service import create_google_meet_event

print("\n" + "="*50)
print("Testing Google Meet Integration...")
print("="*50)

# Use plain Python datetime — no Django timezone needed
start_dt = datetime.now(tz=timezone(timedelta(hours=5, minutes=30)))  # IST

result = create_google_meet_event(
    title="Test Consultation",
    description="Testing Google Meet integration for AgeReboot",
    start_datetime=start_dt,
    duration_minutes=30,
    patient_email="kavyasetava135@gmail.com",
    doctor_email="kavyasetava135@gmail.com",
)

print("\nResults:")
print(f"  Meet Link    : {result['meet_link']}")
print(f"  Event ID     : {result['calendar_event_id']}")
print(f"  Calendar URL : {result['html_link']}")

is_real = (
    result["meet_link"].startswith("https://meet.google.com/")
    and "placeholder" not in result["meet_link"]
    and "error" not in result["meet_link"]
)

if is_real:
    print("\n✅ SUCCESS! Real Google Meet link created.")
    print("   Check your Gmail for a calendar invite.")
    print(f"   Open this link to test: {result['meet_link']}")
else:
    print("\n❌ Got a placeholder/error link.")
    print("   Reasons:")
    print("   1. token.json is missing — run: python run_once_get_token.py")
    print("   2. token.json is in wrong folder — must be same folder as this file")
    print("   3. Token expired — re-run: python run_once_get_token.py")

print("="*50 + "\n")