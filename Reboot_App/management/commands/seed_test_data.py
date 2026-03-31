from django.core.management.base import BaseCommand
import uuid
import random
from datetime import timedelta
from django.contrib.auth.models import User
from django.utils import timezone
from Reboot_App.models import (
    Role, UserProfile, BiomarkerDefinition, PillarConfig, 
    BiomarkerResult, HPSScore, Appointment, EMREncounter,
    CCAssignment, MemberMedicalHistory, Company
)

class Command(BaseCommand):
    help = 'Seeds database with test data for api endpoints'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting data seeding process...")
        
        # 1. Ensure Roles exist
        role_names = [
            ("super_admin", "Super Admin"),
            ("hr_admin", "HR Admin"),   
            ("employee", "Employee / Patient"),
            ("hcp", "Healthcare Provider"),
            ("care_coordinator", "Care Coordinator"),
            ("coach", "Health Coach")
        ]
        
        roles = {}
        for code, name in role_names:
            role, created = Role.objects.get_or_create(name=code)
            roles[code] = role
            if created:
                self.stdout.write(f"Created Role: {name}")

        # 1b. Ensure a Company exists for UserProfiles
        company, _ = Company.objects.get_or_create(name="AgeReboot Demo Corp")

        # 2. Create Users
        users_data = [
            {"username": "demo_patient", "email": "patient@agereboot.test", "role": "employee", "first_name": "Demo", "last_name": "Patient"},
            {"username": "dr_smith", "email": "dr.smith@agereboot.test", "role": "hcp", "first_name": "Sarah", "last_name": "Smith"},
            {"username": "cc_john", "email": "coordinator@agereboot.test", "role": "care_coordinator", "first_name": "John", "last_name": "Doe"},
        ]

        db_users = {}
        for u in users_data:
            user, created = User.objects.get_or_create(username=u["username"])
            if created:
                user.email = u["email"]
                user.first_name = u["first_name"]
                user.last_name = u["last_name"]
                user.set_password("Agereboot123!")
                user.save()
                self.stdout.write(f"Created User: {user.username}")
            db_users[u["username"]] = user

            # Ensure Profile exists
            profile, created = UserProfile.objects.get_or_create(user=user)
            if created:
                profile.role = roles.get(u["role"], roles["employee"])
                profile.company = company
                profile.save()

        patient = db_users["demo_patient"]
        doctor = db_users["dr_smith"]
        coordinator = db_users["cc_john"]

        # 3. Create Biomarker Definitions & Pillar Config
        pillar, _ = PillarConfig.objects.get_or_create(code="BR", defaults={"name": "Biomarker Resilience", "color": "#7B35D8"})
        
        bdefs = [
            {"code": "hba1c", "name": "HbA1c", "unit": "%", "direction": "lower_better"},
            {"code": "resting_hr", "name": "Resting Heart Rate", "unit": "bpm", "direction": "lower_better"},
            {"code": "vo2_max", "name": "VO2 Max", "unit": "mL/kg/min", "direction": "higher_better"}
        ]
        
        db_bdefs = {}
        for bd in bdefs:
            bdef, created = BiomarkerDefinition.objects.get_or_create(
                code=bd["code"],
                defaults={"name": bd["name"], "unit": bd["unit"], "direction": bd["direction"], "pillar": "BR"}
            )
            db_bdefs[bd["code"]] = bdef

        # 4. Generate BiomarkerResults for Patient
        self.stdout.write("Generating Biomarker Results...")
        for _ in range(5):
            BiomarkerResult.objects.create(
                user=patient,
                biomarker=db_bdefs["hba1c"],
                value=random.uniform(4.5, 6.5),
                source="LAB_SEED",
                collected_at=timezone.now() - timedelta(days=random.randint(1, 60))
            )
            BiomarkerResult.objects.create(
                user=patient,
                biomarker=db_bdefs["resting_hr"],
                value=random.uniform(55, 80),
                source="WEARABLE_SEED",
                collected_at=timezone.now() - timedelta(days=random.randint(1, 60))
            )

        # 5. Generate HPS Score
        self.stdout.write("Generating HPS Score...")
        HPSScore.objects.create(
            user=patient,
            hps_final=random.uniform(600, 850),
            hps_base=700,
            tier="VITALITY",
            timestamp=timezone.now()
        )

        # 6. Generate Appointment
        self.stdout.write("Generating Appointments...")
        Appointment.objects.create(
            member=patient,
            assigned_hcp=doctor,
            appointment_type="clinician_consult",
            mode="virtual",
            scheduled_at=timezone.now() + timedelta(days=2),
            status="scheduled"
        )

        # 7. Generate Medical History & CC Data
        self.stdout.write("Generating Medical History & CC Data...")
        
        # Use get_or_create to prevent UniqueConstraint failure
        history, created = MemberMedicalHistory.objects.get_or_create(member=patient)
        history.conditions=[{"name": "Pre-diabetes", "diagnosed_year": 2023}]
        history.save()
        
        CCAssignment.objects.create(
            member=patient,
            cc=coordinator,
            role="coach"
        )

        self.stdout.write("=========================================")
        self.stdout.write(self.style.SUCCESS("Successfully Seeded Demo Data!"))
        self.stdout.write("Test Patient Login == username: demo_patient | password: Agereboot123!")
        self.stdout.write("Test Doctor Login  == username: dr_smith | password: Agereboot123!")
