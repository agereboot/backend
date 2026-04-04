from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Count, Avg, Q
import uuid
import random
import logging
import statistics
from datetime import datetime, timedelta

from .models import (
    MentalAssessment, CareTeamMember, CareTeamReview, 
    CreditTransaction, Season, PrivacySetting, UserProfile,
    Appointment, HPSScore
)
from .serializers_misc import (
    MentalAssessmentSerializer, CareTeamMemberSerializer, 
    CareTeamReviewSerializer, CreditTransactionSerializer, 
    SeasonSerializer, PrivacySettingSerializer, ProfileUpdateSerializer
)

logger = logging.getLogger(__name__)

# --- Constants from FastAPI ---
MENTAL_HEALTH_QUESTIONS = [
    {"q": "How often have you felt little interest or pleasure in doing things?", "category": "depression", "weight": 1.5},
    {"q": "How often have you felt down, depressed, or hopeless?", "category": "depression", "weight": 1.5},
    {"q": "How often have you had trouble with appetite?", "category": "depression", "weight": 1.0},
    {"q": "How often have you felt bad about yourself?", "category": "depression", "weight": 1.2},
    {"q": "How often have you had trouble concentrating?", "category": "depression", "weight": 1.0},
    {"q": "How often have you felt nervous, anxious, or on edge?", "category": "anxiety", "weight": 1.5},
    {"q": "How often have you not been able to stop worrying?", "category": "anxiety", "weight": 1.5},
    {"q": "How often have you had trouble relaxing?", "category": "anxiety", "weight": 1.2},
    {"q": "How often have you been easily annoyed or irritable?", "category": "anxiety", "weight": 1.0},
    {"q": "How often have you felt afraid?", "category": "anxiety", "weight": 1.3},
    {"q": "How would you rate your overall sleep quality?", "category": "sleep", "weight": 1.5},
    {"q": "How often do you have trouble falling asleep?", "category": "sleep", "weight": 1.3},
    {"q": "How often do you wake up in the middle of the night?", "category": "sleep", "weight": 1.2},
    {"q": "How often do you feel sleepy during the day?", "category": "sleep", "weight": 1.0},
    {"q": "How often do you forget appointments?", "category": "cognitive", "weight": 1.3},
    {"q": "How difficult is it to focus for more than 15 minutes?", "category": "cognitive", "weight": 1.2},
    {"q": "How often do you feel mentally foggy?", "category": "cognitive", "weight": 1.5},
    {"q": "How often do you find it hard to wind down?", "category": "stress", "weight": 1.3},
    {"q": "How often do you over-react to situations?", "category": "stress", "weight": 1.0},
    {"q": "How often do you feel that life is meaningless?", "category": "stress", "weight": 1.5},
]

MH_CATEGORIES = {
    "depression": {"name": "Depression", "levels": ["Minimal", "Mild", "Moderate", "Moderately Severe", "Severe"]},
    "anxiety": {"name": "Anxiety", "levels": ["Minimal", "Mild", "Moderate", "Severe", "Very Severe"]},
    "sleep": {"name": "Sleep Quality", "levels": ["Good", "Fair", "Poor", "Very Poor", "Severely Disrupted"]},
    "cognitive": {"name": "Cognitive Clarity", "levels": ["Sharp", "Good", "Moderate Fog", "Significant Fog", "Severe Fog"]},
    "stress": {"name": "Stress Level", "levels": ["Low", "Moderate", "Elevated", "High", "Very High"]},
}

MH_ACTIONS = {
    "depression": [
        {"action": "30-min outdoor walk min morning sunlight", "hps_impact": 8, "frequency": "daily", "measurable": True},
        {"action": "Gratitude journaling — write 3 things", "hps_impact": 5, "frequency": "daily", "measurable": True},
        {"action": "Social connection — call or meet a friend", "hps_impact": 6, "frequency": "weekly", "measurable": True},
    ],
    "anxiety": [
        {"action": "4-7-8 breathing exercise for 5 minutes", "hps_impact": 6, "frequency": "daily", "measurable": True},
        {"action": "Progressive muscle relaxation session", "hps_impact": 5, "frequency": "daily", "measurable": True},
        {"action": "Mindfulness meditation — 10 minutes", "hps_impact": 8, "frequency": "daily", "measurable": True},
    ],
    "sleep": [
        {"action": "Maintain consistent sleep/wake times", "hps_impact": 10, "frequency": "daily", "measurable": True},
        {"action": "Magnesium supplement before bed", "hps_impact": 5, "frequency": "daily", "measurable": True},
    ],
    "cognitive": [
        {"action": "Brain training exercise — 15 minutes", "hps_impact": 8, "frequency": "daily", "measurable": True},
        {"action": "Learn something new for 20 minutes", "hps_impact": 6, "frequency": "daily", "measurable": True},
        {"action": "Digital detox — 2 hours phone-free", "hps_impact": 5, "frequency": "daily", "measurable": True},
    ],
    "stress": [
        {"action": "Deep breathing — box breathing 4-4-4-4", "hps_impact": 6, "frequency": "daily", "measurable": True},
        {"action": "Nature walk — 20 minutes in green space", "hps_impact": 8, "frequency": "daily", "measurable": True},
        {"action": "Journaling — express emotions freely", "hps_impact": 5, "frequency": "daily", "measurable": True},
    ],
}

# --- Mental Health Endpoints ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mental_health_questions(request):
    """Fetch randomized mental health assessment questions."""
    selected = []
    for cat in ["depression", "anxiety", "sleep", "cognitive", "stress"]:
        cat_qs = [q for q in MENTAL_HEALTH_QUESTIONS if q["category"] == cat]
        sorted_qs = sorted(cat_qs, key=lambda x: x["weight"], reverse=True)
        picks = sorted_qs[:2]
        remaining = [q for q in sorted_qs[2:] if q not in picks]
        if remaining:
            picks.append(random.choice(remaining))
        for i, p in enumerate(picks):
            original_idx = MENTAL_HEALTH_QUESTIONS.index(p)
            selected.append({**p, "id": f"{cat}_{original_idx}"})
    random.shuffle(selected)
    return Response({
        "questions": selected, 
        "total": len(selected), 
        "scale": ["Never (0)", "Sometimes (1)", "Often (2)", "Always (3)"]
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_mental_health_assessment(request):
    """Submit assessment answers and calculate category scores."""
    answers = request.data.get("answers", [])
    cat_scores = {c: 0 for c in MH_CATEGORIES}
    cat_max = {c: 0 for c in MH_CATEGORIES}
    
    for ans in answers:
        qid = ans.get("id", "")
        score = ans.get("score", 0)
        cat = qid.split("_")[0] if "_" in qid else ""
        if cat in cat_scores:
            q_idx = int(qid.split("_")[-1]) if "_" in qid else 0
            weight = MENTAL_HEALTH_QUESTIONS[q_idx]["weight"] if q_idx < len(MENTAL_HEALTH_QUESTIONS) else 1.0
            cat_scores[cat] += score * weight
            cat_max[cat] += 3 * weight

    results = {}
    for cat, info in MH_CATEGORIES.items():
        raw = cat_scores[cat]
        mx = cat_max[cat] if cat_max[cat] > 0 else 1
        pct = (raw / mx) * 100
        level_idx = min(4, int(pct / 20))
        level = info["levels"][level_idx]
        actions = MH_ACTIONS.get(cat, [])
        results[cat] = {
            "name": info["name"], 
            "score": round(raw, 1), 
            "max_score": round(mx, 1), 
            "percentage": round(pct, 1), 
            "level": level, 
            "level_index": level_idx, 
            "actions": actions
        }

    submission = MentalAssessment.objects.create(
        user=request.user,
        results=results,
        answers=answers
    )
    
    serializer = MentalAssessmentSerializer(submission)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mental_health_history(request):
    """Get previous mental health assessment history."""
    history = MentalAssessment.objects.filter(user=request.user).order_by("-completed_at")[:20]
    serializer = MentalAssessmentSerializer(history, many=True)
    return Response({"history": serializer.data})

def _generate_fallback_analysis(history):
    if not history:
        return None
    latest = history[0].results
    domain_insights = []
    for cat, r in latest.items():
        trend = "stable"
        if len(history) >= 2:
            prev = history[1].results.get(cat, {})
            if prev:
                diff = r.get("percentage", 0) - prev.get("percentage", 0)
                trend = "improving" if diff < -5 else ("declining" if diff > 5 else "stable")
        if r.get("level_index", 0) >= 2:
            domain_insights.append({
                "domain": cat, "trend": trend, 
                "insight": f"{r['name']} is at {r['level']} level ({r['percentage']:.0f}%).", 
                "priority_action": r.get("actions", [{}])[0].get("action", "Focus on self-care")
            })

    elevated = [cat for cat, r in latest.items() if r.get("level_index", 0) >= 2]
    overall = "stable"
    if len(history) >= 2:
        curr_avg = sum(r.get("percentage", 0) for r in latest.values()) / max(len(latest), 1)
        prev_avg = sum(r.get("percentage", 0) for r in history[1].results.values()) / max(len(history[1].results), 1)
        overall = "improving" if curr_avg < prev_avg - 3 else ("declining" if curr_avg > prev_avg + 3 else "stable")

    return {
        "overall_trend": overall, 
        "trend_summary": f"Based on {len(history)} assessment(s). {len(elevated)} domain(s) need attention." if elevated else f"Based on {len(history)} assessment(s). All domains within healthy range.", 
        "domain_insights": domain_insights, "connections": [], 
        "weekly_focus": domain_insights[0]["priority_action"] if domain_insights else "Maintain your current wellness routine", 
        "positive_note": "Keep tracking regularly for better insights."
    }

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mental_health_ai_analysis(request):
    """AI analysis of mental health trends (simulated fallback for now)."""
    history = MentalAssessment.objects.filter(user=request.user).order_by("-completed_at")[:20]
    if not history.exists():
        return Response({"analysis": None, "message": "Take at least one assessment to get AI insights."})
    
    # Ideally integrate LLM here like in FastAPI, but providing dynamic fallback for now
    analysis = _generate_fallback_analysis(list(history))
    return Response({"analysis": analysis, "ai_generated": False, "assessments_analyzed": history.count()})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mental_health_roadmap(request):
    """Generate a mental health wellness roadmap based on latest assessment."""
    history = MentalAssessment.objects.filter(user=request.user).order_by("-completed_at")[:20]
    if not history.exists():
        return Response({"roadmap": None})

    latest = history[0].results
    domain_summaries = []
    critical_actions = []
    for cat, r in latest.items():
        summary = {
            "domain": cat, "name": r.get("name", cat), 
            "level": r.get("level", "Unknown"), "level_index": r.get("level_index", 0), 
            "percentage": r.get("percentage", 0), "actions": r.get("actions", [])
        }
        domain_summaries.append(summary)
        if r.get("level_index", 0) >= 2:
            for act in r.get("actions", [])[:2]:
                critical_actions.append({
                    **act, "domain": cat, "domain_name": r.get("name", cat), 
                    "severity": r.get("level", "Moderate")
                })
    
    return Response({
        "roadmap": {
            "domain_summaries": domain_summaries, 
            "critical_actions": critical_actions[:6], 
            "assessment_count": history.count(), 
            "last_assessed": history[0].completed_at
        }
    })

def compute_franchise_roi(avg_hps, member_count, avg_healthcare_cost_per_employee=8500):
    """
    Compute estimated ROI for franchise based on HPS levels.
    """
    hps_above_baseline = max(0, avg_hps - 400)
    reduction_pct = min(40, hps_above_baseline * 0.068)  # Cap at 40%

    annual_savings_per_employee = avg_healthcare_cost_per_employee * (reduction_pct / 100)
    total_savings = annual_savings_per_employee * member_count

    productivity_gain_pct = min(15, hps_above_baseline * 0.05)
    sick_days_reduction = min(8, hps_above_baseline * 0.015)
    days_saved = sick_days_reduction * member_count

    return {
        "healthcare_cost_reduction_pct": round(reduction_pct, 1),
        "annual_savings_per_employee": round(annual_savings_per_employee),
        "total_annual_savings": round(total_savings),
        "productivity_gain_pct": round(productivity_gain_pct, 1),
        "sick_days_saved_total": round(days_saved),
        "sick_days_saved_per_employee": round(sick_days_reduction, 1),
        "roi_multiplier": round(total_savings / max(1, member_count * 500), 1),
        "avg_healthcare_cost_assumed": avg_healthcare_cost_per_employee,
        "member_count": member_count,
    }

def _get_burnout_suggestion(domain, level):
    suggestions = {
        "stress": {"Severe": "Implement immediate stress reduction: daily meditation, workload audit", "High": "Practice 10-min daily breathwork", "Moderate": "Incorporate stress buffers: nature walks"},
        "sleep": {"Severe": "Sleep is critically compromised. Establish strict schedule", "High": "Prioritize sleep hygiene", "Moderate": "Fine-tune sleep: aim for 7-9 hours"},
        "depression": {"Severe": "Consider professional counseling", "High": "Engage in regular physical activity", "Moderate": "Stay active"},
        "cognitive": {"Severe": "Cognitive fatigue is high. Reduce decision load", "High": "Reduce multitasking", "Moderate": "Stay mentally engaged"},
        "anxiety": {"Severe": "Anxiety is elevated. Practice grounding techniques", "High": "Regular exercise, limit stimulants", "Moderate": "Mindfulness practice"},
    }
    return suggestions.get(domain, {}).get(level, "Monitor this domain and take preventive action")

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def predict_burnout(request):
    """Predict burnout risk based on multi-domain assessment scores."""
    history = MentalAssessment.objects.filter(user=request.user).order_by("-completed_at")[:20]
    if not history.exists():
        return Response({"prediction": None, "message": "Complete at least one assessment to get burnout prediction"})

    BURNOUT_WEIGHTS = {"stress": 0.35, "sleep": 0.25, "depression": 0.20, "cognitive": 0.12, "anxiety": 0.08}
    latest = history[0].results
    burnout_score = 0
    domain_contributions = {}
    for cat, weight in BURNOUT_WEIGHTS.items():
        r = latest.get(cat, {})
        pct = r.get("percentage", 0) / 100
        contribution = pct * weight * 100
        burnout_score += contribution
        domain_contributions[cat] = {
            "name": r.get("name", cat.title()), 
            "level": r.get("level", "Unknown"), 
            "percentage": r.get("percentage", 0), 
            "weight": weight, 
            "contribution": round(contribution, 1)
        }

    burnout_score = min(round(burnout_score, 1), 100)
    if burnout_score >= 70:
        level, color, rec = "critical", "#DC2626", "Immediate intervention recommended."
    elif burnout_score >= 50:
        level, color, rec = "high", "#EF4444", "High burnout risk. Prioritize stress management."
    elif burnout_score >= 35:
        level, color, rec = "moderate", "#D97706", "Moderate burnout indicators."
    else:
        level, color, rec = "low", "#0F9F8F", "Low burnout risk."

    risk_factors = []
    for cat, info in sorted(domain_contributions.items(), key=lambda x: -x[1]["contribution"])[:3]:
        if info["contribution"] > 5:
            risk_factors.append({
                "domain": info["name"], "level": info["level"], 
                "impact": "high" if info["contribution"] > 15 else "moderate", 
                "suggestion": _get_burnout_suggestion(cat, info["level"])
            })

    return Response({
        "prediction": {
            "burnout_score": burnout_score, 
            "risk_level": level, "risk_color": color, 
            "recommendation": rec,
            "domain_contributions": domain_contributions,
            "risk_factors": risk_factors,
            "last_assessed": history[0].completed_at
        }
    })

# --- Care Team Endpoints ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_care_team(request):
    """Retrieve assigned or default care team members."""
    team = CareTeamMember.objects.filter(status="active")
    if not team.exists():
        # Fallback to hardcoded defaults if DB is empty
        defaults = [
            {"name": "Dr. Priya Sharma", "role": "Primary Physician", "specialization": "Internal Medicine", "email": "dr.sharma@agereboot.care"},
            {"name": "Meera Patel, RD", "role": "Nutritionist", "specialization": "Metabolic Health", "email": "meera.p@agereboot.care"},
        ]
        return Response({"members": defaults})
    
    serializer = CareTeamMemberSerializer(team, many=True)
    return Response({"members": serializer.data})

# @api_view(['GET', 'POST'])
# @permission_classes([IsAuthenticated])
# def manage_care_appointments(request):
#     """Fetch or book care team appointments."""
#     if request.method == 'POST':
#         member_id = request.data.get("member_id")
#         # Handle member_index or member_id for parity
#         member_index = request.data.get("member_index")
#         if member_index is not None:
#             team = CareTeamMember.objects.filter(status="active")
#             if member_index < team.count():
#                 member = team[member_index]
#             else:
#                 return Response({"error": "Invalid member index"}, status=status.HTTP_400_BAD_REQUEST)
#         else:
#             member = get_object_or_404(CareTeamMember, id=member_id)
            
#         profile = request.user.profile
#         if profile.credits < member.credits_per_session:
#             return Response({"error": "Insufficient credits"}, status=status.HTTP_400_BAD_REQUEST)
            
#         profile.credits -= member.credits_per_session
#         profile.save()
        
#         CreditTransaction.objects.create(
#             user=request.user, type="consume", amount=member.credits_per_session,
#             description=f"Booked session with {member.name}"
#         )
        
#         appt = Appointment.objects.create(
#             member=request.user, 
#             member_name=request.user.get_full_name() or request.user.username,
#             assigned_hcp=User.objects.filter(role__name="longevity_physician").first() or request.user, 
#             assigned_hcp_name=member.name,
#             scheduled_at=timezone.now() + timedelta(days=2),
#             appointment_type="Care Team Consultation",
#             mode="telehealth",
#             status="scheduled"
#         )
        
#         return Response({"id": str(appt.id), "member_name": member.name, "status": "confirmed"})

#     appts = Appointment.objects.filter(member=request.user).order_by("-scheduled_at")
#     return Response({"appointments": appts.values()})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def manage_care_appointments(request):
    """Fetch or book care team appointments."""
    
    if request.method == 'POST':
        member_id = request.data.get("member_id")

        # Handle member_index or member_id for parity
        member_index = request.data.get("member_index")
        if member_index is not None:
            team = CareTeamMember.objects.filter(status="active")
            if int(member_index) < team.count():
                member = team[int(member_index)]
            else:
                return Response({"error": "Invalid member index"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            member = get_object_or_404(CareTeamMember, id=member_id)
            
        profile = request.user.profile

        if profile.credits < member.credits_per_session:
            return Response({"error": "Insufficient credits"}, status=status.HTTP_400_BAD_REQUEST)
            
        profile.credits -= member.credits_per_session
        profile.save()
        
        CreditTransaction.objects.create(
            user=request.user,
            type="consume",
            amount=member.credits_per_session,
            description=f"Booked session with {member.name}"
        )
        
        # ✅ FIXED LINE (ONLY CHANGE)
        assigned_hcp = (
            User.objects.filter(profile__role__name="longevity_physician").first()
            or request.user
        )
        
        appt = Appointment.objects.create(
            member=request.user, 
            member_name=request.user.get_full_name() or request.user.username,
            assigned_hcp=assigned_hcp, 
            assigned_hcp_name=member.name,
            scheduled_at=timezone.now() + timedelta(days=2),
            appointment_type="Care Team Consultation",
            mode="telehealth",
            status="scheduled"
        )
        
        return Response({
            "id": str(appt.id),
            "member_name": member.name,
            "status": "confirmed"
        })

    appts = Appointment.objects.filter(member=request.user).order_by("-scheduled_at")

    return Response({"appointments": appts.values()})


# @api_view(['GET', 'POST'])
# @permission_classes([IsAuthenticated])
# def manage_care_reviews(request):
#     """Get member stats or submit a review."""
#     if request.method == 'POST':
#         member_id = request.data.get("member_id")
#         member_index = request.data.get("member_index")
#         if member_index is not None:
#              team = CareTeamMember.objects.filter(status="active")
#              member = team[member_index] if member_index < team.count() else None
#         else:
#              member = get_object_or_404(CareTeamMember, id=member_id)
        
#         if not member:
#             return Response({"error": "Invalid member"}, status=status.HTTP_400_BAD_REQUEST)

#         review = CareTeamReview.objects.create(
#             user=request.user, member=member,
#             rating=request.data.get("rating", 5),
#             nps_score=request.data.get("nps_score"),
#             review_text=request.data.get("review_text", "")
#         )
#         return Response({"id": str(review.id), "member_name": member.name, "rating": review.rating})

#     reviews = CareTeamReview.objects.all()
#     stats = {}
#     for r in reviews:
#         mid = str(r.member.id)
#         if mid not in stats: stats[mid] = {"ratings": [], "nps": []}
#         stats[mid]["ratings"].append(r.rating)
#         if r.nps_score is not None: stats[mid]["nps"].append(r.nps_score)
        
#     results = {}
#     # Link stats to member index for legacy parity
#     team = list(CareTeamMember.objects.filter(status="active"))
#     for i, member in enumerate(team):
#         m_reviews = [r for r in reviews if r.member == member]
#         if m_reviews:
#             avg = round(sum(r.rating for r in m_reviews)/len(m_reviews), 1)
#             results[i] = {"avg_rating": avg, "total_reviews": len(m_reviews), "reviews": []}
            
#     return Response({"member_stats": results})



@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def manage_care_reviews(request):
    """Get member stats or submit a review."""

    if request.method == 'POST':
        member_id = request.data.get("member_id")
        member_index = request.data.get("member_index")

        if member_index is not None:
            team = CareTeamMember.objects.filter(status="active")
            member_index = int(member_index)  # ✅ FIX
            member = team[member_index] if member_index < team.count() else None
        else:
            member = get_object_or_404(CareTeamMember, id=member_id)

        if not member:
            return Response({"error": "Invalid member"}, status=status.HTTP_400_BAD_REQUEST)

        review = CareTeamReview.objects.create(
            user=request.user,
            member=member,
            rating=request.data.get("rating", 5),
            nps_score=request.data.get("nps_score"),
            review_text=request.data.get("review_text", "")
        )

        return Response({
            "id": str(review.id),
            "member_name": member.name,
            "rating": review.rating
        })

    # ✅ GET LOGIC
    reviews = CareTeamReview.objects.select_related("user", "member").all()

    results = {}

    # Maintain index-based mapping
    team = list(CareTeamMember.objects.filter(status="active"))

    for i, member in enumerate(team):
        m_reviews = [r for r in reviews if r.member == member]

        if m_reviews:
            avg = round(sum(r.rating for r in m_reviews) / len(m_reviews), 1)

            results[i] = {
                "avg_rating": avg,
                "total_reviews": len(m_reviews),
                "nps_score": max(
                    [r.nps_score for r in m_reviews if r.nps_score is not None],
                    default=None
                ),
                "reviews": [
                    {
                        "id": str(r.id),
                        "user_id": str(r.user.id),
                        "user_name": r.user.get_full_name() or r.user.username,
                        "member_index": i,
                        "member_name": member.name,
                        "member_role": member.role,
                        "rating": r.rating,
                        "nps_score": r.nps_score,
                        "review_text": r.review_text,
                        "created_at": r.created_at
                    }
                    for r in m_reviews
                ]
            }

    return Response({"member_stats": results})

# --- Settings & Profile ---

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def privacy_settings(request):
    """Get or update user privacy settings."""
    settings, _ = PrivacySetting.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        serializer = PrivacySettingSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = PrivacySettingSerializer(settings)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Update user profile fields."""
    profile = request.user.profile
    serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- Credits ---

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_credits(request):
#     """Get credit balance and history."""
#     profile = request.user.profile
#     txs = CreditTransaction.objects.filter(user=request.user).order_by("-timestamp")
#     return Response({
#         "available": profile.credits,
#         "purchased": txs.filter(type="purchase").aggregate(Count('id'))['id__count'] or 0,
#         "transactions": CreditTransactionSerializer(txs, many=True).data
#     })




@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_credits(request):
    """Mock endpoint for credit purchase."""
    amount = request.data.get("amount", 0)
    profile = request.user.profile
    profile.credits += amount
    profile.save()
    
    CreditTransaction.objects.create(
        user=request.user, type="purchase", amount=amount,
        description=f"Purchased {amount} credits"
    )
    return Response({"message": f"Purchased {amount} credits", "new_balance": profile.credits})

# --- Franchise & Seasons ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_franchises(request):
    """List franchises by member count."""
    stats = UserProfile.objects.values('franchise').annotate(count=Count('user')).order_by('-count')
    return Response({"franchises": [{"name": s['franchise'], "members": s['count']} for s in stats if s['franchise']]})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def franchise_dashboard(request, franchise_name):
    """Dashboard analytics for a specific franchise."""
    members = UserProfile.objects.filter(franchise=franchise_name)
    user_ids = members.values_list('user_id', flat=True)
    scores = HPSScore.objects.filter(user_id__in=user_ids).order_by('-timestamp')
    
    avg_hps = scores.aggregate(Avg('hps_final'))['hps_final__avg'] or 0
    roi = compute_franchise_roi(avg_hps or 0, members.count())
    
    return Response({
        "franchise": franchise_name,
        "total_members": members.count(),
        "avg_hps": round(float(avg_hps), 1),
        "roi": roi
    })

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def manage_seasons(request):
    """List or create competition seasons."""
    if request.method == 'POST':
        request.data['created_by'] = request.user.id
        serializer = SeasonSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    seasons = Season.objects.all().order_by("-start_date")
    return Response({"seasons": SeasonSerializer(seasons, many=True).data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_season(request, season_id):
    """Join a competition season."""
    season = get_object_or_404(Season, id=season_id)
    season.participants.add(request.user)
    return Response({"message": "Joined season", "season": season.name})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def season_standings(request, season_id):
    """Get leaderboard for a specific season."""
    season = get_object_or_404(Season, id=season_id)
    participant_ids = season.participants.values_list('id', flat=True)
    scores = HPSScore.objects.filter(user_id__in=participant_ids).order_by('-hps_final')
    
    standings = []
    for i, s in enumerate(scores[:50]):
        u = s.user
        standings.append({"rank": i+1, "name": u.username, "hps": s.hps_final})
        
    return Response({"season": season.name, "standings": standings})
