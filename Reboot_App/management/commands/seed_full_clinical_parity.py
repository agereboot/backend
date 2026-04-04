import random
import uuid
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from Reboot_App.models import (
    Role, Company, Location, Department, UserProfile,
    CCAssignment, HPSScore, BiomarkerResult, VitalsLog,
    CCAlert, NFLETask, Escalation, CCReferral,
    CCSession, CCMessage, CCOverrideAudit,
    CCProtocol, CCPrescription, CarePlan,
    Appointment, EMREncounter, DiagnosticOrder, LabPanel, LabPartner,
    BiomarkerDefinition
)

class Command(BaseCommand):
    help = 'Comprehensive clinical data seeding for full parity testing'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting Comprehensive Data Seed...'))
        now = timezone.now()

        # 1. Base Setup
        company, _ = Company.objects.get_or_create(name="AgeReboot Demo Corp")
        location, _ = Location.objects.get_or_create(company=company, name="Headquarters")
        dept, _ = Department.objects.get_or_create(company=company, name="Clinical Ops")
        
        # Roles from choice list
        roles = {r.name: r for r in Role.objects.all()}
        
        # 2. HCPs (Existing from previous seed)
        hcp_roles = [
            "longevity_physician", "fitness_coach", "psychologist", "nutritional_coach",
            "clinician", "coach", "medical_director", "clinical_admin", "phlebotomist"
        ]
        hcps = {}
        for r in hcp_roles:
            user = User.objects.filter(username=f"demo_{r}").first()
            if user:
                hcps[r] = user
        
        # 3. Create 5 Members (Employees)
        members = []
        for i in range(1, 6):
            username = f"member_0{i}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": f"Member",
                    "last_name": f"Zero{i}",
                    "email": f"{username}@example.com"
                }
            )
            if created:
                user.set_password("password123")
                user.save()
            
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "role": roles["employee"],
                    "company": company,
                    "location": location,
                    "department": dept,
                    "status": "active"
                }
            )
            members.append(user)

        self.stdout.write(self.style.SUCCESS(f'Ensured {len(members)} Members exist.'))

        # 4. Assignments (Link HCPs to Members)
        for m in members:
            # Each member gets a physician, coach and nutritionist
            CCAssignment.objects.get_or_create(cc=hcps["longevity_physician"], member=m, role="primary_clinician")
            CCAssignment.objects.get_or_create(cc=hcps["fitness_coach"], member=m, role="primary_coach")
            CCAssignment.objects.get_or_create(cc=hcps["nutritional_coach"], member=m, role="nutritional_expert")

        # 5. Clinical Data (HPS, Biomarkers, Vitals)
        biomarker_types = [
            ("HbA1c", "%", "BR"), ("LDL", "mg/dL", "BR"), ("HRV", "ms", "BR"), 
            ("VO2Max", "ml/kg/min", "PF"), ("BodyFat", "%", "PF"), ("FastingGlucose", "mg/dL", "BR")
        ]

        for m in members:
            # 12 weeks of HPS
            for w in range(12):
                timestamp = now - timedelta(weeks=11-w)
                score = 650 + (w * 10) + random.randint(-20, 20)
                HPSScore.objects.create(
                    user=m,
                    hps_final=score,
                    hps_base=score - 20,
                    tier="OPTIMAL" if score > 750 else "AVERAGE" if score > 600 else "AT_RISK",
                    pillars={"BR": score-10, "PF": score+10, "CA": score},
                    timestamp=timestamp,
                    algorithm_version="v2.5",
                    audit_hash=str(uuid.uuid4())
                )

            # Core Biomarkers (past and current)
            for code_val, unit_val, pillar_val in biomarker_types:
                definition, _ = BiomarkerDefinition.objects.get_or_create(
                    code=code_val,
                    defaults={
                        "name": code_val,
                        "unit": unit_val,
                        "pillar": pillar_val,
                        "data_source": "manual"
                    }
                )
                # Baseline (3 months ago)
                BiomarkerResult.objects.create(
                    user=m, biomarker=definition, value=random.uniform(5, 10),
                    source="MANUAL", collected_at=now - timedelta(days=90)
                )
                # Current
                BiomarkerResult.objects.create(
                    user=m, biomarker=definition, value=random.uniform(5, 10),
                    source="MANUAL", collected_at=now
                )

            # Daily Vitals (30 days)
            for d in range(30):
                VitalsLog.objects.create(
                    member=m,
                    recorded_at=now - timedelta(days=29-d),
                    vitals={"steps": random.randint(5000, 15000), "sleep_score": random.randint(60, 100)}
                )

        # 6. Action Items (Alerts, Tasks, Escalations)
        critical_member = members[0]
        # Alert for Physician
        CCAlert.objects.create(
            member=critical_member, cc=hcps["longevity_physician"],
            biomarker="HbA1c", severity="CRITICAL", aps_score=95,
            ai_interpretation="Significant elevation detected. Recommend immediate review of metabolic protocol.",
            status="open"
        )
        # Task for Coach
        NFLETask.objects.create(
            member=critical_member, task_description="Review declining PF trend",
            priority="high", assigned_roles=["fitness_coach"],
            protocol_suggestion="Increase HIIT frequency", status="open"
        )
        # Escalation from Coach to Physician
        Escalation.objects.create(
            member=critical_member, coach=hcps["fitness_coach"], coach_name="Fitness Demo",
            severity="high", category="clinical_review",
            clinical_summary="Patient suffering from exercise-induced fatigue. Requesting medical review of biomarkers.",
            status="pending"
        )
        # Referral
        CCReferral.objects.create(
            member=members[1], reason="Advanced cardiovascular screening required.",
            referral_type="cardiology", status="pending",
            referred_to=hcps["longevity_physician"], referred_to_name="Longevity Demo"
        )

        # 7. Interactions (Sessions, Messages, Appointments)
        for m in members[:2]:
            # Past Session
            CCSession.objects.create(
                cc=hcps["longevity_physician"], member=m, session_type="initial_consultation",
                scheduled_at=now - timedelta(days=7), status="completed", notes="Patient set longevity goals."
            )
            # Upcoming Session
            CCSession.objects.create(
                cc=hcps["fitness_coach"], member=m, session_type="training_review",
                scheduled_at=now + timedelta(days=2), status="scheduled"
            )
            # Messages
            CCMessage.objects.create(
                sender=hcps["longevity_physician"], recipient=m, content="How are you feeling after the new protocol?"
            )
            CCMessage.objects.create(
                sender=m, recipient=hcps["longevity_physician"], content="Feeling much better, thank you!"
            )
            # Appointment
            Appointment.objects.create(
                member=m, assigned_hcp=hcps["longevity_physician"],
                appointment_type="clinical", mode="video",
                scheduled_at=now + timedelta(days=5), status="confirmed"
            )

        # 8. Care Coordination (Protocols, Care Plans)
        metabolic_prot, _ = CCProtocol.objects.get_or_create(
            name="Metabolic Health Foundation", category="Metabolic", duration_weeks=12
        )
        for m in members:
            CCPrescription.objects.create(
                member=m, clinician=hcps["longevity_physician"], protocol=metabolic_prot,
                protocol_name=metabolic_prot.name, category="Metabolic", status="active"
            )
            CarePlan.objects.create(
                member=m, hcp=hcps["longevity_physician"], title="Longevity Baseline Plan", status="active"
            )

        # 9. Labs
        partner, _ = LabPartner.objects.get_or_create(name="Precision Bioscience")
        panel, _ = LabPanel.objects.get_or_create(name="Comprehensive Longevity Panel", category="Longevity")
        DiagnosticOrder.objects.create(
            member=critical_member, ordered_by=hcps["longevity_physician"],
            test_name="Full Blood Count", category="Routine",
            status="ordered"
        )

        self.stdout.write(self.style.SUCCESS('Successfully seeded full clinical parity data!'))
