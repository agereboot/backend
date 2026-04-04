from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from Reboot_App.models import Role, UserProfile, Company, Location, Department

class Command(BaseCommand):
    help = 'Seed a user for every specified role'

    def handle(self, *args, **kwargs):
        roles_to_seed = [
            "longevity_physician", "fitness_coach", "psychologist",
            "nutritional_coach", "clinician", "coach", "medical_director", 
            "clinical_admin", "corporate_hr_admin", "corporate_wellness_head",
            "cxo_executive", "phlebotomist", "employee"
        ]

        # 1. Ensure basic infrastructure
        company, _ = Company.objects.get_or_create(name="AgeReboot Demo Corp")
        location, _ = Location.objects.get_or_create(company=company, name="Headquarters")
        dept, _ = Department.objects.get_or_create(company=company, name="Clinical Ops")

        self.stdout.write(self.style.SUCCESS('Ensured Company, Location, and Department exist.'))

        for role_name in roles_to_seed:
            # 2. Ensure Role object exists
            role, _ = Role.objects.get_or_create(name=role_name)

            # 3. Create User
            username = f"demo_{role_name}"
            email = f"{role_name}@agereboot.com"
            
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password="password123",
                    first_name=role_name.replace("_", " ").title(),
                    last_name="Demo"
                )
                
                # 4. Create UserProfile
                UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        "role": role,
                        "company": company,
                        "location": location,
                        "department": dept,
                        "status": "active",
                        "phone_number": "1234567890"
                    }
                )
                self.stdout.write(self.style.SUCCESS(f'Created user: {username} with role: {role_name}'))
            else:
                # Update existing profile role if needed
                user = User.objects.get(username=username)
                profile, created = UserProfile.objects.get_or_create(user=user)
                profile.role = role
                profile.save()
                self.stdout.write(self.style.WARNING(f'User {username} already exists. Updated role to {role_name}.'))

        self.stdout.write(self.style.SUCCESS('Successfully seeded all role-based users.'))
