import os
import django
import uuid
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Reboot.settings')
django.setup()

from Reboot_App.models import Roadmap, RoadmapReview, User, HPSScore

def seed_roadmap():
    user = User.objects.filter(username='member_05').first()
    if not user:
        print("member_05 not found. Creating member_05...")
        user = User.objects.create_user(username='member_05', password='password123', email='member_05@example.com')
        user.first_name = "Kavya"
        user.last_name = "Setava"
        user.save()

    print(f"Seeding roadmap for user: {user.username}")

    # Ensure user has an HPS score
    score = HPSScore.objects.filter(user=user).first()
    if not score:
        score = HPSScore.objects.create(
            user=user,
            hps_final=750,
            pillars={
                "physical": {"percentage": 70, "name": "Physical Health"},
                "mental": {"percentage": 80, "name": "Mental Wellness"}
            }
        )

    # Remove existing dummy roadmaps for this user
    Roadmap.objects.filter(user=user, title__contains="Seed").delete()

    # 1. Active Roadmap
    roadmap = Roadmap.objects.create(
        user=user,
        title="Seed: My Personalized Longevity Roadmap",
        hps_at_generation=750.0,
        ai_narrative="Your baseline HPS indicates strong mental resilience but room for improvement in glycemic control.",
        gaps=[
            {"pillar_code": "BR", "pillar_name": "Metabolic Health", "gap_score": 15.5, "icon": "heart-pulse", "color": "#EF4444"},
            {"pillar_code": "PF", "pillar_name": "Physical Fitness", "gap_score": 12.0, "icon": "dumbbell", "color": "#0F9F8F"}
        ],
        protocols=[
            {"domain": "Metabolic Health", "protocol": "Mediterranean Diet", "evidence": "Grade A", "priority_pillar": "Metabolic Health"}
        ],
        interventions={
            "BR": [{"id": "br-vitd", "intervention": "Vitamin D3 + K2 Supplementation", "priority": "must_do", "credits": 25}],
            "PF": [{"id": "pf-zone2", "intervention": "Zone 2 Cardio Protocol", "priority": "must_do", "credits": 0}]
        },
        biological_age={
            "current_biological_age": 32.5,
            "current_chronological_age": 35.0,
            "projected_biological_age_12m": 30.2,
            "projected_hps_12m": 830,
            "trajectory": []
        },
        phases=[
            {"phase": "Phase 1 — Foundation", "timeline": "Days 1-90", "objective": "Stabilization", "actions": ["Sleep hygiene", "Cardio"]},
            {"phase": "Phase 2 — Performance", "timeline": "Days 91-180", "objective": "Optimization", "actions": ["Resistance training"]}
        ],
        generated=False,
        status="active"
    )

    # 2. Review Record
    RoadmapReview.objects.create(
        roadmap=roadmap,
        hps_at_review=750,
        notes="Initial roadmap generated and approved by Dr. Smith.",
        goals_achieved=["Initial baseline established"],
        next_steps=["Follow the 3-month plan closely", "Re-test biomarkers in 90 days"]
    )
    
    print(f"Successfully seeded roadmap data for {user.username}.")

if __name__ == "__main__":
    seed_roadmap()
