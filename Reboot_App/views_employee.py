"""
views_employee.py
================
Django DRF port of flask_temp/backend/routes/employee.py

All 20 endpoints are replicated here using Django ORM (SQLite).
Response keys/structure kept IDENTICAL to the original FastAPI routes.

Endpoints:
  GET  /employee/dashboard-stats
  GET  /employee/global-ranking
  GET  /employee/daily-challenge
  POST /employee/daily-challenge/complete
  GET  /employee/action-items
  GET  /employee/streak-calendar
  GET  /challenges
  POST /challenges/<id>/join
  POST /challenges/<id>/progress
  GET  /rewards/badges
  GET  /rewards/my-badges
  GET  /feed
  GET  /feed/highlights
  POST /feed/post
  POST /feed/<id>/like
  POST /feed/<id>/comment
  POST /feed/upload-photo
  GET  /feed/photo/<photo_id>
  POST /profile/upload-photo
  GET  /profile/photo/<user_id>
  GET  /employee/address
  PUT  /employee/address
  GET  /leaderboard
  GET  /leaderboard/franchises
"""

import os
import re
import uuid
import random
import hashlib
from datetime import datetime, timedelta, timezone as dt_timezone

from django.contrib.auth.models import User
from django.db.models import Q, Max
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status

from .models import (
    UserProfile, Challenge, ChallengeParticipant,
    HPSScore, BiomarkerResult, WearableConnection, NutritionLog,
    UserBadge, CreditBalance, CreditTransaction,
    SocialPost, SocialComment,
    Roadmap, Medication, DailyChallenge,
    PrivacySetting, UserAddress, HealthSnapshot,
    BadgeCatalog, DopamineChallengeTemplate, WellnessProgramme,
)
from .hps_engine.employee import (
    BADGE_CATALOG as _BADGE_CATALOG_FALLBACK, CHALLENGE_TEMPLATES,
    compute_badge_eligibility, generate_sample_challenges, generate_sample_feed_items,
)


# ─── DB-backed catalog helpers ────────────────────────────────────────────────

def _get_badge_catalog():
    """
    Return list of badge dicts from DB (BadgeCatalog table).
    Falls back to hardcoded constant if DB is empty (e.g. before seeding).
    """
    qs = list(BadgeCatalog.objects.filter(is_active=True))
    if qs:
        return [b.to_dict() for b in qs]
    return _BADGE_CATALOG_FALLBACK  # fallback


def _get_dopamine_templates():
    """
    Return list of dopamine challenge template dicts from DB.
    Falls back to hardcoded constant if DB is empty.
    """
    qs = list(DopamineChallengeTemplate.objects.filter(is_active=True).order_by("sort_order", "id"))
    if qs:
        return [t.to_dict() for t in qs]
    # Fallback to hardcoded constant (imported at top of this module)
    return DAILY_DOPAMINE_CHALLENGES

# ─── Upload directories ────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "feed_photos")
PROFILE_PHOTO_DIR = os.path.join(BASE_DIR, "uploads", "profile_photos")
SNAPSHOT_DIR = os.path.join(BASE_DIR, "uploads", "health_snapshots")
for _d in (UPLOAD_DIR, PROFILE_PHOTO_DIR, SNAPSHOT_DIR):
    os.makedirs(_d, exist_ok=True)

MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 MB

SNAPSHOT_CATEGORIES = ["meal", "workout", "sleep", "progress", "lab_result", "supplements", "other"]

# ─── Static fallback pool (used only if DB not yet seeded) ───────────────────
# After running: python manage.py seed_static_data
# these views will read from BadgeCatalog / DopamineChallengeTemplate tables instead.
DAILY_DOPAMINE_CHALLENGES = [
    {"title": "Hydration Hero", "description": "Drink 8 glasses of water today", "type": "wellness", "xp": 15,
     "surprise_pool": ["5 bonus credits", "Mini badge boost", "Priority queue in next challenge"]},
    {"title": "Breathwork Blitz", "description": "Complete a 5-minute breathwork session", "type": "mindfulness", "xp": 20,
     "surprise_pool": ["10 bonus credits", "Stress score boost", "Exclusive breathwork badge"]},
    {"title": "Step Surge", "description": "Take an extra 2,000 steps before noon", "type": "movement", "xp": 25,
     "surprise_pool": ["15 bonus credits", "Streak multiplier x2", "Activity badge unlock"]},
    {"title": "Protein Power", "description": "Hit your protein target for every meal today", "type": "nutrition", "xp": 20,
     "surprise_pool": ["10 bonus credits", "Nutrition streak bonus", "Clean Eater badge progress"]},
    {"title": "Sleep Ritual", "description": "Be in bed with screens off by 10:30 PM", "type": "sleep", "xp": 25,
     "surprise_pool": ["15 bonus credits", "Sleep efficiency boost", "Recovery badge progress"]},
    {"title": "Gratitude Pulse", "description": "Write 3 things you're grateful for", "type": "social", "xp": 15,
     "surprise_pool": ["5 bonus credits", "Social engagement bonus", "Community badge progress"]},
    {"title": "Cold Exposure", "description": "End your shower with 30 seconds of cold water", "type": "resilience", "xp": 30,
     "surprise_pool": ["20 bonus credits", "Resilience streak bonus", "Ice badge unlock"]},
    {"title": "Posture Check", "description": "Set 5 posture check reminders", "type": "movement", "xp": 15,
     "surprise_pool": ["5 bonus credits", "Mobility score boost", "Spine warrior badge"]},
    {"title": "Digital Detox", "description": "No social media for 3 hours today", "type": "mindfulness", "xp": 25,
     "surprise_pool": ["15 bonus credits", "Focus score boost", "Digital warrior badge"]},
    {"title": "Veggie Load", "description": "Eat 5 different colored vegetables today", "type": "nutrition", "xp": 20,
     "surprise_pool": ["10 bonus credits", "Antioxidant boost", "Rainbow eater badge"]},
]

DEMO_MEDICATIONS = [
    {"id": "med_1", "name": "Metformin 500mg", "condition": "Pre-Diabetes", "schedule": "evening",
     "time": "8:00 PM", "with_food": True, "refill_date": "2026-04-01", "refill_remaining": 27,
     "instructions": "Take with dinner.", "compliance_reward": 2},
    {"id": "med_2", "name": "Amlodipine 5mg", "condition": "Mild Hypertension", "schedule": "morning",
     "time": "8:00 AM", "with_food": False, "refill_date": "2026-03-25", "refill_remaining": 20,
     "instructions": "Take on empty stomach.", "compliance_reward": 2},
    {"id": "med_3", "name": "Vitamin D3 5000 IU", "condition": "Vitamin D Deficiency", "schedule": "morning",
     "time": "9:00 AM", "with_food": True, "refill_date": "2026-05-10", "refill_remaining": 66,
     "instructions": "Take with fat-containing meal.", "compliance_reward": 1},
    {"id": "med_4", "name": "Omega-3 Fish Oil 1000mg", "condition": "General Wellness", "schedule": "morning",
     "time": "9:00 AM", "with_food": True, "refill_date": "2026-04-15", "refill_remaining": 41,
     "instructions": "Take with breakfast.", "compliance_reward": 1},
]


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _add_credits(user, amount, description):
    """Add credits to user's balance and record a transaction."""
    bal, _ = CreditBalance.objects.get_or_create(user=user)
    bal.available += amount
    bal.purchased += amount
    bal.save(update_fields=["available", "purchased"])
    CreditTransaction.objects.create(
        user=user,
        type="reward",          # field is 'type' not 'transaction_type'
        amount=amount,
        description=description,
    )


def _award_badge(user, badge_code, challenge=None):
    """Award a badge if not already earned."""
    UserBadge.objects.get_or_create(user=user, badge_code=badge_code)


def _create_feed_item(user, post_type, content, photo_id=None):
    """Create a social feed post and return its dict."""
    post = SocialPost.objects.create(
        user=user,
        post_type=post_type,
        content=content,
        photo_id=photo_id,
    )
    return _post_to_dict(post, user)


def _post_to_dict(post, requesting_user=None):
    """Serialize a SocialPost to a dict matching the original API response."""
    liked_by_ids = list(post.liked_by.values_list("id", flat=True))
    user_liked = requesting_user.id in liked_by_ids if requesting_user else False
    profile = getattr(post.user, "profile", None)
    return {
        "id": str(post.id),
        "user_id": post.user.id,
        "user_name": f"{post.user.first_name} {post.user.last_name}".strip() or post.user.username,
        "type": post.post_type,
        "content": post.content,
        "photo_id": post.photo_id,
        "timestamp": post.created_at.isoformat(),
        "likes": post.likes,
        "liked_by": liked_by_ids,
        "user_liked": user_liked,
        "comments": [
            {
                "id": str(c.id),
                "user_id": c.user.id,
                "user_name": f"{c.user.first_name} {c.user.last_name}".strip() or c.user.username,
                "text": c.text,
                "timestamp": c.created_at.isoformat(),
            }
            for c in post.comments.select_related("user").all()
        ],
        "user_franchise": profile.company.name if profile and profile.company else "",
        "user_avatar_initial": (post.user.first_name or post.user.username or "A")[0].upper(),
    }


def _get_user_hps(user):
    """Return the latest HPSScore for user or None."""
    return HPSScore.objects.filter(user=user).order_by("-timestamp").first()


def _get_profile_name(user):
    name = f"{user.first_name} {user.last_name}".strip()
    return name or user.username


def _get_franchise(user):
    try:
        c = user.profile.company
        return c.name if c else "Independent"
    except Exception:
        return "Independent"


# ══════════════════════════════════════════════════════════════════════════════
# 1. GET /employee/dashboard-stats
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    user = request.user
    now = datetime.now(dt_timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    participations = ChallengeParticipant.objects.filter(
        user=user
    ).select_related("challenge", "wellness_programme")

    active_challenges = []
    for p in participations:
        # Standardize challenge data from either Challenge or WellnessProgramme
        ch_name = ""
        ch_type = "general"
        ch_reward = 0
        ch_target = 100
        ch_end = None
        ch_id = None
        is_active = False

        if p.challenge:
            ch = p.challenge
            ch_id = ch.id
            ch_name = ch.name
            ch_type = ch.challenge_type if hasattr(ch, "challenge_type") else "general"
            ch_reward = ch.reward_credits if hasattr(ch, "reward_credits") else 0
            ch_target = ch.target_value or 100
            ch_end = ch.end_date
            is_active = (ch.status == "active")
        elif p.wellness_programme:
            ch = p.wellness_programme
            ch_id = str(ch.id)
            ch_name = ch.name
            ch_type = ch.type or "challenge"
            ch_reward = ch.reward_healthcoins
            ch_target = 100 # Default target for programmes if not specified
            ch_end = None # Programmes might not have end_date field
            is_active = (ch.status == "active")

        if is_active:
            progress = p.progress or 0
            active_challenges.append({
                "id": ch_id,
                "name": ch_name,
                "type": ch_type,
                "progress": progress,
                "target": ch_target,
                "pct": round((progress / ch_target) * 100, 1) if ch_target > 0 else 0,
                "reward_credits": ch_reward,
                "end_date": ch_end.isoformat() if ch_end else None,
            })

    # Streak days from UserProfile
    try:
        streak = user.profile.streak_days if hasattr(user.profile, "streak_days") else 0
    except Exception:
        streak = 0

    # Weekly credits (reward/bonus transactions in last 7 days)
    weekly_credits = (
        CreditTransaction.objects.filter(
            user=user,
            type__in=["reward", "bonus"],   # field is 'type' not 'transaction_type'
            created_at__gte=week_ago,
        ).values_list("amount", flat=True)
    )
    weekly_credits_total = sum(weekly_credits)

    # Monthly badges — read from DB catalog
    monthly_badge_qs = UserBadge.objects.filter(user=user, earned_at__gte=month_ago)
    badge_codes = set(monthly_badge_qs.values_list("badge_code", flat=True))
    catalog = _get_badge_catalog()
    badge_details = [b for b in catalog if b["code"] in badge_codes]

    return Response({
        "active_challenges": active_challenges,
        "streak_days": streak,
        "weekly_credits": weekly_credits_total,
        "monthly_badges": badge_details,
        "monthly_badges_count": len(badge_details),
        "total_active_challenges": len(active_challenges),
    })


# ══════════════════════════════════════════════════════════════════════════════
# 2. GET /employee/global-ranking
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def global_ranking(request):
    user = request.user

    # Latest HPS per user — subquery approach
    from django.db.models import Subquery, OuterRef
    latest_ts = HPSScore.objects.filter(user=OuterRef("user")).order_by("-timestamp").values("timestamp")[:1]
    all_scores = (
        HPSScore.objects.filter(timestamp=Subquery(latest_ts))
        .select_related("user__profile__company")
        .order_by("-hps_final")
    )

    all_scores_list = list(all_scores)
    total_players = len(all_scores_list)

    user_rank = None
    for i, s in enumerate(all_scores_list):
        if s.user_id == user.id:
            user_rank = i + 1
            break

    top_20 = []
    for i, s in enumerate(all_scores_list[:20]):
        top_20.append({
            "rank": i + 1,
            "name": _get_profile_name(s.user),
            "franchise": _get_franchise(s.user),
            "is_you": s.user_id == user.id,
        })

    franchise_name = _get_franchise(user)

    # Franchise scores
    franchise_user_ids = []
    for q in User.objects.filter(profile__company__name=franchise_name):
        franchise_user_ids.append(q.id)

    franchise_scores = (
        HPSScore.objects.filter(user_id__in=franchise_user_ids, timestamp=Subquery(
            HPSScore.objects.filter(user=OuterRef("user")).order_by("-timestamp").values("timestamp")[:1]
        ))
        .order_by("-hps_final")
    )
    franchise_rank = None
    franchise_list = list(franchise_scores)
    for i, s in enumerate(franchise_list):
        if s.user_id == user.id:
            franchise_rank = i + 1
            break

    percentile = round(((total_players - (user_rank or total_players)) / max(total_players, 1)) * 100, 1) if user_rank else 0

    return Response({
        "global_rank": user_rank,
        "total_players": total_players,
        "percentile": percentile,
        "franchise_rank": franchise_rank,
        "franchise_total": len(franchise_user_ids),
        "franchise_name": franchise_name,
        "top_20": top_20,
    })


# ══════════════════════════════════════════════════════════════════════════════
# 3. GET /employee/daily-challenge
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_daily_challenge(request):
    user = request.user
    today = datetime.now(dt_timezone.utc).strftime("%Y-%m-%d")

    existing = DailyChallenge.objects.filter(user=user, date=today).first()
    if existing:
        data = _daily_challenge_to_dict(existing)
        data["surprise_reward"] = "Complete to reveal!" if not existing.completed else existing.surprise_reward
        return Response(data)

    templates = _get_dopamine_templates()
    seed_val = hash(today + str(user.id)) % len(templates)
    template = templates[seed_val]
    surprise = random.choice(template["surprise_pool"])

    dc = DailyChallenge.objects.create(
        user=user,
        date=today,
        title=template["title"],
        description=template["description"],
        challenge_type=template["type"],
        xp=template["xp"],
        surprise_reward=surprise,
        completed=False,
    )
    data = _daily_challenge_to_dict(dc)
    data["surprise_reward"] = "Complete to reveal!"
    return Response(data)


def _daily_challenge_to_dict(dc):
    return {
        "id": str(dc.id),
        "user_id": dc.user.id,
        "date": dc.date,
        "title": dc.title,
        "description": dc.description,
        "type": dc.challenge_type,
        "xp": dc.xp,
        "surprise_reward": dc.surprise_reward,
        "completed": dc.completed,
        "completed_at": dc.completed_at.isoformat() if dc.completed_at else None,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 4. POST /employee/daily-challenge/complete
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def complete_daily_challenge(request):
    user = request.user
    today = datetime.now(dt_timezone.utc).strftime("%Y-%m-%d")

    dc = DailyChallenge.objects.filter(user=user, date=today).first()
    if not dc:
        return Response({"detail": "No daily challenge found for today"}, status=404)

    if dc.completed:
        return Response(_daily_challenge_to_dict(dc))

    dc.completed = True
    dc.completed_at = timezone.now()
    dc.save(update_fields=["completed", "completed_at"])

    # Award credits if the surprise contains "bonus credits"
    credit_match = re.search(r"(\d+)\s*bonus\s*credits", dc.surprise_reward or "")
    if credit_match:
        credits = int(credit_match.group(1))
        _add_credits(user, credits, f"Daily challenge reward: {dc.title}")

    # Increment streak on profile (best-effort)
    try:
        profile = user.profile
        if hasattr(profile, "streak_days"):
            profile.streak_days = (profile.streak_days or 0) + 1
            profile.save(update_fields=["streak_days"])
    except Exception:
        pass

    # Create social feed item
    _create_feed_item(user, "daily_challenge", f"completed today's daily challenge: **{dc.title}**!")

    return Response(_daily_challenge_to_dict(dc))


# ══════════════════════════════════════════════════════════════════════════════
# 5. GET /employee/action-items
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_action_items(request):
    user = request.user
    today = datetime.now(dt_timezone.utc).strftime("%Y-%m-%d")
    items = []

    # ── Medications ────────────────────────────────────────────────
    meds_qs = Medication.objects.filter(member=user, status="active")
    if not meds_qs.exists():
        # Seed demo medications if none exist
        for m in DEMO_MEDICATIONS:
            Medication.objects.get_or_create(
                member=user,
                medication_name=m["name"],
                defaults={
                    "dosage": m.get("time", ""),
                    "frequency": m.get("schedule", "daily"),
                    "clinical_notes": m.get("instructions", ""),
                    "status": "active",
                    "medication_type": "supplement",
                }
            )
        meds_qs = Medication.objects.filter(member=user, status="active")

    meds = list(meds_qs)
    med_streak = 0

    for med in meds:
        # Check if there's a log for today (we use a simple convention: look at DailyChallenge for now)
        # In production this would use a MedicationLog model
        schedule_label = "Morning" if "morning" in (med.frequency or "").lower() else "Evening"
        items.append({
            "priority": "high",
            "category": "medication",
            "action": f"{schedule_label}: Take {med.medication_name} ({med.dosage})",
            "link": "/health-overview",
            "icon": "pill",
            "med_id": str(med.id),
            "reward": 1,
        })

    # ── HPS score check ─────────────────────────────────────────────
    score = _get_user_hps(user)
    if not score:
        items.append({"priority": "high", "category": "health",
                      "action": "Compute your first Health Performance Score",
                      "link": "/", "icon": "zap"})
    else:
        pillars = score.pillars or {}
        if pillars:
            # Defensive check for structure (parity sync)
            try:
                weakest_code = min(pillars, key=lambda k: pillars[k].get("percentage", 100) if isinstance(pillars[k], dict) else pillars[k])
                val = pillars[weakest_code]
                pct = val.get("percentage", val) if isinstance(val, dict) else val
                name = val.get("name", weakest_code) if isinstance(val, dict) else weakest_code
                
                if pct < 50:
                    items.append({
                        "priority": "high", "category": "health",
                        "action": f"Focus on {name} — currently at {pct}%",
                        "link": "/biomarkers", "icon": "target",
                    })
            except Exception:
                pass
        last_ts = score.timestamp
        if last_ts and (timezone.now() - last_ts).days > 7:
            items.append({
                "priority": "medium", "category": "health",
                "action": "Re-compute your HPS — last update was over a week ago",
                "link": "/", "icon": "refresh",
            })

    # ── Wearable check ──────────────────────────────────────────────
    if not WearableConnection.objects.filter(user=user, status="active").exists():
        items.append({"priority": "medium", "category": "device",
                      "action": "Connect a wearable device for continuous tracking",
                      "link": "/wearables", "icon": "watch"})

    # ── Nutrition check ─────────────────────────────────────────────
    if not NutritionLog.objects.filter(user=user, date=today).exists():
        items.append({"priority": "medium", "category": "nutrition",
                      "action": "Log your meals today to track macros",
                      "link": "/nutrition", "icon": "utensils"})

    # ── Badge check ─────────────────────────────────────────────────
    badge_codes = set(UserBadge.objects.filter(user=user).values_list("badge_code", flat=True))
    if "first_score" not in badge_codes and score:
        items.append({"priority": "low", "category": "achievement",
                      "action": "Claim your First Blood badge",
                      "link": "/rewards", "icon": "award"})

    # ── Roadmap check ───────────────────────────────────────────────
    if not Roadmap.objects.filter(user=user).exists() and score:
        items.append({"priority": "medium", "category": "planning",
                      "action": "Generate your AI-powered Longevity Roadmap",
                      "link": "/roadmap", "icon": "map"})

    # ── Social feed check ───────────────────────────────────────────
    if not SocialPost.objects.filter(user=user).exists():
        items.append({"priority": "low", "category": "social",
                      "action": "Share your first update with the community",
                      "link": "/feed", "icon": "message"})

    # ── Random wellness tip ─────────────────────────────────────────
    wellness_tips = [
        {"priority": "low", "category": "wellness", "action": "Take a 5-minute stretch break", "link": None, "icon": "heart"},
        {"priority": "low", "category": "wellness", "action": "Stay hydrated — aim for 3L of water today", "link": None, "icon": "droplet"},
        {"priority": "low", "category": "wellness", "action": "Practice 4-7-8 breathing for 2 minutes", "link": None, "icon": "wind"},
    ]
    items.append(random.choice(wellness_tips))

    priority_order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda x: priority_order.get(x["priority"], 2))

    return Response({
        "items": items,
        "count": len(items),
        "date": today,
        "meds_taken": med_streak,
        "meds_total": len(meds),
    })


# ══════════════════════════════════════════════════════════════════════════════
# 6. GET /employee/streak-calendar
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def streak_calendar(request):
    user = request.user
    now = datetime.now(dt_timezone.utc)
    start_dt = now - timedelta(days=30)

    activity_map = {}

    # Daily challenges completed
    for dc in DailyChallenge.objects.filter(user=user, completed=True):
        d = dc.date
        activity_map[d] = activity_map.get(d, 0) + 2

    # Nutrition logs
    for nl in NutritionLog.objects.filter(user=user):
        d = str(nl.date)
        activity_map[d] = activity_map.get(d, 0) + 1

    # HPS scores computed in last 30 days
    for hs in HPSScore.objects.filter(user=user, timestamp__gte=start_dt):
        d = hs.timestamp.strftime("%Y-%m-%d")
        activity_map[d] = activity_map.get(d, 0) + 3

    # Challenge participations started
    for cp in ChallengeParticipant.objects.filter(user=user):
        if cp.joined_at:
            d = cp.joined_at.strftime("%Y-%m-%d")
            activity_map[d] = activity_map.get(d, 0) + 1

    # Social posts
    for fp in SocialPost.objects.filter(user=user, created_at__gte=start_dt):
        d = fp.created_at.strftime("%Y-%m-%d")
        activity_map[d] = activity_map.get(d, 0) + 1

    days = []
    for i in range(30):
        date = now - timedelta(days=29 - i)
        date_str = date.strftime("%Y-%m-%d")
        count = activity_map.get(date_str, 0)
        days.append({
            "date": date_str,
            "count": count,
            "intensity": min(4, count),
            "weekday": date.weekday(),
        })

    streak = 0
    for i in range(29, -1, -1):
        if days[i]["count"] > 0:
            streak += 1
        else:
            break

    total_active = sum(1 for d in days if d["count"] > 0)
    return Response({
        "days": days,
        "streak": streak,
        "total_active_days": total_active,
        "period_days": 30,
        "activity_rate": round((total_active / 30) * 100, 1),
    })


# ══════════════════════════════════════════════════════════════════════════════
# 7. GET /challenges
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_challenges(request):
    user = request.user
    challenges_qs = Challenge.objects.order_by("-created_at")

    if not challenges_qs.exists():
        # Seed sample challenges
        for ch_data in generate_sample_challenges(6):
            from datetime import date
            Challenge.objects.get_or_create(
                name=ch_data["name"],
                defaults={
                    "description": ch_data["description"],
                    "challenge_type": ch_data.get("type", "general"),
                    "target_value": ch_data.get("target_value", 100),
                    "reward_credits": ch_data.get("reward_credits", 50),
                    "status": "active",
                },
            )
        challenges_qs = Challenge.objects.order_by("-created_at")

    result = []
    # 1. Standard Challenges
    for ch in challenges_qs[:50]:
        participant_count = ChallengeParticipant.objects.filter(challenge=ch).count()
        user_participation = ChallengeParticipant.objects.filter(challenge=ch, user=user).first()
        user_joined = user_participation is not None
        user_progress = user_participation.progress if user_participation else 0

        result.append({
            "id": ch.id,
            "name": ch.name,
            "description": ch.description,
            "type": getattr(ch, "challenge_type", "general"),
            "status": ch.status,
            "target_value": ch.target_value if hasattr(ch, "target_value") else 100,
            "reward_credits": ch.reward_credits if hasattr(ch, "reward_credits") else 0,
            "end_date": ch.end_date.isoformat() if ch.end_date else None,
            "created_at": ch.created_at.isoformat() if ch.created_at else None,
            "participant_count": participant_count,
            "user_joined": user_joined,
            "user_progress": user_progress,
        })

    # 2. Wellness Programmes (of type 'challenge')
    progs = WellnessProgramme.objects.filter(type="challenge", status="active")
    for pr in progs:
        participant_count = ChallengeParticipant.objects.filter(wellness_programme=pr).count()
        user_participation = ChallengeParticipant.objects.filter(wellness_programme=pr, user=user).first()
        user_joined = user_participation is not None
        user_progress = user_participation.progress if user_participation else 0

        result.append({
            "id": str(pr.id), # UUID to string
            "name": pr.name,
            "description": f"Wellness programme focusing on {pr.target_dimension}",
            "type": "wellness",
            "status": pr.status,
            "target_value": 100,
            "reward_credits": pr.reward_healthcoins,
            "end_date": None,
            "created_at": pr.created_at.isoformat() if pr.created_at else None,
            "participant_count": participant_count,
            "user_joined": user_joined,
            "user_progress": user_progress,
        })

    return Response({"challenges": result})


# ══════════════════════════════════════════════════════════════════════════════
# 8. POST /challenges/<challenge_id>/join
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join_challenge(request, challenge_id):
    # Check if ID is UUID (Programme) or Int (Challenge)
    is_uuid = False
    try:
        uuid.UUID(str(challenge_id))
        is_uuid = True
    except ValueError:
        pass

    if is_uuid:
        try:
            ch = WellnessProgramme.objects.get(pk=challenge_id)
            ChallengeParticipant.objects.get_or_create(
                wellness_programme=ch,
                user=request.user,
                defaults={"progress": 0},
            )
            name = ch.name
        except WellnessProgramme.DoesNotExist:
            return Response({"detail": "Programme not found"}, status=404)
    else:
        try:
            ch = Challenge.objects.get(pk=challenge_id)
            ChallengeParticipant.objects.get_or_create(
                challenge=ch,
                user=request.user,
                defaults={"progress": 0},
            )
            name = ch.name
        except Challenge.DoesNotExist:
            return Response({"detail": "Challenge not found"}, status=404)

    _create_feed_item(request.user, "challenge_join", f"joined the **{name}** challenge.")

    return Response({"message": "Joined challenge", "challenge_id": challenge_id})


# ══════════════════════════════════════════════════════════════════════════════
# 9. POST /challenges/<challenge_id>/progress
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_challenge_progress(request, challenge_id):
    increment = request.data.get("increment", 1)
    
    # Check ID type
    is_uuid = False
    try:
        uuid.UUID(str(challenge_id))
        is_uuid = True
    except ValueError:
        pass

    if is_uuid:
        try:
            ch = WellnessProgramme.objects.get(pk=challenge_id)
            participation, _ = ChallengeParticipant.objects.get_or_create(
                wellness_programme=ch, user=request.user, defaults={"progress": 0}
            )
            target = 100
            name = ch.name
            reward = ch.reward_healthcoins
        except WellnessProgramme.DoesNotExist:
            return Response({"detail": "Programme not found"}, status=404)
    else:
        try:
            ch = Challenge.objects.get(pk=challenge_id)
            participation, _ = ChallengeParticipant.objects.get_or_create(
                challenge=ch, user=request.user, defaults={"progress": 0}
            )
            target = ch.target_value if hasattr(ch, "target_value") else 100
            name = ch.name
            reward = ch.reward_credits if hasattr(ch, "reward_credits") else 0
        except Challenge.DoesNotExist:
            return Response({"detail": "Challenge not found"}, status=404)

    participation.progress = (participation.progress or 0) + increment
    participation.save(update_fields=["progress"])

    completed = participation.progress >= (target or 100)

    if completed:
        _create_feed_item(
            request.user, "challenge_complete",
            f"completed the **{name}** and earned {reward} credits!"
        )
        if reward:
            _add_credits(request.user, reward, f"Challenge reward: {name}")

    return Response({
        "progress": participation.progress,
        "target": target,
        "completed": completed,
    })


# ══════════════════════════════════════════════════════════════════════════════
# 10. GET /rewards/badges
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_badge_catalog(request):
    """Returns full badge catalog from DB (BadgeCatalog table)."""
    return Response({"badges": _get_badge_catalog()})


# ══════════════════════════════════════════════════════════════════════════════
# 11. GET /rewards/my-badges
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_my_badges(request):
    user = request.user
    user_badges_qs = UserBadge.objects.filter(user=user).order_by("earned_at")

    bm_count = BiomarkerResult.objects.filter(user=user).count()
    score_doc = _get_user_hps(user)
    hps = score_doc.hps_final if score_doc else None
    ch_done = ChallengeParticipant.objects.filter(user=user, progress__gt=0).count()

    eligible = compute_badge_eligibility({}, hps, bm_count, ch_done)
    existing_codes = set(user_badges_qs.values_list("badge_code", flat=True))

    for code in eligible:
        if code not in existing_codes:
            _award_badge(user, code)
            existing_codes.add(code)

    badges_list = [
        {
            "user_id": user.id,
            "badge_code": b.badge_code,
            "earned_at": b.earned_at.isoformat(),
        }
        for b in UserBadge.objects.filter(user=user)
    ]

    # Tier point calculation — read from DB catalog
    catalog = _get_badge_catalog()
    TIER_POINTS = {"bronze": 10, "silver": 25, "gold": 50}
    total_points = 0
    for ub in badges_list:
        catalog_entry = next((b for b in catalog if b["code"] == ub["badge_code"]), None)
        if catalog_entry:
            total_points += TIER_POINTS.get(catalog_entry.get("tier", "bronze"), 10)

    try:
        streak = user.profile.streak_days if hasattr(user.profile, "streak_days") else 0
    except Exception:
        streak = 0

    return Response({
        "badges": badges_list,
        "total_earned": len(badges_list),
        "total_points": total_points,
        "streak_days": streak,
        "catalog_total": len(catalog),  # Bug 1 fix: was len(BADGE_CATALOG) which is not in scope
    })


# ══════════════════════════════════════════════════════════════════════════════
# 12. GET /feed
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_feed(request):
    user = request.user
    posts_qs = SocialPost.objects.select_related("user__profile__company").prefetch_related("liked_by", "comments__user").order_by("-created_at")[:50]

    if not posts_qs.exists():
        # Seed sample feed items
        for item in generate_sample_feed_items(user.id, _get_profile_name(user)):
            SocialPost.objects.create(
                user=user,
                post_type=item.get("type", "post"),
                content=item.get("content", ""),
                likes=item.get("likes", 0),
            )
        posts_qs = SocialPost.objects.select_related("user__profile__company").prefetch_related("liked_by", "comments__user").order_by("-created_at")[:50]

    feed = [_post_to_dict(p, user) for p in posts_qs]
    return Response({"feed": feed, "count": len(feed)})


# ══════════════════════════════════════════════════════════════════════════════
# 13. GET /feed/highlights
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_feed_highlights(request):
    now = datetime.now(dt_timezone.utc)
    week_ago = now - timedelta(days=7)

    highlights = []
    seen_users = set()

    # Top HPS scores this week
    top_scores = (
        HPSScore.objects.filter(timestamp__gte=week_ago)
        .select_related("user")
        .order_by("-hps_final")[:8]
    )
    for s in top_scores:
        if s.user_id in seen_users:
            continue
        seen_users.add(s.user_id)
        tier_data = s.tier or {}
        highlights.append({
            "user_id": s.user_id,
            "name": _get_profile_name(s.user),
            "initial": (_get_profile_name(s.user) or "A")[0].upper(),
            "franchise": _get_franchise(s.user),
            "highlight_type": "hps_milestone",
            "value": round(s.hps_final or 0),
            "tier": tier_data.get("tier", "VITALITY") if isinstance(tier_data, dict) else "VITALITY",
            "subtitle": f"HPS {round(s.hps_final or 0)}",
        })

    # Recent badge earners
    recent_badges = (
        UserBadge.objects.filter(earned_at__gte=week_ago)
        .select_related("user")
        .order_by("-earned_at")[:10]
    )
    for b in recent_badges:
        if b.user_id in seen_users:
            continue
        seen_users.add(b.user_id)
        badge_info = next((bg for bg in _get_badge_catalog() if bg["code"] == b.badge_code), None)
        highlights.append({
            "user_id": b.user_id,
            "name": _get_profile_name(b.user),
            "initial": (_get_profile_name(b.user) or "A")[0].upper(),
            "franchise": _get_franchise(b.user),
            "highlight_type": "badge_earned",
            "value": b.badge_code,
            "badge_name": badge_info["name"] if badge_info else b.badge_code,
            "subtitle": f"Earned {badge_info['name'] if badge_info else 'badge'}",
        })


    return Response({"highlights": highlights[:10]})


# ══════════════════════════════════════════════════════════════════════════════
# 14. POST /feed/post
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_feed_post(request):
    post_type = request.data.get("post_type", "post")
    content = request.data.get("content", "").strip()
    photo_id = request.data.get("photo_id")

    if not content:
        return Response({"detail": "Content is required"}, status=400)

    item = _create_feed_item(request.user, post_type, content, photo_id)
    return Response(item, status=201)


# ══════════════════════════════════════════════════════════════════════════════
# 15. POST /feed/<item_id>/like
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def like_feed_item(request, item_id):
    try:
        post = SocialPost.objects.get(id=item_id)
    except (SocialPost.DoesNotExist, Exception):
        return Response({"detail": "Feed item not found"}, status=404)

    user = request.user
    if post.liked_by.filter(id=user.id).exists():
        # Unlike
        post.liked_by.remove(user)
        post.likes = max(0, post.likes - 1)
        post.save(update_fields=["likes"])
        return Response({"liked": False, "likes": post.likes})
    else:
        # Like
        post.liked_by.add(user)
        post.likes += 1
        post.save(update_fields=["likes"])
        return Response({"liked": True, "likes": post.likes})


# ══════════════════════════════════════════════════════════════════════════════
# 16. POST /feed/<item_id>/comment
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def comment_on_feed(request, item_id):
    text = (request.data.get("text") or "").strip()
    if not text:
        return Response({"detail": "Comment text required"}, status=400)

    try:
        post = SocialPost.objects.get(id=item_id)
    except (SocialPost.DoesNotExist, Exception):
        return Response({"detail": "Feed item not found"}, status=404)

    comment = SocialComment.objects.create(post=post, user=request.user, text=text)
    return Response({
        "id": str(comment.id),
        "user_id": request.user.id,
        "user_name": _get_profile_name(request.user),
        "text": comment.text,
        "timestamp": comment.created_at.isoformat(),
    }, status=201)


# ══════════════════════════════════════════════════════════════════════════════
# 17. POST /feed/upload-photo
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def upload_feed_photo(request):
    user = request.user

    # Check privacy settings
    try:
        privacy = user.privacy_settings
        if not privacy.allow_photo_posts:
            return Response({"detail": "Photo posts disabled in your privacy settings"}, status=403)
    except Exception:
        pass

    file = request.FILES.get("file")
    if not file:
        return Response({"detail": "No file uploaded"}, status=400)
    if not file.content_type.startswith("image/"):
        return Response({"detail": "Only image files allowed"}, status=400)

    contents = file.read()
    if len(contents) > MAX_PHOTO_SIZE:
        return Response({"detail": f"File too large. Max {MAX_PHOTO_SIZE // (1024*1024)}MB"}, status=400)

    ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else "jpg"
    if ext not in ("jpg", "jpeg", "png", "webp", "gif"):
        return Response({"detail": "Unsupported image format"}, status=400)

    photo_id = str(uuid.uuid4())
    filename = f"{photo_id}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    return Response({"photo_id": photo_id, "filename": filename, "size_bytes": len(contents)})


# ══════════════════════════════════════════════════════════════════════════════
# 18. GET /feed/photo/<photo_id>
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([AllowAny])
def serve_feed_photo(request, photo_id):
    # Sanitise: only hex+dash chars allowed in UUID
    safe = re.sub(r"[^a-zA-Z0-9\-]", "", photo_id)
    for ext in ("jpg", "jpeg", "png", "webp", "gif"):
        filepath = os.path.join(UPLOAD_DIR, f"{safe}.{ext}")
        if os.path.exists(filepath):
            content_types = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                             "webp": "image/webp", "gif": "image/gif"}
            response = FileResponse(open(filepath, "rb"), content_type=content_types.get(ext, "image/jpeg"))
            response["Cache-Control"] = "no-store, no-cache"
            response["Content-Disposition"] = "inline"
            return response
    raise Http404("Photo not found")


# ══════════════════════════════════════════════════════════════════════════════
# 19. POST /profile/upload-photo
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def upload_profile_photo(request):
    user = request.user
    file = request.FILES.get("file")
    if not file:
        return Response({"detail": "No file uploaded"}, status=400)
    if not file.content_type.startswith("image/"):
        return Response({"detail": "Only image files allowed"}, status=400)

    contents = file.read()
    if len(contents) > 5 * 1024 * 1024:
        return Response({"detail": "Max 5MB"}, status=400)

    ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else "jpg"
    photo_id = str(uuid.uuid4())
    filename = f"{user.id}_{photo_id}.{ext}"
    filepath = os.path.join(PROFILE_PHOTO_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    # Store on profile if there's a profile_photo field
    try:
        profile = user.profile
        if hasattr(profile, "profile_photo"):
            profile.profile_photo = photo_id
        if hasattr(profile, "profile_photo_filename"):
            profile.profile_photo_filename = filename
        profile.save()
    except Exception:
        pass

    return Response({"photo_id": photo_id, "filename": filename})


# ══════════════════════════════════════════════════════════════════════════════
# 20. GET /profile/photo/<user_id>
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([AllowAny])
def serve_profile_photo(request, user_id):
    # Search for any file starting with user_id in PROFILE_PHOTO_DIR
    if not os.path.isdir(PROFILE_PHOTO_DIR):
        raise Http404("No profile photos directory")
    for fname in os.listdir(PROFILE_PHOTO_DIR):
        if fname.startswith(str(user_id) + "_"):
            filepath = os.path.join(PROFILE_PHOTO_DIR, fname)
            response = FileResponse(open(filepath, "rb"), content_type="image/jpeg")
            response["Cache-Control"] = "public, max-age=3600"
            return response
    raise Http404("No profile photo")


# ══════════════════════════════════════════════════════════════════════════════
# 21. GET /employee/address
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_address(request):
    user = request.user
    addr = UserAddress.objects.filter(user=user, is_default=True).first()
    if not addr:
        addr = UserAddress.objects.filter(user=user).first()

    if addr:
        address_dict = {
            "address_line": addr.address_line,
            "landmark": addr.landmark,
            "city": addr.city,
            "state": addr.state,
            "pin_code": addr.pin_code,
            "latitude": addr.latitude,
            "longitude": addr.longitude,
            "address_type": addr.address_type,
        }
        location_confirmed = addr.location_confirmed
    else:
        address_dict = {}
        location_confirmed = False

    return Response({"address": address_dict, "location_confirmed": location_confirmed})


# ══════════════════════════════════════════════════════════════════════════════
# 22. PUT /employee/address
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_address(request):
    user = request.user
    data = request.data

    address_type = data.get("address_type", "home")

    # Get or create a default address
    addr, _ = UserAddress.objects.get_or_create(
        user=user,
        address_type=address_type,
        defaults={"is_default": True},
    )
    addr.address_line = data.get("address_line", "")
    addr.landmark = data.get("landmark", "")
    addr.city = data.get("city", "")
    addr.state = data.get("state", "")
    addr.pin_code = data.get("pin_code", "")
    addr.latitude = data.get("latitude")
    addr.longitude = data.get("longitude")
    addr.location_confirmed = True
    addr.is_default = True
    addr.save()

    address_dict = {
        "address_line": addr.address_line,
        "landmark": addr.landmark,
        "city": addr.city,
        "state": addr.state,
        "pin_code": addr.pin_code,
        "latitude": addr.latitude,
        "longitude": addr.longitude,
        "address_type": addr.address_type,
        "contact_number": data.get("contact_number", ""),
    }
    return Response({"address": address_dict, "location_confirmed": True})


# ══════════════════════════════════════════════════════════════════════════════
# 23. GET /leaderboard
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def leaderboard(request):
    from django.db.models import Subquery, OuterRef
    latest_ts = HPSScore.objects.filter(user=OuterRef("user")).order_by("-timestamp").values("timestamp")[:1]
    scores = (
        HPSScore.objects.filter(timestamp=Subquery(latest_ts))
        .select_related("user__profile__company")
        .order_by("-hps_final")[:50]
    )

    leaderboard_list = []
    for i, s in enumerate(scores):
        leaderboard_list.append({
            "rank": i + 1,
            "user_id": s.user_id,
            "name": _get_profile_name(s.user),
            "franchise": _get_franchise(s.user),
            "hps_final": s.hps_final,
            "tier": s.tier,
            "n_metrics": s.n_metrics_tested or 0,
            "timestamp": s.timestamp.isoformat() if s.timestamp else None,
        })

    return Response({"leaderboard": leaderboard_list, "count": len(leaderboard_list)})


# ══════════════════════════════════════════════════════════════════════════════
# 24. GET /leaderboard/franchises
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def franchise_leaderboard(request):
    from django.db.models import Subquery, OuterRef
    latest_ts = HPSScore.objects.filter(user=OuterRef("user")).order_by("-timestamp").values("timestamp")[:1]
    scores = (
        HPSScore.objects.filter(timestamp=Subquery(latest_ts))
        .select_related("user__profile__company")
    )

    franchise_scores = {}
    for s in scores:
        franchise = _get_franchise(s.user)
        if franchise not in franchise_scores:
            franchise_scores[franchise] = {"total": 0, "count": 0, "members": []}
        franchise_scores[franchise]["total"] += (s.hps_final or 0)
        franchise_scores[franchise]["count"] += 1
        franchise_scores[franchise]["members"].append(_get_profile_name(s.user))

    result = []
    for fname, fdata in franchise_scores.items():
        avg = fdata["total"] / fdata["count"] if fdata["count"] > 0 else 0
        result.append({
            "franchise": fname,
            "avg_hps": round(avg, 1),
            "members": fdata["count"],
            "top_members": fdata["members"][:5],
        })
    result.sort(key=lambda x: x["avg_hps"], reverse=True)
    for i, r in enumerate(result):
        r["rank"] = i + 1

    return Response({"franchises": result})


# ══════════════════════════════════════════════════════════════════════════════
# 25. POST /health-snapshots/upload
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def upload_health_snapshot(request):
    """
    POST /health-snapshots/upload
    Query params: category (str), notes (str)
    Matches original flask: POST /health-snapshots/upload
    """
    user = request.user
    category = request.query_params.get("category", "other")
    notes = request.query_params.get("notes", "")

    if category not in SNAPSHOT_CATEGORIES:
        category = "other"

    file = request.FILES.get("file")
    if not file:
        return Response({"detail": "No file uploaded"}, status=400)
    if not file.content_type.startswith("image/"):
        return Response({"detail": "Only image files allowed"}, status=400)

    contents = file.read()
    if len(contents) > 10 * 1024 * 1024:
        return Response({"detail": "Max 10MB"}, status=400)

    ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else "jpg"
    snap_id = str(uuid.uuid4())
    filename = f"{snap_id}.{ext}"
    filepath = os.path.join(SNAPSHOT_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    snap = HealthSnapshot.objects.create(
        user=user,
        category=category,
        notes=notes,
        filename=filename,
        content_type=file.content_type,
        size_bytes=len(contents),
    )

    return Response({
        "id": str(snap.id),
        "user_id": user.id,
        "category": snap.category,
        "notes": snap.notes,
        "filename": snap.filename,
        "content_type": snap.content_type,
        "size_bytes": snap.size_bytes,
        "created_at": snap.created_at.isoformat(),
    }, status=201)


# ══════════════════════════════════════════════════════════════════════════════
# 26. GET /health-snapshots
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_health_snapshots(request):
    """
    GET /health-snapshots?category=<optional>
    Matches original flask: GET /health-snapshots
    Response: {"snapshots": [...], "count": N}
    """
    user = request.user
    category = request.query_params.get("category")

    qs = HealthSnapshot.objects.filter(user=user)
    if category and category != "all":
        qs = qs.filter(category=category)

    snapshots = [
        {
            "id": str(s.id),
            "user_id": user.id,
            "category": s.category,
            "notes": s.notes,
            "filename": s.filename,
            "content_type": s.content_type,
            "size_bytes": s.size_bytes,
            "created_at": s.created_at.isoformat(),
        }
        for s in qs.order_by("-created_at")[:100]
    ]
    return Response({"snapshots": snapshots, "count": len(snapshots)})


# ══════════════════════════════════════════════════════════════════════════════
# 27. GET /health-snapshots/photo/<snap_id>
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([AllowAny])
def serve_snapshot_photo(request, snap_id):
    """
    GET /health-snapshots/photo/<snap_id>
    Serves the actual image file inline (no download).
    Matches original flask: GET /health-snapshots/photo/{snap_id}
    """
    try:
        snap = HealthSnapshot.objects.get(id=snap_id)
    except (HealthSnapshot.DoesNotExist, Exception):
        raise Http404("Snapshot not found")

    filepath = os.path.join(SNAPSHOT_DIR, snap.filename)
    if not os.path.exists(filepath):
        raise Http404("File missing")

    response = FileResponse(
        open(filepath, "rb"),
        content_type=snap.content_type or "image/jpeg",
    )
    response["Cache-Control"] = "no-store"
    response["Content-Disposition"] = "inline"
    response["X-Download-Options"] = "noopen"
    return response


# ══════════════════════════════════════════════════════════════════════════════
# 28. DELETE /health-snapshots/<snap_id>
# ══════════════════════════════════════════════════════════════════════════════
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_health_snapshot(request, snap_id):
    """
    DELETE /health-snapshots/<snap_id>
    Only the owning user can delete their snapshot.
    Response: {"deleted": True}
    Matches original flask: DELETE /health-snapshots/{snap_id}
    """
    try:
        snap = HealthSnapshot.objects.get(id=snap_id, user=request.user)
    except HealthSnapshot.DoesNotExist:
        return Response({"detail": "Snapshot not found"}, status=404)

    filepath = os.path.join(SNAPSHOT_DIR, snap.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    snap.delete()
    return Response({"deleted": True})

