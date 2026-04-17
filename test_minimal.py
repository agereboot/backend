
import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Reboot.settings')
django.setup()

from Reboot_App.models import User, Appointment

def check_creation():
    member = User.objects.filter(role__name='member').first()
    admin = User.objects.filter(email='clinical_admin@agereboot.com').first()
    
    try:
        print("Creating minimal appointment...")
        a = Appointment()
        a.member_id = member.id
        a.member_name = member.username
        a.scheduled_at = timezone.now()
        a.reason = "Test"
        a.save()
        print(f"Success! ID: {a.id}")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_creation()
