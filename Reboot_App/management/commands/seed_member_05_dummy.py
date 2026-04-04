import random
import uuid
from datetime import datetime, timedelta, timezone
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from Reboot_App.models import (
    UserProfile, Role, Company, Location, Department,
    Challenge, ChallengeParticipant, HPSScore, BiomarkerResult,
    BiomarkerDefinition, CreditTransaction, UserBadge, BadgeCatalog,
    OrganSystem, MedicalCondition, WellnessProgramme, CreditBalance,
    Medication, MedicationLog, Appointment, AppointmentService
)

class Command(BaseCommand):
    help = 'Dumps dummy data for member_05 for dashboard_stats and organ_ages parity testing'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding dummy data for member_05...')

        # 1. Get member_05
        user = User.objects.filter(username='member_05').first()
        if not user:
            self.stdout.write(self.style.ERROR('User member_05 not found! Run seed_full_clinical_parity first.'))
            return

        now = datetime.now(timezone.utc)
        
        # 2. Ensure Organ Systems exist (Global)
        organs = [
            {
                "code": "cardio", "name": "Cardiovascular", "icon": "heart",
                "biomarkers": ["systolic_bp", "heart_rate_resting", "ldl"],
                "proxy_biomarkers": ["hrv"],
                "pillar_weights": {"BR": 0.5, "CA": 0.5},
                "conditions_risk": ["hypertension", "arrhythmia"],
                "suggested_tests": [{"test": "ECG", "credits": 50, "category": "Cardiac", "priority": "high"}]
            },
            {
                "code": "metabolic", "name": "Metabolic", "icon": "zap",
                "biomarkers": ["hba1c", "fasting_glucose"],
                "proxy_biomarkers": ["bmi"],
                "pillar_weights": {"BR": 0.7, "PF": 0.3},
                "conditions_risk": ["diabetes", "obesity"],
                "suggested_tests": [{"test": "Continuous Glucose Monitor", "credits": 150, "category": "Metabolic", "priority": "high"}]
            }
        ]
        for o in organs:
            OrganSystem.objects.update_or_create(code=o["code"], defaults=o)

        # 3. Ensure Badge Catalog (Global)
        badges = [
            {"code": "first_score", "name": "First Blood", "description": "Computed first HPS score", "icon": "award", "tier": "bronze", "category": "milestone"},
            {"code": "streak_7", "name": "Week Warrior", "description": "7 day activity streak", "icon": "flame", "tier": "silver", "category": "streak"}
        ]
        for b in badges:
            BadgeCatalog.objects.update_or_create(code=b["code"], defaults=b)

        # 4. User specific data for member_05
        # Set Age
        profile = user.profile
        profile.age = 42
        profile.streak_days = 15
        profile.save()

        # Credits
        bal, _ = CreditBalance.objects.get_or_create(user=user)
        bal.available = 750
        bal.save()

        CreditTransaction.objects.get_or_create(
            user=user, description="Initial Bonus", amount=100, type="bonus"
        )
        CreditTransaction.objects.get_or_create(
            user=user, description="Challenge Reward", amount=50, type="reward",
            created_at=now - timedelta(days=2)
        )

        # Badges
        UserBadge.objects.get_or_create(user=user, badge_code="first_score")

        # Challenges
        company = profile.company
        ch1, _ = Challenge.objects.get_or_create(
            name="Step Marathon", 
            company=company,
            defaults={"description": "Walk 100k steps", "target_value": 100000, "reward_credits": 200, "status": "active"}
        )
        ChallengeParticipant.objects.get_or_create(user=user, challenge=ch1, defaults={"progress": 45000})

        # HPS Score with pillars (Percentages)
        HPSScore.objects.update_or_create(
            user=user, 
            timestamp=now,
            defaults={
                "hps_final": 720.5,
                "hps_base": 700.0,
                "pillars": {
                    "BR": {"percentage": 75, "name": "Biological Resilience"},
                    "PF": {"percentage": 65, "name": "Physical Fitness"},
                    "CA": {"percentage": 82, "name": "Cardio Health"}
                },
                "tier": "AVERAGE",
                "algorithm_version": "v2.5",
                "audit_hash": str(uuid.uuid4())
            }
        )

        # Biomarkers
        bm_data = [
            ("systolic_bp", 125, "BR"),
            ("heart_rate_resting", 68, "BR"),
            ("ldl", 110, "BR"),
            ("hba1c", 5.4, "BR"),
            ("fasting_glucose", 92, "BR"),
            ("hrv", 55, "BR"),
            ("bmi", 24.2, "PF")
        ]
        for code, val, pill in bm_data:
            defn, _ = BiomarkerDefinition.objects.get_or_create(
                code=code, defaults={"name": code.replace("_", " ").title(), "pillar": pill, "unit": "unit"}
            )
            BiomarkerResult.objects.create(
                user=user, biomarker=defn, value=val, source="MANUAL", collected_at=now
            )
            # Add historical data for trends
            BiomarkerResult.objects.create(
                user=user, biomarker=defn, value=val * 1.05, source="SEED_DATA", collected_at=now - timedelta(days=30)
            )

        # 5. Health Overview Specifics
        # Conditions
        cond, _ = MedicalCondition.objects.get_or_create(
            user=user, code="HTN",
            defaults={
                "name": "Hypertension", "status": "attention", 
                "severity": "mild", "relevant_biomarkers": ["systolic_bp", "heart_rate_resting"]
            }
        )
        
        # Medications
        med, _ = Medication.objects.get_or_create(
            member=user, medication_name="Amlodipine",
            defaults={"dosage": "5mg", "frequency": "Daily", "status": "active", "diagnosis_code": "HTN"}
        )
        MedicationLog.objects.get_or_create(user=user, medication=med, date=now.date())

        # Appointments
        AppointmentService.objects.get_or_create(
            code="medical", defaults={"name": "Medical Consultation", "service_type": "clinical", "duration": 30}
        )
        Appointment.objects.get_or_create(
            member=user, appointment_type="medical",
            defaults={
                "member_name": "Member 05", "mode": "video", 
                "scheduled_at": now + timedelta(days=3), "status": "confirmed"
            }
        )

        self.stdout.write(self.style.SUCCESS('Successfully dumped comprehensive dummy data for member_05!'))
