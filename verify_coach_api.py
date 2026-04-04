import os
import django
import json
from rest_framework.test import APIClient
from django.contrib.auth.models import User

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Reboot.settings')
django.setup()

def verify():
    client = APIClient()
    coach = User.objects.get(username="fitness_coach_demo")
    member = User.objects.get(id=6)
    client.force_authenticate(user=coach)

    print("--- Testing Coach Dashboard ---")
    response = client.get('/api/coach/dashboard')
    print(f"Dashboard Status: {response.status_code}")

    print("\n--- Testing Fitness Profile ---")
    response = client.get(f'/api/coach/pfc/fitness-profile/{member.id}')
    print(f"Fitness Profile Status: {response.status_code}")

    print("\n--- Testing Challenges ---")
    response = client.get('/api/coach-v2/challenges')
    print(f"Challenges Status: {response.status_code}")

    print("\n--- Testing Psychological Therapy Programs ---")
    response = client.get('/api/coach-v2/psy/therapy-programs')
    print(f"Therapy Programs Status: {response.status_code}")

    print("\n--- Testing Coach V2 Profile ---")
    response = client.get('/api/coach-v2/profile')
    print(f"Profile Status: {response.status_code}")

    print("\n--- Testing Role Alerts ---")
    response = client.get('/api/coach-v2/alerts')
    print(f"Alerts Status: {response.status_code}")

    print("\n--- Testing Escalations ---")
    response = client.get('/api/coach-v2/escalations')
    print(f"Escalations Status: {response.status_code}")

if __name__ == "__main__":
    verify()
