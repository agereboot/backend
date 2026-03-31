from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
import json
import os
import logging
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

from .models import (
    HPSScore, BiomarkerResult, UserProfile, CCAlert, NutritionLog
)

logger = logging.getLogger(__name__)

# Fallback in case Litellm is not fully installed but we want to load views
try:
    import litellm
except ImportError:
    litellm = None

def _get_api_key():
    key = os.environ.get("EMERGENT_LLM_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    return key

def _ask_ai(system_message: str, prompt: str, model="claude-3-sonnet-20240229"):
    """Wrapper calling LiteLLM to handle any key provided in the environment."""
    api_key = _get_api_key()
    if not api_key:
        logger.warning("AI Service not fully configured. Using fallback text.")
        return None
        
    if not litellm:
        return None

    try:
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            api_key=api_key
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LiteLLM completion error: {e}")
        return None


# ─── MODULE C: HPS Score Explainer ────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def explain_hps_score(request, user_id):
    """AI-powered plain-language explanation of HPS score and pillar breakdown."""
    score = HPSScore.objects.filter(user__id=user_id).order_by('-timestamp').first()
    if not score:
        return Response({"explanation": None, "message": "No HPS score available yet"})

    patient = get_object_or_404(User, id=user_id)

    pillars = score.pillars or {}
    pillar_text = "\n".join([
        f"- {v.get('name', k)}: {v.get('percentage', v.get('score', 0))}% ({v.get('tier', 'N/A')})"
        for k, v in pillars.items()
    ])

    prompt = f"""Explain this Health Performance Score (HPS) in simple, encouraging language for a patient.
Patient: {patient.get_full_name() or patient.username}
Overall HPS: {score.hps_final}/1000
Tier: {score.tier}

Pillar Breakdown:
{pillar_text}

Provide:
1. A 2-3 sentence overall summary of their health performance
2. Their strongest pillar and why it matters
3. The pillar needing most attention with one actionable tip
4. An encouraging closing statement about their longevity trajectory

Format as JSON with keys: summary, strongest_pillar, focus_area, encouragement"""

    text = _ask_ai(
        system_message="You are a longevity medicine expert. Explain health scores in patient-friendly language. Always respond in valid JSON without markdown wrapping.",
        prompt=prompt
    )
    
    if text:
        try:
            if text.startswith("```"):
                text = text.split("```")[1].replace("json", "", 1).strip()
            explanation = json.loads(text)
        except json.JSONDecodeError:
            explanation = {"summary": text, "strongest_pillar": "", "focus_area": "", "encouragement": ""}
    else:
        explanation = {
            "summary": f"Your HPS score is {score.hps_final}/1000 ({score.tier} tier).",
            "strongest_pillar": "Review your pillar breakdown for details.",
            "focus_area": "Focus on your lowest-scoring pillar for maximum improvement.",
            "encouragement": "Every step towards better health counts. Keep going!"
        }

    return Response({"explanation": explanation, "hps_final": score.hps_final, "tier": score.tier})


# ─── MODULE G: Lab Report Interpretation Engine ───────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def interpret_lab_report(request, user_id):
    """AI-powered per-biomarker interpretation for recent lab results."""
    # Since we mapped reports natively to BiomarkerResult, we fetch the latest 30 days
    recent_date = timezone.now() - timedelta(days=30)
    biomarkers = BiomarkerResult.objects.filter(user__id=user_id, collected_at__gte=recent_date)
    
    if not biomarkers.exists():
        return Response({"interpretations": [], "message": "No biomarker data in recent reports"})

    patient = get_object_or_404(User, id=user_id)

    markers_text = "\n".join([
        f"- {m.biomarker.name if m.biomarker else 'Unknown'}: {m.value} {m.unit if hasattr(m, 'unit') else ''}"
        for m in biomarkers
    ])

    prompt = f"""Interpret these lab results for a longevity-focused patient.
Patient: {patient.get_full_name() or patient.username}

Biomarkers:
{markers_text}

For each biomarker, provide:
1. What this marker measures (1 sentence)
2. Whether the value is optimal for longevity
3. One specific, actionable recommendation if not optimal

Also provide an overall_summary (2-3 sentences).

Respond as JSON: {{"interpretations": [{{"biomarker": "name", "explanation": "...", "longevity_status": "optimal|needs_attention|critical", "recommendation": "..."}}], "overall_summary": "..."}}"""

    text = _ask_ai(
        system_message="You are a longevity medicine specialist interpreting lab results. Always respond in valid JSON without markdown formatting.",
        prompt=prompt
    )

    if text:
        try:
            if text.startswith("```"):
                text = text.split("```")[1].replace("json", "", 1).strip()
            result = json.loads(text)
        except json.JSONDecodeError:
            result = {"interpretations": [], "overall_summary": text}
    else:
        result = {
            "interpretations": [{"biomarker": m.biomarker.name if m.biomarker else "Test", "explanation": f"Value: {m.value}", "longevity_status": "Unknown", "recommendation": "Consult your doctor."} for m in biomarkers],
            "overall_summary": "AI interpretation temporarily unavailable. Please review with your physician."
        }

    return Response(result)


# ─── AI CHAT ASSIST ───────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ai_chat_context(request, patient_id):
    """Surface patient history and flags for doctor during chat."""
    patient = get_object_or_404(User, id=patient_id)

    hps = HPSScore.objects.filter(user=patient).order_by('-timestamp').first()
    recent_biomarkers = BiomarkerResult.objects.filter(user=patient).order_by('-collected_at')[:20]
    recent_alerts = CCAlert.objects.filter(member=patient, status="open").order_by('-created_at')[:5]

    context_data = {
        "hps_score": hps.hps_final if hps else None,
        "hps_tier": hps.tier if hps else None,
        "recent_biomarkers_count": recent_biomarkers.count(),
        "active_alerts_count": recent_alerts.count()
    }

    # Gather text fields
    alerts = [a.alert_type for a in recent_alerts]

    prompt = f"""Summarize this patient's key health context for a consulting doctor in 3-4 bullet points.
Patient: {patient.get_full_name() or patient.username}
HPS Score: {context_data['hps_score']}/1000 ({context_data['hps_tier']})
Recent Biomarkers Monitored: {context_data['recent_biomarkers_count']}
Active alerts: {'; '.join(alerts) or 'None'}

Respond as JSON: {{"bullet_points": ["...", "..."], "priority_flag": "none|low|medium|high", "suggested_topics": ["...", "..."]}}"""

    text = _ask_ai("You are a clinical decision support AI. Provide concise patient context summaries. Always respond in valid JSON.", prompt)

    if text:
        try:
            if text.startswith("```"):
                text = text.split("```")[1].replace("json", "", 1).strip()
            ai_context = json.loads(text)
        except Exception as e:
            ai_context = {"bullet_points": ["AI parsing failed"], "priority_flag": "low", "suggested_topics": []}
    else:
        ai_context = {
            "bullet_points": [f"HPS: {context_data['hps_score']}/1000", f"Active alerts: {len(alerts)}"],
            "priority_flag": "high" if alerts else "low",
            "suggested_topics": ["Review active alerts"]
        }

    return Response({"ai_context": ai_context, "raw_data": context_data})


# ─── MODULE F: DROPOUT RISK DETECTOR ─────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detect_dropout_risk(request, patient_id):
    """Detect patient disengagement risk based on activity patterns (Nutrition, Appts, CCs)."""
    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    patient = get_object_or_404(User, id=patient_id)

    # Activity signals (Adapted for Django fields)
    recent_biomarkers = BiomarkerResult.objects.filter(user=patient, collected_at__gte=thirty_days_ago).count()
    nutrition_logs = NutritionLog.objects.filter(user=patient, date__gte=seven_days_ago.date()).count()

    risk_score = 0
    risk_factors = []

    if recent_biomarkers == 0:
        risk_score += 20
        risk_factors.append("No biomarker updates in 30 days")
    if nutrition_logs == 0:
        risk_score += 25
        risk_factors.append("No nutrition logs in 7 days")

    risk_level = "low" if risk_score < 25 else "medium" if risk_score < 50 else "high" if risk_score < 75 else "critical"

    return Response({
        "patient_id": patient_id,
        "patient_name": patient.get_full_name() or patient.username,
        "risk_score": min(100, risk_score),
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "activity_summary": {
            "biomarkers_30d": recent_biomarkers,
            "nutrition_logs_7d": nutrition_logs,
        },
        "assessed_at": now.isoformat()
    })
