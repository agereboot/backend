import uuid
import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from Reboot_App.models import (
    LabPartner, LabPanel, DiagnosticCatalog, PharmacyCatalogItem,
    CCAlert, NFLETask, Escalation, CCReferral, CCAssignment, Role, UserProfile
)

class Command(BaseCommand):
    help = 'Seeds EMR and Care Coordination data with legacy Flask parity'

    def handle(self, *args, **options):
        self.stdout.write('Seeding EMR & CC Data...')

        # 1. Ensure Roles and HCP User
        hcp_role, _ = Role.objects.get_or_create(name="Longevity Physician")
        hcp_user, created = User.objects.get_or_create(
            username="dr_smith",
            defaults={
                "email": "smith@reboot.com",
                "first_name": "John",
                "last_name": "Smith",
                "is_staff": True
            }
        )
        if created:
            hcp_user.set_password("admin123")
            hcp_user.save()
        
        hcp_profile, _ = UserProfile.objects.get_or_create(
            user=hcp_user,
            defaults={"role": hcp_role, "phone_number": "1234567890"}
        )

        # 2. Ensure Members
        member_role, _ = Role.objects.get_or_create(name="Employee")
        members = []
        for i in range(1, 6):
            m_user, m_created = User.objects.get_or_create(
                username=f"member_{i}",
                defaults={
                    "email": f"member{i}@example.com",
                    "first_name": f"Member",
                    "last_name": str(i)
                }
            )
            if m_created:
                m_user.set_password("member123")
                m_user.save()
            
            UserProfile.objects.get_or_create(
                user=m_user,
                defaults={"role": member_role, "phone_number": f"900000000{i}"}
            )
            members.append(m_user)
            
            # Assign to HCP
            CCAssignment.objects.get_or_create(
                cc=hcp_user,
                member=m_user,
                defaults={"role": "primary_clinician"}
            )

        # 3. Lab Partner & Panels (Existing)
        partner, _ = LabPartner.objects.get_or_create(
            name="Thyrocare",
            defaults={"contact_person": "Thyrocare Admin", "is_active": True}
        )

        LAB_PANELS = {
            "CBC": "Complete Blood Count",
            "CMP": "Comprehensive Metabolic Panel",
            "LIPID": "Lipid Panel",
            "HBA1C": "Glycated Hemoglobin",
        }
        for code, name in LAB_PANELS.items():
            LabPanel.objects.get_or_create(
                panel_id=code,
                defaults={"name": name, "price": 1500.00}
            )

        # 4. CC Alerts
        ALERTS = [
            {"biomarker": "HbA1c", "value": 6.8, "severity": "CRITICAL", "interp": "High risk of insulin resistance. Immediate review needed."},
            {"biomarker": "LDL", "value": 175, "severity": "HIGH", "interp": "Elevated cardiovascular risk marker."},
            {"biomarker": "Vitamin D", "value": 18, "severity": "MEDIUM", "interp": "Suboptimal levels, supplement protocol suggested."},
        ]
        for i, alert in enumerate(ALERTS):
            CCAlert.objects.get_or_create(
                member=members[i % len(members)],
                biomarker=alert["biomarker"],
                status="open",
                defaults={
                    "cc": hcp_user,
                    "value": alert["value"],
                    "severity": alert["severity"],
                    "ai_interpretation": alert["interp"],
                    "aps_score": 85 - (i * 10),
                    "alert_type": "biomarker_threshold"
                }
            )

        # 5. NFLE Tasks
        TASKS = [
            {"task": "Review Metabolic Profile", "suggest": "Time-Restricted Eating"},
            {"task": "Cardio Training Review", "suggest": "Zone 2 Aerobic Base Building"},
        ]
        for i, task in enumerate(TASKS):
            NFLETask.objects.get_or_create(
                member=members[i % len(members)],
                task_description=task["task"],
                status="open",
                defaults={
                    "assigned_roles": ["longevity_physician", "fitness_coach"],
                    "priority": "high",
                    "protocol_suggestion": task["suggest"]
                }
            )

        # 6. Escalations
        Escalation.objects.get_or_create(
            member=members[0],
            status="pending",
            defaults={
                "coach_name": "Coach Mike",
                "category": "clinical_concern",
                "severity": "high",
                "clinical_summary": "Member reporting persistent fatigue and joint pain after starting new protocol.",
                "member_name": f"{members[0].first_name} {members[0].last_name}"
            }
        )

        self.stdout.write(self.style.SUCCESS('Successfully seeded EMR & CC data'))
