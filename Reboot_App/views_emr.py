from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.db.models import Q
import uuid

from .models import (
    EMREncounter, MemberMedicalHistory, Appointment, User,
    MedicalCondition, Medication, EMRAllergy, LabOrder, DiagnosticOrder,
    LabPanel, LabPartner, HPSScore, CCProtocol, CarePlan, LongevityProtocol,
    VitalsLog, Roadmap, AuditLog, HCPProfile,
    PharmacyOrder, PharmacyOrderItem, CCPrescription, CCReferral,
    DiagnosticCatalog, BiomarkerResult, PharmacyCatalogItem
)
from django.db import transaction
from .serializers import (
    EMREncounterSerializer, MemberMedicalHistorySerializer, AppointmentSerializer,
    MedicalConditionSerializer, MedicationSerializer, EMRAllergySerializer,
    LabOrderSerializer, DiagnosticOrderSerializer, LabPanelSerializer,
    HPSScoreSerializer, CCProtocolSerializer, CarePlanSerializer,
    VitalsLogSerializer
)
from rest_framework.parsers import MultiPartParser, FormParser


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
        "total": encounters.count()
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_encounter_detail(request, encounter_id):
    encounter = get_object_or_404(EMREncounter, id=encounter_id)
    return Response(EMREncounterSerializer(encounter).data)


# -------------------------------------------------------------------------
# PATIENT CHART (Aggregated)
# -------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_patient_chart(request, member_id):
    """Full patient chart: encounters, problems, medications, allergies."""
    member = get_object_or_404(User, id=member_id)
    
    encounters = EMREncounter.objects.filter(member=member).order_by('-created_at')[:20]
    problems = MedicalCondition.objects.filter(user=member).order_by('-diagnosed_date')
    medications = Medication.objects.filter(member=member).order_by('-created_at')
    allergies = EMRAllergy.objects.filter(member=member).order_by('-created_at')

    vitals_latest = VitalsLog.objects.filter(member=member).order_by('-recorded_at').first()

    return Response({
        "member": {
            "id": member.id,
            "username": member.username,
            "email": member.email,
            "first_name": member.first_name,
            "last_name": member.last_name,
            "role": member.profile.role.name if member.profile.role else "user"
        },
        "encounters": EMREncounterSerializer(encounters, many=True).data,
        "problems": MedicalConditionSerializer(problems, many=True).data,
        "medications": MedicationSerializer(medications, many=True).data,
        "allergies": EMRAllergySerializer(allergies, many=True).data,
        "vitals_latest": VitalsLogSerializer(vitals_latest).data if vitals_latest else {},
        "encounter_count": encounters.count(),
        "active_problems": problems.filter(status="active").count(),
        "active_medications": medications.filter(status="active").count(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_problem(request, member_id):
    member = get_object_or_404(User, id=member_id)
    problem = MedicalCondition.objects.create(
        user=member,
        name=request.data.get("name"),
        code=request.data.get("code"),
        icd10=request.data.get("icd10"),
        severity=request.data.get("severity", "moderate"),
        status="active",
        diagnosed_date=request.data.get("onset_date") or timezone.now().date()
    )
    return Response(MedicalConditionSerializer(problem).data, status=status.HTTP_201_CREATED)

@api_view(['PUT', 'POST'])
@permission_classes([IsAuthenticated])
def update_problem(request, member_id, problem_id):
    problem = get_object_or_404(MedicalCondition, id=problem_id, user__id=member_id)
    if "name" in request.data:
        problem.name = request.data["name"]
    if "status" in request.data:
        problem.status = request.data["status"]
    if "severity" in request.data:
        problem.severity = request.data["severity"]
    if "notes" in request.data:
        problem.notes = request.data["notes"]
    problem.save()
    return Response(MedicalConditionSerializer(problem).data)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_problem(request, member_id, problem_id):
    problem = get_object_or_404(MedicalCondition, id=problem_id, user__id=member_id)
    problem.delete()
    return Response({"status": "deleted", "id": problem_id}, status=204)


# -------------------------------------------------------------------------
# MEDICATION MANAGEMENT
# -------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_medication(request, member_id):
    member = get_object_or_404(User, id=member_id)
    medication = Medication.objects.create(
        member=member,
        medication_name=request.data.get("medication_name"),
        dosage=request.data.get("dosage"),
        frequency=request.data.get("frequency"),
        route=request.data.get("route", "oral"),
        status="active"
    )
    return Response(MedicationSerializer(medication).data, status=status.HTTP_201_CREATED)


# -------------------------------------------------------------------------
# ALLERGY TRACKING
# -------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_allergy(request, member_id):
    member = get_object_or_404(User, id=member_id)
    allergy = EMRAllergy.objects.create(
        member=member,
        allergen=request.data.get("allergen"),
        reaction=request.data.get("reaction"),
        severity=request.data.get("severity", "mild"),
        status="active"
    )
    return Response(EMRAllergySerializer(allergy).data, status=status.HTTP_201_CREATED)


# -------------------------------------------------------------------------
# LAB ORDERS
# -------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_lab_order(request, member_id):
    member = get_object_or_404(User, id=member_id)
    panel_codes = request.data.get("panels", [])
    panels = LabPanel.objects.filter(panel_id__in=panel_codes)
    
    order = LabOrder.objects.create(
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        member=member,
        ordered_by=request.user,
        partner=LabPartner.objects.filter(is_active=True).first(),
        status="pending"
    )
    order.panels.set(panels)
    
    return Response(LabOrderSerializer(order).data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_lab_order_detail(request, order_id):
    order = get_object_or_404(LabOrder, id=order_id)
    return Response(LabOrderSerializer(order).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_lab_orders(request):
    """List lab orders. If member_id provided in query params, filter by member."""
    member_id = request.query_params.get("member_id")
    if member_id:
        orders = LabOrder.objects.filter(member__id=member_id)
    elif request.user.profile.role.name in ["employee", "user"]:
        orders = LabOrder.objects.filter(member=request.user)
    else:
        orders = LabOrder.objects.all()
    
    return Response(LabOrderSerializer(orders.order_by('-ordered_at')[:50], many=True).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_lab_panels(request):
    panels = LabPanel.objects.all()
    return Response({"panels": LabPanelSerializer(panels, many=True).data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_lab_order_status(request, order_id):
    order = get_object_or_404(LabOrder, id=order_id)
    order.status = request.data.get("status", order.status)
    order.save()
    return Response(LabOrderSerializer(order).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_lab_results(request, order_id):
    order = get_object_or_404(LabOrder, id=order_id)
    # assuming results is a JSON field in LabOrder model
    order.results = request.data.get("results", [])
    order.status = "resulted"
    order.resulted_at = timezone.now()
    order.save()
    return Response(LabOrderSerializer(order).data)


# -------------------------------------------------------------------------
# DIAGNOSTICS
# -------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_diagnostic_order(request):
    member_id = request.data.get("member_id")
    member = get_object_or_404(User, id=member_id)
    
    diag = DiagnosticOrder.objects.create(
        member=member,
        ordered_by=request.user,
        test_name=request.data.get("test_name"),
        category=request.data.get("category", "Radiology"),
        urgency=request.data.get("urgency", "routine"),
        reason=request.data.get("reason", "")
    )
    return Response(DiagnosticOrderSerializer(diag).data, status=status.HTTP_201_CREATED)

# -------------------------------------------------------------------------
# E-PRESCRIBE
# -------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_prescription(request):
    member_id = request.data.get("member_id")
    member = get_object_or_404(User, id=member_id)
    
    rx = Medication.objects.create(
        member=member,
        # prescribed_by=request.user, # If model supports it
        medication_name=request.data.get("medication_name"),
        dosage=request.data.get("dosage"),
        frequency=request.data.get("frequency"),
        route=request.data.get("route", "oral"),
        duration_days=request.data.get("duration", 90),
        status="active"
    )
    return Response(MedicationSerializer(rx).data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_prescriptions(request):
    member_id = request.query_params.get("member_id")
    if member_id:
        rx = Medication.objects.filter(member__id=member_id)
    else:
        rx = Medication.objects.all()
    return Response({"prescriptions": MedicationSerializer(rx.order_by('-created_at')[:50], many=True).data})

@api_view(['PUT', 'POST'])
@permission_classes([IsAuthenticated])
def update_prescription(request, rx_id):
    rx = get_object_or_404(Medication, id=rx_id)
    rx.status = request.data.get("status", rx.status)
    rx.save()
    return Response(MedicationSerializer(rx).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refill_prescription(request, rx_id):
    rx = get_object_or_404(Medication, id=rx_id)
    return Response({"status": "refill_requested", "medication": rx.medication_name})


# -------------------------------------------------------------------------
# APPOINTMENTS
# -------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_appointments(request):
    """
    GET /api/emr/appointments
    Lists appointments for the clinical team.
    """
    if request.user.profile.role.name not in ["longevity_physician", "clinician", "medical_director", "clinical_admin"]:
        return Response({"detail": "Access restricted to clinical team"}, status=403)

    query = Q()
    status_filter = request.query_params.get("status")
    hcp_id = request.query_params.get("hcp_id")
    date_filter = request.query_params.get("date")

    if status_filter:
        query &= Q(status=status_filter)
    if hcp_id:
        query &= Q(assigned_hcp_id=hcp_id)
    if date_filter:
        # Simple date match
        query &= Q(scheduled_at__date=date_filter)

    appts = Appointment.objects.filter(query).order_by('scheduled_at')[:200]
    return Response({
        "appointments": AppointmentSerializer(appts, many=True).data,
        "total": appts.count()
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_appointment(request):
    """
    POST /api/emr/appointments/create
    Creates a new appointment for a member.
    """
    if request.user.profile.role.name not in ["longevity_physician", "clinician", "medical_director", "clinical_admin"]:
        return Response({"detail": "Access restricted to clinical team"}, status=403)

    data = request.data
    member_id = data.get("member_id")
    if not member_id:
        return Response({"detail": "member_id is required"}, status=400)

    member = get_object_or_404(User, id=member_id)
    
    # Determine if new patient
    is_new_patient = not EMREncounter.objects.filter(member=member).exists()

    # Parse scheduled_at
    scheduled_at = data.get("scheduled_at")
    if not scheduled_at:
        scheduled_at = timezone.now() + timedelta(days=1)
    
    appt = Appointment.objects.create(
        member=member,
        member_name=member.get_full_name() or member.username,
        appointment_type=data.get("appointment_type", "new" if is_new_patient else "follow_up"),
        mode=data.get("mode", "telehealth"),
        scheduled_at=scheduled_at,
        duration_min=data.get("duration_min", 30),
        fee_type=data.get("fee_type", "insurance"),
        fee_amount=data.get("fee_amount", 0.0),
        reason=data.get("reason", ""),
        assigned_hcp=request.user, # Default to the one creating it
        assigned_hcp_name=request.user.get_full_name() or request.user.username,
        is_new_patient=is_new_patient,
        status="scheduled",
        notes=data.get("notes", "")
    )

    return Response(AppointmentSerializer(appt).data, status=201)

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
    apts = Appointment.objects.filter(assigned_hcp=request.user).order_by('scheduled_at')[:50]
    return Response(AppointmentSerializer(apts, many=True).data)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def get_appointment_detail(request, apt_id):
    """
    GET /api/emr/appointments/<apt_id>
    PUT /api/emr/appointments/<apt_id>
    """
    if request.user.profile.role.name not in ["longevity_physician", "clinician", "medical_director", "clinical_admin"]:
        return Response({"detail": "Access restricted to clinical team"}, status=403)

    # Note: apt_id can be UUID or string. get_object_or_404 handles it.
    try:
        appt = Appointment.objects.get(id=apt_id)
    except Appointment.DoesNotExist:
        return Response({"detail": "Appointment not found"}, status=404)

    if request.method == 'PUT':
        data = request.data
        if "status" in data:
            appt.status = data["status"]
        if "notes" in data:
            appt.notes = data["notes"]
        if "scheduled_at" in data:
            appt.scheduled_at = data["scheduled_at"]
        appt.save()
        return Response(AppointmentSerializer(appt).data)

    return Response(AppointmentSerializer(appt).data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_appointment_status(request, pt_id):
    apt = get_object_or_404(Appointment, id=pt_id)
    new_status = request.data.get("status")
    if new_status:
        apt.status = new_status
        apt.save()
    return Response(AppointmentSerializer(apt).data)


# -------------------------------------------------------------------------
# LIST VIEWS (Parity with Legacy)
# -------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_member_problems(request, member_id):
    problems = MedicalCondition.objects.filter(user__id=member_id).order_by('-diagnosed_date')
    return Response(MedicalConditionSerializer(problems, many=True).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_member_medications(request, member_id):
    meds = Medication.objects.filter(member__id=member_id).order_by('-created_at')
    return Response(MedicationSerializer(meds, many=True).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_member_allergies(request, member_id):
    allergies = EMRAllergy.objects.filter(member__id=member_id).order_by('-created_at')
    return Response(EMRAllergySerializer(allergies, many=True).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_lab_orders(request):
    """List lab orders. If member_id provided in query params, filter by member."""
    member_id = request.query_params.get("member_id")
    if member_id:
        orders = LabOrder.objects.filter(patient__id=member_id)
    elif request.user.profile.role.name in ["employee", "user"]:
        orders = LabOrder.objects.filter(patient=request.user)
    else:
        orders = LabOrder.objects.all()
    
    return Response(LabOrderSerializer(orders.order_by('-ordered_at')[:50], many=True).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_lab_panels(request):
    panels = LabPanel.objects.all()
    return Response({"panels": LabPanelSerializer(panels, many=True).data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_lab_order_status(request, order_id):
    order = get_object_or_404(LabOrder, id=order_id)
    order.status = request.data.get("status", order.status)
    order.save()
    return Response(LabOrderSerializer(order).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_lab_results(request, order_id):
    order = get_object_or_404(LabOrder, id=order_id)
    order.results = request.data.get("results", [])
    order.status = "resulted"
    order.resulted_at = timezone.now()
    order.save()
    return Response(LabOrderSerializer(order).data)


# -------------------------------------------------------------------------
# E-PRESCRIBE
# -------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_prescription(request):
    member_id = request.data.get("member_id")
    member = get_object_or_404(User, id=member_id)
    
    rx = Medication.objects.create(
        member=member,
        prescribed_by=request.user,
        medication_name=request.data.get("medication_name"),
        medication_type=request.data.get("medication_type", "supplement"),
        dosage=request.data.get("dosage"),
        frequency=request.data.get("frequency"),
        route=request.data.get("route", "oral"),
        duration_days=request.data.get("duration_days", 90),
        clinical_notes=request.data.get("clinical_notes", ""),
        start_date=timezone.now().date(),
        status="active"
    )
    return Response(MedicationSerializer(rx).data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_prescriptions(request):
    member_id = request.query_params.get("member_id")
    if member_id:
        rx = Medication.objects.filter(member__id=member_id)
    else:
        rx = Medication.objects.all()
    return Response({"prescriptions": MedicationSerializer(rx.order_by('-created_at')[:50], many=True).data})

@api_view(['PUT', 'POST'])
@permission_classes([IsAuthenticated])
def update_prescription(request, rx_id):
    rx = get_object_or_404(Medication, id=rx_id)
    rx.status = request.data.get("status", rx.status)
    rx.clinical_notes = request.data.get("clinical_notes", rx.clinical_notes)
    rx.save()
    return Response(MedicationSerializer(rx).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refill_prescription(request, rx_id):
    rx = get_object_or_404(Medication, id=rx_id)
    # Simple logic: extend duration or just log the refill
    return Response({"status": "refill_requested", "medication": rx.medication_name})


# -------------------------------------------------------------------------
# VISIT SUMMARY & ENCOUNTERS
# -------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_visit_summary(request, member_id):
    member = get_object_or_404(User, id=member_id)
    last_encounter = EMREncounter.objects.filter(member=member).order_by('-created_at').first()
    
    return Response({
        "member_name": member.get_full_name(),
        "summary": last_encounter.plan if last_encounter else "No recent visits.",
        "last_visit": last_encounter.created_at if last_encounter else None,
        "diagnoses": last_encounter.diagnosis_codes if last_encounter else []
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_smart_encounter(request):
    """
    AI-powered smart encounter (parity with legacy /encounters/smart)
    Handles inline creation of Labs, Rx, Referrals, and Protocols.
    """
    data = request.data
    member_id = data.get("member_id")
    member = get_object_or_404(User, id=member_id)
    
    with transaction.atomic():
        # 1. Create Encounter record
        encounter = EMREncounter.objects.create(
            member=member,
            hcp=request.user,
            encounter_type=data.get("encounter_type", "office_visit"),
            chief_complaint=data.get("chief_complaint", ""),
            subjective=data.get("subjective", ""),
            objective=data.get("objective", ""),
            assessment=data.get("assessment", ""),
            plan=data.get("plan", ""),
            diagnosis_codes=data.get("diagnosis_codes", []),
            vitals=data.get("vitals", {})
        )
        
        # 2. Labs Ordered
        linked_labs = []
        labs_data = data.get("labs_ordered", [])
        for l_req in labs_data:
            panel_id = l_req.get("panel_id")
            panel = LabPanel.objects.filter(panel_id=panel_id).first()
            if panel:
                l_order = LabOrder.objects.create(
                    order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
                    patient=member,
                    ordered_by=request.user,
                    panel=panel,
                    lab_partner=LabPartner.objects.first(),
                    status="ordered",
                    priority=l_req.get("priority", "routine")
                )
                linked_labs.append(str(l_order.id))
        encounter.linked_lab_orders = linked_labs
        
        # 3. Pharmacy Orders
        linked_pharmacy = []
        pharm_data = data.get("pharmacy_ordered", [])
        for p_req in pharm_data:
            order = PharmacyOrder.objects.create(
                order_number=f"PH-{uuid.uuid4().hex[:8].upper()}",
                patient=member,
                ordered_by=request.user,
                total_price=p_req.get("total_estimated_price", 0.0),
                status="pending"
            )
            for item in p_req.get("items", []):
                item_name = item.get("name", "Unknown Item")
                item_id = item.get("item_id", f"RX-MOCK-{uuid.uuid4().hex[:4].upper()}")
                
                # Try to get existing item from catalog
                catalog_item = PharmacyCatalogItem.objects.filter(Q(item_id=item_id) | Q(name__iexact=item_name)).first()
                if not catalog_item:
                    catalog_item = PharmacyCatalogItem.objects.create(
                        item_id=item_id,
                        name=item_name,
                        type="prescription" if "rx" in item_name.lower() else "nutraceutical",
                        category="General",
                        price=item.get("price_at_order", 0.0)
                    )
                
                PharmacyOrderItem.objects.create(
                    order=order,
                    catalog_item=catalog_item,
                    price_at_order=item.get("price_at_order", 0.0),
                    quantity=item.get("quantity", 1),
                    dosing_instructions=item.get("instructions", "")
                )
            linked_pharmacy.append(str(order.id))
        encounter.linked_pharmacy_orders = linked_pharmacy
        
        # 4. Referrals
        linked_referrals = []
        ref_data = data.get("referrals_ordered", [])
        for r_req in ref_data:
            ref = CCReferral.objects.create(
                member=member,
                member_name=member.get_full_name(),
                referral_type=r_req.get("role", "specialist"),
                referred_to_name=r_req.get("hcp_name", ""),
                reason=r_req.get("reason", ""),
                referring_clinician=request.user,
                referring_clinician_name=request.user.get_full_name(),
                status="pending"
            )
            linked_referrals.append(str(ref.id))
        encounter.linked_referrals = linked_referrals
        
        # 5. Protocols
        linked_protocols = []
        proto_data = data.get("protocols_prescribed", [])
        for proto_req in proto_data:
            status = "active"
            care_plan = CarePlan.objects.create(
                member=member,
                hcp=request.user,
                hcp_name=request.user.get_full_name(),
                title=f"Protocol Assignment: {proto_req.get('protocol_name')}",
                protocols=[proto_req],
                notes=f"Prescribed during encounter {encounter.id}"
            )
            linked_protocols.append(str(care_plan.id))
        encounter.linked_protocols = linked_protocols
        
        # 6. Diagnostics
        linked_diagnostics = []
        diag_data = data.get("diagnostics_ordered", [])
        for d_req in diag_data:
            diag = DiagnosticOrder.objects.create(
                member=member,
                test_name=d_req.get("name"),
                category=d_req.get("category", "Radiology"),
                ordered_by=request.user,
                urgency=d_req.get("urgency", "routine"),
                status="ordered"
            )
            linked_diagnostics.append(str(diag.id))
        encounter.linked_diagnostics = linked_diagnostics
        
        # 7. Follow-up Appointment
        if "follow up" in encounter.plan.lower():
            Appointment.objects.create(
                member=member,
                member_name=member.get_full_name(),
                appointment_type="follow_up",
                mode="telehealth",
                scheduled_at=timezone.now() + timedelta(days=7),
                reason=f"Follow up from encounter {encounter.id}",
                assigned_hcp=request.user,
                assigned_hcp_name=request.user.get_full_name(),
                status="scheduled"
            )
            
        encounter.save()
        
    return Response({
        "status": "success",
        "encounter_id": str(encounter.id),
        "linked_entities": {
            "labs": encounter.linked_lab_orders,
            "pharmacy": encounter.linked_pharmacy_orders,
            "referrals": encounter.linked_referrals,
            "protocols": encounter.linked_protocols,
            "diagnostics": encounter.linked_diagnostics
        }
    }, status=status.HTTP_201_CREATED)


# -------------------------------------------------------------------------
# HEALTH ANALYTICS (HPS)
# -------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_member_hps_profile(request, member_id):
    member = get_object_or_404(User, id=member_id)
    print('member',member)
    hps = HPSScore.objects.filter(user=member).order_by('-timestamp').first()
    if not hps:
        return Response({"detail": "HPS Profile not found"}, status=404)
    return Response(HPSScoreSerializer(hps).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_hps_delta(request, member_id):
    member = get_object_or_404(User, id=member_id)
    scores = HPSScore.objects.filter(user=member).order_by('-timestamp')[:2]
    if scores.count() < 2:
        return Response({"delta": 0, "notes": "Insufficient data for delta calculation"})
    
    delta = scores[0].hps_final - scores[1].hps_final
    return Response({
        "delta": round(delta, 2),
        "current": scores[0].hps_final,
        "previous": scores[1].hps_final,
        "timestamp": scores[0].timestamp
    })


# -------------------------------------------------------------------------
# SEARCH & DIRECTORIES
# -------------------------------------------------------------------------

@api_view(['GET'])
def search_drugs(request):
    query = request.query_params.get("q", "").lower()
    items = PharmacyCatalogItem.objects.filter(Q(name__icontains=query) | Q(category__icontains=query))
    results = [
        {"id": item.item_id, "name": item.name, "type": item.type, "price": str(item.price)}
        for item in items[:20]
    ]
    return Response({"results": results})

@api_view(['GET'])
def search_diagnostics(request):
    query = request.query_params.get("q", "").lower()
    items = DiagnosticCatalog.objects.filter(Q(name__icontains=query) | Q(category__icontains=query))
    results = [
        {"id": str(item.id), "name": item.name, "category": item.category}
        for item in items[:20]
    ]
    return Response({"results": results})


# -------------------------------------------------------------------------
# PROTOCOLS & COACHES
# -------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_smart_protocols(request, member_id):
    # Logic to return protocols based on HPS/Biomarkers
    protocols = CCProtocol.objects.all()[:5]
    return Response({"protocols": CCProtocolSerializer(protocols, many=True).data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_hcp_coaches(request):
    coaches = User.objects.filter(profile__role__name__in=["clinician", "coach", "fitness_coach", "nutritional_coach"])
    return Response([{
        "id": c.id,
        "name": c.get_full_name(),
        "role": c.profile.role.name,
        "specialty": getattr(c.profile, 'specialty', 'Longevity')
    } for c in coaches])


# -------------------------------------------------------------------------
# VITALS
# -------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_vitals_history(request, member_id):
    logs = VitalsLog.objects.filter(member__id=member_id).order_by('-recorded_at')[:20]
    return Response(VitalsLogSerializer(logs, many=True).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def record_vitals_log(request):
    member_id = request.data.get("member_id")
    member = get_object_or_404(User, id=member_id)
    log = VitalsLog.objects.create(
        member=member,
        vitals=request.data.get("vitals", {}),
        recorded_by=request.user
    )
    return Response(VitalsLogSerializer(log).data, status=status.HTTP_201_CREATED)


# -------------------------------------------------------------------------
# CDSS & CARE PLANS
# -------------------------------------------------------------------------

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_cdss_suggestions(request, member_id):
#     """
#     AgeReboot CDSS (Clinical Decision Support) 
#     Auto-suggests diagnostics and prescriptions based on biomarkers.
#     """
#     member = get_object_or_404(User, id=member_id)
#     latest_results = BiomarkerResult.objects.filter(user=member).order_by('biomarker__code', '-collected_at').distinct('biomarker__code')
    
#     suggestions = {"diagnostics": [], "prescriptions": [], "lifestyle": [], "alerts": []}
    
#     # Rule definitions (Ported from Flask)
#     # This should ideally be in a separate engine or DB table for full dynamic parity.
#     CDSS_RULES = {
#         "hba1c": {
#             "threshold_high": 5.7,
#             "diagnostics": [{"name": "Fasting Insulin / HOMA-IR", "reason": "Elevated HbA1c suggests insulin resistance screening"}],
#             "prescriptions": [{"drug": "Metformin", "dose": "500mg", "reason": "Consider metformin for pre-diabetic HbA1c"}],
#             "lifestyle": ["Time-restricted eating window", "Zone 2 exercise 150min/week"],
#         },
#         "ldl_cholesterol": {
#             "threshold_high": 130,
#             "diagnostics": [{"name": "ApoB / Lp(a)", "reason": "Elevated LDL warrants advanced lipid assessment"}],
#             "prescriptions": [{"drug": "Omega-3 Fish Oil", "dose": "2000mg", "reason": "Omega-3 for lipid optimization"}],
#             "lifestyle": ["Mediterranean diet pattern", "Increase fiber intake to 30g/day"],
#         },
#         "triglycerides": {
#             "threshold_high": 150,
#             "diagnostics": [{"name": "CMP", "reason": "Elevated triglycerides - check metabolic markers"}],
#             "prescriptions": [{"drug": "Berberine", "dose": "500mg", "reason": "Berberine for triglyceride management"}],
#             "lifestyle": ["Reduce refined carbohydrates", "Implement intermittent fasting"],
#         },
#         "vitamin_d": {
#             "threshold_low": 40,
#             "diagnostics": [{"name": "DEXA Scan", "reason": "Low Vitamin D - assess bone density"}],
#             "prescriptions": [{"drug": "Vitamin D3", "dose": "5000 IU", "reason": "Supplement Vitamin D to target 60-80 ng/mL"}],
#             "lifestyle": ["15 min daily sun exposure"],
#         }
#     }
    
#     for res in latest_results:
#         code = res.biomarker.code.lower()
#         if code in CDSS_RULES:
#             rule = CDSS_RULES[code]
#             triggered = False
#             if "threshold_high" in rule and res.value > rule["threshold_high"]:
#                 triggered = True
#             if "threshold_low" in rule and res.value < rule["threshold_low"]:
#                 triggered = True
            
#             if triggered:
#                 for d in rule.get("diagnostics", []):
#                     suggestions["diagnostics"].append({**d, "biomarker": res.biomarker.name, "value": res.value})
#                 for p in rule.get("prescriptions", []):
#                     suggestions["prescriptions"].append({**p, "biomarker": res.biomarker.name, "value": res.value})
#                 for l in rule.get("lifestyle", []):
#                     suggestions["lifestyle"].append({"recommendation": l, "biomarker": res.biomarker.name})

#     # HPS Pillar Alerts
#     latest_hps = HPSScore.objects.filter(user=member).order_by('-timestamp').first()
#     if latest_hps and latest_hps.pillars:
#         for p_name, p_data in latest_hps.pillars.items():
#             pct = p_data.get("percentage", 100) if isinstance(p_data, dict) else p_data
#             if pct < 30:
#                 suggestions["alerts"].append({
#                     "level": "critical",
#                     "pillar": p_name,
#                     "score": round(pct),
#                     "message": f"{p_name} critically low. Urgent intervention needed."
#                 })
#             elif pct < 50:
#                 suggestions["alerts"].append({
#                     "level": "warning",
#                     "pillar": p_name,
#                     "score": round(pct),
#                     "message": f"{p_name} below target. Review recommended."
#                 })

#     return Response(suggestions)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cdss_suggestions(request, member_id):
    """
    AgeReboot CDSS (Clinical Decision Support)
    Auto-suggests diagnostics and prescriptions based on biomarkers.
    """

    member = get_object_or_404(User, id=member_id)

    # ✅ FIX: Replace DISTINCT ON with Python grouping
    results = BiomarkerResult.objects.filter(user=member)\
        .select_related("biomarker")\
        .order_by('biomarker__code', '-collected_at')

    latest_results_map = {}
    for r in results:
        code = (r.biomarker.code or "").lower()
        if code and code not in latest_results_map:
            latest_results_map[code] = r

    latest_results = latest_results_map.values()

    # -------------------------------
    # Suggestions Structure
    # -------------------------------
    suggestions = {
        "diagnostics": [],
        "prescriptions": [],
        "lifestyle": [],
        "alerts": []
    }

    # -------------------------------
    # CDSS RULES
    # -------------------------------
    CDSS_RULES = {
        "hba1c": {
            "threshold_high": 5.7,
            "diagnostics": [
                {"name": "Fasting Insulin / HOMA-IR", "reason": "Elevated HbA1c suggests insulin resistance screening"}
            ],
            "prescriptions": [
                {"drug": "Metformin", "dose": "500mg", "reason": "Consider metformin for pre-diabetic HbA1c"}
            ],
            "lifestyle": [
                "Time-restricted eating window",
                "Zone 2 exercise 150min/week"
            ],
        },
        "ldl_cholesterol": {
            "threshold_high": 130,
            "diagnostics": [
                {"name": "ApoB / Lp(a)", "reason": "Elevated LDL warrants advanced lipid assessment"}
            ],
            "prescriptions": [
                {"drug": "Omega-3 Fish Oil", "dose": "2000mg", "reason": "Omega-3 for lipid optimization"}
            ],
            "lifestyle": [
                "Mediterranean diet pattern",
                "Increase fiber intake to 30g/day"
            ],
        },
        "triglycerides": {
            "threshold_high": 150,
            "diagnostics": [
                {"name": "CMP", "reason": "Elevated triglycerides - check metabolic markers"}
            ],
            "prescriptions": [
                {"drug": "Berberine", "dose": "500mg", "reason": "Berberine for triglyceride management"}
            ],
            "lifestyle": [
                "Reduce refined carbohydrates",
                "Implement intermittent fasting"
            ],
        },
        "vitamin_d": {
            "threshold_low": 40,
            "diagnostics": [
                {"name": "DEXA Scan", "reason": "Low Vitamin D - assess bone density"}
            ],
            "prescriptions": [
                {"drug": "Vitamin D3", "dose": "5000 IU", "reason": "Supplement Vitamin D to target 60-80 ng/mL"}
            ],
            "lifestyle": [
                "15 min daily sun exposure"
            ],
        }
    }

    # -------------------------------
    # Apply CDSS Rules
    # -------------------------------
    for res in latest_results:
        code = (res.biomarker.code or "").lower()

        if code in CDSS_RULES:
            rule = CDSS_RULES[code]
            triggered = False

            # Handle None values safely
            value = res.value or 0

            if "threshold_high" in rule and value > rule["threshold_high"]:
                triggered = True

            if "threshold_low" in rule and value < rule["threshold_low"]:
                triggered = True

            if triggered:
                # Diagnostics
                for d in rule.get("diagnostics", []):
                    suggestions["diagnostics"].append({
                        **d,
                        "biomarker": res.biomarker.name,
                        "value": value
                    })

                # Prescriptions
                for p in rule.get("prescriptions", []):
                    suggestions["prescriptions"].append({
                        **p,
                        "biomarker": res.biomarker.name,
                        "value": value
                    })

                # Lifestyle
                for l in rule.get("lifestyle", []):
                    suggestions["lifestyle"].append({
                        "recommendation": l,
                        "biomarker": res.biomarker.name
                    })

    # -------------------------------
    # HPS Alerts
    # -------------------------------
    latest_hps = HPSScore.objects.filter(user=member)\
        .order_by('-timestamp')\
        .first()

    if latest_hps and latest_hps.pillars:
        for p_name, p_data in latest_hps.pillars.items():

            pct = p_data.get("percentage", 100) if isinstance(p_data, dict) else p_data

            if pct < 30:
                suggestions["alerts"].append({
                    "level": "critical",
                    "pillar": p_name,
                    "score": round(pct),
                    "message": f"{p_name} critically low. Urgent intervention needed."
                })

            elif pct < 50:
                suggestions["alerts"].append({
                    "level": "warning",
                    "pillar": p_name,
                    "score": round(pct),
                    "message": f"{p_name} below target. Review recommended."
                })

    return Response(suggestions)



@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def get_emr_care_plan(request, member_id):
    member = get_object_or_404(User, id=member_id)
    if request.method == 'GET':
        plan = CarePlan.objects.filter(member=member).order_by('-created_at').first()
        if not plan:
            return Response({"detail": "No care plan found"}, status=404)
        return Response(CarePlanSerializer(plan).data)
    else:
        plan = CarePlan.objects.create(
            member=member,
            hcp=request.user,
            hcp_name=request.user.get_full_name(),
            title=request.data.get("title", "Longevity Care Plan"),
            protocols=request.data.get("protocols", []),
            notes=request.data.get("notes", "")
        )
        return Response(CarePlanSerializer(plan).data, status=status.HTTP_201_CREATED)


# -------------------------------------------------------------------------
# LONGEVITY ROADMAP
# -------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_longevity_roadmap(request, member_id):
    roadmap_items = Roadmap.objects.filter(user__id=member_id)
    # Return structure matching legacy roadmap
    return Response({"roadmap_items": []}) # Placeholder for complex roadmap data

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_longevity_protocols(request, member_id):
    # Logic to move protocols from CarePlan to Roadmap
    return Response({"status": "approved", "count": len(request.data.get("protocol_ids", []))})
