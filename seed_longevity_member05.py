import os
import django
import uuid
import random
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Reboot.settings')
django.setup()

from Reboot_App.models import LongevityProtocol, User

def seed_longevity():
    user = User.objects.filter(username='member_05').first()
    if not user:
        # Fallback to creating member_05 if they don't exist? 
        # User said "if user required add data to member_05", 
        # usually suggests they are there or I should make them.
        print("member_05 not found. Creating member_05...")
        user = User.objects.create_user(username='member_05', password='password123', email='member_05@example.com')
        user.first_name = "Kavya"
        user.last_name = "Setava"
        user.save()

    print(f"Seeding longevity protocol for user: {user.username}")

    # Remove existing dummy protocols for this user to ensure clean state
    # LongevityProtocol.objects.filter(patient=user).delete()

    # 1. Approved Protocol (The Active Roadmap)
    LongevityProtocol.objects.create(
        patient=user,
        patient_name=f"{user.first_name} {user.last_name}" if user.first_name else user.username,
        generated_by=user, 
        generated_by_name="System AI Engine",
        hps_at_generation=720,
        status="approved",
        three_month_plan=[
            {"category": "Supplements", "action": "NMN 500mg Morning + Vitamin D3 5000 IU", "priority": "high"},
            {"category": "Fitness", "action": "150 min Zone 2 Cardio + 3 Resistance Sessions", "priority": "high"},
            {"category": "Sleep", "action": "Magnesium Threonate 400mg before bed", "priority": "medium"}
        ],
        six_month_plan=[
            {"category": "Advanced", "action": "Intro to Spermidine 1mg for Autophagy", "priority": "medium"},
            {"category": "Imaging", "action": "Repeat DEXA and VO2 Max Assessment", "priority": "high"}
        ],
        nine_month_plan=[
            {"category": "Review", "action": "Comprehensive Annual Longevity Audit", "priority": "high"}
        ]
    )
    
    # 2. A Pending Protocol (Simulating a newly generated roadmap awaiting review)
    LongevityProtocol.objects.create(
        patient=user,
        patient_name=f"{user.first_name} {user.last_name}" if user.first_name else user.username,
        generated_by=user,
        generated_by_name="AI Diagnostics v4.2",
        hps_at_generation=745,
        status="pending_review",
        three_month_plan=[
            {"category": "Intervention", "action": "Increase fiber intake to 35g/day", "priority": "high"}
        ],
        six_month_plan=[],
        nine_month_plan=[]
    )
    
    print(f"Successfully seeded longevity protocol data for {user.username}.")

if __name__ == "__main__":
    seed_longevity()
