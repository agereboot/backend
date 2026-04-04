import json
from django.core.management.base import BaseCommand
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from Reboot_App.models import VideoConsultation, BiomarkerDefinition, LabPanel
from Reboot_App.views_video_consultation import (
    get_available_slots, book_consultation, get_my_consultations,
    get_consultation_detail, end_consultation, get_biomarker_panels
)
import uuid

class Command(BaseCommand):
    help = "Verify Video Consultation APIs"

    def handle(self, *args, **options):
        from Reboot_App.models import CareTeamMember
        client = APIClient()
        user, _ = User.objects.get_or_create(username="test_patient", email="patient@test.com")
        doctor_user, _ = User.objects.get_or_create(username="test_doctor", email="doctor@test.com")
        
        # Link doctor to CareTeamMember
        doctor, _ = CareTeamMember.objects.get_or_create(
            name="Test Doctor",
            defaults={"role": "Doctor", "specialization": "Longevity", "email": "doctor@test.com", "user": doctor_user}
        )
        
        client.force_authenticate(user=user)
        
        # 1. Test Available Slots
        response = client.get(f"/api/video-consultation/available-slots/{doctor.id}")
        self.stdout.write(f"GET available-slots: {response.status_code}")
        
        # 2. Test Booking
        booking_data = {
            "doctor_id": str(doctor.id),
            "scheduled_date": "2026-05-10",
            "scheduled_time": "10:30",
            "reason": "Annual checkup",
            "duration_min": 30
        }
        response = client.post("/api/video-consultation/book", data=booking_data, format="json")
        self.stdout.write(f"POST book: {response.status_code}")
        if response.status_code != 200:
             self.stdout.write(f"Error: {response}")
             return
        consultation_id = response.data["consultation"]["id"]
        
        # 3. Test My Consultations
        response = client.get("/api/video-consultation/my-consultations")
        self.stdout.write(f"GET my-consultations: {response.status_code} (Found: {len(response.data['consultations'])})")

        # 4. Test Detail
        response = client.get(f"/api/video-consultation/consultation/{consultation_id}")
        self.stdout.write(f"GET consultation-detail: {response.status_code}")
        self.stdout.write(f"  Token present: {bool(response.data.get('auth_token'))}")

        # 5. Test End Consultation (Authenticate as Doctor)
        client.force_authenticate(user=doctor_user)
        end_data = {
            "emr_data": {"chief_complaint": "Fatigue", "clinical_notes": "Patient reports low energy"},
            "biomarker_codes": ["hba1c", "fasting_glucose"],
            "panel_ids": ["agereboot_longevity"],
            "notes": "Follow up in 3 months"
        }
        response = client.post(f"/api/video-consultation/end/{consultation_id}", data=end_data, format="json")
        self.stdout.write(f"POST end: {response.status_code}")
        
        # 6. Test Biomarker Panels (Dynamic)
        response = client.get("/api/video-consultation/biomarker-panels")
        self.stdout.write(f"GET biomarker-panels: {response.status_code}")
        if response.status_code == 200:
            self.stdout.write(f"  Groups: {len(response.data.get('groups', []))}, Prebuilt: {len(response.data.get('prebuilt_panels', []))}")

        self.stdout.write(self.style.SUCCESS("Verification complete!"))
