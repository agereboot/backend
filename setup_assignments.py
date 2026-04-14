
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Reboot.settings')
django.setup()

from django.contrib.auth.models import User
from Reboot_App.models import CCAssignment, Role, UserProfile

def setup_test_data():
    # 1. Ensure clinical_admin exists
    admin_user, _ = User.objects.get_or_create(username='clinical_admin@agereboot.com', defaults={'email': 'clinical_admin@agereboot.com'})
    
    # Ensure they have a clinician-like role to pass _require_hcp
    clinician_role, _ = Role.objects.get_or_create(name='longevity_physician')
    admin_profile, _ = UserProfile.objects.get_or_create(user=admin_user)
    admin_profile.role = clinician_role
    admin_profile.save()

    # 2. Assign member5 to clinical_admin
    m5, _ = User.objects.get_or_create(username='member5', defaults={'email': 'member5@test.com'})
    CCAssignment.objects.get_or_create(cc=admin_user, member=m5, defaults={'role': 'longevity_physician'})

    # 3. Assign member4 to clinical_admin (or whomever the user is testing with)
    m4, _ = User.objects.get_or_create(username='member4', defaults={'email': 'member4@test.com'})
    CCAssignment.objects.get_or_create(cc=admin_user, member=m4, defaults={'role': 'longevity_physician'})

    print(f"Assigned member5 and member4 to {admin_user.username}")

if __name__ == "__main__":
    setup_test_data()
