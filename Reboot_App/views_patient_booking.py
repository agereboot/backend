
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta
import uuid
import random

from .models import SampleBooking, User, Notification, LabOrder
from .serializers import SampleBookingSerializer

AVAILABLE_SLOTS = [
    {"label": "7:00 - 9:00 AM", "code": "07-09", "fasting_friendly": True},
    {"label": "9:00 - 11:00 AM", "code": "09-11", "fasting_friendly": True},
    {"label": "11:00 AM - 1:00 PM", "code": "11-13", "fasting_friendly": False},
    {"label": "2:00 - 4:00 PM", "code": "14-16", "fasting_friendly": False},
    {"label": "4:00 - 6:00 PM", "code": "16-18", "fasting_friendly": False},
]

SAMPLE_STATUSES = [
    "booking_confirmed", "phlebotomist_assigned", "phlebotomist_en_route",
    "phlebotomist_arrived", "sample_collected", "sample_dispatched",
    "sample_received_at_lab", "sample_under_analysis", "report_ready"
]

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_booking_slots(request):
    """Get available time slots for the next 5 days."""
    slots = []
    base = timezone.now()
    for day_offset in range(1, 6):
        day = base + timedelta(days=day_offset)
        day_str = day.strftime("%Y-%m-%d")
        day_label = day.strftime("%A, %b %d")
        day_slots = []
        for slot in AVAILABLE_SLOTS:
            available = random.random() > 0.2
            day_slots.append({**slot, "available": available})
        slots.append({"date": day_str, "label": day_label, "slots": day_slots})
    return Response({"available_dates": slots})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_bookings(request):
    """Get all sample collection bookings for the current patient."""
    bookings = SampleBooking.objects.filter(patient=request.user).order_by('-created_at')
    return Response({"bookings": SampleBookingSerializer(bookings, many=True).data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def book_sample_collection(request):
    """Book a home sample collection appointment."""
    data = request.data
    user_profile = request.user.profile if hasattr(request.user, 'profile') else None
    
    # Simple address parsing for parity
    booking = SampleBooking.objects.create(
        patient=request.user,
        # lab_order assigned if lab_order_id provided
        preferred_date=data.get("preferred_date", timezone.now().date()),
        preferred_slot=data.get("preferred_slot", "07-09"),
        address_line=data.get("address_line", ""), # Simplified for model
        city=data.get("city", ""),
        pincode=data.get("pin_code", ""),
        fasting_confirmed=data.get("fasting_confirmed", False),
        special_instructions=data.get("special_instructions", ""),
        status="booking_confirmed"
    )

    Notification.objects.create(
        user=request.user,
        type="sample_booking",
        message=f"Home sample collection booked for {booking.preferred_date} ({booking.preferred_slot})",
    )

    return Response({"booking": SampleBookingSerializer(booking).data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pending_order_info(request):
    """Get post-consultation info showing pending lab orders for booking."""
    pending_orders = LabOrder.objects.filter(
        patient=request.user, 
        status__in=["ordered", "pending"]
    ).order_by('-ordered_at')[:10]

    active_bookings = SampleBooking.objects.filter(
        patient=request.user
    ).exclude(status__in=["report_ready", "cancelled"])[:10]

    return Response({
        "pending_lab_orders": [], # Will populate once LabOrder model usage is confirmed
        "active_bookings": SampleBookingSerializer(active_bookings, many=True).data,
        "has_pending_orders": pending_orders.exists(),
    })
