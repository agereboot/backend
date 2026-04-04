from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta
import random
import uuid
from django.db.models import Avg, Count
from django.contrib.auth.models import User
from .models import (
    UserProfile, BiomarkerResult, WearableConnection, 
    LabOrder, CareTeamEscalation, Notification
)
from .views_corp_utils import _req_corp, _tier_str
from .serializers_corp import CareTeamEscalationSerializer

EXPECTED_BIOMARKERS = 14
EXPECTED_LAB_PANELS = {"Complete Blood Panel", "Lipid Profile", "Metabolic Panel", "Thyroid Function", "Vitamin D & B12"}
WEARABLE_STALE_HOURS = 24

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_data_quality_dashboard(request):
    _req_corp(request.user)
    company = request.user.profile.company
    employees = User.objects.filter(profile__company=company, profile__role__name='employee')
    
    now = timezone.now()
    employee_quality = []
    total_biomarker_coverage = 0
    total_wearable_fresh = 0
    total_lab_complete = 0
    gap_alerts = []
    
    for emp in employees:
        eid = str(emp.id)
        
        # --- Biomarker Coverage ---
        biomarkers = BiomarkerResult.objects.filter(user=emp)
        unique_codes = set(biomarkers.values_list('biomarker__code', flat=True))
        biomarker_count = len(unique_codes)
        
        oldest_dt = biomarkers.order_by('collected_at').first().collected_at if biomarkers.exists() else None
        oldest_days = (now - oldest_dt).days if oldest_dt else 0
        
        biomarker_pct = round(biomarker_count / EXPECTED_BIOMARKERS * 100)
        biomarker_status = "green" if biomarker_pct >= 80 else "amber" if biomarker_pct >= 50 else "red"
        
        # --- Wearable Sync Freshness ---
        wearable = WearableConnection.objects.filter(user=emp).first()
        wearable_connected = (wearable is not None and wearable.status == 'connected')
        wearable_fresh = False
        wearable_hours_ago = None
        
        if wearable and wearable.last_sync:
            wearable_hours_ago = round((now - wearable.last_sync).total_seconds() / 3600, 1)
            wearable_fresh = (wearable_hours_ago <= WEARABLE_STALE_HOURS)
            
        wearable_status = "green" if wearable_fresh else "amber" if wearable_connected else "red"
            
        # --- Lab Panel Completeness ---
        lab_orders = LabOrder.objects.filter(patient=emp)
        completed_tests = set()
        ordered_tests = set()
        for lo in lab_orders:
            tests = lo.tests if isinstance(lo.tests, list) else []
            ordered_tests.update(tests)
            if lo.status in ("completed", "resulted"):
                completed_tests.update(tests)
        
        lab_pct = round(len(completed_tests) / max(len(EXPECTED_LAB_PANELS), 1) * 100)
        lab_status = "green" if lab_pct >= 80 else "amber" if lab_pct >= 40 else "red"
        
        # --- Overall Quality Score ---
        quality_score = round(biomarker_pct * 0.4 + (100 if wearable_fresh else 30 if wearable_connected else 0) * 0.3 + lab_pct * 0.3)
        overall_status = "green" if quality_score >= 75 else "amber" if quality_score >= 45 else "red"
        
        total_biomarker_coverage += biomarker_pct
        total_wearable_fresh += (1 if wearable_fresh else 0)
        total_lab_complete += lab_pct
        
        # Generate gap alerts
        emp_name = emp.get_full_name() or emp.username
        if biomarker_status == "red":
            gap_alerts.append({
                "employee_id": eid, "employee_name": emp_name,
                "type": "biomarker_gap", "severity": "high",
                "message": f"Only {biomarker_count}/{EXPECTED_BIOMARKERS} biomarkers on file"
            })
        if oldest_days > 90:
            gap_alerts.append({
                "employee_id": eid, "employee_name": emp_name,
                "type": "stale_biomarker", "severity": "medium",
                "message": f"Oldest biomarker is {oldest_days} days old — retest recommended"
            })
        if wearable_status == "red":
            gap_alerts.append({
                "employee_id": eid, "employee_name": emp_name,
                "type": "no_wearable", "severity": "medium",
                "message": "No wearable device connected"
            })
            
        employee_quality.append({
            "employee_id": eid,
            "employee_name": emp_name,
            "department": emp.profile.department.name if emp.profile.department else "Unknown",
            "quality_score": quality_score,
            "overall_status": overall_status,
            "biomarker": {
                "count": biomarker_count,
                "expected": EXPECTED_BIOMARKERS,
                "coverage_pct": biomarker_pct,
                "oldest_days": oldest_days,
                "status": biomarker_status,
            },
            "wearable": {
                "connected": wearable_connected,
                "fresh": wearable_fresh,
                "hours_since_sync": wearable_hours_ago,
                "device": wearable.provider if wearable else "None",
                "status": wearable_status,
            },
            "lab_panels": {
                "completed": len(completed_tests),
                "ordered": len(ordered_tests),
                "expected": len(EXPECTED_LAB_PANELS),
                "completion_pct": lab_pct,
                "missing": sorted(list(EXPECTED_LAB_PANELS - ordered_tests)),
                "status": lab_status,
            },
        })
        
    n = max(employees.count(), 1)
    return Response({
        "summary": {
            "total_employees": employees.count(),
            "avg_quality_score": round(sum(eq["quality_score"] for eq in employee_quality) / n),
            "avg_biomarker_coverage": round(total_biomarker_coverage / n),
            "wearable_connected_pct": round(total_wearable_fresh / n * 100),
            "avg_lab_completion": round(total_lab_complete / n),
            "quality_distribution": {
                "green": sum(1 for eq in employee_quality if eq["overall_status"] == "green"),
                "amber": sum(1 for eq in employee_quality if eq["overall_status"] == "amber"),
                "red": sum(1 for eq in employee_quality if eq["overall_status"] == "red"),
            }
        },
        "employees": sorted(employee_quality, key=lambda x: x["quality_score"]),
        "gap_alerts": sorted(gap_alerts, key=lambda x: 0 if x["severity"] == "high" else 1),
        "last_updated": now.isoformat(),
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_data_quality_nudge(request):
    _req_corp(request.user)
    data = request.data
    emp_id = data.get("employee_id")
    gap_type = data.get("gap_type", "general")
    message = data.get("message", "Please update your health data to keep your HPS score accurate.")
    
    nudge = Notification.objects.create(
        user_id=emp_id,
        type="data_quality",
        message=message,
        data={
            "title": f"Data Update Needed: {gap_type.replace('_', ' ').title()}",
            "category": "data_quality",
            "source": "wellness_head",
            "sender_id": str(request.user.id),
            "gap_type": gap_type
        }
    )
    return Response({"status": "sent", "notification_id": str(nudge.id)})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def escalate_to_care_team(request):
    _req_corp(request.user)
    data = request.data
    try:
        emp = User.objects.get(id=data["employee_id"])
    except User.DoesNotExist:
        return Response({"error": "Employee not found"}, status=404)
        
    esc = CareTeamEscalation.objects.create(
        employee=emp,
        escalated_by=request.user,
        type=data.get("type", "clinical_review"),
        reason=data.get("reason", ""),
        urgency=data.get("urgency", "normal"),
        status="open"
    )
    
    # Notify clinicians
    clinicians = User.objects.filter(profile__role__name__in=['longevity_physician', 'clinician'])
    for doc in clinicians:
        Notification.objects.create(
            user_id=doc.id,
            type="escalation",
            message=f"HR/Wellness escalated {emp.get_full_name() or emp.username}: {esc.reason}",
            data={
                "title": f"Escalation: {emp.get_full_name() or emp.username}",
                "category": "escalation",
                "source": "corporate",
                "escalation_id": str(esc.id),
                "employee_id": str(emp.id)
            }
        )
        
    return Response({
        "status": "escalated", 
        "escalation_id": str(esc.id), 
        "notified_physicians": clinicians.count()
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_care_team_escalations(request):
    _req_corp(request.user)
    role = getattr(request.user.profile.role, 'name', '')
    query = {}
    if role in ("corporate_hr_admin", "corporate_wellness_head"):
        query["escalated_by"] = request.user
        
    escalations = CareTeamEscalation.objects.filter(**query).order_by('-created_at')
    serializer = CareTeamEscalationSerializer(escalations, many=True)
    return Response({"escalations": serializer.data, "total": len(serializer.data)})
