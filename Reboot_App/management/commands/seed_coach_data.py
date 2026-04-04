import uuid
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from Reboot_App.models import (
    Role, UserProfile, CCAssignment, CoachTask, Habit, 
    CBTModule, NutritionalProfile, FitnessProfile,
    TherapyProgram, MealPlan, SupplementStack, Challenge, ChallengeParticipant,
    Escalation, HCPProfile, HPSScore, BiomarkerResult, CrisisAlert,
    Company, Department, Location
)

class Command(BaseCommand):
    help = "Seed dummy data for Coach Platform (PFC, PSY, NUT)"

    def handle(self, *args, **options):
        # 1. Get or Create Roles
        roles = ["fitness_coach", "psychologist", "nutritional_coach", "clinician"]
        role_objs = {}
        for rname in roles:
            role_objs[rname], _ = Role.objects.get_or_create(name=rname)

        # 2. Create Coaches
        coaches = [
            {"username": "fitness_coach_demo", "email": "fitness@agereboot.com", "role": "fitness_coach"},
            {"username": "psych_coach_demo", "email": "psych@agereboot.com", "role": "psychologist"},
            {"username": "nutri_coach_demo", "email": "nutri@agereboot.com", "role": "nutritional_coach"},
            {"username": "clinician_demo", "email": "clinician@agereboot.com", "role": "clinician"},
        ]
        
        coach_users = {}
        for c in coaches:
            user, created = User.objects.get_or_create(
                username=c["username"],
                defaults={"email": c["email"], "first_name": c["username"].split('_')[0].capitalize()}
            )
            if created:
                user.set_password("coach123")
                user.save()
            
            profile = user.profile
            profile.role = role_objs[c["role"]]
            profile.save()
            
            # Create/Update HCPProfile
            hcp_profile, _ = HCPProfile.objects.get_or_create(user=user)
            hcp_profile.role = c["role"]
            hcp_profile.specialty = f"{c['role'].capitalize()} Specialist"
            hcp_profile.bio = f"I am a highly experienced {c['role']} dedicated to health optimization."
            hcp_profile.save()
            
            coach_users[c["role"]] = user
            self.stdout.write(self.style.SUCCESS(f"Coach {c['username']} ready."))

        # 3. Get Demo Member (ID 6 from previous steps)
        member = User.objects.filter(id=6).first()
        if not member:
            member = User.objects.create(username="member_5", email="member5@example.com")
            member.set_password("pass123")
            member.save()

        # 4. Create Assignments
        for role_name, coach in coach_users.items():
            if role_name != "clinician": # Clinician is slightly different
                CCAssignment.objects.get_or_create(
                    member=member,
                    cc=coach,
                    defaults={"role": role_name}
                )

        # 5. Seed Tasks
        CoachTask.objects.get_or_create(
            assigned_to=coach_users["fitness_coach"],
            member=member,
            title="Review 10k Steps Badge",
            defaults={
                "description": "Member reached 10k steps 7 days in a row.",
                "priority": "medium"
            }
        )
        CoachTask.objects.get_or_create(
            assigned_to=coach_users["psychologist"],
            member=member,
            title="PHQ-9 Follow-up",
            defaults={
                "description": "Member score dropped. Schedule check-in.",
                "priority": "high"
            }
        )

        # 6. Seed Habits
        Habit.objects.get_or_create(
            member=member,
            name="10,000 Steps",
            category="activity",
            assigned_by=coach_users["fitness_coach"]
        )
        Habit.objects.get_or_create(
            member=member,
            name="Evening Meditation",
            category="mindfulness",
            assigned_by=coach_users["psychologist"]
        )

        # 7. Seed CBT Modules
        cbt_mod, _ = CBTModule.objects.get_or_create(
            name="Cognitive Restructuring",
            category="CBT Core",
            defaults={"sessions": 8, "description": "Identify and challenge negative thought patterns."}
        )

        # 8. Seed Therapy Programs (PSY)
        TherapyProgram.objects.get_or_create(
            member=member,
            therapist=coach_users["psychologist"],
            name="Stress Relief 101",
            defaults={
                "type": "Stress Management",
                "duration_weeks": 4,
                "modules": ["Breathing", "Journaling", "Social Exposure"],
                "goals": ["Reduce avg cortisol", "Improve PSQI score"]
            }
        )

        # 9. Seed Meal Plans (NUT)
        MealPlan.objects.get_or_create(
            member=member,
            coach=coach_users["nutritional_coach"],
            name="Lean Muscle 7-Day Plan",
            defaults={
                "target_kcal": 2400,
                "macros": {"protein": 180, "carbs": 250, "fat": 70},
                "status": "active"
            }
        )

        # 10. Seed Challenges (PFC)
        company, _ = Company.objects.get_or_create(
            name="Demo Corp",
            defaults={"admin_email": "hr@agereboot.com", "industry": "Wellness"}
        )
        
        challenge, _ = Challenge.objects.get_or_create(
            name="Spring Step Count Challenge",
            company=company,
            defaults={
                "description": "Walk 10,000 steps daily for 30 days.",
                "challenge_type": "steps",
                "target_value": 300000,
                "start_date": timezone.now().date(),
                "created_by": coach_users["fitness_coach"],
                "status": "active"
            }
        )
        ChallengeParticipant.objects.get_or_create(
            user=member,
            challenge=challenge,
            defaults={"progress": 15} # 15% progress
        )

        # 11. Seed Escalations (Shared)
        Escalation.objects.get_or_create(
            member=member,
            coach=coach_users["fitness_coach"],
            defaults={
                "member_name": member.username,
                "coach_name": coach_users["fitness_coach"].username,
                "clinical_summary": "Member reported heart palpitations during exercise",
                "severity": "high",
                "category": "clinical_review",
                "status": "pending"
            }
        )

        # 12. Ensure HPS exist
        HPSScore.objects.get_or_create(
            user=member,
            defaults={
                "hps_final": 485,
                "pillars": {"physical_fitness": 82, "psychology": 78, "nutrition": 75},
                "tier": "ELITE"
            }
        )

        # 13. Ensure Profiles exist
        FitnessProfile.objects.get_or_create(member=member)
        NutritionalProfile.objects.get_or_create(member=member)

        # 14. Seed Crisis Alert
        CrisisAlert.objects.get_or_create(
            member=member,
            defaults={
                "type": "Low sleep + reported panic attack",
                "severity": "CRITICAL",
                "status": "active"
            }
        )

        self.stdout.write(self.style.SUCCESS(f"Full Coaching V2 data seeded for member {member.username}"))
