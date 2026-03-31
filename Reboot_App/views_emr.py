from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
import uuid

# Import Models & Serializers
from .models import EMREncounter, MemberMedicalHistory, Appointment, User
from .serializers import EMREncounterSerializer, MemberMedicalHistorySerializer, AppointmentSerializer


# -------------------------------------------------------------------------
# MEDICAL HISTORY ENPOINTS
# -------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_medical_history(request, member_id=None):
    if member_id:
        target_user = get_object_or_404(User, id=member_id)
        # Authorisation logic could go here
    else:
        target_user = request.user
        
    history, created = MemberMedicalHistory.objects.get_or_create(member=target_user)
    return Response(MemberMedicalHistorySerializer(history).data)


@api_view(['POST', 'PUT'])
@permission_classes([IsAuthenticated])
def update_medical_history(request, member_id=None):
    if member_id:
        target_user = get_object_or_404(User, id=member_id)
    else:
        target_user = request.user

    history, created = MemberMedicalHistory.objects.get_or_create(member=target_user)
    
    # Update fields
    if "conditions" in request.data:
        history.conditions = request.data["conditions"]
    if "family_history" in request.data:
        history.family_history = request.data["family_history"]
    if "surgical_history" in request.data:
        history.surgical_history = request.data["surgical_history"]
    if "allergies" in request.data:
        history.allergies = request.data["allergies"]
        
    history.save()
    return Response(MemberMedicalHistorySerializer(history).data)


# -------------------------------------------------------------------------
# CONSULTATION / EMR ENCOUNTER ENDPOINTS
# -------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_emr_encounter(request):
    member_id = request.data.get("member_id")
    encounter_type = request.data.get("encounter_type", "office_visit")
    
    member = get_object_or_404(User, id=member_id)
    
    encounter = EMREncounter.objects.create(
        member=member,
        hcp=request.user,  # assuming HCP is the one calling this
        encounter_type=encounter_type,
        chief_complaint=request.data.get("chief_complaint", ""),
        subjective=request.data.get("subjective", ""),
        objective=request.data.get("objective", ""),
        assessment=request.data.get("assessment", ""),
        plan=request.data.get("plan", ""),
        diagnosis_codes=request.data.get("diagnosis_codes", []),
        vitals=request.data.get("vitals", {})
    )
    
    return Response(EMREncounterSerializer(encounter).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_member_encounters(request, member_id):
    encounters = EMREncounter.objects.filter(member__id=member_id).order_by('-created_at')
    return Response({
        "encounters": EMREncounterSerializer(encounters, many=True).data,
        "count": encounters.count()
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_encounter_detail(request, encounter_id):
    encounter = get_object_or_404(EMREncounter, id=encounter_id)
    return Response(EMREncounterSerializer(encounter).data)


# -------------------------------------------------------------------------
# APPOINTMENTS
# -------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_appointments(request):
    """Get appointments for the currently logged in user (patient POV)"""
    apts = Appointment.objects.filter(member=request.user).order_by('scheduled_at')[:50]
    return Response(AppointmentSerializer(apts, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_hcp_appointments(request):
    """Get appointments assigned to the logged-in HCP (doctor POV)"""
    # Assuming standard roles mechanism logic ensures only valid roles use this
    apts = Appointment.objects.filter(assigned_hcp=request.user).order_by('scheduled_at')[:50]
    return Response(AppointmentSerializer(apts, many=True).data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_appointment_status(request, pt_id):
    apt = get_object_or_404(Appointment, id=pt_id)
    new_status = request.data.get("status")
    if new_status:
        apt.status = new_status
        apt.save()
    return Response(AppointmentSerializer(apt).data)
