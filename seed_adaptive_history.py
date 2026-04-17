import os
import django
import uuid
import random
from datetime import datetime, timedelta, timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Reboot.settings')
django.setup()

from Reboot_App.models import AdaptiveAssessment, User

def seed_adaptive_history():
    user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not user:
        print("No users found to seed data for.")
        return

    print(f"Seeding adaptive history for user: {user.username}")

    # Remove existing dummy data for this user to avoid clutter
    AdaptiveAssessment.objects.filter(user=user, algorithm="seed_test_v1.0").delete()

    # Create 5 assessments
    for i in range(5):
        # Note: timestamp is auto_now_add, so we'll just create them.
        # If we wanted to backdate, we'd need to modify the model or save twice.
        AdaptiveAssessment.objects.create(
            user=user,
            domain_scores={
                "mood": {"name": "Mood & Energy", "score": random.uniform(60, 90), "flag": "GREEN"},
                "calm": {"name": "Calm & Control", "score": random.uniform(60, 90), "flag": "GREEN"},
                "stress": {"name": "Stress Resilience", "score": random.uniform(40, 70), "flag": "YELLOW"},
                "resilience": {"name": "Inner Strength", "score": random.uniform(70, 95), "flag": "GREEN"},
                "wellbeing": {"name": "Quality of Life", "score": random.uniform(70, 95), "flag": "GREEN"},
                "sharpness": {"name": "Mental Sharpness", "score": random.uniform(70, 90), "flag": "GREEN"},
                "sleep": {"name": "Rest & Recovery", "score": random.uniform(50, 80), "flag": "YELLOW"}
            },
            overall_wellness=round(random.uniform(70, 85), 1),
            ca_result={"score": random.randint(80, 95), "tier": "GOOD"},
            ca_raw_mapped={"phq9": random.randint(1, 5), "gad7": random.randint(1, 4), "pss10": random.randint(5, 15)},
            mh_compat={
                "depression": {"level": "Minimal", "percentage": random.uniform(5, 15)},
                "anxiety": {"level": "Minimal", "percentage": random.uniform(5, 15)}
            },
            answers_count=35,
            algorithm="seed_test_v1.0"
        )
    
    print(f"Successfully seeded 5 assessment records for {user.username}.")

if __name__ == "__main__":
    seed_adaptive_history()
