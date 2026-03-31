"""
HPS Engine v3.0 — Employee Portal Business Logic
Challenges, Badges, Credits, Nutrition, Social Feed, Care Team.
"""
import random
import uuid
from datetime import datetime, timezone, timedelta

# === Badge Definitions ===
BADGE_CATALOG = [
    {"code": "first_score", "name": "First Blood", "description": "Computed your first HPS score", "icon": "zap", "category": "milestone", "tier": "bronze", "requirement": "Compute HPS once"},
    {"code": "full_panel", "name": "Full Spectrum", "description": "Tested all 26 biomarkers", "icon": "flask", "category": "milestone", "tier": "gold", "requirement": "26/26 biomarkers recorded"},
    {"code": "tier_stable", "name": "Stable Ground", "description": "Reached LONGEVITY tier (600+)", "icon": "shield", "category": "tier", "tier": "bronze", "requirement": "HPS >= 600"},
    {"code": "tier_high", "name": "High Performer", "description": "Reached RESILIENCE tier (700+)", "icon": "trending-up", "category": "tier", "tier": "silver", "requirement": "HPS >= 700"},
    {"code": "tier_elite", "name": "Biological Elite", "description": "Reached CENTENARIAN tier (800+)", "icon": "crown", "category": "tier", "tier": "gold", "requirement": "HPS >= 800"},
    {"code": "streak_7", "name": "Weekly Warrior", "description": "7-day activity streak", "icon": "flame", "category": "streak", "tier": "bronze", "requirement": "7 consecutive active days"},
    {"code": "streak_30", "name": "Monthly Machine", "description": "30-day activity streak", "icon": "flame", "category": "streak", "tier": "silver", "requirement": "30 consecutive active days"},
    {"code": "streak_90", "name": "Quarterly Champion", "description": "90-day unbreakable streak", "icon": "flame", "category": "streak", "tier": "gold", "requirement": "90 consecutive active days"},
    {"code": "improvement_10", "name": "Rising Star", "description": "+10% HPS improvement", "icon": "arrow-up", "category": "improvement", "tier": "bronze", "requirement": "10% HPS improvement"},
    {"code": "improvement_25", "name": "Comeback King", "description": "+25% HPS improvement", "icon": "rocket", "category": "improvement", "tier": "silver", "requirement": "25% HPS improvement"},
    {"code": "wearable_sync", "name": "Plugged In", "description": "Connected a wearable device", "icon": "watch", "category": "integration", "tier": "bronze", "requirement": "Connect 1 wearable"},
    {"code": "lab_upload", "name": "Lab Rat", "description": "Uploaded lab results", "icon": "file-text", "category": "integration", "tier": "bronze", "requirement": "Upload 1 lab report"},
    {"code": "roadmap_gen", "name": "Cartographer", "description": "Generated longevity roadmap", "icon": "map", "category": "milestone", "tier": "silver", "requirement": "Generate AI roadmap"},
    {"code": "challenge_first", "name": "Challenger", "description": "Completed first challenge", "icon": "trophy", "category": "challenge", "tier": "bronze", "requirement": "Complete 1 challenge"},
    {"code": "challenge_5", "name": "Veteran", "description": "Completed 5 challenges", "icon": "award", "category": "challenge", "tier": "silver", "requirement": "Complete 5 challenges"},
    {"code": "social_first", "name": "Social Butterfly", "description": "Made first social post", "icon": "message-circle", "category": "social", "tier": "bronze", "requirement": "Post 1 update"},
    {"code": "top_10", "name": "Leaderboard Legend", "description": "Reached Top 10 in leaderboard", "icon": "crown", "category": "competition", "tier": "gold", "requirement": "Rank in top 10"},
    {"code": "nutrition_7", "name": "Clean Eater", "description": "7 days of nutrition logging", "icon": "apple", "category": "nutrition", "tier": "bronze", "requirement": "Log meals for 7 days"},
    {"code": "sleep_master", "name": "Sleep Master", "description": "Sleep efficiency above 90% for 7 days", "icon": "moon", "category": "health", "tier": "silver", "requirement": "7 days sleep eff > 90%"},
    {"code": "pillar_perfect", "name": "Pillar Perfect", "description": "All 5 pillars above 60%", "icon": "star", "category": "milestone", "tier": "gold", "requirement": "All pillars > 60%"},
]

CHALLENGE_TEMPLATES = [
    {"name": "10K Steps Sprint", "description": "Walk 10,000 steps daily for 7 days", "type": "steps", "duration_days": 7, "target_metric": "steps", "target_value": 70000, "reward_badges": ["streak_7"], "reward_credits": 50},
    {"name": "Sleep Hygiene Challenge", "description": "Achieve 85%+ sleep efficiency for 14 nights", "type": "sleep", "duration_days": 14, "target_metric": "sleep_efficiency", "target_value": 85, "reward_badges": ["sleep_master"], "reward_credits": 75},
    {"name": "Nutrition Reset", "description": "Log all meals for 7 consecutive days", "type": "nutrition", "duration_days": 7, "target_metric": "meal_logs", "target_value": 21, "reward_badges": ["nutrition_7"], "reward_credits": 40},
    {"name": "HPS Boost Sprint", "description": "Improve your HPS by 30+ points in 30 days", "type": "hps_improvement", "duration_days": 30, "target_metric": "hps_delta", "target_value": 30, "reward_badges": ["improvement_10"], "reward_credits": 100},
    {"name": "Full Panel Challenge", "description": "Complete all 26 biomarker tests within 14 days", "type": "biomarker", "duration_days": 14, "target_metric": "biomarkers_tested", "target_value": 26, "reward_badges": ["full_panel"], "reward_credits": 150},
    {"name": "Zone 2 Cardio Month", "description": "Complete 12 zone-2 cardio sessions in 30 days", "type": "exercise", "duration_days": 30, "target_metric": "cardio_sessions", "target_value": 12, "reward_badges": ["streak_30"], "reward_credits": 80},
]

SAMPLE_NUTRITION_PLANS = {
    "breakfast": [
        {"item": "Overnight oats with berries and chia seeds", "calories": 320, "protein": 12, "carbs": 45, "fats": 10},
        {"item": "Egg white omelette with spinach and avocado", "calories": 280, "protein": 22, "carbs": 8, "fats": 16},
        {"item": "Greek yogurt with granola and honey", "calories": 310, "protein": 18, "carbs": 42, "fats": 8},
    ],
    "lunch": [
        {"item": "Grilled chicken salad with quinoa", "calories": 420, "protein": 35, "carbs": 30, "fats": 14},
        {"item": "Salmon bowl with brown rice and vegetables", "calories": 480, "protein": 32, "carbs": 42, "fats": 16},
        {"item": "Lentil soup with whole wheat bread", "calories": 380, "protein": 20, "carbs": 50, "fats": 8},
    ],
    "dinner": [
        {"item": "Baked fish with roasted vegetables", "calories": 350, "protein": 30, "carbs": 22, "fats": 12},
        {"item": "Chicken stir-fry with tofu and broccoli", "calories": 400, "protein": 34, "carbs": 28, "fats": 14},
        {"item": "Mediterranean bowl with falafel", "calories": 420, "protein": 16, "carbs": 48, "fats": 18},
    ],
    "snacks": [
        {"item": "Mixed nuts and dark chocolate", "calories": 180, "protein": 5, "carbs": 14, "fats": 12},
        {"item": "Protein shake with banana", "calories": 220, "protein": 24, "carbs": 26, "fats": 3},
    ],
}


def generate_sample_challenges(n=6):
    challenges = []
    for i, tmpl in enumerate(CHALLENGE_TEMPLATES[:n]):
        start = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 10))
        challenges.append({
            "id": str(uuid.uuid4()),
            "name": tmpl["name"],
            "description": tmpl["description"],
            "type": tmpl["type"],
            "duration_days": tmpl["duration_days"],
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=tmpl["duration_days"])).isoformat(),
            "target_metric": tmpl["target_metric"],
            "target_value": tmpl["target_value"],
            "reward_badges": tmpl["reward_badges"],
            "reward_credits": tmpl["reward_credits"],
            "status": "active",
            "participants": [],
            "created_at": start.isoformat(),
        })
    return challenges


def generate_sample_feed_items(user_id, user_name, count=10):
    templates = [
        {"type": "achievement", "content": "earned the **Rising Star** badge for 10% HPS improvement!"},
        {"type": "milestone", "content": "reached **LONGEVITY** tier with an HPS of 616!"},
        {"type": "challenge_join", "content": "joined the **10K Steps Sprint** challenge."},
        {"type": "hps_update", "content": "computed a new HPS score of **616** points."},
        {"type": "wearable_sync", "content": "synced their **Oura Ring** data — 4 new metrics imported."},
        {"type": "post", "content": "Feeling great after a week of consistent Zone 2 cardio. HRV is trending up!"},
        {"type": "lab_upload", "content": "uploaded new lab results from **Thyrocare** — 7 biomarkers processed."},
        {"type": "nutrition_log", "content": "logged 3 meals today — Diet quality score: **78/100**."},
        {"type": "streak", "content": "is on a **7-day** activity streak! Keep it going."},
        {"type": "challenge_complete", "content": "completed the **Sleep Hygiene Challenge** and earned 75 credits!"},
    ]
    items = []
    for i in range(min(count, len(templates))):
        t = templates[i]
        items.append({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "user_name": user_name,
            "type": t["type"],
            "content": t["content"],
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 168))).isoformat(),
            "likes": random.randint(0, 15),
            "comments": [],
        })
    return sorted(items, key=lambda x: x["timestamp"], reverse=True)


def compute_badge_eligibility(user_data, hps_score, biomarker_count, challenge_count):
    earned = []
    if hps_score:
        earned.append("first_score")
        if hps_score >= 600:
            earned.append("tier_stable")
        if hps_score >= 700:
            earned.append("tier_high")
        if hps_score >= 800:
            earned.append("tier_elite")
    if biomarker_count >= 26:
        earned.append("full_panel")
    if biomarker_count >= 10:
        earned.append("lab_upload")
    if challenge_count >= 1:
        earned.append("challenge_first")
    if challenge_count >= 5:
        earned.append("challenge_5")
    return earned
