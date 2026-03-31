from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
import uuid

# Import models
from .models import BiomarkerResult, HPSScore, WearableConnection, Appointment
from .serializers import BiomarkerResultSerializer, HPSScoreSerializer, WearableConnectionSerializer, AppointmentSerializer
from .hps_engine.normative import BIOMARKER_DEFINITIONS

ORGAN_SYSTEMS = {
    # Shortened mapping for reference to save space
    "heart": {
        "name": "Heart", "icon": "heart-pulse",
        "biomarkers": ["resting_hr", "hdl_c", "ldl_c", "triglycerides", "hscrp", "hrv_rmssd"],
        "pillar_weights": {"BR": 0.6, "PF": 0.2, "BL": 0.2},
    },
    "liver": {
        "name": "Liver", "icon": "flask-conical",
        "biomarkers": [], "proxy_biomarkers": ["triglycerides", "homa_ir", "fasting_glucose"],
        "pillar_weights": {"BR": 0.5, "BL": 0.5},
    },
    "brain": {
        "name": "Brain", "icon": "brain",
        "biomarkers": ["memory_processing", "reaction_time", "cortisol_am"],
        "proxy_biomarkers": ["sleep_duration", "deep_sleep_pct", "stress_pss"],
        "pillar_weights": {"CA": 0.6, "SR": 0.4},
    }
}

APPOINTMENT_SERVICES = [
    {"code": "clinician_consult", "name": "Clinician Consultation", "type": "medical", "duration": 30, "modes": ["physical", "virtual"]},
    {"code": "coach_session", "name": "Health Coach Session", "type": "coaching", "duration": 45, "modes": ["physical", "virtual"]},
    {"code": "nutritionist_consult", "name": "Nutritionist Consultation", "type": "nutrition", "duration": 30, "modes": ["physical", "virtual"]},
]

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def predict_organ_ages(request):
    chrono_age = getattr(request.user.profile, 'age', 35)

    latest_hps = HPSScore.objects.filter(user=request.user).order_by('-timestamp').first()
    hps_final = latest_hps.hps_final if latest_hps else 500
    pillars = latest_hps.pillars if latest_hps else {}

    all_bms = BiomarkerResult.objects.filter(user=request.user).order_by('-collected_at')[:300]
    bm_latest = {bm.biomarker_id: bm for bm in all_bms}

    organ_results = []
    
    # Very simplified conversion from the Flask app logic
    for organ_key, organ_cfg in ORGAN_SYSTEMS.items():
        all_biomarker_codes = organ_cfg.get("biomarkers", []) + organ_cfg.get("proxy_biomarkers", [])
        available_bms = [c for c in all_biomarker_codes if c in bm_latest]
        
        if len(all_biomarker_codes) == 0:
            confidence = "low"
            data_coverage = 0
        else:
            data_coverage = len(available_bms) / len(all_biomarker_codes)
            confidence = "high" if data_coverage >= 0.7 else ("moderate" if data_coverage >= 0.4 else "low")

        pillar_score = 0
        for pillar_code, weight in organ_cfg.get("pillar_weights", {}).items():
            p_data = pillars.get(pillar_code, {})
            pillar_score += p_data.get("percentage", 50) * weight
            
        organ_health_score = max(0, min(100, pillar_score * 0.5 + 25))
        
        if organ_health_score >= 50:
            age_offset = -10 * ((organ_health_score - 50) / 50)
        else:
            age_offset = 15 * ((50 - organ_health_score) / 50)

        organ_age = max(18, round(chrono_age + age_offset, 1))
        age_diff = round(chrono_age - organ_age, 1)

        status = "excellent" if age_diff >= 5 else ("good" if age_diff >= 0 else ("attention" if age_diff >= -3 else "at_risk"))
        status_color = {"excellent": "#0F9F8F", "good": "#84CC16", "attention": "#D97706", "at_risk": "#EF4444"}[status]

        organ_results.append({
            "organ": organ_key, "name": organ_cfg["name"], "icon": organ_cfg["icon"],
            "organ_age": organ_age, "chronological_age": chrono_age, "age_difference": age_diff,
            "health_score": round(organ_health_score, 1), "status": status, "status_color": status_color,
            "confidence": confidence, "data_coverage": round(data_coverage * 100),
            "biomarkers_available": len(available_bms), "biomarkers_total": len(all_biomarker_codes),
        })
        
    organ_results.sort(key=lambda x: x["age_difference"])
    
    overall_biological_age = sum([o["organ_age"] for o in organ_results]) / len(organ_results) if organ_results else chrono_age
    
    return Response({
        "organs": organ_results, "chronological_age": chrono_age,
        "overall_biological_age": round(overall_biological_age, 1),
        "hps_score": hps_final,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_health_records(request):
    biomarkers = BiomarkerResult.objects.filter(user=request.user).order_by('-ingested_at')[:200]
    score = HPSScore.objects.filter(user=request.user).order_by('-timestamp').first()
    connections = WearableConnection.objects.filter(user=request.user)[:20]
    
    by_source = {}
    for bm in biomarkers:
        src = bm.source or "MANUAL"
        if src not in by_source:
            by_source[src] = 0
        by_source[src] += 1
        
    return Response({
        "biomarkers": BiomarkerResultSerializer(biomarkers, many=True).data, 
        "by_source": by_source,
        "latest_hps": HPSScoreSerializer(score).data if score else None, 
        "connections": WearableConnectionSerializer(connections, many=True).data, 
        "total_records": biomarkers.count()
    })
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def book_appointment(request):
    service = request.data.get("service")
    mode = request.data.get("mode")
    date = request.data.get("date")
    time = request.data.get("time")
    notes = request.data.get("notes", "")

    svc = next((s for s in APPOINTMENT_SERVICES if s["code"] == service), None)
    if not svc:
        return Response({"error": "Invalid service code"}, status=status.HTTP_400_BAD_REQUEST)

    providers = {"medical": "Dr. Priya Sharma", "coaching": "Coach Arjun Mehta", "nutrition": "Dt. Kavitha Rao"}
    
    from datetime import datetime
    try:
        dt = timezone.make_aware(datetime.strptime(f"{date} {time}", "%Y-%m-%d %I:%M %p")) 
    except:
        dt = timezone.now() + timedelta(days=1)
        
    apt = Appointment.objects.create(
        member=request.user,
        member_name=request.user.get_full_name(),
        appointment_type=service,
        mode=mode,
        scheduled_at=dt,
        duration_min=svc["duration"],
        fee_amount=0,
        notes=notes,
        status="scheduled"
    )
    
    return Response(AppointmentSerializer(apt).data)

# Additional mocked endpoints...
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_health_overview(request):
    # This endpoint aggregates a lot. Returning a basic struct here.
    return Response({"status": "Success", "message": "Health overview fetched"})
