# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.response import Response
# from rest_framework import status
# from django.utils import timezone
# from django.db.models import Q
# from datetime import datetime, timedelta
# import uuid
# import os
# import logging

# from .models import VideoConsultation, User, Notification, LabOrder, EMREncounter, LabPanel, BiomarkerDefinition,CareTeamMember
# from .serializers import VideoConsultationSerializer

# logger = logging.getLogger(__name__)

# HMS_ACCESS_KEY = os.environ.get("HMS_ACCESS_KEY", "")
# HMS_SECRET = os.environ.get("HMS_SECRET", "")
# HMS_TEMPLATE_ID = os.environ.get("HMS_TEMPLATE_ID", "")

# def _generate_hms_token(room_id, user_id, role):
#     """Generate 100ms auth token. Returns placeholder if keys not configured."""
#     if not HMS_ACCESS_KEY or not HMS_SECRET:
#         return f"placeholder_token_{room_id}_{user_id}_{role}"
#     try:
#         import jwt as pyjwt
#         payload = {
#             "access_key": HMS_ACCESS_KEY,
#             "room_id": room_id,
#             "user_id": str(user_id),
#             "role": role,
#             "type": "app",
#             "version": 2,
#             "iat": timezone.now().timestamp(),
#             "nbf": timezone.now().timestamp(),
#             "exp": (timezone.now() + timedelta(hours=1)).timestamp(),
#         }
#         return pyjwt.encode(payload, HMS_SECRET, algorithm="HS256")
#     except Exception as e:
#         logger.error(f"HMS token generation failed: {e}")
#         return f"error_token_{room_id}"

# async def _create_hms_room(room_name):
#     """Create 100ms room. Returns simulated room if keys not configured."""
#     if not HMS_ACCESS_KEY or not HMS_SECRET:
#         return {"id": f"room_{uuid.uuid4().hex[:12]}", "name": room_name}
#     try:
#         import jwt as pyjwt
#         import httpx
#         mgmt_token = pyjwt.encode({
#             "access_key": HMS_ACCESS_KEY, "type": "management", "version": 2,
#             "iat": timezone.now().timestamp(),
#             "nbf": timezone.now().timestamp(),
#         }, HMS_SECRET, algorithm="HS256")
#         async with httpx.AsyncClient() as client:
#             resp = await client.post("https://api.100ms.live/v2/rooms", headers={
#                 "Authorization": f"Bearer {mgmt_token}", "Content-Type": "application/json"
#             }, json={"name": room_name, "template_id": HMS_TEMPLATE_ID, "region": "in"})
#             if resp.status_code == 200:
#                 return resp.json()
#         return {"id": f"room_{uuid.uuid4().hex[:12]}", "name": room_name}
#     except Exception as e:
#         logger.error(f"HMS room creation failed: {e}")
#         return {"id": f"room_{uuid.uuid4().hex[:12]}", "name": room_name}

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_available_slots(request, doctor_id):
#     """Get available video consultation slots for a doctor (next 7 days)."""
#     try:
#         doctor = CareTeamMember.objects.get(id=doctor_id)
#     except CareTeamMember.DoesNotExist:
#         return Response({"error": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)

#     slots = []
#     base = timezone.now()
#     for day_offset in range(0, 7):
#         day = base + timedelta(days=day_offset)
#         day_str = day.strftime("%Y-%m-%d")
#         day_label = day.strftime("%A, %b %d")
#         time_slots = []
#         for hour in [9, 10, 11, 14, 15, 16, 17, 18]:
#             for minute in [0, 30]:
#                 t = f"{hour:02d}:{minute:02d}"
#                 time_slots.append({"time": t, "available": True, "is_morning": hour < 12})
#         slots.append({"date": day_str, "label": day_label, "time_slots": time_slots})

#     return Response({
#         "doctor": {"id": doctor.id, "name":  doctor.name, "role": "doctor"},
#         "slots": slots
#     })

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def book_consultation(request):
#     """Book a video consultation with a doctor."""
#     data = request.data
#     doctor_id = data.get("doctor_id")
#     try:
#         doctor = CareTeamMember.objects.get(id=doctor_id)
#     except (CareTeamMember.DoesNotExist, ValueError):
#         return Response({"error": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)

#     scheduled_date = data.get("scheduled_date")
#     scheduled_time = data.get("scheduled_time")
    
#     try:
#         scheduled_at_str = f"{scheduled_date} {scheduled_time}"
#         scheduled_at = timezone.make_aware(datetime.strptime(scheduled_at_str, "%Y-%m-%d %H:%M"))
#     except Exception:
#         scheduled_at = timezone.now() # Fallback

#     room_name = f"consultation_{uuid.uuid4().hex[:8]}"
#     # Simulating async room creation
#     room_id = f"room_{uuid.uuid4().hex[:12]}"

#     consultation = VideoConsultation.objects.create(
#         patient=request.user,
#         doctor=doctor,
#         doctor_name=doctor.name,
#         scheduled_at=scheduled_at,
#         duration_min=data.get("duration_min", 30),
#         reason=data.get("reason", ""),
#         status="scheduled",
#         room_id=room_id,
#         room_name=room_name
#     )

#     # Notifications
#     Notification.objects.create(
#         user=request.user,
#         type="consultation_booked",
#         message=f"Your consultation with {doctor.name} is booked for {scheduled_date} at {scheduled_time}.",
#     )
    
#     # Notify doctor if they have a linked user account
#     if doctor.user:
#         Notification.objects.create(
#             user=doctor.user,
#             type="new_consultation",
#             message=f"New consultation with {request.user.get_full_name() or request.user.username} scheduled for {scheduled_date} at {scheduled_time}.",
#         )

#     return Response({"consultation": VideoConsultationSerializer(consultation).data})

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_my_consultations(request):
#     """Get all consultations for the current user."""
#     consultations = VideoConsultation.objects.filter(
#         Q(patient=request.user) | Q(doctor__user=request.user)
#     ).order_by('-created_at')
#     return Response({"consultations": VideoConsultationSerializer(consultations, many=True).data})

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_consultation_detail(request, consultation_id):
#     """Get consultation detail with room token for joining."""
#     try:
#         c = VideoConsultation.objects.get(id=consultation_id)
#     except (VideoConsultation.DoesNotExist, ValueError):
#         return Response({"error": "Consultation not found"}, status=status.HTTP_404_NOT_FOUND)

#     is_doctor = (c.doctor and c.doctor.user == request.user)
#     role = "host" if is_doctor else "guest"
#     token = _generate_hms_token(c.room_id, request.user.id, role)

#     return Response({
#         "consultation": VideoConsultationSerializer(c).data,
#         "auth_token": token,
#         "role": role,
#         "sdk_configured": bool(HMS_ACCESS_KEY and HMS_SECRET),
#     })

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def join_consultation(request, consultation_id):
#     """Join a video consultation and get auth token."""
#     try:
#         c = VideoConsultation.objects.get(id=consultation_id)
#     except (VideoConsultation.DoesNotExist, ValueError):
#         return Response({"error": "Consultation not found"}, status=status.HTTP_404_NOT_FOUND)

#     is_doctor = (c.doctor and c.doctor.user == request.user)
#     role = "host" if is_doctor else "guest"
#     token = _generate_hms_token(c.room_id, request.user.id, role)

#     if c.status == "scheduled":
#         c.status = "in_progress"
#         # started_at would be nice, but not in model yet
#         c.save()

#     return Response({"auth_token": token, "room_id": c.room_id, "role": role})

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def end_consultation(request, consultation_id):
#     """End consultation, save EMR data and biomarker orders."""
#     try:
#         c = VideoConsultation.objects.get(id=consultation_id)
#     except (VideoConsultation.DoesNotExist, ValueError):
#         return Response({"error": "Consultation not found"}, status=status.HTTP_404_NOT_FOUND)

#     data = request.data
#     c.status = "completed"
#     c.emr_data = data.get("emr_data", {})
#     c.biomarkers_ordered = data.get("biomarker_codes", [])
#     c.panels_ordered = data.get("panel_ids", [])
#     c.consultation_summary = data.get("notes", "")
#     c.save()

#     # Handle lab order creation if biomarkers/panels are ordered
#     lab_order_created = False
#     if c.biomarkers_ordered or c.panels_ordered:
#         # Fetch a panel if panel_ids provided, otherwise use a default or none
#         panel = None
#         if c.panels_ordered:
#             panel = LabPanel.objects.filter(panel_id=c.panels_ordered[0]).first()
        
#         # If no panel found but biomarkers are ordered, we might need a generic panel
#         if not panel:
#             panel = LabPanel.objects.first() # Fallback to any active panel

#         if panel:
#             from Reboot_App.models import LabPartner
#             partner = LabPartner.objects.first()
#             if partner:
#                 LabOrder.objects.create(
#                     order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
#                     patient=c.patient,
#                     ordered_by=request.user,
#                     panel=panel,
#                     lab_partner=partner,
#                     status="ordered",
#                     notes=f"Consultation ID: {c.id}\nBiomarkers: {', '.join(c.biomarkers_ordered)}"
#                 )
#                 lab_order_created = True

#             Notification.objects.create(
#                 user=c.patient,
#                 type="lab_order_placed",
#                 message=f"Dr. {request.user.get_full_name() or request.user.username} has ordered your lab tests. Book your home sample collection.",
#             )

#     # Create EMR Encounter if data present
#     if data.get("emr_data"):
#         emr_data = data["emr_data"]
#         # Consolidate history into subjective if not in model fields
#         subjective_text = emr_data.get("history_present_illness", "")
#         if emr_data.get("allergies") or emr_data.get("existing_conditions"):
#             subjective_text += f"\nAllergies: {emr_data.get('allergies', 'None')}"
#             subjective_text += f"\nConditions: {', '.join(emr_data.get('existing_conditions', []))}"

#         encounter = EMREncounter.objects.create(
#             member=c.patient,
#             hcp=request.user,
#             encounter_type="video_consultation",
#             chief_complaint=emr_data.get("chief_complaint", ""),
#             subjective=subjective_text,
#             objective=emr_data.get("current_medications", ""),
#             assessment=emr_data.get("clinical_notes", ""),
#             plan=emr_data.get("lifestyle_notes", ""),
#             vitals=emr_data.get("vitals", {}),
#         )
#         c.emr_encounter = encounter
#         c.save()

#     return Response({
#         "status": "completed", 
#         "lab_order_created": lab_order_created
#     })

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_biomarker_panels(request):
#     """Get grouped biomarker panels for doctor selection during consultation."""
#     from collections import defaultdict
    
#     # 1. Fetch all biomarkers and group by domain
#     biomarkers = BiomarkerDefinition.objects.filter(data_source="lab")
#     grouped_biomarkers = defaultdict(list)
#     for b in biomarkers:
#         domain = b.domain or "General"
#         grouped_biomarkers[domain].append({
#             "code": b.code,
#             "name": b.name
#         })
    
#     groups = []
#     for domain, markers in grouped_biomarkers.items():
#         groups.append({
#             "code": domain.lower().replace(" ", "_"),
#             "name": f"{domain} Panel",
#             "biomarkers": markers
#         })

#     # 2. Fetch prebuilt panels
#     panels = LabPanel.objects.filter(is_active=True)
#     prebuilt_panels = []
#     for p in panels:
#         prebuilt_panels.append({
#             "id": p.panel_id,
#             "name": p.name,
#             "markers": len(p.tests_included),
#             "description": p.description,
#             "fasting": True # Placeholder as field doesn't exist on LabPanel, using common default
#         })

#     # Fallback to static structure if DB is empty (should not be based on my check)
#     if not groups:
#         groups = [
#             {"code": "metabolic", "name": "Metabolic Panel", "biomarkers": [
#                 {"code": "fasting_glucose", "name": "Fasting Glucose"},
#                 {"code": "hba1c", "name": "HbA1c"},
#             ]}
#         ]

#     return Response({
#         "groups": sorted(groups, key=lambda x: x["name"]),
#         "prebuilt_panels": prebuilt_panels
#     })



"""
views_video_consultation.py
────────────────────────────
All video-consultation API views.
Google Meet links are created via the Calendar API on booking
and deleted if a consultation is cancelled.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
import uuid
import os
import logging

from .models import (
    VideoConsultation, User, Notification, LabOrder,
    EMREncounter, LabPanel, BiomarkerDefinition, CareTeamMember,
)
from .serializers import VideoConsultationSerializer
from Google_meet_service import (
    create_google_meet_event,
    delete_google_meet_event,
    update_google_meet_event,
)

logger = logging.getLogger(__name__)

# ─── 100ms / HMS (kept for backward-compat, now optional) ────────────────────
HMS_ACCESS_KEY  = os.environ.get("HMS_ACCESS_KEY", "")
HMS_SECRET      = os.environ.get("HMS_SECRET", "")
HMS_TEMPLATE_ID = os.environ.get("HMS_TEMPLATE_ID", "")


def _generate_hms_token(room_id, user_id, role):
    """Generate 100ms auth token. Returns placeholder if keys not configured."""
    if not HMS_ACCESS_KEY or not HMS_SECRET:
        return f"placeholder_token_{room_id}_{user_id}_{role}"
    try:
        import jwt as pyjwt
        payload = {
            "access_key": HMS_ACCESS_KEY,
            "room_id":    room_id,
            "user_id":    str(user_id),
            "role":       role,
            "type":       "app",
            "version":    2,
            "iat": timezone.now().timestamp(),
            "nbf": timezone.now().timestamp(),
            "exp": (timezone.now() + timedelta(hours=1)).timestamp(),
        }
        return pyjwt.encode(payload, HMS_SECRET, algorithm="HS256")
    except Exception as exc:
        logger.error("HMS token generation failed: %s", exc)
        return f"error_token_{room_id}"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _patient_email(user) -> str:
    return user.email or f"{user.username}@placeholder.com"


def _doctor_email(doctor: CareTeamMember) -> str:
    if doctor.user and doctor.user.email:
        return doctor.user.email
    return doctor.email or f"doctor_{doctor.id}@placeholder.com"


# ─── Available slots ─────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_available_slots(request, doctor_id):
    """
    GET /video-consultation/available-slots/<doctor_id>

    Returns the next 7 days of available time slots for a doctor.
    Each slot now includes a `meet_link` field that will be populated
    when the slot is actually booked (it is empty here — links are
    generated at booking time to avoid creating thousands of dead events).
    """
    try:
        doctor = CareTeamMember.objects.get(id=doctor_id)
    except CareTeamMember.DoesNotExist:
        return Response({"error": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)

    # Fetch already-booked slots so we can mark them unavailable
    booked_slots = set(
        VideoConsultation.objects
        .filter(doctor=doctor, status__in=["scheduled", "in_progress"])
        .values_list("scheduled_at", flat=True)
    )
    booked_hours = {dt.strftime("%Y-%m-%d %H:%M") for dt in booked_slots}

    slots = []
    base = timezone.now()

    for day_offset in range(0, 7):
        day       = base + timedelta(days=day_offset)
        day_str   = day.strftime("%Y-%m-%d")
        day_label = day.strftime("%A, %b %d")
        time_slots = []

        for hour in [9, 10, 11, 14, 15, 16, 17, 18]:
            for minute in [0, 30]:
                t          = f"{hour:02d}:{minute:02d}"
                slot_key   = f"{day_str} {t}"
                is_booked  = slot_key in booked_hours
                is_past    = day.replace(hour=hour, minute=minute, second=0, microsecond=0) < timezone.now()

                time_slots.append({
                    "time":       t,
                    "available":  not is_booked and not is_past,
                    "is_morning": hour < 12,
                    # meet_link is empty here; it is created when the slot is booked
                    "meet_link":  None,
                })

        slots.append({"date": day_str, "label": day_label, "time_slots": time_slots})

    return Response({
        "doctor": {
            "id":   doctor.id,
            "name": doctor.name,
            "role": "doctor",
        },
        "slots": slots,
    })


# ─── Book consultation ────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def book_consultation(request):
    """
    POST /video-consultation/book

    Body:
        doctor_id       – CareTeamMember PK
        scheduled_date  – "YYYY-MM-DD"
        scheduled_time  – "HH:MM"
        duration_min    – int (default 30)
        reason          – str

    Creates the VideoConsultation record and a real Google Meet event.
    The meet_link is stored on the consultation and returned in the response.
    """
    data      = request.data
    doctor_id = data.get("doctor_id")

    try:
        doctor = CareTeamMember.objects.get(id=doctor_id)
    except (CareTeamMember.DoesNotExist, ValueError):
        return Response({"error": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)

    scheduled_date = data.get("scheduled_date", "")
    scheduled_time = data.get("scheduled_time", "")
    duration_min   = int(data.get("duration_min", 30))
    reason         = data.get("reason", "")

    try:
        scheduled_at = timezone.make_aware(
            datetime.strptime(f"{scheduled_date} {scheduled_time}", "%Y-%m-%d %H:%M")
        )
    except Exception:
        scheduled_at = timezone.now()

    # ── Check slot is still available ────────────────────────────────────────
    conflict = VideoConsultation.objects.filter(
        doctor=doctor,
        scheduled_at=scheduled_at,
        status__in=["scheduled", "in_progress"],
    ).exists()
    if conflict:
        return Response(
            {"error": "This slot is already booked. Please choose another time."},
            status=status.HTTP_409_CONFLICT,
        )

    # ── Create Google Meet event ──────────────────────────────────────────────
    patient_name = request.user.get_full_name() or request.user.username
    meet_info    = create_google_meet_event(
        title=f"Health Consultation – {patient_name} & Dr. {doctor.name}",
        description=(
            f"Video consultation between {patient_name} and Dr. {doctor.name}.\n"
            f"Reason: {reason or 'General consultation'}\n\n"
            "Please join via the Google Meet link at the scheduled time."
        ),
        start_datetime=scheduled_at,
        duration_minutes=duration_min,
        patient_email=_patient_email(request.user),
        doctor_email=_doctor_email(doctor),
    )

    # ── Persist the consultation ──────────────────────────────────────────────
    room_name = f"consultation_{uuid.uuid4().hex[:8]}"
    room_id   = f"room_{uuid.uuid4().hex[:12]}"

    consultation = VideoConsultation.objects.create(
        patient            = request.user,
        doctor             = doctor,
        doctor_name        = doctor.name,
        scheduled_at       = scheduled_at,
        duration_min       = duration_min,
        reason             = reason,
        status             = "scheduled",
        room_id            = room_id,
        room_name          = room_name,
        # ── NEW fields (add these to the model — see migration instructions) ──
        meet_link          = meet_info["meet_link"],
        calendar_event_id  = meet_info["calendar_event_id"],
    )

    # ── Notifications ─────────────────────────────────────────────────────────
    meet_link = meet_info["meet_link"]

    Notification.objects.create(
        user    = request.user,
        type    = "consultation_booked",
        message = (
            f"Your consultation with Dr. {doctor.name} is booked for "
            f"{scheduled_date} at {scheduled_time}. "
            f"Join via Google Meet: {meet_link}"
        ),
        data    = {"meet_link": meet_link, "consultation_id": str(consultation.id)},
    )

    if doctor.user:
        Notification.objects.create(
            user    = doctor.user,
            type    = "new_consultation",
            message = (
                f"New consultation with {patient_name} scheduled for "
                f"{scheduled_date} at {scheduled_time}. "
                f"Join via Google Meet: {meet_link}"
            ),
            data    = {"meet_link": meet_link, "consultation_id": str(consultation.id)},
        )

    return Response({
        "consultation": VideoConsultationSerializer(consultation).data,
        "meet_link":    meet_link,
        "calendar_url": meet_info.get("html_link", ""),
    })


# ─── My consultations ─────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_my_consultations(request):
    """
    GET /video-consultation/my-consultations

    Returns all consultations for the current user (patient OR doctor).
    """
    consultations = (
        VideoConsultation.objects
        .filter(Q(patient=request.user) | Q(doctor__user=request.user))
        .order_by("-created_at")
    )
    return Response({
        "consultations": VideoConsultationSerializer(consultations, many=True).data
    })


# ─── Consultation detail ──────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_consultation_detail(request, consultation_id):
    """
    GET /video-consultation/consultation/<consultation_id>

    Returns full consultation detail including the Google Meet link
    and (optionally) a 100ms HMS token if that integration is also active.
    """
    try:
        c = VideoConsultation.objects.get(id=consultation_id)
    except (VideoConsultation.DoesNotExist, ValueError):
        return Response({"error": "Consultation not found"}, status=status.HTTP_404_NOT_FOUND)

    is_doctor = c.doctor and c.doctor.user == request.user
    role      = "host" if is_doctor else "guest"
    token     = _generate_hms_token(c.room_id, request.user.id, role)

    return Response({
        "consultation":   VideoConsultationSerializer(c).data,
        # ── Google Meet (primary) ──────────────────────────────────────────
        "meet_link":      getattr(c, "meet_link", None),
        # ── 100ms HMS (legacy / optional) ─────────────────────────────────
        "auth_token":     token,
        "role":           role,
        "sdk_configured": bool(HMS_ACCESS_KEY and HMS_SECRET),
    })


# ─── Join consultation ────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join_consultation(request, consultation_id):
    """
    POST /video-consultation/join/<consultation_id>

    Marks the consultation as in_progress and returns the Meet link
    so the frontend can open it directly.
    """
    try:
        c = VideoConsultation.objects.get(id=consultation_id)
    except (VideoConsultation.DoesNotExist, ValueError):
        return Response({"error": "Consultation not found"}, status=status.HTTP_404_NOT_FOUND)

    is_doctor = c.doctor and c.doctor.user == request.user
    role      = "host" if is_doctor else "guest"
    token     = _generate_hms_token(c.room_id, request.user.id, role)

    if c.status == "scheduled":
        c.status = "in_progress"
        c.save(update_fields=["status"])

    return Response({
        # ── Google Meet (primary) ──────────────────────────────────────────
        "meet_link":      getattr(c, "meet_link", None),
        # ── 100ms HMS (optional) ──────────────────────────────────────────
        "auth_token":     token,
        "room_id":        c.room_id,
        "role":           role,
    })


# ─── Cancel consultation ──────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_consultation(request, consultation_id):
    """
    POST /video-consultation/cancel/<consultation_id>

    Cancels the consultation and removes the Google Calendar / Meet event
    so the slot becomes free again and attendees are notified.
    """
    try:
        c = VideoConsultation.objects.get(id=consultation_id)
    except (VideoConsultation.DoesNotExist, ValueError):
        return Response({"error": "Consultation not found"}, status=status.HTTP_404_NOT_FOUND)

    if c.status in ("completed", "cancelled"):
        return Response(
            {"error": f"Consultation is already {c.status}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Delete the Google Calendar event (sends cancellation email to attendees)
    calendar_event_id = getattr(c, "calendar_event_id", "")
    if calendar_event_id:
        delete_google_meet_event(calendar_event_id)

    c.status = "cancelled"
    c.save(update_fields=["status"])

    Notification.objects.create(
        user    = c.patient,
        type    = "consultation_cancelled",
        message = (
            f"Your consultation with Dr. {c.doctor_name} on "
            f"{c.scheduled_at.strftime('%d %b %Y at %H:%M')} has been cancelled."
        ),
    )

    return Response({"status": "cancelled"})


# ─── Reschedule consultation ──────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reschedule_consultation(request, consultation_id):
    """
    POST /video-consultation/reschedule/<consultation_id>

    Body:
        scheduled_date  – "YYYY-MM-DD"
        scheduled_time  – "HH:MM"

    Updates the Google Calendar event (sends new invite emails) and
    saves the new scheduled_at + meet_link on the consultation.
    """
    try:
        c = VideoConsultation.objects.get(id=consultation_id)
    except (VideoConsultation.DoesNotExist, ValueError):
        return Response({"error": "Consultation not found"}, status=status.HTTP_404_NOT_FOUND)

    if c.status in ("completed", "cancelled"):
        return Response(
            {"error": "Cannot reschedule a completed or cancelled consultation."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data           = request.data
    scheduled_date = data.get("scheduled_date", "")
    scheduled_time = data.get("scheduled_time", "")

    try:
        new_scheduled_at = timezone.make_aware(
            datetime.strptime(f"{scheduled_date} {scheduled_time}", "%Y-%m-%d %H:%M")
        )
    except Exception:
        return Response({"error": "Invalid date/time format."}, status=status.HTTP_400_BAD_REQUEST)

    calendar_event_id = getattr(c, "calendar_event_id", "")
    meet_info = update_google_meet_event(
        calendar_event_id=calendar_event_id,
        new_start_datetime=new_scheduled_at,
        duration_minutes=c.duration_min,
    )

    c.scheduled_at = new_scheduled_at
    if meet_info.get("meet_link"):
        c.meet_link = meet_info["meet_link"]
    c.save(update_fields=["scheduled_at", "meet_link"])

    Notification.objects.create(
        user    = c.patient,
        type    = "consultation_rescheduled",
        message = (
            f"Your consultation with Dr. {c.doctor_name} has been rescheduled to "
            f"{scheduled_date} at {scheduled_time}. "
            f"Meet link: {c.meet_link}"
        ),
        data    = {"meet_link": c.meet_link, "consultation_id": str(c.id)},
    )

    return Response({
        "consultation": VideoConsultationSerializer(c).data,
        "meet_link":    c.meet_link,
    })


# ─── End consultation ────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end_consultation(request, consultation_id):
    """
    POST /video-consultation/end/<consultation_id>

    Saves EMR data, creates lab orders, and creates an EMREncounter.
    The Meet link is NOT deleted here — call cancel if the session never happened.
    """
    try:
        c = VideoConsultation.objects.get(id=consultation_id)
    except (VideoConsultation.DoesNotExist, ValueError):
        return Response({"error": "Consultation not found"}, status=status.HTTP_404_NOT_FOUND)

    data                  = request.data
    c.status              = "completed"
    c.emr_data            = data.get("emr_data", {})
    c.biomarkers_ordered  = data.get("biomarker_codes", [])
    c.panels_ordered      = data.get("panel_ids", [])
    c.consultation_summary = data.get("notes", "")
    c.save()

    # ── Lab order ────────────────────────────────────────────────────────────
    lab_order_created = False
    if c.biomarkers_ordered or c.panels_ordered:
        panel = None
        if c.panels_ordered:
            panel = LabPanel.objects.filter(panel_id=c.panels_ordered[0]).first()
        if not panel:
            panel = LabPanel.objects.first()

        if panel:
            from .models import LabPartner
            partner = LabPartner.objects.first()
            if partner:
                LabOrder.objects.create(
                    order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}",
                    patient      = c.patient,
                    ordered_by   = request.user,
                    panel        = panel,
                    lab_partner  = partner,
                    status       = "ordered",
                    notes        = (
                        f"Consultation ID: {c.id}\n"
                        f"Biomarkers: {', '.join(c.biomarkers_ordered)}"
                    ),
                )
                lab_order_created = True

            Notification.objects.create(
                user    = c.patient,
                type    = "lab_order_placed",
                message = (
                    f"Dr. {request.user.get_full_name() or request.user.username} "
                    "has ordered your lab tests. Book your home sample collection."
                ),
            )

    # ── EMR Encounter ────────────────────────────────────────────────────────
    if data.get("emr_data"):
        emr_data       = data["emr_data"]
        subjective_text = emr_data.get("history_present_illness", "")
        if emr_data.get("allergies") or emr_data.get("existing_conditions"):
            subjective_text += f"\nAllergies: {emr_data.get('allergies', 'None')}"
            subjective_text += f"\nConditions: {', '.join(emr_data.get('existing_conditions', []))}"

        encounter = EMREncounter.objects.create(
            member          = c.patient,
            hcp             = request.user,
            encounter_type  = "video_consultation",
            chief_complaint = emr_data.get("chief_complaint", ""),
            subjective      = subjective_text,
            objective       = emr_data.get("current_medications", ""),
            assessment      = emr_data.get("clinical_notes", ""),
            plan            = emr_data.get("lifestyle_notes", ""),
            vitals          = emr_data.get("vitals", {}),
        )
        c.emr_encounter = encounter
        c.save(update_fields=["emr_encounter"])

    return Response({"status": "completed", "lab_order_created": lab_order_created})


# ─── Biomarker panels ────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_biomarker_panels(request):
    """
    GET /video-consultation/biomarker-panels

    Returns grouped biomarker panels for doctor selection during consultation.
    """
    from collections import defaultdict

    biomarkers         = BiomarkerDefinition.objects.filter(data_source="lab")
    grouped_biomarkers = defaultdict(list)
    for b in biomarkers:
        domain = b.domain or "General"
        grouped_biomarkers[domain].append({"code": b.code, "name": b.name})

    groups = [
        {
            "code":       domain.lower().replace(" ", "_"),
            "name":       f"{domain} Panel",
            "biomarkers": markers,
        }
        for domain, markers in grouped_biomarkers.items()
    ]

    panels = LabPanel.objects.filter(is_active=True)
    prebuilt_panels = [
        {
            "id":          p.panel_id,
            "name":        p.name,
            "markers":     len(p.tests_included),
            "description": p.description,
            "fasting":     True,
        }
        for p in panels
    ]

    if not groups:
        groups = [
            {
                "code": "metabolic",
                "name": "Metabolic Panel",
                "biomarkers": [
                    {"code": "fasting_glucose", "name": "Fasting Glucose"},
                    {"code": "hba1c",            "name": "HbA1c"},
                ],
            }
        ]

    return Response({
        "groups":          sorted(groups, key=lambda x: x["name"]),
        "prebuilt_panels": prebuilt_panels,
    })