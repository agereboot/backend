"""
Management command: seed_static_data
======================================
Seeds the two catalog tables that replace hardcoded Python constants:

  - BadgeCatalog          ← was BADGE_CATALOG list in hps_engine/employee.py
  - DopamineChallengeTemplate  ← was DAILY_DOPAMINE_CHALLENGES list in views_employee.py

Usage:
    python manage.py seed_static_data            # idempotent, skips existing rows
    python manage.py seed_static_data --reset    # wipe and re-seed
"""

from django.core.management.base import BaseCommand
from Reboot_App.models import BadgeCatalog, DopamineChallengeTemplate


# ── Badge catalog data (mirrors BADGE_CATALOG from hps_engine/employee.py) ───
BADGE_CATALOG_DATA = [
    {
        "code": "first_score",
        "name": "First Blood",
        "description": "Computed your first HPS score",
        "icon": "zap",
        "category": "milestone",
        "tier": "bronze",
        "requirement": "Compute HPS once",
    },
    {
        "code": "full_panel",
        "name": "Full Spectrum",
        "description": "Tested all 26 biomarkers",
        "icon": "flask",
        "category": "milestone",
        "tier": "gold",
        "requirement": "26/26 biomarkers recorded",
    },
    {
        "code": "tier_stable",
        "name": "Stable Ground",
        "description": "Reached LONGEVITY tier (600+)",
        "icon": "shield",
        "category": "tier",
        "tier": "bronze",
        "requirement": "HPS >= 600",
    },
    {
        "code": "tier_high",
        "name": "High Performer",
        "description": "Reached RESILIENCE tier (700+)",
        "icon": "trending-up",
        "category": "tier",
        "tier": "silver",
        "requirement": "HPS >= 700",
    },
    {
        "code": "tier_elite",
        "name": "Biological Elite",
        "description": "Reached CENTENARIAN tier (800+)",
        "icon": "crown",
        "category": "tier",
        "tier": "gold",
        "requirement": "HPS >= 800",
    },
    {
        "code": "streak_7",
        "name": "Weekly Warrior",
        "description": "7-day activity streak",
        "icon": "flame",
        "category": "streak",
        "tier": "bronze",
        "requirement": "7 consecutive active days",
    },
    {
        "code": "streak_30",
        "name": "Monthly Machine",
        "description": "30-day activity streak",
        "icon": "flame",
        "category": "streak",
        "tier": "silver",
        "requirement": "30 consecutive active days",
    },
    {
        "code": "streak_90",
        "name": "Quarterly Champion",
        "description": "90-day unbreakable streak",
        "icon": "flame",
        "category": "streak",
        "tier": "gold",
        "requirement": "90 consecutive active days",
    },
    {
        "code": "improvement_10",
        "name": "Rising Star",
        "description": "+10% HPS improvement",
        "icon": "arrow-up",
        "category": "improvement",
        "tier": "bronze",
        "requirement": "10% HPS improvement",
    },
    {
        "code": "improvement_25",
        "name": "Comeback King",
        "description": "+25% HPS improvement",
        "icon": "rocket",
        "category": "improvement",
        "tier": "silver",
        "requirement": "25% HPS improvement",
    },
    {
        "code": "wearable_sync",
        "name": "Plugged In",
        "description": "Connected a wearable device",
        "icon": "watch",
        "category": "integration",
        "tier": "bronze",
        "requirement": "Connect 1 wearable",
    },
    {
        "code": "lab_upload",
        "name": "Lab Rat",
        "description": "Uploaded lab results",
        "icon": "file-text",
        "category": "integration",
        "tier": "bronze",
        "requirement": "Upload 1 lab report",
    },
    {
        "code": "roadmap_gen",
        "name": "Cartographer",
        "description": "Generated longevity roadmap",
        "icon": "map",
        "category": "milestone",
        "tier": "silver",
        "requirement": "Generate AI roadmap",
    },
    {
        "code": "challenge_first",
        "name": "Challenger",
        "description": "Completed first challenge",
        "icon": "trophy",
        "category": "challenge",
        "tier": "bronze",
        "requirement": "Complete 1 challenge",
    },
    {
        "code": "challenge_5",
        "name": "Veteran",
        "description": "Completed 5 challenges",
        "icon": "award",
        "category": "challenge",
        "tier": "silver",
        "requirement": "Complete 5 challenges",
    },
    {
        "code": "social_first",
        "name": "Social Butterfly",
        "description": "Made first social post",
        "icon": "message-circle",
        "category": "social",
        "tier": "bronze",
        "requirement": "Post 1 update",
    },
    {
        "code": "top_10",
        "name": "Leaderboard Legend",
        "description": "Reached Top 10 in leaderboard",
        "icon": "crown",
        "category": "competition",
        "tier": "gold",
        "requirement": "Rank in top 10",
    },
    {
        "code": "nutrition_7",
        "name": "Clean Eater",
        "description": "7 days of nutrition logging",
        "icon": "apple",
        "category": "nutrition",
        "tier": "bronze",
        "requirement": "Log meals for 7 days",
    },
    {
        "code": "sleep_master",
        "name": "Sleep Master",
        "description": "Sleep efficiency above 90% for 7 days",
        "icon": "moon",
        "category": "health",
        "tier": "silver",
        "requirement": "7 days sleep eff > 90%",
    },
    {
        "code": "pillar_perfect",
        "name": "Pillar Perfect",
        "description": "All 5 pillars above 60%",
        "icon": "star",
        "category": "milestone",
        "tier": "gold",
        "requirement": "All pillars > 60%",
    },
]


# ── Daily dopamine challenge templates (mirrors DAILY_DOPAMINE_CHALLENGES) ────
DOPAMINE_CHALLENGE_DATA = [
    {
        "sort_order": 0,
        "title": "Hydration Hero",
        "description": "Drink 8 glasses of water today",
        "challenge_type": "wellness",
        "xp": 15,
        "surprise_pool": ["5 bonus credits", "Mini badge boost", "Priority queue in next challenge"],
    },
    {
        "sort_order": 1,
        "title": "Breathwork Blitz",
        "description": "Complete a 5-minute breathwork session",
        "challenge_type": "mindfulness",
        "xp": 20,
        "surprise_pool": ["10 bonus credits", "Stress score boost", "Exclusive breathwork badge"],
    },
    {
        "sort_order": 2,
        "title": "Step Surge",
        "description": "Take an extra 2,000 steps before noon",
        "challenge_type": "movement",
        "xp": 25,
        "surprise_pool": ["15 bonus credits", "Streak multiplier x2", "Activity badge unlock"],
    },
    {
        "sort_order": 3,
        "title": "Protein Power",
        "description": "Hit your protein target for every meal today",
        "challenge_type": "nutrition",
        "xp": 20,
        "surprise_pool": ["10 bonus credits", "Nutrition streak bonus", "Clean Eater badge progress"],
    },
    {
        "sort_order": 4,
        "title": "Sleep Ritual",
        "description": "Be in bed with screens off by 10:30 PM",
        "challenge_type": "sleep",
        "xp": 25,
        "surprise_pool": ["15 bonus credits", "Sleep efficiency boost", "Recovery badge progress"],
    },
    {
        "sort_order": 5,
        "title": "Gratitude Pulse",
        "description": "Write 3 things you're grateful for",
        "challenge_type": "social",
        "xp": 15,
        "surprise_pool": ["5 bonus credits", "Social engagement bonus", "Community badge progress"],
    },
    {
        "sort_order": 6,
        "title": "Cold Exposure",
        "description": "End your shower with 30 seconds of cold water",
        "challenge_type": "resilience",
        "xp": 30,
        "surprise_pool": ["20 bonus credits", "Resilience streak bonus", "Ice badge unlock"],
    },
    {
        "sort_order": 7,
        "title": "Posture Check",
        "description": "Set 5 posture check reminders",
        "challenge_type": "movement",
        "xp": 15,
        "surprise_pool": ["5 bonus credits", "Mobility score boost", "Spine warrior badge"],
    },
    {
        "sort_order": 8,
        "title": "Digital Detox",
        "description": "No social media for 3 hours today",
        "challenge_type": "mindfulness",
        "xp": 25,
        "surprise_pool": ["15 bonus credits", "Focus score boost", "Digital warrior badge"],
    },
    {
        "sort_order": 9,
        "title": "Veggie Load",
        "description": "Eat 5 different colored vegetables today",
        "challenge_type": "nutrition",
        "xp": 20,
        "surprise_pool": ["10 bonus credits", "Antioxidant boost", "Rainbow eater badge"],
    },
]


class Command(BaseCommand):
    help = "Seed BadgeCatalog and DopamineChallengeTemplate tables with static data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Wipe existing records and re-seed from scratch.",
        )

    def handle(self, *args, **options):
        reset = options["reset"]

        # ── BadgeCatalog ────────────────────────────────────────────────────
        if reset:
            BadgeCatalog.objects.all().delete()
            self.stdout.write("  Cleared BadgeCatalog table.")

        created_badges = 0
        updated_badges = 0
        for data in BADGE_CATALOG_DATA:
            obj, created = BadgeCatalog.objects.update_or_create(
                code=data["code"],
                defaults={
                    "name":        data["name"],
                    "description": data["description"],
                    "icon":        data["icon"],
                    "category":    data["category"],
                    "tier":        data["tier"],
                    "requirement": data["requirement"],
                    "is_active":   True,
                },
            )
            if created:
                created_badges += 1
            else:
                updated_badges += 1

        self.stdout.write(self.style.SUCCESS(
            f"  BadgeCatalog: {created_badges} created, {updated_badges} updated  "
            f"(total: {BadgeCatalog.objects.count()})"
        ))

        # ── DopamineChallengeTemplate ───────────────────────────────────────
        if reset:
            DopamineChallengeTemplate.objects.all().delete()
            self.stdout.write("  Cleared DopamineChallengeTemplate table.")

        created_dc = 0
        updated_dc = 0
        for data in DOPAMINE_CHALLENGE_DATA:
            obj, created = DopamineChallengeTemplate.objects.update_or_create(
                title=data["title"],
                defaults={
                    "description":    data["description"],
                    "challenge_type": data["challenge_type"],
                    "xp":             data["xp"],
                    "surprise_pool":  data["surprise_pool"],
                    "sort_order":     data["sort_order"],
                    "is_active":      True,
                },
            )
            if created:
                created_dc += 1
            else:
                updated_dc += 1

        self.stdout.write(self.style.SUCCESS(
            f"  DopamineChallengeTemplate: {created_dc} created, {updated_dc} updated  "
            f"(total: {DopamineChallengeTemplate.objects.count()})"
        ))

        self.stdout.write(self.style.SUCCESS("\n✅ seed_static_data complete."))
