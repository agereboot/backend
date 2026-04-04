import uuid
import statistics
import logging
from datetime import datetime, timezone, timedelta
from django.utils import timezone as django_timezone
from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import (
    BiomarkerResult, HPSScore, WearableConnection, Appointment,
    Medication, MedicationLog, RefillRequest, SOSAlert,
    OrganSystem, AppointmentService, MedicalCondition
)
from .serializers import (
    BiomarkerResultSerializer, HPSScoreSerializer, WearableConnectionSerializer, 
    AppointmentSerializer, MedicationSerializer, MedicationLogSerializer,
    RefillRequestSerializer, SOSAlertSerializer, OrganSystemSerializer,
    AppointmentServiceSerializer, MedicalConditionSerializer
)
from .hps_engine.normative import BIOMARKER_DEFINITIONS

logger = logging.getLogger(__name__)

# ── Organ Age Prediction System ───────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def predict_organ_ages(request):
    """Predicts organ ages based on biomarkers, HPS scores, and medical conditions."""
    uid = request.user.id
    profile = getattr(request.user, 'profile', None)
    chrono_age = getattr(profile, 'age', 35)

    latest_hps = HPSScore.objects.filter(user=request.user).order_by('-timestamp').first()
    hps_final = latest_hps.hps_final if latest_hps else 500
    pillars = latest_hps.pillars if latest_hps else {}

    all_bms = BiomarkerResult.objects.filter(user=request.user).order_by('-collected_at')[:300]
    bm_latest = {bm.biomarker_id: bm for bm in all_bms}

    conditions = MedicalCondition.objects.filter(user=request.user, status="active")
    condition_names = [c.name.lower() for c in conditions]

    # Fetch dynamic OrganSystems from DB
    organ_configs = OrganSystem.objects.all()
    if not organ_configs.exists():
        # Fallback to hardcoded if not seeded yet
        return Response({"error": "Organ configurations not found. Please seed demo data."}, status=500)

    organ_results = []
    for organ_cfg in organ_configs:
        all_biomarker_codes = organ_cfg.biomarkers + organ_cfg.proxy_biomarkers
        available_bms = [c for c in all_biomarker_codes if c in bm_latest]
        direct_available = [c for c in organ_cfg.biomarkers if c in bm_latest]
        has_direct = len(organ_cfg.biomarkers) == 0 or len(direct_available) > 0

        if len(all_biomarker_codes) == 0:
            confidence = "low"
            data_coverage = 0
        else:
            data_coverage = len(available_bms) / len(all_biomarker_codes)
            confidence = "high" if data_coverage >= 0.7 else ("moderate" if data_coverage >= 0.4 else "low")

        pillar_score = 0
        for pillar_code, weight in organ_cfg.pillar_weights.items():
            p_data = pillars.get(pillar_code, {})
            pillar_score += p_data.get("percentage", 50) * weight

        bm_adjustment = 0
        bm_count = 0
        for code in available_bms:
            bm = bm_latest[code]
            defn = BIOMARKER_DEFINITIONS.get(code)
            if not defn: continue
            val = bm.value
            opt_low = defn.get("optimal_low", 0)
            opt_high = defn.get("optimal_high", 100)
            direction = defn.get("direction", "optimal_range")
            
            if direction == "lower_better":
                bm_score = 100 if val <= opt_high else max(0, 100 - (val - opt_high) / (opt_high or 1) * 100)
            elif direction == "higher_better":
                bm_score = 100 if val >= opt_low else max(0, val / (opt_low or 1) * 100)
            else:
                mid = (opt_low + opt_high) / 2
                rng = (opt_high - opt_low) / 2
                bm_score = max(0, 100 - abs(val - mid) / (rng or 1) * 50) if rng > 0 else 50
            bm_adjustment += bm_score
            bm_count += 1

        avg_bm = (bm_adjustment / bm_count) if bm_count > 0 else 50

        condition_penalty = 0
        matching_conditions = []
        for cond in condition_names:
            for risk_term in organ_cfg.conditions_risk:
                if risk_term in cond:
                    condition_penalty += 12
                    matching_conditions.append(cond)
                    break
        condition_penalty = min(condition_penalty, 30)

        organ_health_score = max(0, min(100, pillar_score * 0.5 + avg_bm * 0.4 + 10 - condition_penalty))

        if organ_health_score >= 50:
            age_offset = -10 * ((organ_health_score - 50) / 50)
        else:
            age_offset = 15 * ((50 - organ_health_score) / 50)

        organ_age = max(18, round(chrono_age + age_offset, 1))
        age_diff = round(chrono_age - organ_age, 1)

        suggested_tests = []
        if confidence != "high" or not has_direct:
            for test in organ_cfg.suggested_tests:
                suggested_tests.append({
                    "test": test["test"], "credits": test["credits"], "category": test["category"], 
                    "priority": test["priority"], 
                    "reason": f"Improve {organ_cfg.name} age estimate accuracy" if confidence != "high" else f"Monitor {organ_cfg.name} health"
                })

        status_key = "excellent" if age_diff >= 5 else ("good" if age_diff >= 0 else ("attention" if age_diff >= -3 else "at_risk"))
        status_color = {"excellent": "#0F9F8F", "good": "#84CC16", "attention": "#D97706", "at_risk": "#EF4444"}[status_key]

        organ_results.append({
            "organ": organ_cfg.code, "name": organ_cfg.name, "icon": organ_cfg.icon,
            "organ_age": organ_age, "chronological_age": chrono_age, "age_difference": age_diff,
            "health_score": round(organ_health_score, 1), "status": status_key, "status_color": status_color,
            "confidence": confidence, "data_coverage": round(data_coverage * 100),
            "biomarkers_available": len(available_bms), "biomarkers_total": len(all_biomarker_codes),
            "matching_conditions": matching_conditions, "suggested_tests": suggested_tests,
        })

    organ_results.sort(key=lambda x: x["age_difference"])
    return Response({
        "organs": organ_results, "chronological_age": chrono_age,
        "overall_biological_age": round(statistics.mean([o["organ_age"] for o in organ_results]), 1) if organ_results else chrono_age,
        "hps_score": hps_final,
    })

# ── Health Records ────────────────────────────────────────────────────────

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
            by_source[src] = []
        by_source[src].append(BiomarkerResultSerializer(bm).data)
        
    return Response({
        "biomarkers": BiomarkerResultSerializer(biomarkers, many=True).data, 
        "by_source": {k: len(v) for k, v in by_source.items()},
        "latest_hps": HPSScoreSerializer(score).data if score else None, 
        "connections": WearableConnectionSerializer(connections, many=True).data, 
        "total_records": biomarkers.count()
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_health_summary(request):
    score = HPSScore.objects.filter(user=request.user).order_by('-timestamp').first()
    biomarkers = BiomarkerResult.objects.filter(user=request.user).order_by('-ingested_at')[:200]
    latest_bm = {}
    for bm in biomarkers:
        if bm.biomarker_id not in latest_bm:
            latest_bm[bm.biomarker_id] = BiomarkerResultSerializer(bm).data
            
    from .models import Roadmap
    roadmap = Roadmap.objects.filter(user=request.user).first()
    
    return Response({
        "user": {
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email,
            "name": f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
        },
        "hps": HPSScoreSerializer(score).data if score else None, 
        "biomarkers": list(latest_bm.values()), 
        "biomarker_count": len(latest_bm),
        "roadmap_exists": roadmap is not None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_title": f"AgeReboot Health Report — {request.user.first_name or 'Athlete'}",
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_health_overview(request):
    uid = request.user
    score = HPSScore.objects.filter(user=request.user).order_by('-timestamp').first()

    vitals_codes = {
        "systolic_bp": {"name": "Blood Pressure (Systolic)", "unit": "mmHg", "icon": "heart-pulse"},
        "heart_rate_resting": {"name": "Heart Rate (Resting)", "unit": "bpm", "icon": "activity"},
        "respiratory_rate": {"name": "Respiratory Rate", "unit": "breaths/min", "icon": "wind"},
        "bmi": {"name": "BMI", "unit": "kg/m2", "icon": "scale"},
    }
    vitals = []
    for code, meta in vitals_codes.items():
        records = BiomarkerResult.objects.filter(user=request.user, biomarker__code=code).order_by('-collected_at')[:5]
        if records.exists():
            latest = records[0].value
            prev = records[1].value if records.count() > 1 else latest
            delta = latest - prev
            trend = "stable"
            if abs(delta) >= 0.5:
                if delta > 0:
                    trend = "deteriorating" if code in ["systolic_bp", "heart_rate_resting"] else "improving"
                else:
                    trend = "improving" if code in ["systolic_bp", "heart_rate_resting"] else "deteriorating"
            vitals.append({"code": code, "name": meta["name"], "value": round(latest, 1), "unit": meta["unit"], "trend": trend, "icon": meta["icon"], "prev_value": round(prev, 1)})
        else:
            demo_vals = {"systolic_bp": 128, "heart_rate_resting": 72, "respiratory_rate": 16, "bmi": 23.5}
            val = demo_vals.get(code, 0)
            vitals.append({"code": code, "name": meta["name"], "value": val, "unit": meta["unit"], "trend": "stable", "icon": meta["icon"], "prev_value": val})

    conditions_db = MedicalCondition.objects.filter(user=request.user)
    conditions = []
    for cond in conditions_db:
        bio_trends = []
        for bc in cond.relevant_biomarkers:
            recs = BiomarkerResult.objects.filter(user=request.user, biomarker__code=bc).order_by('-collected_at')[:5]
            if recs.exists():
                vals = [r.value for r in recs]
                defn = BIOMARKER_DEFINITIONS.get(bc, {})
                bio_trends.append({"code": bc, "name": defn.get("name", bc), "latest": round(vals[0], 2), "unit": defn.get("unit", ""), "values": [round(v, 2) for v in reversed(vals)]})
        conditions.append({
            "code": cond.code, "name": cond.name, "status": cond.status, 
            "diagnosed_date": cond.diagnosed_date, "severity": cond.severity, "icd10": cond.icd10, 
            "care_plan": cond.care_plan, "biomarker_trends": bio_trends
        })

    meds_db = Medication.objects.filter(member=request.user)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    meds = []
    for med in meds_db:
        taken_today = MedicationLog.objects.filter(user=request.user, medication=med, date=today_str).exists()
        meds.append({
            "id": str(med.id), "name": med.medication_name, "condition": med.diagnosis_code, 
            "dosage": med.dosage, "frequency": med.frequency, "taken_today": taken_today,
            "refills_remaining": med.refills_allowed, "instructions": med.clinical_notes
        })

    appointments = Appointment.objects.filter(member=request.user, status__in=["scheduled", "confirmed"]).order_by('scheduled_at')[:10]
    services = AppointmentService.objects.all()

    lab_reports = BiomarkerResult.objects.filter(user=request.user, source__in=["LAB_OCR", "LAB_UPLOAD", "SEED_DATA"]).order_by('-collected_at')[:8]

    return Response({
        "hps_score": {
            "score": round(score.hps_final) if score else None, 
            "tier": score.tier if score else None, 
            "timestamp": score.timestamp if score else None
        },
        "vitals": vitals, "conditions": conditions, "medications": meds,
        "appointments": AppointmentSerializer(appointments, many=True).data, 
        "lab_reports": BiomarkerResultSerializer(lab_reports, many=True).data, 
        "services": AppointmentServiceSerializer(services, many=True).data,
    })

# ── Medication Management ────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_medication(request, med_id):
    """Log medication compliance and reward credits."""
    try:
        med = Medication.objects.get(id=med_id, member=request.user)
    except Medication.DoesNotExist:
        return Response({"error": "Medication not found"}, status=404)

    today = datetime.now(timezone.utc).date()
    if MedicationLog.objects.filter(user=request.user, medication=med, date=today).exists():
        return Response({"message": "Already logged today", "logged": True})

    MedicationLog.objects.create(
        user=request.user, medication=med, 
        medication_name=med.medication_name, date=today
    )
    
    # Reward credits (logic from views_employee.py)
    from .views_employee import _add_credits
    reward = 2 # Default reward
    _add_credits(request.user, reward, f"Medication compliance: {med.medication_name}")
    
    return Response({"message": f"Logged {med.medication_name}. +{reward} credits!", "logged": True, "credits_earned": reward})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_medication_refill(request, med_id):
    """Request a refill for a medication."""
    try:
        med = Medication.objects.get(id=med_id, member=request.user)
    except Medication.DoesNotExist:
        return Response({"error": "Medication not found"}, status=404)

    refill = RefillRequest.objects.create(
        user=request.user, medication=med, medication_name=med.medication_name,
        status="requested"
    )
    
    # Notifications (legacy parity)
    from .views_employee import _create_feed_item
    _create_feed_item(request.user, "refill", f"requested a refill for {med.medication_name}")
    
    return Response({"message": f"Refill request sent for {med.medication_name}. Care team notified.", "request_id": str(refill.id)})

# ── SOS Alerts ────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_sos(request):
    """Trigger an emergency SOS alert."""
    message = request.data.get("message", "Emergency assistance requested")
    severity = request.data.get("severity", "high")
    
    sos = SOSAlert.objects.create(
        user=request.user, 
        user_name=f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
        message=message, severity=severity, status="active",
        franchise=getattr(request.user.profile, 'company', None).name if getattr(request.user.profile, 'company', None) else "Independent"
    )

    from .views_employee import _create_feed_item
    _create_feed_item(request.user, "sos", f"triggered an SOS alert: {message}")

    return Response({
        "id": str(sos.id), "user_name": sos.user_name, "message": sos.message,
        "severity": sos.severity, "status": sos.status, "triggered_at": sos.triggered_at,
        "notified_team": [{"name": "Dr. Priya Sharma", "role": "Primary Physician", "email": "dr.sharma@agereboot.care"}]
    })

# ── Appointment Booking ──────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def book_appointment(request):
    service_code = request.data.get("service")
    mode = request.data.get("mode")
    date = request.data.get("date")
    time = request.data.get("time")
    notes = request.data.get("notes", "")

    try:
        svc = AppointmentService.objects.get(code=service_code)
    except AppointmentService.DoesNotExist:
        return Response({"error": "Invalid service code"}, status=400)

    providers = {"medical": "Dr. Priya Sharma", "coaching": "Coach Arjun Mehta", "nutrition": "Dt. Kavitha Rao"}
    
    # Mock date parsing
    try:
        dt = django_timezone.make_aware(datetime.strptime(f"{date} {time}", "%Y-%m-%d %I:%M %p")) 
    except:
        dt = django_timezone.now() + timedelta(days=5)

    apt = Appointment.objects.create(
        member=request.user,
        member_name=f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
        appointment_type=service_code,
        mode=mode,
        scheduled_at=dt,
        duration_min=svc.duration,
        notes=notes,
        status="scheduled"
    )
    
    from .views_employee import _create_feed_item
    _create_feed_item(request.user, "appointment", f"booked a {svc.name} ({mode}) for {date}")

    return Response(AppointmentSerializer(apt).data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def reschedule_appointment(request, apt_id):
    try:
        apt = Appointment.objects.get(id=apt_id, member=request.user)
    except Appointment.DoesNotExist:
        return Response({"error": "Appointment not found"}, status=404)

    date = request.data.get("date")
    time = request.data.get("time")
    
    try:
        dt = django_timezone.make_aware(datetime.strptime(f"{date} {time}", "%Y-%m-%d %I:%M %p"))
        print('dt',dt)
        apt.scheduled_at = dt
        apt.status = "rescheduled"
        apt.save()
    except:
        return Response({"error": "Invalid date/time format"}, status=400)
    
    return Response(AppointmentSerializer(apt).data)

# ── Notifications & Digest ────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_health_digest(request):
    """Generates and sends a monthly health digest (mocked email)."""
    score = HPSScore.objects.filter(user=request.user).order_by('-timestamp').first()
    hps = round(score.hps_final) if score else "N/A"
    tier = score.tier if score else "N/A"
    user_name = request.user.first_name or "Athlete"
    
    html = f"<h1>AgeReboot Monthly Digest</h1><p>Hi {user_name}, your latest HPS is {hps} ({tier}).</p>"
    
    return Response({
        "message": f"Health digest generated for {request.user.email}",
        "email_result": {"status": "no_api_key", "message": "RESEND_API_KEY not configured."},
        "html_preview": html
    })
