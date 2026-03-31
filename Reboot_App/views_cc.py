from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.shortcuts import get_object_or_404
import uuid

# Import Models & Serializers
from .models import CCAssignment, CCAlert, CCSession, CCProtocol, User
from .serializers import CCAssignmentSerializer, CCAlertSerializer, CCSessionSerializer, CCProtocolSerializer

# -------------------------------------------------------------------------
# CARE COORDINATION - ASSIGNMENTS
# -------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cc_roster(request):
    """Get the roster of members assigned to the Care Coordinator"""
    assignments = CCAssignment.objects.filter(care_coordinator=request.user, is_active=True).select_related('member')
    return Response(CCAssignmentSerializer(assignments, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_member_to_cc(request):
    member_id = request.data.get("member_id")
    cc_id = request.data.get("coordinator_id")
    
    member = get_object_or_404(User, id=member_id)
    coordinator = get_object_or_404(User, id=cc_id)
    
    assignment, created = CCAssignment.objects.update_or_create(
        member=member,
        defaults={
            'care_coordinator': coordinator,
            'is_active': True,
            'risk_level': request.data.get("risk_level", "low")
        }
    )
    
    return Response(CCAssignmentSerializer(assignment).data)


# -------------------------------------------------------------------------
# CARE COORDINATION - ALERTS
# -------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cc_alerts(request):
    """Get unresolved alerts for a Care Coordinator"""
    alerts = CCAlert.objects.filter(
        member__cc_assignments__care_coordinator=request.user, 
        member__cc_assignments__is_active=True,
        is_resolved=False
    ).order_by('-created_at')
    
    return Response(CCAlertSerializer(alerts, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_cc_alert(request):
    """Create an alert for a specific member"""
    member_id = request.data.get("member_id")
    alert_type = request.data.get("alert_type")
    description = request.data.get("description", "")
    severity = request.data.get("severity", "medium")
    
    member = get_object_or_404(User, id=member_id)
    
    alert = CCAlert.objects.create(
        member=member,
        alert_type=alert_type,
        description=description,
        severity=severity,
        is_resolved=False
    )
    
    # In a full app, notify the Care Coordinator assigned to this member via Channels or Email
    
    return Response(CCAlertSerializer(alert).data, status=status.HTTP_201_CREATED)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def resolve_cc_alert(request, alert_id):
    alert = get_object_or_404(CCAlert, id=alert_id)
    alert.is_resolved = True
    alert.resolved_at = timezone.now()
    alert.resolved_by = request.user
    alert.resolution_note = request.data.get("resolution_note", "")
    alert.save()
    
    return Response(CCAlertSerializer(alert).data)


# -------------------------------------------------------------------------
# CARE COORDINATION - PROTOCOLS
# -------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cc_protocols(request, protocol_id=None):
    if protocol_id:
        protocol = get_object_or_404(CCProtocol, id=protocol_id)
        return Response(CCProtocolSerializer(protocol).data)
    
    protocols = CCProtocol.objects.all()
    return Response(CCProtocolSerializer(protocols, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_cc_protocol(request):
    protocol = CCProtocol.objects.create(
        name=request.data.get("name"),
        description=request.data.get("description", ""),
        trigger_conditions=request.data.get("trigger_conditions", {}),
        action_steps=request.data.get("action_steps", [])
    )
    return Response(CCProtocolSerializer(protocol).data, status=status.HTTP_201_CREATED)

# -------------------------------------------------------------------------
# CARE COORDINATION - SESSIONS
# -------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_member_cc_sessions(request, member_id):
    sessions = CCSession.objects.filter(member__id=member_id).order_by('-session_date')
    return Response(CCSessionSerializer(sessions, many=True).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_cc_session(request):
    member_id = request.data.get("member_id")
    member = get_object_or_404(User, id=member_id)
    
    session = CCSession.objects.create(
        care_coordinator=request.user,
        member=member,
        session_type=request.data.get("session_type", "check_in"),
        notes=request.data.get("notes", ""),
        action_items=request.data.get("action_items", []),
        duration_minutes=request.data.get("duration_minutes", 15)
    )
    
    return Response(CCSessionSerializer(session).data, status=status.HTTP_201_CREATED)
