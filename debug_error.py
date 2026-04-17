
import os
import django
import traceback
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Reboot.settings')
django.setup()

from Reboot_App.models import User, Appointment

def run_debug():
    member = User.objects.filter(role__name='member').first()
    admin = User.objects.filter(email='clinical_admin@agereboot.com').first()
    
    print(f"Using Member: {member}")
    print(f"Using Admin: {admin}")
    
    try:
        print("Attempting creation...")
        Appointment.objects.create(
            member=member,
            member_name=member.username,
            appointment_type='test',
            mode='test',
            scheduled_at=timezone.now(),
            assigned_hcp=admin,
            assigned_hcp_name=admin.username,
            reason='test'
        )
        print("SUCCESS! No error.")
    except Exception as e:
        print(f"CAUGHT ERROR: {type(e).__name__}")
        with open('fatal_error.txt', 'w') as f:
            f.write(traceback.format_exc())
        print("Traceback written to fatal_error.txt")

if __name__ == "__main__":
    run_debug()
