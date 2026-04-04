import random
import uuid
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from Reboot_App.models import (
    Role, Company, Location, Department, UserProfile, HCPProfile,
    HPSScore, BiomarkerResult, BiomarkerDefinition, PlatformAnnouncement, EmployeeLeave,
    HelpdeskTicket, WearableConnection, NutritionLog, Notification,
    CreditBalance, PrivacySetting, PillarConfig, SupportTicket,
    OrganSystem, AppointmentService, Medication, MedicalCondition,
    Appointment, EMREncounter, LabOrder, LabPanel, LabPartner, Phlebotomist, SampleBooking
)

# ── SEED DATA CONSTANTS ────────────────────────────────────────

ROLES_TO_SEED = [
    ("longevity_physician", "physician_demo", "physician@agereboot.ai", "Longevity", "Physician"),
    ("fitness_coach", "fitness_coach_demo", "fitness@agereboot.ai", "Fitness", "Coach"),
    ("psychologist", "psychologist_demo", "psychology@agereboot.ai", "Psychology", "Expert"),
    ("nutritional_coach", "nutrition_coach_demo", "nutrition@agereboot.ai", "Nutrition", "Coach"),
    ("clinician", "clinician_demo", "clinician@agereboot.ai", "Clinical", "Specialist"),
    ("coach", "coach_demo", "coach@agereboot.ai", "Performance", "Coach"),
    ("medical_director", "medical_director_demo", "medical_director@agereboot.ai", "Medical", "Director"),
    ("clinical_admin", "clinical_admin_demo", "clinical_admin@agereboot.ai", "Clinical", "Admin"),
    ("corporate_hr_admin", "hr_admin_demo", "hr_admin@agereboot.ai", "HR", "Admin"),
    ("corporate_wellness_head", "wellness_head_demo", "wellness@agereboot.ai", "Wellness", "Head"),
    ("cxo_executive", "cxo_demo", "cxo@agereboot.ai", "Sarah", "CXO"),
    ("phlebotomist", "phlebotomist_demo", "phlebotomist@agereboot.ai", "Phlebotomy", "Tech"),
]

BIOMARKER_METRICS = {
    "hrv_rmssd": {"name": "HRV (RMSSD)", "unit": "ms", "pillar": "BR"},
    "resting_hr": {"name": "Resting Heart Rate", "unit": "bpm", "pillar": "BR"},
    "hscrp": {"name": "hs-CRP", "unit": "mg/L", "pillar": "BR"},
    "fasting_glucose": {"name": "Fasting Glucose", "unit": "mg/dL", "pillar": "BR"},
    "hba1c": {"name": "HbA1c", "unit": "%", "pillar": "BR"},
    "vo2_max": {"name": "VO2 Max", "unit": "ml/kg/min", "pillar": "PF"},
    "body_fat_pct": {"name": "Body Fat %", "unit": "%", "pillar": "PF"},
}

# ── SEED UTILITIES ──────────────────────────────────────────────

def _rand_normal(mean, sd, low=None, high=None):
    v = random.gauss(mean, sd)
    if low is not None: v = max(low, v)
    if high is not None: v = min(high, v)
    return round(v, 1)

class Command(BaseCommand):
    help = "Seeds the database with 12 specialized roles and dashboard dummy data."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Specialized Role Seed..."))
        now = timezone.now()
        
        # 1. Base Setup
        for r_name, _ in Role.ROLE_CHOICES: 
            Role.objects.get_or_create(name=r_name)
        roles = {r.name: r for r in Role.objects.all()}
        comp, _ = Company.objects.get_or_create(name="AgeReboot Demo Corp")
        loc, _ = Location.objects.get_or_create(company=comp, name="Headquarters")
        depts = {d: Department.objects.get_or_create(company=comp, name=d)[0] for d in ["Medical", "Coaching", "Admin", "Operations"]}

        panel, _ = LabPanel.objects.get_or_create(
            panel_id="advanced_longevity", 
            defaults={"name": "Advanced Longevity Panel", "category": "Longevity", "price": 2500, "turnaround_days": 3}
        )
        partner, _ = LabPartner.objects.get_or_create(
            id="LP-GL01", 
            defaults={"name": "Global Labs", "type": "reference_lab"}
        )

        # 2. Hero Employee (Target for most data)
        hero, _ = User.objects.get_or_create(username="demo_user")
        hero.email, hero.first_name, hero.last_name = "demo@agereboot.ai", "Demo", "Athlete"
        hero.password = make_password("demo-password-2026!")
        hero.save()
        UserProfile.objects.update_or_create(user=hero, defaults={"company": comp, "role": roles["employee"]})

        # 3. Create 12 Specialized Users
        seeded_users = {}
        for r_code, username, email, fname, lname in ROLES_TO_SEED:
            self.stdout.write(f"Creating role: {r_code} ({username})")
            user, _ = User.objects.get_or_create(username=username)
            user.email, user.first_name, user.last_name = email, fname, lname
            user.password = make_password("demo-password-2026!")
            user.save()
            
            # Use 'hr_admin' for administrative roles, 'employee' for providers
            sys_role = "hr_admin" if "admin" in r_code or "head" in r_code or "cxo" in r_code else "employee"
            UserProfile.objects.update_or_create(user=user, defaults={"company": comp, "role": roles[sys_role]})
            HCPProfile.objects.update_or_create(user=user, defaults={"role": r_code, "is_demo": True})
            seeded_users[r_code] = user

            # 4. Role-Specific Data Generation
            if r_code in ["longevity_physician", "clinician", "medical_director", "fitness_coach", "coach", "nutritional_coach", "psychologist"]:
                # Create Appointments
                for i in range(5):
                    Appointment.objects.create(
                        member=hero, member_name=hero.get_full_name(),
                        appointment_type="consultation",
                        scheduled_at=now + timedelta(days=i, hours=10),
                        status="scheduled" if i > 0 else "completed",
                        notes=f"Sample session for {r_code}"
                    )
            
            if r_code in ["longevity_physician", "clinician"]:
                EMREncounter.objects.create(
                    member=hero, hcp=user,
                    encounter_type="longevity_review",
                    subjective="Patient feeling energetic.",
                    assessment="Optimal progress observed.",
                    plan="Continue current protocol."
                )

            if r_code == "phlebotomist":
                phleb, _ = Phlebotomist.objects.get_or_create(user=user, defaults={"name": f"{fname} {lname}", "phone": "999-000-1111", "status": "active"})
                
                order = LabOrder.objects.create(
                    order_number=f"ORD-{random.randint(1000, 9999)}",
                    patient=hero, ordered_by=hero, # In reality ordered by a doc
                    panel=panel, lab_partner=partner,
                    status="ordered"
                )
                
                SampleBooking.objects.create(
                    patient=hero, lab_order=order,
                    preferred_date=now.date(),
                    preferred_slot="10 AM - 12 PM",
                    address_line="123 Wellness Way",
                    status="assigned"
                )

            if r_code in ["corporate_hr_admin", "corporate_wellness_head"]:
                EmployeeLeave.objects.create(
                    employee=hero, leave_type="sick",
                    start_date=now.date(), end_date=(now + timedelta(days=1)).date(),
                    status="pending", reason="Follow-up recovery"
                )
                SupportTicket.objects.create(
                    id=f"TKT-{random.randint(1000, 9999)}",
                    user=hero, user_name=hero.get_full_name(),
                    subject="Insurance Query", status="open"
                )

        self.stdout.write(self.style.SUCCESS("12 Specialized Roles Seeded Successfully!"))
