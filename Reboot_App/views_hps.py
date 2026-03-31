from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
import uuid
import hashlib

# Import models
from .models import BiomarkerResult, HPSScore
from .serializers import HPSScoreSerializer
from .hps_engine.scoring import compute_hps
from .hps_engine.predictions import predict_hps_trajectory
from .hps_engine.questionnaire_scoring import compute_ca_score

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
        
    score = HPSScore.objects.filter(user__id=target_user_id).order_by('-timestamp').first()
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
        best = max(pillars.items(), key=lambda x: x[1].get("percentage", 0))
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

# Note: The CA Assessments / Adaptive assessments routes from Flask were omitted
# here because their parent DB models (CAAssessment, AdaptiveAssessment) 
# were not part of the initial core DB models migration. 
# They can easily be re-added once Models are created.
