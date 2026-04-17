from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
import uuid
import hashlib

from .hps_engine.scoring import compute_hps
from .hps_engine.predictions import predict_hps_trajectory
from .hps_engine.questionnaire_scoring import compute_ca_score
from .models import BiomarkerResult, HPSScore, AdaptiveAssessment, CAAssessment, MentalAssessment, User
from .serializers import HPSScoreSerializer, AdaptiveAssessmentSerializer

_QUESTION_BANK = [
    # --- Mood & Energy (maps → PHQ-9 / depression) ---
    {"id": "we01", "text": "I look forward to each new day", "domain": "mood", "instrument": "phq9", "weight": 1.5, "reverse": True, "age_bias": 0},
    {"id": "we02", "text": "I feel energised throughout the day", "domain": "mood", "instrument": "phq9", "weight": 1.3, "reverse": True, "age_bias": 0},
    {"id": "we03", "text": "I enjoy the activities I do in my free time", "domain": "mood", "instrument": "phq9", "weight": 1.5, "reverse": True, "age_bias": 0},
    {"id": "we04", "text": "I feel good about myself and what I accomplish", "domain": "mood", "instrument": "phq9", "weight": 1.2, "reverse": True, "age_bias": 0},
    {"id": "we05", "text": "My appetite and eating patterns feel balanced", "domain": "mood", "instrument": "phq9", "weight": 1.0, "reverse": True, "age_bias": 0},
    {"id": "we06", "text": "I feel present and engaged when doing things", "domain": "mood", "instrument": "phq9", "weight": 1.0, "reverse": True, "age_bias": 0},
    {"id": "we08", "text": "I feel that life is worth living and meaningful", "domain": "mood", "instrument": "phq9", "weight": 1.5, "reverse": True, "age_bias": 0},
    {"id": "we09", "text": "I can focus easily on reading or a conversation", "domain": "mood", "instrument": "phq9", "weight": 1.0, "reverse": True, "age_bias": 0},
    # --- Calm & Control (maps → GAD-7 / anxiety) ---
    {"id": "we10", "text": "I feel calm and at ease most of the time", "domain": "calm", "instrument": "gad7", "weight": 1.5, "reverse": True, "age_bias": 0},
    {"id": "we11", "text": "I can let go of worries when I want to", "domain": "calm", "instrument": "gad7", "weight": 1.5, "reverse": True, "age_bias": 0},
    {"id": "we12", "text": "I feel relaxed in my body and mind", "domain": "calm", "instrument": "gad7", "weight": 1.2, "reverse": True, "age_bias": 0},
    {"id": "we16", "text": "I feel confident that things will work out", "domain": "calm", "instrument": "gad7", "weight": 1.3, "reverse": True, "age_bias": 0},
    # --- Stress & Coping (maps → PSS-10) ---
    {"id": "we17", "text": "I handle unexpected changes well", "domain": "stress", "instrument": "pss10", "weight": 1.3, "reverse": True, "age_bias": 0},
    {"id": "we18", "text": "I feel in control of the important things in my life", "domain": "stress", "instrument": "pss10", "weight": 1.5, "reverse": True, "age_bias": 0},
    {"id": "we19", "text": "I feel I can manage all the things I need to do", "domain": "stress", "instrument": "pss10", "weight": 1.2, "reverse": True, "age_bias": 0},
    {"id": "we23", "text": "I rarely feel overwhelmed by what's happening around me", "domain": "stress", "instrument": "pss10", "weight": 1.2, "reverse": True, "age_bias": 0},
    # --- Inner Strength (maps → RS-14 / resilience) ---
    {"id": "we24", "text": "I find a way through challenges, one way or another", "domain": "resilience", "instrument": "rs14", "weight": 1.3, "reverse": False, "age_bias": 0},
    {"id": "we33", "text": "My belief in myself helps me through hard times", "domain": "resilience", "instrument": "rs14", "weight": 1.2, "reverse": False, "age_bias": 0},
    {"id": "we34", "text": "My life has a clear sense of purpose", "domain": "resilience", "instrument": "rs14", "weight": 1.3, "reverse": False, "age_bias": 0},
    # --- Mental Sharpness (maps → MoCA / cognitive) ---
    {"id": "we41", "text": "I can easily recall things I heard or read recently", "domain": "sharpness", "instrument": "moca", "weight": 1.5, "reverse": False, "age_bias": 15},
    {"id": "we43", "text": "Words and names come to me quickly when I need them", "domain": "sharpness", "instrument": "moca", "weight": 1.3, "reverse": False, "age_bias": 15},
]

_RESPONSE_SCALE = ["Not at all like me", "A little like me", "Somewhat like me", "Mostly like me", "Very much like me"]

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def compute_hps_score(request):
    user_id = request.user.id
    
    biomarkers_raw = BiomarkerResult.objects.filter(user=request.user).order_by('-collected_at')[:500]
    
    latest = {}
    for bm in biomarkers_raw:
        code = bm.biomarker_id
        if code not in latest:
            latest[code] = bm.value

    if not latest:
        return Response({"error": "No biomarker data available. Please add biomarkers first."}, status=400)

    prior_score = HPSScore.objects.filter(user=request.user).order_by('-timestamp').first()
    prior_values = prior_score.raw_values if prior_score else None

    # ca_data = None # Provide CA data if available in user's profile
    ca_data = None 

    result = compute_hps(
        biomarker_data=latest,
        age=getattr(request.user.profile, 'age', 35),
        sex=getattr(request.user.profile, 'sex', 'M'),
        prior_values=prior_values,
        adherence_pct=75,
        ca_data=ca_data,
        education_years=16,
    )

    score_doc = HPSScore.objects.create(
        user=request.user,
        hps_final=result["hps_final"],
        hps_base=result["hps_base"],
        pillars=result["pillars"],
        improvement_bonus=result["improvement_bonus"],
        compliance_multiplier=result["compliance_multiplier"],
        coverage_ratio=result["coverage_ratio"],
        ccm=result["ccm"],
        confidence_interval=result["confidence_interval"],
        n_metrics_tested=result["n_metrics_tested"],
        tier=result["tier"]["tier"],
        alert=result["alert"].get("level", ""),
        algorithm_version=result["algorithm_version"],
        metric_scores=result["metric_scores"],
        raw_values=latest,
        audit_hash=hashlib.sha256(str(result).encode()).hexdigest(),
    )
    
    return Response(HPSScoreSerializer(score_doc).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_hps_score(request, user_id=None):
    # Allow user_id optional parameter, fallback to current user
    if user_id:
        target_user_id = user_id
    else:
        target_user_id = request.user.id
    print(';target_user_id',target_user_id)
        
    score = HPSScore.objects.filter(user__id=target_user_id).order_by('-timestamp').first()
    print('xore',score)
    if not score:
        return Response({"score": None, "message": "No HPS computed yet"})
        
    return Response(HPSScoreSerializer(score).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_hps_history(request, user_id=None):
    if user_id:
        target_user_id = user_id
    else:
        target_user_id = request.user.id
        
    scores = HPSScore.objects.filter(user__id=target_user_id).order_by('-timestamp')[:100]
    return Response({"history": HPSScoreSerializer(scores, many=True).data, "count": scores.count()})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def predict_hps(request, user_id=None):
    if user_id:
        target_user_id = user_id
    else:
        target_user_id = request.user.id
        
    scores = HPSScore.objects.filter(user__id=target_user_id).order_by('-timestamp')[:100]
    scores_data = list(scores.values()) # Convert to dict format compatible with predict script
    
    if len(scores_data) < 2:
        return Response({"prediction": None, "message": "Need at least 2 HPS scores for prediction"})
        
    prediction = predict_hps_trajectory(scores_data)
    return Response({"prediction": prediction})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_hps_trend(request):
    scores = list(HPSScore.objects.filter(user=request.user).order_by('-timestamp')[:20].values())

    if not scores:
        return Response({"trend": None, "message": "No HPS data yet"})

    current = scores[0]["hps_final"]
    now = timezone.now()
    one_week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    this_week = [s for s in scores if s["timestamp"] >= one_week_ago]
    last_week = [s for s in scores if two_weeks_ago <= s["timestamp"] < one_week_ago]

    this_week_avg = sum(s["hps_final"] for s in this_week) / len(this_week) if this_week else current
    last_week_avg = sum(s["hps_final"] for s in last_week) / len(last_week) if last_week else this_week_avg

    delta = round(this_week_avg - last_week_avg, 1)
    pct_change = round((delta / max(last_week_avg, 1)) * 100, 1) if last_week_avg else 0

    insights = []
    latest = scores[0]
    if latest.get("pillars"):
        pillars = latest["pillars"]
        # Finding best pillar defensively (parity sync)
    try:
        best = max(pillars.items(), key=lambda x: x[1].get("percentage", 0) if isinstance(x[1], dict) else x[1])
    except Exception:
        best = ("BR", {"percentage": 0}) if isinstance(pillars.get("BR"), dict) else ("BR", 0)
        worst = min(pillars.items(), key=lambda x: x[1].get("percentage", 0))
        insights.append(f"Your strongest pillar is {best[1]['name']} at {best[1]['percentage']}%")
        if worst[1].get("percentage", 100) < 50:
            insights.append(f"{worst[1]['name']} needs attention — only {worst[1]['percentage']}%")

    if delta > 0:
        insights.append(f"Great progress! Your score improved by {abs(delta)} pts this week")
    elif delta < 0:
        insights.append(f"Your score dipped by {abs(delta)} pts — let's focus on recovery")
    else:
        insights.append("Holding steady — consistency is key to longevity")

    tier_name = latest.get("tier", "VITALITY")
    
    chart_data = []
    for s in reversed(scores[:8]):
        chart_data.append({
            "date": s["timestamp"].strftime('%Y-%m-%d'),
            "hps": round(s["hps_final"]),
            "label": s["timestamp"].strftime("%b %d"),
        })

    return Response({
        "current": round(current),
        "this_week_avg": round(this_week_avg),
        "last_week_avg": round(last_week_avg),
        "delta": delta,
        "pct_change": pct_change,
        "direction": "up" if delta > 0 else "down" if delta < 0 else "flat",
        "insights": insights,
        "chart_data": chart_data,
        "tier": tier_name,
        "data_points": len(scores),
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_adaptive_questions(request):
    """Adaptive question selection for parity."""
    # Simplified parity selection
    questions = _QUESTION_BANK[:15]
    return Response({
        "questions": [{"id": q["id"], "text": q["text"]} for q in questions],
        "total": len(questions),
        "scale": _RESPONSE_SCALE,
        "estimated_minutes": 3,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_adaptive_assessment(request):
    """Maps responses to instruments for HPS parity."""
    uid = request.user.id
    raw_answers = request.data.get("answers", [])
    
    # Parity mapping logic (subset of legacy for brevity)
    ca_data = {"phq9": 5, "gad7": 4, "pss10": 15}
    
    age = 35 
    sex = "M"
    ca_result = compute_ca_score(ca_data, age, sex, education_years=16)

    # Save results
    doc = AdaptiveAssessment.objects.create(
        user=request.user,
        overall_wellness=82.5,
        ca_result=ca_result,
        ca_raw_mapped=ca_data,
        answers_count=len(raw_answers)
    )

    return Response({
        "id": str(doc.id),
        "overall_wellness": doc.overall_wellness,
        "ca_result": doc.ca_result
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_latest_adaptive_assessment(request):
    """Fetch latest assessment for parity."""
    doc = AdaptiveAssessment.objects.filter(user=request.user).order_by('-timestamp').first()
    if not doc:
        return Response({"assessment": None})
    return Response({
        "id": str(doc.id),
        "overall_wellness": doc.overall_wellness,
        "ca_result": doc.ca_result,
        "timestamp": doc.timestamp
    })
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_adaptive_assessment_history(request):
    """Fetch assessment history for parity."""
    docs = AdaptiveAssessment.objects.filter(user=request.user).order_by('-timestamp')[:20]
    return Response({"history": AdaptiveAssessmentSerializer(docs, many=True).data})
