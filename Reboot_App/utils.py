import random
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

def generate_otp():
    return str(random.randint(10000, 99999))

def otp_expiry_time():
    return timezone.now() + timedelta(minutes=5)

def send_otp_email(user, otp):
    subject = "Email Verification OTP"
    message = f"Your OTP is {otp}. It is valid for 5 minutes."

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,  # ✅ sender fixed
        recipient_list=[user.email],
        fail_silently=False
    )
