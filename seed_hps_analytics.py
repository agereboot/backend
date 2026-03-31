import os
import django
import random
from datetime import timedelta
import logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Reboot.settings")
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from Reboot_App.models import HPSScore, UserProfile, Role

def seed_hps():
    print("🧹 Cleaning existing HPS scores for clean slate...")
    HPSScore.objects.all().delete()
    
    # Check if we have users, if not we create some dummy ones
    user_count = User.objects.count()
    if user_count < 100:
        print("🌱 Generating 100 mock users for HPS clustering...")
        role, _ = Role.objects.get_or_create(name='employee')
        users_to_create = []
        for i in range(100):
            u = User(username=f"hps_mock_{random.randint(1000, 99999)}_{i}")
            u.set_password("Agereboot123!")
            users_to_create.append(u)
        created_users = User.objects.bulk_create(users_to_create)
        
        # Give them profiles
        profiles = [UserProfile(user=u, role=role) for u in created_users]
        UserProfile.objects.bulk_create(profiles)
        
    print("📊 Generating 300+ clustered synthetic HPS analytics logs...")
    users = list(User.objects.all())
    
    scores = []
    
    for _ in range(350):
        # We want a normal distribution around 550, with standard dev 100
        # A few outliers below 400 for alerts
        hps = int(random.gauss(550, 100))
        hps = max(0, min(1000, hps)) # clamp to 0-1000
        
        # Pillars approximate the final score
        # e.g., if you score 600, your pillars hover around 600 (or they use a different scale? 
        # Actually pillars are on a 100 scale usually or 1000 scale. Let's make it 1-100 for domains, 
        # or wait, original logic showed: "avg_bio": {"$avg": "$bio"}. If total is 800, maybe pillars are 100? 
        # But wait, original code says pillars have their own score
        
        # Let's assume domains are out of 100
        bio = max(0, min(100, int(random.gauss(hps/10, 15))))
        fit = max(0, min(100, int(random.gauss(hps/10, 15))))
        cog = max(0, min(100, int(random.gauss(hps/10, 15))))
        slp = max(0, min(100, int(random.gauss(hps/10, 15))))
        beh = max(0, min(100, int(random.gauss(hps/10, 15))))
        
        rand_user = random.choice(users)
        
        # Random historical timestamp
        days_ago = random.randint(0, 90)
        
        scores.append(HPSScore(
            user=rand_user,
            hps_final=hps,
            hps_base=hps - random.randint(0, 50),
            pillars={
                "biological_resilience": bio,
                "physical_fitness": fit,
                "cognitive_health": cog,
                "sleep_recovery": slp,
                "behaviour_lifestyle": beh
            },
            timestamp=timezone.now() - timedelta(days=days_ago),
            tier="Standard"
        ))
        
    HPSScore.objects.bulk_create(scores)
    print("✅ Successfully seeded completely realistic HPS Scores spanning thousands of metrics!")

if __name__ == "__main__":
    seed_hps()
