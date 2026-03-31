from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import uuid

from .models import CCAssignment, CCSession

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_coach_assignments(request):
    """Get the coach's assigned members. Utilises the CC tables since coach is a variation of CC"""
    assignments = CCAssignment.objects.filter(care_coordinator=request.user, is_active=True)
    return Response({
        "assignments": [
            {
                "member_id": a.member.id,
                "name": a.member.get_full_name(),
                "risk_level": a.risk_level,
                "since": a.created_at
            } for a in assignments
        ]
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_coach_session(request):
    from .views_cc import log_cc_session
    return log_cc_session(request._request)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_workout_plan(request):
    """
    Generate a workout plan using AI or predefined templates based on user profile
    """
    # In the Flask app, this would use `emergentintegrations` LLM with user details.
    import random
    
    plan = {
        "goal": request.data.get("goal", "general_fitness"),
        "level": request.data.get("level", "intermediate"),
        "weekly_schedule": {
            "monday": ["Warmup 10m", "Squats 3x12", "Bench Press 3x10", "Cooldown 5m"],
            "wednesday": ["Warmup 10m", "Deadlift 3x8", "Pullups 3x8", "Rowing 10m"],
            "friday": ["Light jogging 20m", "Core circuit 15m"]
        },
        "notes": "Ensure 8 hours of sleep. Stay hydrated."
    }
    
    return Response(plan, status=status.HTTP_200_OK)
