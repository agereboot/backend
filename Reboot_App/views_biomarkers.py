from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Q, Avg
from datetime import timedelta
import uuid
import re
import random
import json

# Import models
from .models import (
    User, UserProfile,
    BiomarkerDefinition, BiomarkerResult, ManualEntry,
    WearableDevice, WearableConnection, ReportRepository, 
    CognitiveAssessmentTemplate, CognitiveAssessmentResult,
    PillarConfig, HPSScore
)
from .serializers import (
    BiomarkerDefinitionSerializer, BiomarkerResultSerializer,
    BulkBiomarkerIngestSerializer, ManualEntrySerializer,
    WearableConnectionSerializer, ReportRepositorySerializer,
    CognitiveTemplateSerializer, CognitiveResultSerializer,
    WearableDeviceSerializer
)
from .hps_engine.normative import (
    BIOMARKER_DEFINITIONS, BIOMARKER_CORRELATIONS, COGNITIVE_ASSESSMENTS
)
from .hps_engine.scoring import compute_hps


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ingest_biomarkers(request):
    serializer = BulkBiomarkerIngestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    results = []
    for bm in serializer.validated_data['biomarkers']:
        code = bm['biomarker_code']
        if code not in BIOMARKER_DEFINITIONS:
            continue
            
        defn_data = BIOMARKER_DEFINITIONS[code]
        defn, _ = BiomarkerDefinition.objects.get_or_create(
            code=code,
            defaults={
                'name': defn_data['name'],
                'domain': defn_data['domain'],
                'pillar': defn_data['pillar'],
                'unit': defn_data['unit'],
                'direction': defn_data.get('direction', 'optimal_range'),
                'optimal_low': defn_data.get('optimal_low'),
                'optimal_high': def_data.get('optimal_high')
            }
        )
        
        result = BiomarkerResult.objects.create(
            user=request.user,
            biomarker=defn,
            value=bm['value'],
            source=bm.get('source', 'MANUAL'),
            collected_at=bm.get('collected_at') or timezone.now()
        )
        results.append(BiomarkerResultSerializer(result).data)
        
    return Response({"ingested": len(results), "results": results})


@api_view(['GET'])
def get_biomarker_definitions(request):
    defs = []
    for code, defn in BIOMARKER_DEFINITIONS.items():
        defs.append({
            "code": code,
            "name": defn["name"],
            "domain": defn["domain"],
            "pillar": defn["pillar"],
            "unit": defn["unit"],
            "direction": defn["direction"],
            "optimal_low": defn.get("optimal_low"),
            "optimal_high": defn.get("optimal_high"),
        })
    return Response({"definitions": defs})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def compare_biomarkers(request):
    code_a = request.data.get("code_a", "")
    code_b = request.data.get("code_b", "")
    if not code_a or not code_b:
        return Response({"error": "Provide code_a and code_b"}, status=status.HTTP_400_BAD_REQUEST)

    defn_a = BIOMARKER_DEFINITIONS.get(code_a)
    defn_b = BIOMARKER_DEFINITIONS.get(code_b)
    if not defn_a or not defn_b:
        return Response({"error": "Invalid biomarker code"}, status=status.HTTP_400_BAD_REQUEST)

    bms_a = BiomarkerResult.objects.filter(user=request.user, biomarker_id=code_a).order_by('collected_at')[:50]
    bms_b = BiomarkerResult.objects.filter(user=request.user, biomarker_id=code_b).order_by('collected_at')[:50]

    history_a = [{"date": bm.collected_at.strftime('%Y-%m-%d'), "value": bm.value} for bm in bms_a]
    history_b = [{"date": bm.collected_at.strftime('%Y-%m-%d'), "value": bm.value} for bm in bms_b]

    corr_info = BIOMARKER_CORRELATIONS.get((code_a, code_b)) or BIOMARKER_CORRELATIONS.get((code_b, code_a))
    correlation = None
    if corr_info:
        correlation = {"strength": corr_info["strength"], "direction": corr_info["direction"], "insight": corr_info["insight"]}

    return Response({
        "biomarker_a": {"code": code_a, "name": defn_a["name"], "unit": defn_a["unit"], "pillar": defn_a["pillar"], "optimal_low": defn_a.get("optimal_low"), "optimal_high": defn_a.get("optimal_high"), "direction": defn_a.get("direction"), "history": history_a},
        "biomarker_b": {"code": code_b, "name": defn_b["name"], "unit": defn_b["unit"], "pillar": defn_b["pillar"], "optimal_low": defn_b.get("optimal_low"), "optimal_high": defn_b.get("optimal_high"), "direction": defn_b.get("direction"), "history": history_b},
        "correlation": correlation,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pillar_dashboard(request):
    from .hps_engine.normative import PILLAR_CONFIG
    
    all_bms = BiomarkerResult.objects.filter(user=request.user).order_by('-collected_at')[:500]
    
    latest_by_code = {}
    history_by_code = {}
    
    for bm in all_bms:
        code = bm.biomarker_id
        if code not in latest_by_code:
            latest_by_code[code] = bm
        if code not in history_by_code:
            history_by_code[code] = []
        if len(history_by_code[code]) < 10:
            history_by_code[code].append(bm)
            
    pillars = {}
    for code, defn in BIOMARKER_DEFINITIONS.items():
        pillar = defn["pillar"]
        if pillar not in pillars:
            cfg = PILLAR_CONFIG.get(pillar, {})
            pillars[pillar] = {
                "code": pillar, "name": cfg.get("name", pillar), 
                "color": cfg.get("color", "#7B35D8"), 
                "biomarkers": [], "red": 0, "yellow": 0, "green": 0
            }
            
        bm = latest_by_code.get(code)
        if bm:
            val = bm.value
            opt_low, opt_high = defn.get("optimal_low", 0), defn.get("optimal_high", 100)
            direction = defn.get("direction", "optimal_range")
            if direction == "lower_better":
                status = "green" if val <= opt_high else ("yellow" if val <= opt_high * 1.3 else "red")
            elif direction == "higher_better":
                status = "green" if val >= opt_low else ("yellow" if val >= opt_low * 0.7 else "red")
            else:
                status = "green" if opt_low <= val <= opt_high else ("yellow" if opt_low * 0.8 <= val <= opt_high * 1.2 else "red")
            
            history = [{"value": round(h.value, 2), "date": h.collected_at.strftime('%Y-%m-%d')} for h in reversed(history_by_code.get(code, []))]
            pillars[pillar]["biomarkers"].append({
                "code": code, "name": defn["name"], "value": round(val, 2), "unit": defn["unit"], 
                "domain": defn["domain"], "optimal_low": opt_low, "optimal_high": opt_high, 
                "direction": direction, "status": status, "history": history, "data_source": defn.get("data_source", "manual")
            })
            pillars[pillar][status] += 1
        else:
            pillars[pillar]["biomarkers"].append({
                "code": code, "name": defn["name"], "value": None, "unit": defn["unit"], 
                "domain": defn["domain"], "optimal_low": defn.get("optimal_low"), "optimal_high": defn.get("optimal_high"), 
                "direction": defn.get("direction"), "status": "missing", "history": [], "data_source": defn.get("data_source", "manual")
            })
            
    return Response({"pillars": pillars})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_biomarker_predictions(request):
    all_bms = BiomarkerResult.objects.filter(user=request.user).order_by('-collected_at')[:500]
    
    # Simple compliance mock for parity
    try:
        profile = request.user.profile
        compliance_score = profile.adherence_pct or 75
    except:
        compliance_score = 75

    latest_by_code = {}
    history_by_code = {}
    for bm in all_bms:
        code = bm.biomarker_id
        if code not in latest_by_code:
            latest_by_code[code] = bm
        if code not in history_by_code:
            history_by_code[code] = []
        if len(history_by_code[code]) < 10:
            history_by_code[code].append(bm)

    predictions = []
    for code, defn in BIOMARKER_DEFINITIONS.items():
        bm = latest_by_code.get(code)
        if not bm: continue
        
        val = bm.value
        opt_low, opt_high = defn.get("optimal_low", 0), defn.get("optimal_high", 100)
        direction = defn.get("direction", "optimal_range")
        
        is_red = False
        if direction == "lower_better" and val > opt_high * 1.3: is_red = True
        elif direction == "higher_better" and val < opt_low * 0.7: is_red = True
        elif direction == "optimal_range" and (val < opt_low * 0.8 or val > opt_high * 1.2): is_red = True
        
        if not is_red: continue

        history = [h.value for h in history_by_code.get(code, [])]
        recent_trend = (history[0] - history[-1]) / len(history) if len(history) >= 2 else 0
        cf = compliance_score / 100.0
        
        if direction == "lower_better":
            imp = -abs(recent_trend) * cf * 0.5
            p1, p2, p3 = max(0, val + imp * 30), max(0, val + imp * 60), max(0, val + imp * 90)
        elif direction == "higher_better":
            imp = abs(recent_trend) * cf * 0.5
            p1, p2, p3 = val + imp * 30, val + imp * 60, val + imp * 90
        else:
            mid = (opt_low + opt_high) / 2
            mv = (mid - val) * cf * 0.1
            p1, p2, p3 = val + mv, val + mv * 2, val + mv * 3

        hist_data = [{"value": round(h.value, 2), "date": h.collected_at.strftime('%Y-%m-%d')} for h in reversed(history_by_code.get(code, []))]
        predictions.append({
            "code": code, "name": defn["name"], "unit": defn["unit"], 
            "current": round(val, 2), "optimal_low": opt_low, "optimal_high": opt_high, 
            "direction": direction, 
            "predictions": [{"month": 1, "value": round(p1, 2)}, {"month": 2, "value": round(p2, 2)}, {"month": 3, "value": round(p3, 2)}], 
            "compliance_score": compliance_score, "history": hist_data
        })

    return Response({"predictions": predictions, "compliance_score": compliance_score})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cognitive_assessments(request):
    completed = CognitiveAssessmentResult.objects.filter(user=request.user).order_by('-completed_at')[:50]
    results_data = CognitiveResultSerializer(completed, many=True).data
    return Response({"assessments": COGNITIVE_ASSESSMENTS, "completed": results_data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_cognitive_assessment(request):
    code = request.data.get("assessment_code")
    answers = request.data.get("answers", [])
    total_score = request.data.get("total_score", 0)

    template = next((a for a in COGNITIVE_ASSESSMENTS if a["code"] == code), None)
    if not template:
        return Response({"error": "Invalid assessment code"}, status=400)

    max_s = template["max_score"]
    pct = (total_score / max_s) * 100 if max_s else 0
    severity = "normal" if pct <= 20 else ("mild" if pct <= 40 else ("moderate" if pct <= 60 else "severe"))

    # Ensure template exists in DB
    db_template, _ = CognitiveAssessmentTemplate.objects.get_or_create(
        code=code, 
        defaults={
            "name": template["name"], "domain": template["domain"], 
            "max_score": max_s, "pillar": template["pillar"]
        }
    )

    result = CognitiveAssessmentResult.objects.create(
        user=request.user,
        template=db_template,
        answers=answers,
        total_score=total_score,
        max_score=max_s,
        percentage=round(pct, 1),
        severity=severity
    )

    return Response(CognitiveResultSerializer(result).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_manual_entry(request):
    code = request.data.get("biomarker_code")
    val = request.data.get("value")
    notes = request.data.get("notes", "")
    
    defn = BIOMARKER_DEFINITIONS.get(code)
    if not defn:
        return Response({"error": "Unknown biomarker code"}, status=status.HTTP_400_BAD_REQUEST)
        
    opt_low, opt_high = defn.get("optimal_low", 0), defn.get("optimal_high", 100)
    system_flag = "normal" if opt_low * 0.3 <= float(val) <= opt_high * 3 else "flagged_out_of_range"
    
    bdef, _ = BiomarkerDefinition.objects.get_or_create(code=code, defaults={'name': defn['name'], 'pillar': defn['pillar']})
    
    entry = ManualEntry.objects.create(
        user=request.user,
        biomarker=bdef,
        value=val,
        notes=notes,
        entered_by=request.user.first_name or "Athlete",
        entered_by_role="employee",
        system_validation=system_flag,
        clinician_validation="pending",
        status="pending_validation"
    )
    
    return Response(ManualEntrySerializer(entry).data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def validate_manual_entry(request, entry_id):
    try:
        entry = ManualEntry.objects.get(id=entry_id)
    except ManualEntry.DoesNotExist:
        return Response({"error": "Entry not found"}, status=404)

    approved = request.data.get("approved", False)
    notes = request.data.get("notes", "")

    if approved:
        # Create real result
        BiomarkerResult.objects.create(
            user=entry.user,
            biomarker=entry.biomarker,
            value=entry.value,
            source="VALIDATED_MANUAL",
            collected_at=entry.created_at
        )
        entry.clinician_validation = "approved"
        entry.status = "validated"
    else:
        entry.clinician_validation = "rejected"
        entry.status = "rejected"

    entry.clinician_notes = notes
    entry.validated_at = timezone.now()
    entry.save()

    return Response(ManualEntrySerializer(entry).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_manual_entries(request):
    # For employees, show their own. For clinicians (staff), show all pending or related.
    if request.user.is_staff:
        entries = ManualEntry.objects.all().order_by('-created_at')[:50]
    else:
        entries = ManualEntry.objects.filter(user=request.user).order_by('-created_at')[:50]
    return Response({"entries": ManualEntrySerializer(entries, many=True).data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_correlation_matrix(request):
    all_bms = BiomarkerResult.objects.filter(user=request.user).order_by('-collected_at')[:500]
    latest = {bm.biomarker_id: bm.value for bm in all_bms}

    red_codes = set()
    for code, defn in BIOMARKER_DEFINITIONS.items():
        val = latest.get(code)
        if val is None: continue
        
        opt_low, opt_high = defn.get("optimal_low", 0), defn.get("optimal_high", 100)
        direction = defn.get("direction", "optimal_range")
        if direction == "lower_better" and val > opt_high * 1.3: red_codes.add(code)
        elif direction == "higher_better" and val < opt_low * 0.7: red_codes.add(code)
        elif direction == "optimal_range" and (val < opt_low * 0.8 or val > opt_high * 1.2): red_codes.add(code)

    correlations = []
    cascade_impact = {}
    for (a, b), info in BIOMARKER_CORRELATIONS.items():
        if a in red_codes or b in red_codes:
            a_defn = BIOMARKER_DEFINITIONS.get(a, {})
            b_defn = BIOMARKER_DEFINITIONS.get(b, {})
            correlations.append({
                "biomarker_a": a, "name_a": a_defn.get("name", a),
                "biomarker_b": b, "name_b": b_defn.get("name", b),
                "strength": info["strength"], "direction": info["direction"],
                "insight": info["insight"],
                "a_status": "red" if a in red_codes else "ok",
                "b_status": "red" if b in red_codes else "ok",
            })
            for c in (a, b): cascade_impact[c] = cascade_impact.get(c, 0) + 1

    best_target = None
    if cascade_impact:
        best_code = max(cascade_impact, key=cascade_impact.get)
        best_defn = BIOMARKER_DEFINITIONS.get(best_code, {})
        best_target = {
            "code": best_code, "name": best_defn.get("name", best_code),
            "connections": cascade_impact[best_code],
            "recommendation": f"Improving {best_defn.get('name', best_code)} would positively impact {cascade_impact[best_code]} other biomarkers.",
        }

    return Response({
        "correlations": correlations,
        "red_biomarkers": list(red_codes),
        "cascade_impact": cascade_impact,
        "best_target": best_target,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_biomarker_benchmarking(request):
    try:
        profile = request.user.profile
        user_age = (timezone.now().date() - profile.dob).days // 365 if profile.dob else 35
        user_sex = profile.sex or "M"
    except:
        user_age, user_sex = 35, "M"

    age_low, age_high = max(18, user_age - 10), user_age + 10
    
    user_bms = BiomarkerResult.objects.filter(user=request.user).order_by('-collected_at')[:500]
    user_latest = {bm.biomarker_id: bm.value for bm in user_bms}

    # Cohort query (using is_demo profiles or all same-age-sex)
    cohort_users = User.objects.filter(
        profile__sex=user_sex, 
        profile__dob__range=[timezone.now().date() - timedelta(days=age_high*365), 
                             timezone.now().date() - timedelta(days=age_low*365)]
    ).values_list('id', flat=True)

    if cohort_users.count() < 5:
        cohort_users = User.objects.all().values_list('id', flat=True)
        cohort_label = "All Participants"
    else:
        cohort_label = f"{user_sex}, Age {age_low}-{age_high}"

    cohort_bms_data = BiomarkerResult.objects.filter(user_id__in=cohort_users).values('biomarker_id').annotate(avg_val=Avg('value'))
    cohort_means = {item['biomarker_id']: item['avg_val'] for item in cohort_bms_data}

    # For percentile logic, we need more detail or simulation
    benchmarks = []
    for code, defn in BIOMARKER_DEFINITIONS.items():
        user_val = user_latest.get(code)
        if user_val is None: continue
        
        mean_val = cohort_means.get(code, user_val)
        # Simulated percentile logic for parity
        diff = (user_val - mean_val) / max(mean_val, 1)
        percentile = 50 + (diff * 100)
        percentile = min(99, max(1, percentile))
        
        direction = defn.get("direction", "optimal_range")
        health_percentile = percentile if direction == "higher_better" else (100-percentile if direction == "lower_better" else 100 - abs(50-percentile)*2)
        health_percentile = round(min(99, max(1, health_percentile)), 1)
        
        rating = "excellent" if health_percentile >= 80 else "good" if health_percentile >= 60 else "average" if health_percentile >= 40 else "below_average" if health_percentile >= 20 else "needs_attention"

        benchmarks.append({
            "code": code, "name": defn["name"], "pillar": defn["pillar"], "unit": defn["unit"],
            "user_value": round(user_val, 1), "percentile": round(percentile,1), "health_percentile": health_percentile,
            "cohort_mean": round(mean_val, 1), "cohort_p25": round(mean_val * 0.8, 1), "cohort_p75": round(mean_val * 1.2, 1),
            "cohort_size": cohort_users.count(), "direction": direction, "rating": rating,
        })

    benchmarks.sort(key=lambda x: -x["health_percentile"])
    overall_health_pct = round(sum(b["health_percentile"] for b in benchmarks) / max(len(benchmarks), 1), 1)

    return Response({
        "benchmarks": benchmarks, "cohort_label": cohort_label, "cohort_size": cohort_users.count(),
        "overall_health_percentile": overall_health_pct, "top_strengths": benchmarks[:3],
        "areas_to_improve": benchmarks[-3:], "user_age": user_age, "user_sex": user_sex,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_biomarkers(request, user_id):
    results = BiomarkerResult.objects.filter(user__id=user_id).order_by('-ingested_at')[:500]
    return Response({"biomarkers": BiomarkerResultSerializer(results, many=True).data, "count": results.count()})


# Wearable Devices
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_wearable_devices(request):
    devices = WearableDevice.objects.all()
    # If no devices in DB, return empty or common ones asAvailable
    data = WearableDeviceSerializer(devices, many=True).data
    # Check connections
    conns = WearableConnection.objects.filter(user=request.user).values_list('device_id', flat=True)
    for d in data:
        d['status'] = 'connected' if d['device_id'] in conns else 'available'
    return Response({"devices": data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def connect_device(request, device):
    try:
        dev_obj = WearableDevice.objects.get(device_id=device)
    except WearableDevice.DoesNotExist:
        # Create on the fly for parity if missing
        dev_obj = WearableDevice.objects.create(device_id=device, name=device.capitalize(), category="watch")

    conn, created = WearableConnection.objects.get_or_create(
        user=request.user, device=dev_obj,
        defaults={"status": "active", "mode": "simulated"}
    )
    return Response({"message": "Device connected", "connection": WearableConnectionSerializer(conn).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disconnect_device(request, device):
    WearableConnection.objects.filter(user=request.user, device_id=device).delete()
    return Response({"message": "Device disconnected", "device": device})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_wearable(request):
    device = request.data.get("device", "oura")
    # Simulated sync implementation
    biomarkers = [
        {"biomarker_code": "resting_hr", "value": random.uniform(55, 75)},
        {"biomarker_code": "hrv_rmssd", "value": random.uniform(30, 60)},
        {"biomarker_code": "sleep_duration", "value": random.uniform(6.5, 8.5)}
    ]
    
    # Use existing ingest logic
    request.data['biomarkers'] = biomarkers
    res = ingest_biomarkers(request)
    
    # Update last sync
    WearableConnection.objects.filter(user=request.user, device_id=device).update(last_sync=timezone.now())
    
    return Response({"device": device, "synced": True, **res.data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_connections(request):
    connections = WearableConnection.objects.filter(user=request.user)
    return Response({"connections": WearableConnectionSerializer(connections, many=True).data})


# Reports
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_report_repository(request):
    reports = ReportRepository.objects.filter(user=request.user).order_by('-uploaded_at')[:100]
    return Response({"reports": ReportRepositorySerializer(reports, many=True).data, "consent_required": False})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_report(request):
    content = request.data.get("content", "")
    is_hps = request.data.get("is_hps_report", False)
    
    # Simulate extraction
    extracted = []
    if "glucose" in content.lower():
        extracted.append({"name": "Fasting Glucose", "biomarker_code": "fasting_glucose", "value": 92.5, "unit": "mg/dL"})

    report = ReportRepository.objects.create(
        user=request.user,
        report_type="lab_report" if is_hps else "other",
        title="Uploaded Lab Report" if is_hps else "General Report",
        is_hps_report=is_hps,
        uploaded_by=request.user.get_full_name() or "Athlete",
        report_date=timezone.now(),
        content_preview=content[:200],
        size_bytes=len(content),
        parameters_extracted=len(extracted),
        extracted_parameters=extracted
    )
    
    data = ReportRepositorySerializer(report).data
    data['extracted_parameters'] = extracted
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_lab_text(request):
    text = request.data.get("text", "")
    # Placeholder for regex logic similar to legacy
    extracted = {"fasting_glucose": 94.2} if "glucose" in text.lower() else {}
    
    results = []
    for code, val in extracted.items():
        if code in BIOMARKER_DEFINITIONS:
            # Create real result
            defn, _ = BiomarkerDefinition.objects.get_or_create(code=code, defaults={'name': BIOMARKER_DEFINITIONS[code]['name'], 'pillar': BIOMARKER_DEFINITIONS[code]['pillar']})
            res = BiomarkerResult.objects.create(user=request.user, biomarker=defn, value=val, source="LAB_OCR")
            results.append(BiomarkerResultSerializer(res).data)
            
    return Response({"parsed": len(extracted), "extracted": extracted, "ingested": len(results), "results": results})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_lab_results(request):
    from .serializers import LabUploadSerializer
    serializer = LabUploadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    
    lab_name = serializer.validated_data['lab_name']
    results = serializer.validated_data['results']
    
    biomarkers = []
    for code, value in results.items():
        if code in BIOMARKER_DEFINITIONS:
            biomarkers.append({
                "biomarker_code": code,
                "value": value,
                "source": f"LAB_{lab_name.upper().replace(' ', '_')}"
            })
            
    if not biomarkers:
        return Response({"error": "No valid biomarkers in lab results"}, status=400)
        
    request.data['biomarkers'] = biomarkers
    return ingest_biomarkers(request)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_biomarker_analytics(request, member_id=None):
    """Get per-patient biomarker analytics with trend data for parity.
    If member_id is None, use current user (Employee Portal)."""
    target_user_id = member_id or request.user.id
    
    # Parity ranges (subset of legacy for brevity)
    LONGEVITY_RANGES = {
        "hba1c": {"optimal": [4.0, 5.2], "standard": [4.0, 5.6], "unit": "%", "domain": "Metabolic", "name": "HbA1c"},
        "fasting_glucose": {"optimal": [70, 90], "standard": [70, 100], "unit": "mg/dL", "domain": "Metabolic", "name": "Fasting Glucose"},
        "ldl_cholesterol": {"optimal": [50, 100], "standard": [0, 130], "unit": "mg/dL", "domain": "Cardiovascular", "name": "LDL Cholesterol"},
    }

    results = BiomarkerResult.objects.filter(user_id=target_user_id).order_by('-collected_at')[:500]
    
    from collections import defaultdict
    grouped = defaultdict(list)
    for bm in results:
        grouped[bm.biomarker_id].append(bm)

    analytics = []
    at_risk, optimal, borderline = 0, 0, 0

    for code, entries in grouped.items():
        ref = LONGEVITY_RANGES.get(code, {})
        latest = entries[0]
        val = latest.value
        
        status = "normal"
        if ref.get("optimal"):
            opt_lo, opt_hi = ref["optimal"]
            std_lo, std_hi = ref.get("standard", ref["optimal"])
            if opt_lo <= val <= opt_hi:
                status, optimal = "optimal", optimal + 1
            elif std_lo <= val <= std_hi:
                status, borderline = "borderline", borderline + 1
            else:
                status, at_risk = "at_risk", at_risk + 1
        else:
            optimal += 1

        trend = [{"date": e.collected_at.strftime('%Y-%m-%d'), "value": e.value} for e in reversed(entries[:12])]

        analytics.append({
            "code": code,
            "name": ref.get("name", code),
            "domain": ref.get("domain", "General"),
            "latest_value": val,
            "unit": ref.get("unit", ""),
            "optimal_range": ref.get("optimal"),
            "status": status,
            "trend": trend,
            "readings_count": len(entries),
        })

    return Response({
        "analytics": analytics,
        "summary": {"total": len(analytics), "at_risk": at_risk, "optimal": optimal, "borderline": borderline}
    })

