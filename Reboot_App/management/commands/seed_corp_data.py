import random
import uuid
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from Reboot_App.models import (
    Role, Company, Department, Location, UserProfile, 
    HPSScore, EHSScore, BRIScore, Intervention, 
    HREscalation, CareTeamEscalation, NudgeCampaign, 
    WellnessProgramme, FranchiseSeason, CompanyContract
)

class Command(BaseCommand):
    help = "Seed corporate module with dummy data using update_or_create (safe, no deletion)."

    def handle(self, *args, **options):
        self.stdout.write("Seeding Corporate Data (Safe Mode)...")
        
        # 1. Ensure Roles
        roles_to_create = ["corporate_hr_admin", "corporate_wellness_head", "employee", "longevity_physician", "clinician", "executive"]
        role_objs = {}
        for rname in roles_to_create:
            role, _ = Role.objects.get_or_create(name=rname)
            role_objs[rname] = role

        # 2. Company & Departments
        company, _ = Company.objects.get_or_create(name="AgeReboot Corp", defaults={"status": True})
        
        depts = ["Engineering", "HR", "Sales", "Clinical", "Marketing"]
        dept_objs = []
        for dname in depts:
            dept, _ = Department.objects.get_or_create(name=dname, company=company)
            dept_objs.append(dept)
            
        location, _ = Location.objects.get_or_create(name="Headquarters", company=company)

        # 3. Create Corporate Admin Users
        cha_user, created = User.objects.get_or_create(
            username="corp_admin", 
            defaults={"email": "admin@agereboot.corp", "first_name": "CHA", "last_name": "Admin"}
        )
        if created: cha_user.set_password("Admin@123"); cha_user.save()
        UserProfile.objects.update_or_create(user=cha_user, defaults={"company": company, "role": role_objs["corporate_hr_admin"], "department": dept_objs[1], "location": location})

        cwh_user, created = User.objects.get_or_create(
            username="wellness_head", 
            defaults={"email": "wellness@agereboot.corp", "first_name": "CWH", "last_name": "Head"}
        )
        if created: cwh_user.set_password("Wellness@123"); cwh_user.save()
        UserProfile.objects.update_or_create(user=cwh_user, defaults={"company": company, "role": role_objs["corporate_wellness_head"], "department": dept_objs[3], "location": location})

        # 4. Create Employees and Scores
        self.stdout.write("Ensuring 50 employees and their score history...")
        for i in range(1, 51):
            uname = f"emp_{i}"
            emp, created = User.objects.get_or_create(
                username=uname, 
                defaults={"email": f"emp{i}@agereboot.corp", "first_name": "Employee", "last_name": f"{i}"}
            )
            if created: emp.set_password("Emp@123"); emp.save()
            
            UserProfile.objects.update_or_create(
                user=emp, 
                defaults={
                    "company": company, 
                    "role": role_objs["employee"], 
                    "department": random.choice(dept_objs), 
                    "location": location,
                    "invite_status": "accepted"
                }
            )
            
            # Generate history (6 months)
            now = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            for m in range(6):
                # Use a deterministic timestamp for idempotency
                ts = now - timedelta(days=m*30)
                
                # HPS
                hps_val = random.randint(400, 950)
                tier = "ELITE" if hps_val >= 800 else "RESILIENCE" if hps_val >= 700 else "LONGEVITY" if hps_val >= 600 else "FOUNDATION"
                HPSScore.objects.get_or_create(user=emp, timestamp=ts, defaults={"hps_final": hps_val, "tier": tier})
                
                # EHS
                ehs_val = random.randint(20, 95)
                ehs_tier = "Champion" if ehs_val >= 80 else "Engaged" if ehs_val >= 60 else "Moderate" if ehs_val >= 40 else "At-Risk" if ehs_val >= 20 else "Critical"
                EHSScore.objects.get_or_create(user=emp, timestamp=ts, defaults={"score": ehs_val, "tier": ehs_tier})
                
                # BRI
                bri_val = random.randint(10, 85)
                bri_tier = "red" if bri_val >= 70 else "orange" if bri_val >= 50 else "yellow" if bri_val >= 30 else "green"
                BRIScore.objects.get_or_create(
                    user=emp, timestamp=ts, 
                    defaults={
                        "score": bri_val, "tier": bri_tier,
                        "physiological": random.uniform(20, 80), "behavioural": random.uniform(20, 80),
                        "psychological": random.uniform(20, 80), "organisational": random.uniform(10, 60)
                    }
                )

        # 5. Contract
        CompanyContract.objects.update_or_create(
            company=company, 
            defaults={
                "plan_tier": "Vitality", 
                "start_date": timezone.now().date() - timedelta(days=100),
                "end_date": timezone.now().date() + timedelta(days=265),
                "max_employees": 200,
                "pricing_model": "per_seat",
                "is_active": True
            }
        )

        # 6. Wellness Programmes
        progs = [
            ("Marathon Challenge", "challenge", "Movement"),
            ("Sleep Better Hub", "program", "Sleep"),
            ("Mindfulness Mornings", "workshop", "Mind"),
            ("Nutrition 101", "course", "Nutrition"),
        ]
        for name, ptype, dim in progs:
            WellnessProgramme.objects.get_or_create(
                name=name, 
                defaults={
                    "type": ptype, "target_dimension": dim, 
                    "duration_days": 30, "status": random.choice(["active", "upcoming"]),
                    "enrolled": random.randint(10, 40), "completed": random.randint(5, 10),
                    "created_by": cwh_user
                }
            )

        # 7. Franchise Season
        FranchiseSeason.objects.get_or_create(
            name="Season IV — 2026", 
            defaults={
                "status": "active", 
                "start_date": timezone.now().date() - timedelta(days=30),
                "end_date": timezone.now().date() + timedelta(days=60),
                "qualification_hps": 550, "qualification_pct_required": 60,
                "reward_pool_inr": 5000000, "created_by": cha_user
            }
        )

        # 8. Escalations
        random_emps = list(User.objects.filter(profile__company=company, profile__role__name='employee')[:10])
        for i in range(5):
            emp = random.choice(random_emps)
            HREscalation.objects.get_or_create(
                employee=emp, 
                reason="Declining HPS and low activity in last 14 days.",
                defaults={
                    "type": "engagement_concern", 
                    "recommended_action": "1-on-1 coaching session",
                    "status": "open", "severity": random.choice(["medium", "high", "critical"]),
                    "created_by": cha_user
                }
            )

        self.stdout.write(self.style.SUCCESS("✅ Corporate Seeding Complete (Safe Mode)!"))
