from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from Reboot_App.models import MemberMedicalHistory

class Command(BaseCommand):
    help = "Seed medical history for a member"

    def add_arguments(self, parser):
        parser.add_argument('--member_id', type=str, help='ID of the member to seed')
        parser.add_argument('--member_username', type=str, help='Username of the member to seed')

    def handle(self, *args, **options):
        member_id = options.get('member_id')
        member_username = options.get('member_username')

        if member_id:
            user = User.objects.filter(id=member_id).first()
        elif member_username:
            user = User.objects.filter(username=member_username).first()
        else:
            user = User.objects.filter(is_superuser=False).first()

        if not user:
            self.stdout.write(self.style.ERROR(f"Member not found."))
            return

        history, created = MemberMedicalHistory.objects.get_or_create(member=user)
        
        # Seed some data
        history.conditions = [
            {"condition": "Type 2 Diabetes", "diagnosed_year": 2021, "status": "stable"},
            {"condition": "Hyperlipidemia", "diagnosed_year": 2018, "status": "managed"}
        ]
        history.allergies = [
            {"allergen": "Penicillin", "reaction": "Hives", "severity": "Moderate"},
            {"allergen": "Peanuts", "reaction": "Anaphylaxis", "severity": "High"}
        ]
        history.surgical_history = [
            {"surgery": "Appendectomy", "year": 2010},
            {"surgery": "Knee Arthroscopy", "year": 2015}
        ]
        history.family_history = [
            {"relation": "Father", "condition": "Hypertension"},
            {"relation": "Mother", "condition": "Breast Cancer (Survivor)"}
        ]
        history.personal_history = {
            "smoking": "Never",
            "alcohol": "Occasional",
            "exercise": "3 times/week"
        }
        
        history.save()
        self.stdout.write(self.style.SUCCESS(f"Seeded medical history for {user.username} (ID: {user.id})"))
