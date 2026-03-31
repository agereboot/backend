import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Reboot.settings")
django.setup()

from Reboot_App.models import Plan

PLAN_PRICING = {
    "rookie_league": 0,
    "velocity_circuit": 3000,
    "titan_arena": 8000,
    "apex_nexus": 15000,
}

def seed_plans():
    print("🧹 Wiping old generic plans...")
    Plan.objects.all().delete()
    
    print("🌱 Seeding Live Financial Tiers...")
    for code, price in PLAN_PRICING.items():
        Plan.objects.create(
            name=code,
            price=price,
            duration_days=365,
            features={"description": f"{code.replace('_', ' ').title()} Subscription limit"}
        )
        print(f"✅ Generated {code} @ INR {price}")

if __name__ == "__main__":
    seed_plans()
    print("🚀 Seeding Complete!")
