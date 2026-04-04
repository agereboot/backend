import random
import uuid
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from Reboot_App.models import (
    CCProtocol, Medication, EMRAllergy, MedicalCondition, 
    VitalsLog, CarePlan, Roadmap, HPSScore, UserProfile
)

class Command(BaseCommand):
    help = "Seed EMR parity data for demo_user (Protocols, Meds, Allergies, Vitals, Roadmaps)"

    def handle(self, *args, **options):
        self.stdout.write("Seeding EMR Parity Data...")
        
        # 1. Get or create demo_user
        hero = User.objects.filter(username="demo_user").first()
        if not hero:
            self.stdout.write(self.style.WARNING("demo_user not found. Run seed_demo_data first."))
            return

        now = timezone.now()

        # 2. Seed Protocols (CCProtocol)
        protocols_data = [
            {"name": "Advanced NAD+ Optimization", "category": "Longevity", "duration_weeks": 12, "evidence_grade": "A"},
            {"name": "Circadian Rhythm Reset", "category": "Sleep", "duration_weeks": 4, "evidence_grade": "B"},
            {"name": "Zone 2 Cardiovascular Base", "category": "Fitness", "duration_weeks": 8, "evidence_grade": "A"},
            {"name": "Autophagy Induction Protocol", "category": "Metabolic", "duration_weeks": 6, "evidence_grade": "B"},
        ]
        protocols = []
        for p_data in protocols_data:
            p, _ = CCProtocol.objects.get_or_create(name=p_data["name"], defaults=p_data)
            protocols.append(p)
        self.stdout.write(f"  - Seeded {len(protocols)} CCProtocols")

        # 3. Seed Medical Conditions (Problems)
        conditions = [
            {"name": "Insulin Resistance", "code": "E11.7", "severity": "moderate", "status": "active"},
            {"name": "Dyslipidemia", "code": "E78.5", "severity": "mild", "status": "active"},
        ]
        for c_data in conditions:
            MedicalCondition.objects.get_or_create(
                user=hero, name=c_data["name"], 
                defaults={"code": c_data["code"], "severity": c_data["severity"], "status": c_data["status"], "diagnosed_date": now.date() - timedelta(days=365)}
            )
        self.stdout.write("  - Seeded Medical Conditions")

        # 4. Seed Medications (Prescriptions)
        meds = [
            {"name": "Metformin", "dosage": "500mg", "frequency": "Once daily with meal", "type": "drug"},
            {"name": "NMN", "dosage": "1000mg", "frequency": "Morning", "type": "supplement"},
        ]
        for m_data in meds:
            Medication.objects.get_or_create(
                member=hero, medication_name=m_data["name"],
                defaults={"dosage": m_data["dosage"], "frequency": m_data["frequency"], "medication_type": m_data["type"], "status": "active"}
            )
        self.stdout.write("  - Seeded Medications")

        # 5. Seed Allergies
        allergies = [
            {"allergen": "Penicillin", "reaction": "Hives", "severity": "moderate"},
            {"allergen": "Peanuts", "reaction": "Anaphylaxis", "severity": "severe"},
        ]
        for a_data in allergies:
            EMRAllergy.objects.get_or_create(
                member=hero, allergen=a_data["allergen"],
                defaults={"reaction": a_data["reaction"], "severity": a_data["severity"], "status": "active"}
            )
        self.stdout.write("  - Seeded EMRAllergies")

        # 6. Seed Vitals Logs
        for i in range(5):
            VitalsLog.objects.create(
                member=hero,
                vitals={
                    "systolic": 120 + i,
                    "diastolic": 80 + i,
                    "pulse": 65 + i,
                    "weight_kg": 75.0 - (i * 0.2)
                },
                recorded_at=now - timedelta(days=i * 7)
            )
        self.stdout.write("  - Seeded Vitals History")

        # 7. Seed HPS Scores (for delta calculation)
        hps_values = [780, 755, 740]
        for i, val in enumerate(hps_values):
            HPSScore.objects.create(
                user=hero,
                hps_final=val,
                hps_base=val-10,
                timestamp=now - timedelta(days=i * 30),
                algorithm_version="v3.2",
                tier="optimal",
                audit_hash=uuid.uuid4().hex
            )
        self.stdout.write("  - Seeded HPS History")

        # 8. Seed Care Plan
        CarePlan.objects.get_or_create(
            member=hero,
            title="Longevity Master Plan 2026",
            defaults={
                "hcp_name": "Dr. Sarah Clinician",
                "status": "active",
                "protocols": [
                    {"protocol_id": str(protocols[0].id), "name": protocols[0].name, "goals": ["Improve fasting insulin < 5.0", "NAD+ level > 40"]},
                    {"protocol_id": str(protocols[2].id), "name": protocols[2].name, "goals": ["Resting HR < 55", "VO2 Max > 50"]}
                ]
            }
        )
        self.stdout.write("  - Seeded Care Plan")

        # 9. Seed Roadmap
        Roadmap.objects.get_or_create(
            user=hero,
            title="Personal Longevity Path",
            defaults={
                "status": "active",
                "phases": [
                    {"name": "Phase 1: Baseline Reset", "duration": "4 weeks"},
                    {"name": "Phase 2: Mitochondrial Optimization", "duration": "12 weeks"}
                ]
            }
        )
        self.stdout.write("  - Seeded Health Roadmap")

        self.stdout.write(self.style.SUCCESS("EMR Parity Seeding Complete!"))
