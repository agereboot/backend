from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from Reboot_App.models import CareTeamMember, UserProfile, Role
import uuid

class Command(BaseCommand):
    help = "Seed default care team members and miscellaneous data"

    def handle(self, *args, **options):
        self.stdout.write("Seeding Care Team Members...")
        
        defaults = [
            {
                "name": "Dr. Priya Sharma", 
                "role": "Primary Physician", 
                "specialization": "Internal Medicine & Longevity", 
                "email": "dr.sharma@agereboot.care",
                "credits_per_session": 25
            },
            {
                "name": "Meera Patel, RD", 
                "role": "Nutritionist", 
                "specialization": "Sports Nutrition & Metabolic Health", 
                "email": "meera.p@agereboot.care",
                "credits_per_session": 15
            },
            {
                "name": "Vikram Singh", 
                "role": "Fitness Coach", 
                "specialization": "Strength & Conditioning", 
                "email": "vikram.s@agereboot.care",
                "credits_per_session": 10
            },
            {
                "name": "Dr. Ananya Rao", 
                "role": "Mental Health Counselor", 
                "specialization": "CBT & Stress Management", 
                "email": "dr.rao@agereboot.care",
                "credits_per_session": 20
            },
        ]

        for d in defaults:
            member, created = CareTeamMember.objects.get_or_create(
                email=d["email"],
                defaults=d
            )
            if created:
                self.stdout.write(f"Created {member.name}")
            else:
                self.stdout.write(f"Member {member.name} already exists")

        self.stdout.write(self.style.SUCCESS("Successfully seeded miscellaneous defaults"))
