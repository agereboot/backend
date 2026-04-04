from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
import uuid
import random
import logging

from .models import LongevityProtocol, User, Notification, VideoConsultation, LabOrder
from .serializers import LongevityProtocolSerializer

logger = logging.getLogger(__name__)

CLINICIAN_ROLES = {"longevity_physician", "fitness_coach", "psychologist", "nutritional_coach",
                   "clinician", "coach", "physical_therapist", "nurse_navigator", "super_admin"}

def _generate_protocol_fallback(hps_score, user):
    """Rule-based fallback protocol generation (Parity with Legacy)."""
    return {
        "three_month_plan": [
            {"category": "Supplements", "action": "Start Vitamin D3 4000 IU daily", "priority": "high"},
            {"category": "Exercise", "action": "Zone 2 cardio 150 min/week", "priority": "high"}
        ],
        "six_month_plan": [
            {"category": "Optimization", "action": "Fine-tune supplement stack", "priority": "medium"}
        ],
        "nine_month_plan": [
            {"category": "Prevention", "action": "Comprehensive repeat blood panel", "priority": "high"}
        ],
        "daily_challenges": [
            {"title": "Walk 8,000 steps today", "type": "movement"},
            {"title": "No screens after 10 PM", "type": "sleep"}
        ],
        "weekly_goals": [
            {"title": "Exercise 3 times this week", "target": "3 sessions", "metric": "exercise_frequency"}
        ],
        "ai_generated": False,
    }

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_longevity_protocol(request, patient_id):
    """Generate longevity protocol (AI or fallback) (Parity with Legacy)."""
    try:
        patient = User.objects.get(id=patient_id)
    except User.DoesNotExist:
        return Response({"error": "Patient not found"}, status=404)

    # Simplified generation for parity
    plans = _generate_protocol_fallback(600, patient)

    protocol = LongevityProtocol.objects.create(
        patient=patient,
        patient_name=f"{patient.first_name} {patient.last_name}" if patient.first_name else patient.username,
        generated_by=request.user,
        generated_by_name=f"{request.user.first_name} {request.user.last_name}" if request.user.first_name else request.user.username,
        hps_at_generation=600, # Placeholder
        status="pending_review",
        three_month_plan=plans["three_month_plan"],
        six_month_plan=plans["six_month_plan"],
        nine_month_plan=plans["nine_month_plan"],
    )

    return Response({"protocol": LongevityProtocolSerializer(protocol).data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_active_protocol(request):
    """Get current patient's active/approved longevity protocol (Parity with Legacy)."""
    protocol = LongevityProtocol.objects.filter(
        patient=request.user, 
        status="approved"
    ).order_by('-created_at').first()
    
    if not protocol:
        protocol = LongevityProtocol.objects.filter(patient=request.user).order_by('-created_at').first()
        
    return Response({"protocol": LongevityProtocolSerializer(protocol).data if protocol else None})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_ninety_day_cycle(request):
    """Check if user is due for 90-day follow-up cycle (Parity with Legacy)."""
    last_protocol = LongevityProtocol.objects.filter(
        patient=request.user, 
        status="approved"
    ).order_by('-created_at').first()
    
    if not last_protocol:
        return Response({"due": False, "message": "No active protocol found"})

    days_elapsed = (timezone.now() - last_protocol.created_at).days
    due = days_elapsed >= 90
    
    return Response({
        "due": due,
        "days_elapsed": days_elapsed,
        "days_remaining": max(0, 90 - days_elapsed),
        "message": "Your 90-day review is due." if due else f"{90 - days_elapsed} days until review.",
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_post_call_actions(request, consultation_id):
    """Generate Dynamic CTA actions after a consultation (Parity with Legacy)."""
    # Matches the legacy list exactly for frontend parity
    actions = [
        {
            "type": "diagnostic_requisition",
            "label": "Book Lab Test",
            "description": "Your doctor ordered diagnostic tests.",
            "route": "/book-lab-test",
            "priority": "high",
            "icon": "flask",
        },
        {
            "type": "follow_up",
            "label": "Schedule Follow-Up",
            "description": "Book your next consultation.",
            "route": "/video-consultation",
            "priority": "medium",
            "icon": "calendar",
        },
        {
            "type": "chat_doctor",
            "label": "Message Your Doctor",
            "description": "Have follow-up questions?",
            "route": "/chat",
            "priority": "low",
            "icon": "message",
        }
    ]
    return Response({"actions": actions, "consultation_id": consultation_id})
