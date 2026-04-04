import uuid
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from Reboot_App.models import (
    BiomarkerDefinition, BiomarkerResult, HPSScore, UserProfile, Role, Company
)

class Command(BaseCommand):
    help = "Seed dummy data for CDSS suggestions"

    def add_arguments(self, parser):
        parser.add_argument('--member_email', type=str, help='Email of the member to seed data for')
        parser.add_argument('--create_hr', action='store_true', help='Create the HR Admin user if missing')

    def handle(self, *args, **options):
        member_email = options.get('member_email') or 'demo_member@agereboot.com'
        create_hr = options.get('create_hr')

        if create_hr:
            hr_email = 'corporate_hr_admin@agereboot.com'
            hr_user, created = User.objects.get_or_create(
                username='cooparte_demo_hrdmin',
                defaults={'email': hr_email, 'first_name': 'Demo', 'last_name': 'HR Admin'}
            )
            if created:
                hr_user.set_password('admin123')
                hr_user.save()
                self.stdout.write(self.style.SUCCESS(f"Created HR Admin: {hr_user.username}"))
            
            # Ensure profile has corporate role
            role_hr, _ = Role.objects.get_or_create(name='corporate_hr_admin')
            profile = hr_user.profile
            profile.role = role_hr
            profile.save()

        # 1. Get or Create Demo Member
        member, created = User.objects.get_or_create(
            username='demo_member',
            defaults={'email': member_email, 'first_name': 'Demo', 'last_name': 'Member'}
        )
        if created:
            member.set_password('member123')
            member.save()
            self.stdout.write(self.style.SUCCESS(f"Created Demo Member: {member.username}"))

        # 2. Ensure Biomarker Definitions exist
        definitions = [
            {"code": "hba1c", "name": "HbA1c", "pillar": "Metabolic", "unit": "%"},
            {"code": "ldl_cholesterol", "name": "LDL Cholesterol", "pillar": "Lipids", "unit": "mg/dL"},
            {"code": "triglycerides", "name": "Triglycerides", "pillar": "Lipids", "unit": "mg/dL"},
            {"code": "vitamin_d", "name": "Vitamin D", "pillar": "Nutritional", "unit": "ng/mL"},
        ]

        for d in definitions:
            BiomarkerDefinition.objects.get_or_create(
                code=d["code"],
                defaults={"name": d["name"], "pillar": d["pillar"], "unit": d["unit"]}
            )

        # 3. Create Triggering Results
        # Rules: HbA1c > 5.7, LDL > 130, Triglycerides > 150, Vitamin D < 40
        results = [
            ("hba1c", 6.2),
            ("ldl_cholesterol", 145.0),
            ("triglycerides", 185.0),
            ("vitamin_d", 28.0),
        ]

        now = timezone.now()
        for code, val in results:
            defn = BiomarkerDefinition.objects.get(code=code)
            BiomarkerResult.objects.create(
                user=member,
                biomarker=defn,
                value=val,
                source="LAB",
                collected_at=now - timezone.timedelta(days=2)
            )
        
        self.stdout.write(self.style.SUCCESS(f"Seeded 4 triggering biomarker results for {member.username}"))

        # 4. Create Low HPS Pillars
        pillars = {
            "Metabolic": {"percentage": 25, "score": 250}, # Critical (< 30)
            "Lipids": {"percentage": 45, "score": 450},    # Warning (< 50)
            "Fitness": {"percentage": 80, "score": 800},
            "Mindset": {"percentage": 70, "score": 700}
        }
        
        HPSScore.objects.create(
            user=member,
            hps_final=55.0,
            hps_base=50.0,
            pillars=pillars,
            tier="Silver",
            algorithm_version="1.0",
            timestamp=now
        )
        
        self.stdout.write(self.style.SUCCESS(f"Seeded low HPS profile for {member.username}"))
        self.stdout.write(self.style.SUCCESS(f"Member ID for API: {member.id}"))
