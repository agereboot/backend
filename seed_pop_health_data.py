import os
import django
import random
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Reboot.settings')
django.setup()

from django.contrib.auth.models import User
from Reboot_App.models import HPSScore, CCAssignment

def seed():
    print("Starting Population Health data seeding...")
    
    clinician = User.objects.filter(email='clinical_admin@agereboot.com').first()
    if not clinician:
        print("Error: clinical_admin@agereboot.com not found.")
        return

    # Identify 6 members
    members = list(User.objects.filter(username__startswith='member_').order_by('id')[:6])
    if len(members) < 6:
        print(f"Warning: Only found {len(members)} members. Proceeding anyway.")

    print(f"Assigning {len(members)} members to {clinician.username}...")
    
    # 1. Ensure Assignments
    for member in members:
        CCAssignment.objects.get_or_create(
            member=member,
            cc=clinician,
            defaults={"role": "primary_physician"}
        )

    # 2. Generate HPS Scores
    # Targets based on user sample: Avg 587.8, Optimal 2, At-Risk 1, Longevity 1
    target_scores = [350, 480, 520, 610, 720, 850]
    random.shuffle(target_scores)
    
    print("Generating HPS scores...")
    for i, member in enumerate(members):
        score_val = target_scores[i % len(target_scores)]
        
        # Determine tier
        tier = "UNKNOWN"
        if score_val >= 800: tier = "LONGEVITY"
        elif score_val >= 700: tier = "OPTIMAL"
        elif score_val >= 500: tier = "AVERAGE"
        elif score_val < 400: tier = "AT_RISK"
        
        # Pillar values around 15-30
        pillars = {
            "BR": round(random.uniform(20, 30), 1),
            "PF": round(random.uniform(15, 25), 1),
            "CA": round(random.uniform(20, 30), 1),
            "SR": round(random.uniform(15, 25), 1),
            "BL": round(random.uniform(15, 25), 1)
        }
        
        HPSScore.objects.create(
            user=member,
            hps_final=score_val,
            hps_base=score_val - random.randint(10, 30),
            tier=tier,
            pillars=pillars,
            timestamp=timezone.now(),
            algorithm_version="v2.1",
            audit_hash="dummy_hash_" + str(random.randint(1000, 9999))
        )
        print(f"  Created HPS {score_val} for {member.username} (Tier: {tier})")

    print("\nPopulation Health data seeding complete.")

if __name__ == "__main__":
    seed()
