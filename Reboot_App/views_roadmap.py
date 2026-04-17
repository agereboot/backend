from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import datetime
import uuid

from .models import Roadmap, RoadmapReview, HPSScore, User, CCAssignment, Notification, LongevityProtocol
from .serializers import RoadmapSerializer, RoadmapReviewSerializer

CARE_TEAM_ROLES = {
    "longevity_physician", "clinician", "fitness_coach", "coach",
    "psychologist", "nutritional_coach", "physical_therapist", "nurse_navigator", "super_admin"
}

def _generate_ai_roadmap_fallback(score_data, user):
    """Rule-based roadmap generation fallback matching legacy hps_engine/roadmap.py."""
    hps = score_data.get('hps_final', 0)
    
    # Matching legacy _generate_fallback_roadmap structure
    gaps = [
        {"pillar_code": "BR", "pillar_name": "Metabolic Health", "gap_score": 15.5, "icon": "heart-pulse", "color": "#EF4444"},
        {"pillar_code": "PF", "pillar_name": "Physical Fitness", "gap_score": 12.0, "icon": "dumbbell", "color": "#0F9F8F"}
    ]
    
    protocols = [
        {"domain": "Metabolic Health", "protocol": "Mediterranean Diet", "evidence": "Grade A", "priority_pillar": "Metabolic Health"}
    ]
    
    interventions = {
        "BR": [{"id": "br-vitd", "intervention": "Vitamin D3 + K2 Supplementation", "priority": "must_do", "credits": 25}],
        "PF": [{"id": "pf-zone2", "intervention": "Zone 2 Cardio Protocol", "priority": "must_do", "credits": 0}]
    }
    
    biological_age = {
        "current_biological_age": 32.5,
        "current_chronological_age": 35.0,
        "projected_biological_age_12m": 30.2,
        "projected_hps_12m": hps + 80,
        "trajectory": [] # Simplified for parity
    }

    phases = [
        {"phase": "Phase 1 — Foundation", "timeline": "Days 1-90", "objective": "Stabilization", "actions": ["Sleep hygiene", "Cardio"]},
        {"phase": "Phase 2 — Performance", "timeline": "Days 91-180", "objective": "Optimization", "actions": ["Resistance training"]}
    ]

    return {
        "ai_narrative": f"Based on your HPS of {hps}, focus on foundation building and metabolic recovery.",
        "gaps": gaps,
        "protocols": protocols,
        "interventions": interventions,
        "biological_age": biological_age,
        "phases": phases,
        "generated": False, # Fallback is False
        "hps_at_generation": hps,
    }

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_roadmap(request):
    """Player generates their AI-powered longevity roadmap."""
    user = request.user
    score = HPSScore.objects.filter(user=user).order_by("-timestamp").first()
    if not score:
        return Response({"error": "Compute HPS first before generating roadmap"}, status=400)

    roadmap_data = _generate_ai_roadmap_fallback({"hps_final": score.hps_final}, user)

    roadmap = Roadmap.objects.create(
        user=user,
        **roadmap_data
    )
    
    return Response(RoadmapSerializer(roadmap).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_roadmap(request, user_id=None):
    """Get latest roadmap for a user, including approved longevity protocols (Parity)."""
    uid = user_id or request.user.id
    
    # Resolve user if uid is a string (e.g., "25" or "member_04")
    target_user = None
    if isinstance(uid, str):
        # Case 1: uid is an integer string
        if uid.isdigit():
            target_user = User.objects.filter(id=int(uid)).first()
        # Case 2: uid is a username
        if not target_user:
            target_user = User.objects.filter(username=uid).first()
        # Case 3: uid is a UUID string (original intent)
        if not target_user:
            try:
                target_user = User.objects.filter(id=uid).first()
            except Exception:
                pass
    else:
        target_user = User.objects.filter(id=uid).first()

    if not target_user:
        return Response({"error": "User not found"}, status=404)

    roadmap = Roadmap.objects.filter(user=target_user).order_by("-created_at").first()
    
    # Include approved longevity protocols (parity check)
    approved_protocols = LongevityProtocol.objects.filter(
        patient=target_user, 
        status__in=["approved", "active"]
    ).order_by("-created_at")
    
    # Matching legacy response structure
    from .serializers import LongevityProtocolSerializer
    
    res = RoadmapSerializer(roadmap).data if roadmap else {}
    res["approved_protocols"] = LongevityProtocolSerializer(approved_protocols, many=True).data
    
    if not roadmap and not approved_protocols.exists():
        return Response({"roadmap": None, "approved_protocols": [], "message": "No roadmap generated yet"})
        
    return Response(res)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_roadmap_for_review(request):
    """Player submits their roadmap for care team validation."""
    roadmap_id = request.data.get("roadmap_id")
    if not roadmap_id:
        return Response({"error": "roadmap_id is required"}, status=400)

    try:
        roadmap = Roadmap.objects.get(id=roadmap_id, user=request.user)
    except Roadmap.DoesNotExist:
        return Response({"error": "Roadmap not found"}, status=404)

    # Simplified status tracking in Roadmap model or separate Review model
    # The reference project uses a separate 'roadmap_reviews' collection
    
    review = RoadmapReview.objects.create(
        roadmap=roadmap,
        hps_at_review=roadmap.hps_at_generation,
        notes="Review request submitted by player."
    )

    # Notify care team
    assignments = CCAssignment.objects.filter(member=request.user)
    for asn in assignments:
        Notification.objects.create(
            user=asn.cc,
            type="roadmap_review",
            message=f"{request.user.username} has submitted a roadmap for review.",
        )

    return Response({
        "status": "submitted",
        "review_id": str(review.id),
        "message": "Your roadmap has been submitted for care team review."
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def get_pending_reviews(request):
    """Care team views all pending roadmap reviews assigned to them."""
    # Custom role check if necessary
    user = request.user
    
    member_ids = CCAssignment.objects.filter(cc=user).values_list('member_id', flat=True)
    
    # Roadmaps with reviews that don't have a reviewer yet or are pending logically
    reviews = RoadmapReview.objects.filter(
        roadmap__user_id__in=member_ids,
        reviewer__isnull=True
    ).order_by("-reviewed_at")

    return Response({
        "reviews": RoadmapReviewSerializer(reviews, many=True).data,
        "total": reviews.count()
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_reviews(request):
    """View all roadmap reviews for assigned members."""
    member_ids = CCAssignment.objects.filter(cc=request.user).values_list('member_id', flat=True)
    reviews = RoadmapReview.objects.filter(roadmap__user_id__in=member_ids).order_by("-reviewed_at")
    
    return Response({
        "reviews": RoadmapReviewSerializer(reviews, many=True).data,
        "total": reviews.count()
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_roadmap(request, review_id):
    """Care team approves a roadmap."""
    try:
        review = RoadmapReview.objects.get(id=review_id)
    except RoadmapReview.DoesNotExist:
        return Response({"error": "Review not found"}, status=404)

    review.reviewer = request.user
    review.notes = request.data.get("notes", "")
    review.reviewed_at = timezone.now()
    review.save()

    roadmap = review.roadmap
    roadmap.status = "active"
    roadmap.save()

    # Notify the player
    Notification.objects.create(
        user=roadmap.user,
        type="roadmap_approved",
        message=f"Your longevity roadmap has been approved by {request.user.username}.",
    )

    return Response({
        "status": "approved",
        "review_id": review_id,
        "message": "Roadmap approved and now active."
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_roadmap(request, review_id):
    """Care team rejects a roadmap."""
    try:
        review = RoadmapReview.objects.get(id=review_id)
    except RoadmapReview.DoesNotExist:
        return Response({"error": "Review not found"}, status=404)

    review.reviewer = request.user
    review.notes = request.data.get("clinical_notes", "")
    review.reviewed_at = timezone.now()
    review.save()

    # Notify the player
    Notification.objects.create(
        user=review.roadmap.user,
        type="roadmap_rejected",
        message=f"Your roadmap needs revision. Reason: {review.notes}",
    )

    return Response({
        "status": "rejected",
        "review_id": review_id,
        "message": "Roadmap rejected. Player notified."
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_review_history(request, user_id):
    """Get review history for a specific player."""
    reviews = RoadmapReview.objects.filter(roadmap__user_id=user_id).order_by("-reviewed_at")
    return Response({
        "reviews": RoadmapReviewSerializer(reviews, many=True).data,
        "total": reviews.count()
    })
