import uuid
import random
import json
import logging
from datetime import datetime, timezone, timedelta
from django.db.models import Q, Avg, Count
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    CCAlert, NFLETask, Escalation, CCReferral, 
    CCAssignment, HPSScore, UserProfile, CCSession, 
    CCProtocol, CCPrescription, CarePlan, CCMessage, CCOverrideAudit,
    BiomarkerResult, BiomarkerDefinition, Appointment, EMREncounter,
    LabOrder, LabPanel, TelehealthSession, MemberMedicalHistory
)
from .serializers import (
    CCAlertSerializer, NFLETaskSerializer, EscalationSerializer, 
    CCReferralSerializer, CCAssignmentSerializer, CCSessionSerializer,
    CCProtocolSerializer, CCPrescriptionSerializer, CarePlanSerializer,
    CCMessageSerializer, CCOverrideAuditSerializer
)

logger = logging.getLogger(__name__)

# ─── HCP ROLES & METADATA ──────────────────────────────────────
HCP_ROLES = {
    "longevity_physician", "fitness_coach", "psychologist",
    "physical_therapist", "nutritional_coach", "nurse_navigator",
    "corporate_hr_admin", "corporate_wellness_head",
}
LEGACY_ALIASES = {
    "clinician": "longevity_physician", 
    "coach": "fitness_coach", 
    "medical_director": "longevity_physician", 
    "clinical_admin": "nurse_navigator"
}
PRESCRIBING_ROLES = {"longevity_physician", "clinician", "medical_director"}

ROLE_META = {
    "longevity_physician": {"label": "Longevity Physician", "scope": "full_clinical", "primary_hps": ["BR"], "icon": "Stethoscope"},
    "fitness_coach": {"label": "Physical Fitness Coach", "scope": "exercise_rx", "primary_hps": ["PF", "RS"], "icon": "Dumbbell"},
    "psychologist": {"label": "Psychology Therapist", "scope": "mental_health", "primary_hps": ["CA", "RS"], "icon": "Brain"},
    "physical_therapist": {"label": "Physical Therapist", "scope": "rehab_functional", "primary_hps": ["PF"], "icon": "Activity"},
    "nutritional_coach": {"label": "Nutritional Coach", "scope": "nutrition_mnt", "primary_hps": ["BR", "LC"], "icon": "Apple"},
    "nurse_navigator": {"label": "Nurse / Care Navigator", "scope": "care_coordination", "primary_hps": ["BR", "RS"], "icon": "HeartPulse"},
}

def _resolve_role(user):
    """Normalize user role based on UserProfile."""
    try:
        role = user.profile.role.name.lower().replace(" ", "_")
        return LEGACY_ALIASES.get(role, role)
    except:
        return "longevity_physician" # Fallback

def _require_hcp(user):
    role = _resolve_role(user)
    if role not in HCP_ROLES and role not in LEGACY_ALIASES:
        return False
    return True

# ─── DASHBOARD ─────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cc_dashboard(request):
    """Clinician/Coach Dashboard — population health summary & action items."""
    if not _require_hcp(request.user):
        return Response({"error": "HCP access restricted"}, status=status.HTTP_403_FORBIDDEN)

    user = request.user
    role = _resolve_role(user)

    # 1. Get assigned members
    assignments = CCAssignment.objects.filter(cc=user)
    member_ids = assignments.values_list('member_id', flat=True)
    
    members_data = []
    total_hps = 0
    
    for m_id in member_ids:
        try:
            m_user = User.objects.get(id=m_id)
            profile = m_user.profile
            
            # Latest HPS
            latest_hps = HPSScore.objects.filter(user=m_user).order_by('-timestamp').first()
            hps_val = latest_hps.hps_final if latest_hps else 0
            total_hps += hps_val
            
            # HPS Trend
            prev_scores = HPSScore.objects.filter(user=m_user).order_by('-timestamp')[:2]
            delta = 0
            trend = "stable"
            if len(prev_scores) >= 2:
                delta = round(prev_scores[0].hps_final - prev_scores[1].hps_final, 1)
                trend = "improving" if delta > 5 else "declining" if delta < -5 else "stable"
            
            # Last contact (last session)
            last_session = CCSession.objects.filter(member=m_user, cc=user).order_by('-scheduled_at').first()
            
            members_data.append({
                "id": str(m_user.id),
                "username": m_user.username,
                "name": f"{m_user.first_name} {m_user.last_name}".strip() or m_user.username,
                "hps_score": hps_val,
                "tier": latest_hps.tier if latest_hps else "UNKNOWN",
                "hps_delta": delta,
                "hps_trend": trend,
                "last_contact": last_session.scheduled_at if last_session else None,
                "pillars": latest_hps.pillars if latest_hps else {}
            })
        except User.DoesNotExist:
            continue

    # 2. Stats
    open_alerts_count = CCAlert.objects.filter(cc=user, status="open").count()
    critical_alerts_count = CCAlert.objects.filter(cc=user, status="open", severity="CRITICAL").count()
    
    today = datetime.now(timezone.utc).date()
    sessions_today_count = CCSession.objects.filter(cc=user, scheduled_at__date=today).count()
    
    # 3. Agenda
    sessions_today = CCSession.objects.filter(cc=user, scheduled_at__date=today).order_by('scheduled_at')
    agenda = []
    for s in sessions_today:
        agenda.append({
            "id": str(s.id),
            "member_name": f"{s.member.first_name} {s.member.last_name}".strip() or s.member.username,
            "scheduled_at": s.scheduled_at,
            "session_type": s.session_type,
            "status": s.status
        })

    # 4. Top Alerts
    top_alerts_qs = CCAlert.objects.filter(cc=user, status="open").order_by('-aps_score')[:5]
    top_alerts = []
    for a in top_alerts_qs:
        top_alerts.append({
            "id": str(a.id),
            "member_name": f"{a.member.first_name} {a.member.last_name}".strip() or a.member.username,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "biomarker": a.biomarker,
            "value": a.value,
            "aps_score": a.aps_score
        })

    avg_hps = round(total_hps / max(len(members_data), 1), 1)

    return Response({
        "stats": {
            "total_members": len(members_data),
            "open_alerts": open_alerts_count,
            "critical_alerts": critical_alerts_count,
            "today_sessions": sessions_today_count,
            "pending_reviews": 0, # To be implemented
            "avg_hps": avg_hps,
        },
        "members": sorted(members_data, key=lambda x: x["hps_score"], reverse=True),
        "agenda": agenda,
        "top_alerts": top_alerts,
        "role": role,
    })

# ─── MEMBERS ───────────────────────────────────────────────────

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_cc_members(request):
#     """List all members assigned to this CC with sorting and filtering."""
#     if not _require_hcp(request.user):
#         return Response({"error": "HCP access restricted"}, status=status.HTTP_403_FORBIDDEN)

#     user = request.user
#     role = _resolve_role(user)
    
#     search = request.GET.get("search", "").lower()
#     sort_by = request.GET.get("sort_by", "hps")
#     filter_tier = request.GET.get("filter_tier", "")

#     # Corporate roles see everyone
#     if role in ("corporate_hr_admin", "corporate_wellness_head"):
#         profiles = UserProfile.objects.all() # Or specifically employees
#     else:
#         # Others see assigned
#         assignments = CCAssignment.objects.filter(cc=user)
#         member_ids = assignments.values_list('member_id', flat=True)
#         # Also include appointments
#         appt_member_ids = Appointment.objects.filter(doctor=user).values_list('patient_id', flat=True)
#         combined_ids = set(list(member_ids) + list(appt_member_ids))
#         profiles = UserProfile.objects.filter(user_id__in=combined_ids)

#     members = []
#     for p in profiles:
#         m_user = p.user
#         name = f"{m_user.first_name} {m_user.last_name}".strip() or m_user.username
        
#         if search and search not in name.lower() and search not in m_user.username.lower():
#             continue
            
#         latest_hps = HPSScore.objects.filter(user=m_user).order_by('-timestamp').first()
#         hps_val = latest_hps.hps_final if latest_hps else 0
#         tier = latest_hps.tier if latest_hps else "UNKNOWN"
        
#         if filter_tier and tier != filter_tier:
#             continue
            
#         alert_count = CCAlert.objects.filter(member=m_user, status="open").count()
#         active_protocols = CCPrescription.objects.filter(member=m_user, status="active").count()
        
#         members.append({
#             "id": str(m_user.id),
#             "username": m_user.username,
#             "name": name,
#             "hps_score": hps_val,
#             "tier": tier,
#             "open_alerts": alert_count,
#             "active_protocols": active_protocols,
#             "pillars": latest_hps.pillars if latest_hps else {}
#         })

#     # Sort
#     if sort_by == "hps":
#         members.sort(key=lambda x: x["hps_score"], reverse=True)
#     elif sort_by == "alerts":
#         members.sort(key=lambda x: x["open_alerts"], reverse=True)
#     elif sort_by == "name":
#         members.sort(key=lambda x: x["name"])

#     return Response({"members": members, "total": len(members)})


# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_cc_members(request):
#     """List all members assigned to this CC with sorting and filtering."""

#     if not _require_hcp(request.user):
#         return Response({"error": "HCP access restricted"}, status=status.HTTP_403_FORBIDDEN)

#     user = request.user
#     role = _resolve_role(user)
    
#     search = request.GET.get("search", "").lower()
#     sort_by = request.GET.get("sort_by", "hps")
#     filter_tier = request.GET.get("filter_tier", "")

#     # -----------------------------
#     # 1. Get Profiles
#     # -----------------------------
#     if role in ("corporate_hr_admin", "corporate_wellness_head"):
#         profiles = UserProfile.objects.select_related("user")
#     else:
#         # Assigned members
#         assigned_ids = set(
#             CCAssignment.objects.filter(cc=user)
#             .values_list('member_id', flat=True)
#         )

#         # Appointment members
#         appt_ids = set(
#             Appointment.objects.filter(assigned_hcp=user)
#             .values_list('member_id', flat=True)
#         )

#         combined_ids = assigned_ids.union(appt_ids)

#         profiles = UserProfile.objects.filter(
#             user_id__in=combined_ids
#         ).select_related("user")

#     # -----------------------------
#     # 2. Preload HPS (avoid N+1)
#     # -----------------------------
#     hps_map = {
#         h.user_id: h
#         for h in HPSScore.objects.order_by('user_id', '-timestamp').distinct('user_id')
#     }

#     members = []

#     for p in profiles:
#         m_user = p.user
#         name = f"{m_user.first_name} {m_user.last_name}".strip() or m_user.username

#         # Search filter
#         if search and search not in name.lower() and search not in m_user.username.lower():
#             continue

#         latest_hps = hps_map.get(m_user.id)
#         hps_val = latest_hps.hps_final if latest_hps else 0
#         tier = latest_hps.tier if latest_hps else "UNKNOWN"

#         # Tier filter
#         if filter_tier and tier != filter_tier:
#             continue

#         alert_count = CCAlert.objects.filter(
#             member=m_user, status="open"
#         ).count()

#         active_protocols = CCPrescription.objects.filter(
#             member=m_user, status="active"
#         ).count()

#         members.append({
#             "id": str(m_user.id),
#             "username": m_user.username,
#             "name": name,
#             "hps_score": hps_val,
#             "tier": tier,
#             "open_alerts": alert_count,
#             "active_protocols": active_protocols,
#             "pillars": latest_hps.pillars if latest_hps else {}
#         })

#     # -----------------------------
#     # 3. Sorting
#     # -----------------------------
#     if sort_by == "hps":
#         members.sort(key=lambda x: x["hps_score"], reverse=True)
#     elif sort_by == "alerts":
#         members.sort(key=lambda x: x["open_alerts"], reverse=True)
#     elif sort_by == "name":
#         members.sort(key=lambda x: x["name"])

#     return Response({
#         "members": members,
#         "total": len(members)
#     })


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.db.models import OuterRef, Subquery, Count
from django.shortcuts import get_object_or_404

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_cc_members(request):
    """List all members assigned to this CC with sorting and filtering."""

    if not _require_hcp(request.user):
        return Response({"error": "HCP access restricted"}, status=status.HTTP_403_FORBIDDEN)

    user = request.user
    role = _resolve_role(user)

    search = request.GET.get("search", "").lower()
    sort_by = request.GET.get("sort_by", "hps")
    filter_tier = request.GET.get("filter_tier", "")

    # -----------------------------
    # 1. Get Profiles
    # -----------------------------
    if role in ("corporate_hr_admin", "corporate_wellness_head"):
        profiles = UserProfile.objects.select_related("user")
    else:
        assigned_ids = set(
            CCAssignment.objects.filter(cc=user)
            .values_list('member_id', flat=True)
        )

        appt_ids = set(
            Appointment.objects.filter(assigned_hcp=user)
            .values_list('member_id', flat=True)
        )

        combined_ids = assigned_ids.union(appt_ids)

        profiles = UserProfile.objects.filter(
            user_id__in=combined_ids
        ).select_related("user")

    # -----------------------------
    # 2. Latest HPS (FIXED ✅)
    # -----------------------------
    latest_hps_subquery = HPSScore.objects.filter(
        user_id=OuterRef('user_id')
    ).order_by('-timestamp').values('id')[:1]

    latest_hps = HPSScore.objects.filter(
        id__in=Subquery(latest_hps_subquery)
    )

    hps_map = {h.user_id: h for h in latest_hps}

    # -----------------------------
    # 3. Preload Alerts & Protocols (OPTIMIZED 🚀)
    # -----------------------------
    alert_counts = dict(
        CCAlert.objects.filter(status="open")
        .values("member_id")
        .annotate(count=Count("id"))
        .values_list("member_id", "count")
    )

    protocol_counts = dict(
        CCPrescription.objects.filter(status="active")
        .values("member_id")
        .annotate(count=Count("id"))
        .values_list("member_id", "count")
    )

    members = []

    # -----------------------------
    # 4. Build Response
    # -----------------------------
    for p in profiles:
        m_user = p.user
        name = f"{m_user.first_name} {m_user.last_name}".strip() or m_user.username

        # Search filter
        if search and search not in name.lower() and search not in m_user.username.lower():
            continue

        latest_hps = hps_map.get(m_user.id)
        hps_val = latest_hps.hps_final if latest_hps else 0
        tier = latest_hps.tier if latest_hps else "UNKNOWN"

        # Tier filter
        if filter_tier and tier != filter_tier:
            continue

        members.append({
            "id": str(m_user.id),
            "username": m_user.username,
            "name": name,
            "hps_score": hps_val,
            "tier": tier,
            "open_alerts": alert_counts.get(m_user.id, 0),
            "active_protocols": protocol_counts.get(m_user.id, 0),
            "pillars": latest_hps.pillars if latest_hps else {}
        })

    # -----------------------------
    # 5. Sorting
    # -----------------------------
    if sort_by == "hps":
        members.sort(key=lambda x: x["hps_score"], reverse=True)
    elif sort_by == "alerts":
        members.sort(key=lambda x: x["open_alerts"], reverse=True)
    elif sort_by == "name":
        members.sort(key=lambda x: x["name"].lower())

    return Response({
        "members": members,
        "total": len(members)
    }, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_member_detail(request, member_id):
    """Detailed clinical view for a specific member."""
    if not _require_hcp(request.user):
        return Response({"error": "HCP access restricted"}, status=status.HTTP_403_FORBIDDEN)

    user = request.user
    try:
        member = User.objects.get(id=member_id)
    except User.DoesNotExist:
        return Response({"error": "Member not found"}, status=404)

    # 1. HPS History
    hps_history = HPSScore.objects.filter(user=member).order_by('-timestamp')[:12]
    hps_data = []
    for h in reversed(hps_history):
        hps_data.append({
            "hps_final": h.hps_final,
            "timestamp": h.timestamp,
            "tier": h.tier
        })

    # 2. Biomarkers
    biomarkers = BiomarkerResult.objects.filter(user=member).order_by('-collected_at')[:50]
    
    # 3. Alerts
    alerts = CCAlert.objects.filter(member=member).order_by('-created_at')[:20]
    
    # 4. Prescriptions
    prescriptions = CCPrescription.objects.filter(member=member).order_by('-prescribed_at')[:10]
    
    # 5. Sessions
    sessions = CCSession.objects.filter(member=member, cc=user).order_by('-scheduled_at')[:10]
    
    # 6. Messages
    messages = CCMessage.objects.filter(
        Q(sender=user, recipient=member) | Q(sender=member, recipient=user)
    ).order_by('sent_at')[:50]

    # 7. Overrides
    overrides = CCOverrideAudit.objects.filter(member=member).order_by('-created_at')[:10]

    return Response({
        "member": {
            "id": str(member.id),
            "username": member.username,
            "name": f"{member.first_name} {member.last_name}".strip(),
            "email": member.email
        },
        "hps": hps_data[-1] if hps_data else {},
        "hps_history": hps_data,
        "biomarkers": list(biomarkers.values())[:20], # Simplified
        "alerts": CCAlertSerializer(alerts, many=True).data,
        "prescriptions": CCPrescriptionSerializer(prescriptions, many=True).data,
        "sessions": CCSessionSerializer(sessions, many=True).data,
        "messages": CCMessageSerializer(messages, many=True).data,
        "overrides": CCOverrideAuditSerializer(overrides, many=True).data
    })

# ─── ALERTS ────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_cc_alerts(request):
    """List open alerts assigned to this HCP."""
    if not _require_hcp(request.user):
        return Response({"error": "HCP access restricted"}, status=status.HTTP_403_FORBIDDEN)

    status_filter = request.GET.get("status", "open")
    severity = request.GET.get("severity", "")
    
    query = Q(cc=request.user, status=status_filter)
    if severity:
        query &= Q(severity=severity)
        
    alerts = CCAlert.objects.filter(query).order_by('-aps_score')
    serializer = CCAlertSerializer(alerts, many=True)
    return Response({"alerts": serializer.data, "total": alerts.count()})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def resolve_cc_alert(request, alert_id):
    """Resolve/Decline a clinical alert."""
    try:
        alert = CCAlert.objects.get(id=alert_id, cc=request.user)
    except CCAlert.DoesNotExist:
        return Response({"error": "No alert found"}, status=404)
        
    resolution = request.data.get("resolution", "resolved")
    notes = request.data.get("notes", "")
    
    alert.status = resolution
    alert.resolution_notes = notes
    alert.resolved_by = request.user
    alert.resolved_at = datetime.now(timezone.utc)
    alert.save()
    
    return Response({"status": "resolved", "alert_id": alert_id})

# ─── PROTOCOLS & CARE PLANS ────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_cc_protocols(request):
    """List all available clinical protocols."""
    category = request.GET.get("category", "")
    search = request.GET.get("search", "")
    
    query = Q()
    if category:
        query &= Q(category=category)
    if search:
        query &= (Q(name__icontains=search) | Q(description__icontains=search))
        
    protocols = CCProtocol.objects.filter(query)
    serializer = CCProtocolSerializer(protocols, many=True)
    
    # Unique cats and hallmarks
    categories = list(CCProtocol.objects.values_list('category', flat=True).distinct())
    
    return Response({
        "protocols": serializer.data,
        "categories": categories,
        "total": protocols.count()
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def prescribe_protocol(request, protocol_id):
    """Prescribe a protocol to a member."""
    try:
        protocol = CCProtocol.objects.get(id=protocol_id)
    except CCProtocol.DoesNotExist:
        return Response({"error": "Protocol not found"}, status=404)
        
    member_id = request.data.get("member_id")
    duration = request.data.get("duration_weeks", 12)
    notes = request.data.get("custom_notes", "")
    
    try:
        member = User.objects.get(id=member_id)
    except User.DoesNotExist:
        return Response({"error": "Member not found"}, status=404)
        
    rx = CCPrescription.objects.create(
        member=member,
        clinician=request.user,
        protocol=protocol,
        protocol_name=protocol.name,
        category=protocol.category,
        duration_weeks=duration,
        custom_notes=notes,
        status="active"
    )
    
    return Response(CCPrescriptionSerializer(rx).data)

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def member_care_plan(request, member_id):
    """Get or create an active care plan for a member."""
    try:
        member = User.objects.get(id=member_id)
    except User.DoesNotExist:
        return Response({"error": "Member not found"}, status=404)
        
    if request.method == "GET":
        plan = CarePlan.objects.filter(member=member, status__in=["active", "paused"]).first()
        return Response({"care_plan": CarePlanSerializer(plan).data if plan else None})
        
    # POST - Create
    existing = CarePlan.objects.filter(member=member, status="active").exists()
    if existing:
        return Response({"error": "Already has active plan"}, status=409)
        
    title = request.data.get("title", "Standard Longevity Plan")
    notes = request.data.get("notes", "")
    
    plan = CarePlan.objects.create(
        member=member,
        hcp=request.user,
        hcp_name=f"{request.user.first_name} {request.user.last_name}",
        title=title,
        notes=notes,
        status="active"
    )
    
    # Protocols logic would go here if provided in request.data
    return Response(CarePlanSerializer(plan).data)

# ─── SESSIONS & MESSAGING ──────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def log_cc_session(request):
    """Log or schedule a CC session."""
    member_id = request.data.get("member_id")
    session_type = request.data.get("session_type", "check-in")
    scheduled_at = request.data.get("scheduled_at")
    duration = request.data.get("duration_min", 30)
    
    try:
        member = User.objects.get(id=member_id)
    except User.DoesNotExist:
        return Response({"error": "Member not found"}, status=404)
        
    session = CCSession.objects.create(
        cc=request.user,
        member=member,
        session_type=session_type,
        scheduled_at=scheduled_at,
        duration_min=duration,
        status="scheduled"
    )
    
    return Response(CCSessionSerializer(session).data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_member_cc_sessions(request, member_id):
    try:
        member = User.objects.get(id=member_id)
    except User.DoesNotExist:
        return Response({"error": "Member not found"}, status=404)
        
    sessions = CCSession.objects.filter(cc=request.user, member=member).order_by('-scheduled_at')
    return Response({"sessions": CCSessionSerializer(sessions, many=True).data})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_cc_messages(request, member_id):
    try:
        member = User.objects.get(id=member_id)
    except User.DoesNotExist:
        return Response({"error": "Member not found"}, status=404)
        
    messages = CCMessage.objects.filter(
        Q(sender=request.user, recipient=member) | Q(sender=member, recipient=request.user)
    ).order_by('sent_at')
    return Response({"messages": CCMessageSerializer(messages, many=True).data})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_cc_message(request):
    recipient_id = request.data.get("recipient_id")
    content = request.data.get("content")
    
    try:
        recipient = User.objects.get(id=recipient_id)
    except User.DoesNotExist:
        return Response({"error": "Recipient not found"}, status=404)
        
    msg = CCMessage.objects.create(
        sender=request.user,
        recipient=recipient,
        content=content
    )
    return Response(CCMessageSerializer(msg).data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cc_override_hps(request):
    """Allow clinician to manually override HPS score with audit trail."""
    member_id = request.data.get("member_id")
    new_value = request.data.get("new_value")
    reason_code = request.data.get("reason_code")
    reason_text = request.data.get("reason_text")
    
    try:
        member = User.objects.get(id=member_id)
    except User.DoesNotExist:
        return Response({"error": "Member not found"}, status=404)
        
    latest_score = HPSScore.objects.filter(user=member).order_by('-timestamp').first()
    old_value = latest_score.hps_final if latest_score else 0
    
    audit = CCOverrideAudit.objects.create(
        member=member,
        clinician=request.user,
        old_value=old_value,
        new_value=new_value,
        reason_code=reason_code,
        reason_text=reason_text,
        requires_dual_approval=False, # Stub
        approved=True
    )
    
    if latest_score:
        latest_score.hps_final = new_value
        latest_score.save()
        
    return Response(CCOverrideAuditSerializer(audit).data)

# ─── ANALYTICS ─────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def clinical_kpis(request):
    """Dynamic Clinical Performance Indicators."""
    # Note: These should compute real percentages from DB
    total_members = User.objects.filter(profile__role__name__icontains="Employee").count() or 100
    active_prescriptions = CCPrescription.objects.filter(status="active").count()
    protocol_compliance = round((active_prescriptions / total_members) * 100, 1)

    total_alerts = CCAlert.objects.count() or 1
    resolved_alerts = CCAlert.objects.filter(status__in=["resolved", "acknowledged"]).count()
    alert_resolution_rate = round((resolved_alerts / total_alerts) * 100, 1)

    return Response({
        "protocol_compliance_pct": protocol_compliance,
        "biomarker_improvement_pct": 68.5,
        "avg_hps_score": 712.4,
        "alert_resolution_rate": alert_resolution_rate,
        "lab_completion_rate": 84.0,
        "referral_completion_rate": 72.0,
        "total_encounters": EMREncounter.objects.count(),
        "telehealth_encounters": 0,
        "patient_satisfaction": 4.6,
        "total_members": total_members
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_role_metadata(request):
    """Returns labels, icons, and scopes for HCP dashboard."""
    user_role = _resolve_role(request.user)
    meta = ROLE_META.get(user_role, ROLE_META["longevity_physician"])
    
    return Response({
        "role": user_role,
        "role_label": meta["label"],
        "scope": meta["scope"],
        "primary_hps_dimensions": meta["primary_hps"],
        "icon": meta["icon"],
        "all_roles": {k: v["label"] for k, v in ROLE_META.items()}
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def role_intelligent_dashboard(request):
    """Specialized widgets for each HCP role."""
    user_role = _resolve_role(request.user)
    meta = ROLE_META.get(user_role, ROLE_META["longevity_physician"])
    
    widgets = []
    if user_role in ("longevity_physician", "clinician"):
        widgets = [
            {"type": "stat", "key": "critical_alerts", "label": "Critical Alerts", "value": CCAlert.objects.filter(status="open", severity="CRITICAL").count(), "color": "#EF4444", "icon": "AlertTriangle"},
            {"type": "stat", "key": "pending_labs", "label": "Pending Labs", "value": LabOrder.objects.filter(status="ordered").count(), "color": "#0F9F8F", "icon": "FlaskConical"},
            {"type": "panel", "key": "ai_priority_feed", "label": "AI Clinical Priority Feed"}
        ]
    elif user_role in ("fitness_coach", "coach"):
        widgets = [
            {"type": "stat", "key": "compliance", "label": "Compliance", "value": "78%", "color": "#10B981", "icon": "Users"},
            {"type": "panel", "key": "vo2max_tracker", "label": "VO2max Tracker"}
        ]
    # Add other roles as needed...

    return Response({
        "role": user_role,
        "role_label": meta["label"],
        "widgets": widgets,
        "total_members": CCAssignment.objects.filter(cc=request.user).count(),
        "open_alerts": CCAlert.objects.filter(cc=request.user, status="open").count()
    })

# ─── CDSS & AI ─────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cdss_analyze(request, member_id):
    """Rule-based CDSS analyze (AI Fallback)."""
    return Response({
        "risk_summary": "Simulated analysis based on legacy patterns.",
        "priority_actions": [],
        "protocol_recommendations": [],
        "generated_at": datetime.now(timezone.utc).isoformat()
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_bio_age(request, member_id):
    """Simulate bio-age calculator logic."""
    try:
        member = User.objects.get(id=member_id)
        chrono_age = getattr(member.profile, 'age', 40)
    except:
        chrono_age = 40
        
    return Response({
        "chronological_age": chrono_age,
        "biological_age": chrono_age - 2.5,
        "delta_years": -2.5,
        "direction": "younger"
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_member_hallmarks(request, member_id):
    """Hallmarks of Ageing scoring for a member."""
    if not _require_hcp(request.user):
        return Response({"error": "HCP access restricted"}, status=status.HTTP_403_FORBIDDEN)
        
    try:
        member = User.objects.get(id=member_id)
    except User.DoesNotExist:
        return Response({"error": "Member not found"}, status=404)

    # Hallmarks definitions (Same as Flask)
    HM_DEFS = {
        "genomic_instability": {"label": "Genomic Instability", "biomarkers": ["homocysteine"], "icon": "Dna"},
        "telomere_attrition": {"label": "Telomere Attrition", "biomarkers": [], "icon": "Timer"},
        "epigenetic_alterations": {"label": "Epigenetic Alterations", "biomarkers": ["vitamin_b12", "folate"], "icon": "Fingerprint"},
        "loss_proteostasis": {"label": "Loss of Proteostasis", "biomarkers": ["albumin", "total_protein"], "icon": "Shield"},
        "deregulated_sensing": {"label": "Deregulated Nutrient Sensing", "biomarkers": ["hba1c", "fasting_glucose", "fasting_insulin"], "icon": "Gauge"},
        "mitochondrial_dysfunction": {"label": "Mitochondrial Dysfunction", "biomarkers": ["ferritin", "iron"], "icon": "Zap"},
        "cellular_senescence": {"label": "Cellular Senescence", "biomarkers": ["hscrp", "il6"], "icon": "Clock"},
        "stem_cell_exhaustion": {"label": "Stem Cell Exhaustion", "biomarkers": ["wbc", "rbc"], "icon": "Sprout"},
        "intercellular_communication": {"label": "Altered Communication", "biomarkers": ["testosterone", "cortisol_am", "dhea_s"], "icon": "Network"},
        "chronic_inflammation": {"label": "Chronic Inflammation", "biomarkers": ["hscrp", "esr", "ferritin"], "icon": "Flame"},
    }

    bms = BiomarkerResult.objects.filter(user=member)
    bm_map = {b.biomarker_code: b for b in bms}

    results = {}
    for key, hm in HM_DEFS.items():
        scores = []
        for code in hm["biomarkers"]:
            bm = bm_map.get(code)
            # In Django project, use 'value' or some percentile logic if exists
            if bm:
                # Mocking percentile for now as it matches flask response pattern
                scores.append(random.randint(30, 90)) 
        
        avg_score = round(sum(scores) / len(scores), 1) if scores else None
        status_hm = "unknown"
        if avg_score is not None:
            status_hm = "optimal" if avg_score >= 60 else "suboptimal" if avg_score >= 30 else "at_risk"
            
        results[key] = {
            "label": hm["label"],
            "icon": hm["icon"],
            "score": avg_score,
            "status": status_hm,
            "biomarkers_available": len(scores),
            "biomarkers_total": len(hm["biomarkers"]),
        }

    scored = [v for v in results.values() if v["score"] is not None]
    overall = round(sum(v["score"] for v in scored) / max(len(scored), 1), 1) if scored else None

    return Response({
        "hallmarks": results, 
        "overall_score": overall, 
        "hallmarks_scored": len(scored), 
        "hallmarks_total": len(HM_DEFS)
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_protocol_recommendations(request, member_id):
    """Protocol Recommendation Engine — analyzes biomarkers and triggers."""
    if not _require_hcp(request.user):
        return Response({"error": "HCP access restricted"}, status=status.HTTP_403_FORBIDDEN)

    try:
        member = User.objects.get(id=member_id)
    except User.DoesNotExist:
        return Response({"error": "Member not found"}, status=404)

    # Simplified trigger logic for parity
    biomarkers = BiomarkerResult.objects.filter(user=member)
    at_risk = [b.biomarker_code for b in biomarkers if b.value and b.value > 6.0] # Mock threshold

    protocols = CCProtocol.objects.all()
    recommendations = []
    
    for p in protocols:
        risk_score = 0
        reasons = []
        
        # Mock logic matching Flask patterns
        if "HbA1c" in at_risk and p.category == "Metabolic":
            risk_score = 5
            reasons.append("Elevated HbA1c detected")
        elif "LDL" in at_risk and p.category == "Cardio":
            risk_score = 4
            reasons.append("Elevated LDL levels")
            
        if risk_score > 0:
            recommendations.append({
                "protocol_id": str(p.id),
                "name": p.name,
                "category": p.category,
                "risk_score": risk_score,
                "confidence": 0.85,
                "reasons": reasons,
                "already_prescribed": CCPrescription.objects.filter(member=member, protocol=p, status="active").exists()
            })

    recommendations.sort(key=lambda x: x["risk_score"], reverse=True)

    return Response({
        "member_id": member_id,
        "recommendations": recommendations[:10],
        "total_recommendations": len(recommendations),
        "generated_at": datetime.now(timezone.utc).isoformat()
    })

# ─── REVENUE & POPULATION ──────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def population_health(request):
    """Aggregate stats for CC panel."""
    avg_hps = HPSScore.objects.aggregate(Avg('hps_final'))['hps_final__avg'] or 700.0
    return Response({
        "total_members": User.objects.count(),
        "avg_hps": round(avg_hps, 1),
        "tier_distribution": {"OPTIMAL": 12, "AVERAGE": 45, "AT_RISK": 10},
        "pillar_averages": {"BR": 72, "PF": 65, "CA": 80, "SR": 60, "BL": 75}
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def revenue_analytics(request):
    """Service-wise revenue simulation."""
    return Response({
        "total_revenue_mtd": 12500,
        "streams": {
            "consultation": {"revenue": 4500, "pct": 36},
            "labs": {"revenue": 5500, "pct": 44},
            "pharmacy": {"revenue": 2500, "pct": 20}
        }
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cc_referrals(request):
    referrals = CCReferral.objects.all()
    return Response({"referrals": CCReferralSerializer(referrals, many=True).data})

# ─── AI PRIORITY FEED ──────────────────────────────────────────

# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def ai_priority_feed(request):
#     """Top-3 AI-curated actions for the current role."""
#     user = request.user
#     role = _resolve_role(user)
#     meta = ROLE_META.get(role, ROLE_META["longevity_physician"])
    
#     # 1. Escalations
#     escalations = Escalation.objects.filter(status="pending").order_by("-created_at")[:3]
#     # 2. Alerts
#     alerts = CCAlert.objects.filter(cc=user, status="open").order_by("-aps_score")[:3]
#     # 3. Tasks
#     tasks = NFLETask.objects.filter(assigned_roles__contains=role, status="open").order_by("-created_at")[:3]
    
#     actions = []
    
#     # Priority 1: Escalations
#     for e in escalations:
#         actions.append({
#             "type": "escalation",
#             "priority": "high",
#             "title": f"Escalation: {e.category.replace('_', ' ').title()}",
#             "detail": e.clinical_summary[:100],
#             "member_name": e.member_name,
#             "action": "Review",
#             "coach_name": e.coach_name
#         })
        
#     # Priority 2: High Severity Alerts
#     if len(actions) < 3:
#         for a in alerts:
#             actions.append({
#                 "type": "alert",
#                 "priority": "high",
#                 "title": f"Alert: {a.biomarker} ({a.severity})",
#                 "detail": a.ai_interpretation[:100],
#                 "member_name": a.member.username,
#                 "action": "Triage"
#             })
#             if len(actions) >= 3: break
            
#     # Priority 3: NFLE Tasks
#     if len(actions) < 3:
#         for t in tasks:
#             actions.append({
#                 "type": "nfle_task",
#                 "priority": t.priority,
#                 "title": t.task_description,
#                 "detail": f"Suggest: {t.protocol_suggestion}",
#                 "member_name": t.member.username if t.member else "Unknown",
#                 "action": "Assign"
#             })
#             if len(actions) >= 3: break

#     # Fallback
#     if not actions:
#         actions.append({
#             "type": "info",
#             "priority": "low",
#             "title": "All caught up!",
#             "detail": "No urgent actions detected for your role.",
#             "member_name": "",
#             "action": "Review Population"
#         })

#     return Response({
#         "role": role,
#         "role_label": meta["label"],
#         "actions": actions[:3],
#         "generated_at": datetime.now(timezone.utc).isoformat()
#     })



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ai_priority_feed(request):
    """Top-3 AI-curated actions for the current role."""
    
    user = request.user
    role = _resolve_role(user)
    meta = ROLE_META.get(role, ROLE_META["longevity_physician"])
    
    actions = []

    # -----------------------------
    # 1. Escalations (Priority 1)
    # -----------------------------
    escalations = Escalation.objects.filter(
        status="pending"
    ).order_by("-created_at")[:3]

    for e in escalations:
        actions.append({
            "type": "escalation",
            "priority": "high",
            "title": f"Escalation: {e.category.replace('_', ' ').title()}",
            "detail": (e.clinical_summary or "")[:100],
            "member_name": e.member_name,
            "action": "Review",
            "coach_name": e.coach_name
        })

    # -----------------------------
    # 2. Alerts (Priority 2)
    # -----------------------------
    if len(actions) < 3:
        alerts = CCAlert.objects.filter(
            cc=user,
            status="open"
        ).order_by("-aps_score")[:3]

        for a in alerts:
            actions.append({
                "type": "alert",
                "priority": "high",
                "title": f"Alert: {a.biomarker} ({a.severity})",
                "detail": (a.ai_interpretation or "")[:100],
                "member_name": a.member.username if a.member else "Unknown",
                "action": "Triage"
            })
            if len(actions) >= 3:
                break

    # -----------------------------
    # 3. NFLE Tasks (Priority 3)
    # FIX: Removed JSON __contains
    # -----------------------------
    if len(actions) < 3:
        tasks_qs = NFLETask.objects.filter(
            status="open"
        ).order_by("-created_at")

        filtered_tasks = []

        for t in tasks_qs:
            roles = t.assigned_roles or []

            # Handle both JSON list and string fallback safely
            if isinstance(roles, list) and role in roles:
                filtered_tasks.append(t)
            elif isinstance(roles, str) and role in roles:
                filtered_tasks.append(t)

            if len(filtered_tasks) >= 3:
                break

        for t in filtered_tasks:
            actions.append({
                "type": "nfle_task",
                "priority": t.priority,
                "title": t.task_description,
                "detail": f"Suggest: {t.protocol_suggestion}",
                "member_name": t.member.username if t.member else "Unknown",
                "action": "Assign"
            })
            if len(actions) >= 3:
                break

    # -----------------------------
    # 4. Fallback
    # -----------------------------
    if not actions:
        actions.append({
            "type": "info",
            "priority": "low",
            "title": "All caught up!",
            "detail": "No urgent actions detected for your role.",
            "member_name": "",
            "action": "Review Population"
        })

    # -----------------------------
    # Response
    # -----------------------------
    return Response({
        "role": role,
        "role_label": meta["label"],
        "actions": actions[:3],
        "generated_at": datetime.now(timezone.utc).isoformat()
    })