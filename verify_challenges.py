import os
import django
import uuid

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Reboot.settings')
django.setup()

from Reboot_App.models import WellnessProgramme, Challenge, ChallengeParticipant
from django.contrib.auth.models import User

def verify_challenge_unification():
    print("--- Verifying Challenge Unification ---")
    
    # 1. Create a dummy Wellness Programme
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        admin = User.objects.create_superuser('admin_temp', 'admin@example.com', 'password123')
    
    prog, created = WellnessProgramme.objects.get_or_create(
        name="Verification Challenge (Wellness)",
        defaults={
            "type": "challenge",
            "target_dimension": "Physical",
            "duration_days": 15,
            "status": "active",
            "reward_healthcoins": 750,
            "created_by": admin
        }
    )
    if created:
        print(f"Created WellnessProgramme: {prog.id}")
    else:
        print(f"Existing WellnessProgramme found: {prog.id}")

    # 2. Check if it appears in Challenge list view logic
    # In views_employee.py, list_challenges merges Challenge and WellnessProgramme.
    # We can simulate this logic here.
    from Reboot_App.views_employee import list_challenges
    from rest_framework.test import APIRequestFactory, force_authenticate

    factory = APIRequestFactory()
    user = User.objects.filter(username='employee_1').first() # Assuming employee_1 exists from seed
    if not user:
        user = User.objects.create_user('test_user', 'test@example.com', 'password123')
    
    request = factory.get('/challenges')
    force_authenticate(request, user=user)
    response = list_challenges(request)
    
    challenges = response.data.get('challenges', [])
    found = any(c['id'] == str(prog.id) for c in challenges)
    print(f"Found programme in challenge list: {found}")
    
    if found:
        print("Success: WellnessProgramme correctly mapped to Challenge response keys.")
    else:
        print("Error: WellnessProgramme not found in list.")

if __name__ == "__main__":
    verify_challenge_unification()
